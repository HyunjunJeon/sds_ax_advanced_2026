"""한 턴을 시작하기 전에 Jev 팬아웃으로 모델과 검색을 고정한다.

채팅 모델이 kind/sources를 다시 고르지 못하게 한다.
허용되지 않은 검색·서브에이전트 호출은 여기서 차단한다.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, override

from deepagents.middleware._utils import append_to_system_message
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
    ToolCallRequest,
    TracePolicy,
    omit_payload,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from src.agent.config import with_thinking
from src.attachments import (
    attachment_note,
    attachment_state_files,
    attachment_system_block,
    extract_attached_files,
    latest_human_content,
    store_attachment_passages,
)
from src.schemas import TurnPlan

_SEARCH_TOOLS = frozenset({"search_documentation", "search_web"})
_SUBAGENT_TOOLS = frozenset({"task"})
# 예전 스레드에 남은 판단 카드. 모델 입력에서만 뺀다.
_PLAN_CARD_MARKER = "이 카드는 판단 로그입니다."


class TurnPlanMiddleware(AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]):
    """턴을 한 번 분류한 뒤 모델을 고정하고, 스킵된 도구를 막는다."""

    trace_policy = TracePolicy(process_inputs=omit_payload)

    def __init__(
        self,
        harness: Any,
        fast: BaseChatModel,
        powerful: BaseChatModel,
        backend: Any | None = None,
    ) -> None:
        self.harness = harness
        self.fast = fast
        self.powerful = powerful
        self.backend = backend
        # before_agent가 첨부 추출 결과를 wrap에 넘긴다.
        self._attachment_note = ""
        self._attachment_system = ""
        self._forced_search = False

    def _engine_label(self) -> str:
        engine = getattr(self.harness, "engine", "jev")
        return "Jev Closed Loop" if engine == "jev" else "LLM tool-call"

    @staticmethod
    def _latest_text(state: AgentState[ResponseT]) -> str:
        for message in reversed(state.get("messages", [])):
            if isinstance(message, HumanMessage):
                return _human_text(message.content)
        return ""

    def _selected_model(self) -> BaseChatModel:
        plan = self.harness.last_turn
        # before_agent보다 wrap이 먼저면 기본 모델로 통과한다.
        if plan is None:
            return with_thinking(self.fast, "low")
        base = self.fast
        if plan.model_name == self.harness.settings.powerful_model:
            base = self.powerful
        return with_thinking(base, plan.thinking_effort)

    @override
    def before_agent(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        del runtime
        self._attachment_note = ""
        self._attachment_system = ""
        self._forced_search = False
        if hasattr(self.harness, "last_attachments"):
            self.harness.last_attachments = []
        question = self._latest_text(state)
        files = extract_attached_files(latest_human_content(state))
        if not question and files:
            question = "첨부한 문서의 내용을 설명하세요."
        if not question:
            return None
        # 첨부는 Jev 이전에 풀어 둔다. plan_turn이 last_gated를 비운다.
        gated = []
        file_state: dict[str, dict[str, str]] = {}
        if files:
            gated = store_attachment_passages(self.backend, files)
            file_state = attachment_state_files(gated)
            self._attachment_note = attachment_note(files, gated)
            self._attachment_system = attachment_system_block(files, gated)
        # 판단은 하네스에만 둔다. 채팅에 카드를 넣으면 사용자에게
        # 내부 라우팅이 보이고, Claude는 assistant prefill로 거절한다.
        self.harness.plan_turn(question, attached=files)
        _annotate_plan(self.harness)
        if gated and hasattr(self.harness, "last_attachments"):
            # plan_turn이 last_gated를 비운 뒤에 첨부를 다시 붙인다.
            self.harness.last_attachments = gated
            self.harness.last_gated.extend(gated)
        # StateBackend.upload_files가 실패해도 read_file이 청크를 보게 한다.
        if file_state:
            return {"files": file_state}
        return None

    @override
    async def abefore_agent(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self.before_agent(state, runtime)

    def _with_plan(self, request: ModelRequest[ContextT]) -> ModelRequest[ContextT]:
        updated = request.override(
            model=self._selected_model(),
            messages=_messages_for_model(
                request.messages,
                attachment_note=self._attachment_note,
            ),
        )
        plan = self.harness.last_turn
        if plan is None:
            return updated
        extra = _plan_system_block(plan)
        if self._attachment_system:
            extra = f"{extra}\n{self._attachment_system}"
        return updated.override(
            system_message=append_to_system_message(
                updated.system_message,
                extra,
            )
        )

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        return self._maybe_force_search(handler(self._with_plan(request)))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[
            [ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]
        ],
    ) -> ModelResponse[ResponseT]:
        return self._maybe_force_search(await handler(self._with_plan(request)))

    def _maybe_force_search(
        self,
        response: ModelResponse[ResponseT],
    ) -> ModelResponse[ResponseT]:
        """Jev가 검색을 열었는데 모델이 건너뛰면 계획을 실행한다."""
        forced = forced_search_message(
            self.harness.last_turn,
            has_tool_calls=_response_has_tool_calls(response),
            has_evidence=_has_usable_evidence(self.harness),
            already_forced=self._forced_search,
        )
        if forced is None:
            return response
        self._forced_search = True
        return ModelResponse(result=[forced])

    def _skip_message(
        self,
        request: ToolCallRequest,
        reason: str,
    ) -> ToolMessage:
        tool_call = request.tool_call
        return ToolMessage(
            content=reason,
            tool_call_id=tool_call["id"],
            name=tool_call["name"],
        )

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        skipped = self._maybe_skip(request)
        if skipped is not None:
            return skipped
        return handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[
            [ToolCallRequest],
            Awaitable[ToolMessage | Command[Any]],
        ],
    ) -> ToolMessage | Command[Any]:
        skipped = self._maybe_skip(request)
        if skipped is not None:
            return skipped
        return await handler(request)

    def _maybe_skip(self, request: ToolCallRequest) -> ToolMessage | None:
        name = request.tool_call["name"]
        plan = self.harness.last_turn
        if plan is None:
            return None
        # 계획이 끈 검색을 채팅 모델이 다시 열지 못하게 한다.
        if name in _SEARCH_TOOLS and not plan.allow_search:
            return self._skip_message(
                request,
                f"{self._engine_label()} skipped retrieval. {plan.reason}",
            )
        if name == "search_documentation" and not plan.allowed_local:
            return self._skip_message(
                request,
                f"{self._engine_label()} skipped the local corpus. {plan.reason}",
            )
        if name == "search_web" and not plan.allowed_web:
            return self._skip_message(
                request,
                f"{self._engine_label()} skipped Exa. {plan.reason}",
            )
        # needs_subagents가 꺼진 턴만 task를 막는다.
        if name in _SUBAGENT_TOOLS and not plan.needs_subagents:
            return self._skip_message(
                request,
                f"{self._engine_label()} analysis=self_read. "
                "Read kept files yourself; do not spawn chunk-analyst.",
            )
        return None

    @override
    def after_agent(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        del runtime
        update = _grounding_update(self.harness, state)
        answer = _last_ai_text(state)
        if update and update.get("messages"):
            last = update["messages"][-1]
            if isinstance(last, AIMessage):
                answer = _human_text(last.content) or answer
        from src.observability import record_turn_answer

        record_turn_answer(getattr(self.harness, "last_turn", None), answer)
        return update

    @override
    async def aafter_agent(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self.after_agent(state, runtime)


def _plan_system_block(plan: TurnPlan) -> str:
    """턴 계획을 고정해 채팅 모델이 다시 분류하지 못하게 한다."""
    return (
        "## Turn plan (already decided — do not re-classify)\n\n"
        f"- kind: `{plan.kind}` (confidence={plan.kind_confidence:.2f})\n"
        f"- sources: `{plan.sources}`\n"
        f"- allow_search: `{plan.allow_search}`\n"
        f"- allowed_local: `{plan.allowed_local}`\n"
        f"- allowed_web: `{plan.allowed_web}`\n"
        f"- allowed_attachment: `{plan.allowed_attachment}`\n"
        f"- analysis: `{plan.analysis}`\n"
        f"- needs_subagents: `{plan.needs_subagents}`\n"
        f"- model: `{plan.model_name}`\n"
        f"- thinking: `{plan.thinking_effort}`\n"
        f"- {plan.reason}\n\n"
        "Honor `allowed_*`. Mid-turn judgments go through `ask_jev` / "
        "`judge_evidence`. Generation only: extract facts and write the answer."
    )


def _human_text(content: object) -> str:
    """첨부 파일·이미지 블록을 빼고 질문 텍스트만 남긴다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str) and item.strip():
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text and item.get("type", "text") == "text":
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content)


