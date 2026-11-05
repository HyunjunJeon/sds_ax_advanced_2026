"""H2 목표 유지 게이트(GoalGuard). start_interview의 goal 인자가 사용자가 말한 목표를 그대로 담는지
Decision API(Jev)의 Noul 질문 goal_preserved 하나로 묻는다.

확률이 문턱값보다 낮으면 도구를 부르지 않고 goal_changed를 돌려준다. 판정하지 못하면 도구를 부르지 않고
decision_unavailable을 돌려준다(fail-closed). 확률은 보정을 가정하지 않으며 기본 문턱값 0.5는 라벨로 재지 않은 자리값이다.
사용자 요청과 goal 문장은 선택한 Decision API 공급자에게 그대로 전송된다.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ToolCallRequest
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command

from cap_lab.decisions import DecisionBackend, DecisionError, Noul

GUARDED_TOOL = "start_interview"

GOAL_PRESERVED = Noul(
    name="goal_preserved",
    instructions=(
        "사용자 요청과 start_interview 호출의 goal 인자가 주어진다. goal 인자가 사용자가 말한 목표를 "
        "그대로 담고 있는지 판정하라. 줄이거나, 범위를 넓히거나 좁히거나, '명세 만들기'처럼 다른 일로 바꿔 "
        "해석했으면 거짓이다."
    ),
    true="goal 인자가 사용자가 말한 목표를 줄이거나 범위를 바꾸거나 재해석하지 않고 그대로 담고 있다.",
    false="goal 인자가 사용자의 목표를 줄였거나, 범위를 바꿨거나, '명세 만들기'처럼 다른 일로 재해석했다.",
)
GOAL_CHANGED_MESSAGE = "사용자가 말한 목표 문장을 바꾸지 말고 그대로 goal에 넣으세요."


@dataclass(frozen=True)
class GuardDecision:
    """GoalGuard의 판단 한 번. scorer와 Langfuse metadata가 dataclasses.asdict로 읽는다.

    판정하지 못했으면 probability가 None이다. error는 None(통과), goal_changed, decision_unavailable 중 하나다.
    """

    tool: str
    probability: float | None
    threshold: float
    allowed: bool
    error: str | None


class GoalGuard(AgentMiddleware):
    """start_interview 호출만 검사한다. 다른 도구는 그대로 실행한다. 판단마다 decisions에 하나씩 쌓는다."""

    def __init__(self, decider: DecisionBackend, threshold: float = 0.5) -> None:
        super().__init__()
        self.decider = decider
        self.threshold = threshold
        self.decisions: list[GuardDecision] = []

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        if request.tool_call["name"] != GUARDED_TOOL:
            return handler(request)
        refusal = self._check(request)
        return handler(request) if refusal is None else refusal

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        if request.tool_call["name"] != GUARDED_TOOL:
            return await handler(request)
        # Decision API 호출은 동기 HTTP다(최대 15초). 이벤트 루프를 막지 않도록 스레드에서 판정한다.
        refusal = await asyncio.to_thread(self._check, request)
        return await handler(request) if refusal is None else refusal

    def _check(self, request: ToolCallRequest) -> ToolMessage | None:
        """판단을 기록한다. 통과면 None, 막으면 도구 결과 대신 돌려줄 ToolMessage다."""
        state = (
            f"사용자 요청:\n{_user_request(request.state['messages'])}\n\n"
            f"start_interview의 goal 인자:\n{request.tool_call['args'].get('goal', '')}"
        )
        probability, failure = self._judge(state)
        if probability is not None and probability >= self.threshold:
            self.decisions.append(
                GuardDecision(GUARDED_TOOL, probability, self.threshold, True, None)
            )
            return None
        if probability is None:
            error = "decision_unavailable"
            message = f"{failure} start_interview를 호출하지 않았습니다. 판정기 설정을 확인한 뒤 다시 호출하세요."
        else:
            error, message = "goal_changed", GOAL_CHANGED_MESSAGE
        self.decisions.append(
            GuardDecision(GUARDED_TOOL, probability, self.threshold, False, error)
        )
        result = {"success": False, "error": error, "message": message}
        # 서버의 업무 오류와 같은 모양이다: success=false JSON, 상태는 기본값. artifact도 MCP 도구 결과와 같은 키에 둔다.
        return ToolMessage(
            content=json.dumps(result, ensure_ascii=False),
            tool_call_id=request.tool_call["id"],
            name=GUARDED_TOOL,
            artifact={"structured_content": result},
        )

    def _judge(self, state: str) -> tuple[float | None, str]:
        """(확률, 실패 이유). 판정하지 못했으면 확률이 None이고 이유를 담는다. 어떤 실패도 통과로 바꾸지 않는다."""
        try:
            verdict = self.decider.judge(state, [GOAL_PRESERVED]).verdicts[
                GOAL_PRESERVED.name
            ]
        except DecisionError as error:
            # DecisionError 메시지는 공급자 이름과 HTTP 상태만 담는다(cap_lab/decisions.py:81). 키와 state는 없다.
            return None, f"목표 유지 여부를 판정하지 못했습니다({error})."
        except Exception as error:
            # 내용을 모르는 예외라 메시지는 싣지 않고 종류만 전한다(cap_lab/server/gate.py:78과 같다).
            return (
                None,
                f"목표 유지 여부를 판정하지 못했습니다({type(error).__name__}).",
            )
        if verdict.probability is None:
            return None, "판정기가 goal_preserved 확률을 주지 않았습니다(refused)."
        return verdict.probability, ""


def _user_request(messages: Sequence[AnyMessage]) -> str:
    """첫 사용자 메시지의 글자. Skill 고정(pinned) 메시지는 사용자 메시지 뒤에 붙으므로 첫 HumanMessage가 사용자 요청이다."""
    for message in messages:
        if isinstance(message, HumanMessage):
            return message.text
    return ""


class DeferralSafePromptCaching(AnthropicPromptCachingMiddleware):
    """도구 캐시 표식(cache_control)을 defer_loading이 아닌 도구로 옮기는 프롬프트 캐싱.

    기본 구현은 도구 목록의 마지막 도구에 표식을 붙이는데(langchain_anthropic/middleware/prompt_caching.py:246),
    MCP 도구가 모두 defer_loading이면 마지막 도구가 지연 도구가 되어 Anthropic API가 400으로 거절한다
    ("cannot have both defer_loading=true and cache_control set"). 표식을 마지막 비지연 도구로 옮기면
    캐시와 Skill 공개 지연이 함께 유지된다. 비지연 도구가 없으면 표식을 도구에 붙이지 않는다.
    name이 기본 캐싱 미들웨어와 같아야 create_deep_agent가 그 자리를 대신 채운다(deepagents/graph.py:216-246).
    이름이 다르면 기본 것이 안쪽에 남아 표식을 다시 붙인다.
    """

    @property
    def name(self) -> str:
        return "AnthropicPromptCachingMiddleware"

    def _apply_caching(self, request: ModelRequest) -> ModelRequest:
        cached = super()._apply_caching(request)
        tools = cached.tools or []
        deferred = [
            tool for tool in tools if _is_deferred(tool) and _has_cache_control(tool)
        ]
        if not deferred:
            return cached
        cache_control = self._cache_control
        target = next(
            (
                tool
                for tool in reversed(tools)
                if isinstance(tool, BaseTool) and not _is_deferred(tool)
            ),
            None,
        )
        fixed = [
            _with_extras(
                tool, {k: v for k, v in tool.extras.items() if k != "cache_control"}
            )
            if tool in deferred
            else _with_extras(
                tool, {**(tool.extras or {}), "cache_control": cache_control}
            )
            if tool is target
            else tool
            for tool in tools
        ]
        return cached.override(tools=fixed)


def _is_deferred(tool: object) -> bool:
    return (
        isinstance(tool, BaseTool) and (tool.extras or {}).get("defer_loading") is True
    )


def _has_cache_control(tool: object) -> bool:
    return isinstance(tool, BaseTool) and "cache_control" in (tool.extras or {})


def _with_extras(tool: BaseTool, extras: dict) -> BaseTool:
    return tool.model_copy(update={"extras": extras})