def _is_plan_card(message: object) -> bool:
    """UI 판단 카드인지. 채팅 모델에는 넘기지 않는다."""
    if not isinstance(message, AIMessage):
        return False
    content = message.content
    text = content if isinstance(content, str) else str(content)
    return _PLAN_CARD_MARKER in text


def _messages_for_model(
    messages: list,
    attachment_note: str = "",
) -> list:
    """판단 카드와 PDF 바이너리를 모델 입력에서 뺀다."""
    kept: list = []
    for item in messages:
        if _is_plan_card(item):
            continue
        if isinstance(item, HumanMessage) and _has_file_parts(item.content):
            text = _human_text(item.content)
            if attachment_note:
                text = f"{text}\n\n{attachment_note}".strip()
            if hasattr(item, "model_copy"):
                kept.append(item.model_copy(update={"content": text}))
            else:
                kept.append(HumanMessage(content=text))
            continue
        kept.append(item)
    return kept


def _has_file_parts(content: object) -> bool:
    if not isinstance(content, list):
        return False
    return any(
        isinstance(item, dict)
        and str(item.get("type") or "").lower() in {"file", "document"}
        for item in content
    )


def forced_search_message(
    plan: TurnPlan | None,
    *,
    has_tool_calls: bool,
    has_evidence: bool,
    already_forced: bool,
) -> AIMessage | None:
    """검색이 필요한데 도구가 없으면 Jev 계획을 실행하는 tool_call을 만든다."""
    if plan is None or already_forced or has_tool_calls or has_evidence:
        return None
    if not plan.allow_search:
        return None
    name = ""
    if plan.allowed_local:
        name = "search_documentation"
    elif plan.allowed_web:
        name = "search_web"
    if not name:
        return None
    return AIMessage(
        content="",
        tool_calls=[
            {
                "id": "forced-jev-search",
                "name": name,
                "args": {"query": plan.query},
                "type": "tool_call",
            }
        ],
    )


def _response_has_tool_calls(response: object) -> bool:
    messages = getattr(response, "result", None)
    if messages is None and isinstance(response, AIMessage):
        messages = [response]
    for message in messages or []:
        if getattr(message, "tool_calls", None):
            return True
    return False


def _annotate_plan(harness: Any) -> None:
    """Jev 선택을 Langfuse 현재 트레이스에 붙인다. 실패해도 턴은 계속한다."""
    plan = getattr(harness, "last_turn", None)
    if plan is None:
        return
    engine = getattr(harness, "engine", "jev")
    graph = "agent" if engine == "jev" else "baseline"
    from src.observability import annotate_turn

    annotate_turn(plan, graph=graph, engine=engine)


def _has_usable_evidence(harness: Any) -> bool:
    gated = [
        *getattr(harness, "last_gated", []),
        *getattr(harness, "last_attachments", []),
    ]
    return any(
        item.route in {"include", "conflicting_evidence"} for item in gated
    )


def _last_ai_text(state: dict[str, Any]) -> str:
    for message in reversed(state.get("messages", [])):
        if not isinstance(message, AIMessage):
            continue
        if getattr(message, "tool_calls", None):
            continue
        # Claude 답은 thinking·text 블록 목록일 수 있다. 그라운딩에는 text 블록만 넘긴다.
        text = message.text.strip()
        if text and _PLAN_CARD_MARKER not in text:
            return text
    return ""


def _grounding_update(harness: Any, state: dict[str, Any]) -> dict[str, Any] | None:
    """답 후 그라운딩. 실패하면 Jev 점수를 답 아래에 붙인다."""
    plan = getattr(harness, "last_turn", None)
    if plan is None or plan.kind == "other":
        return None
    needs = plan.allow_search or plan.allowed_attachment
    if not needs:
        return None
    answer = _last_ai_text(state)
    if not answer:
        return None
    gated = [
        item
        for item in getattr(harness, "last_gated", [])
        if item.route in {"include", "conflicting_evidence"}
    ]
    if not gated:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "Jev did not keep any evidence for this question. "
                        "I cannot answer from parametric knowledge."
                    )
                )
            ]
        }
    if not hasattr(harness, "check_grounding"):
        return None
    grounding = harness.check_grounding(plan.query, answer, gated)
    if grounding.ok:
        return None
    return {
        "messages": [
            AIMessage(
                content=(
                    f"{answer}\n\n"
                    f"—\nJev grounding: grounded={grounding.grounded:.2f} "
                    f"invents={grounding.invents_facts:.2f}. "
                    "이 답은 남긴 근거 밖에 사실을 넣은 것으로 판단되어 "
                    "그대로 신뢰하지 마세요."
                )
            )
        ]
    }
