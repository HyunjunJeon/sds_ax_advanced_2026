"""Day04_new Deep Agent 조립. Claude, MCP 서버(stdio 자식 프로세스)의 도구 7개, requirements-interview Skill, H2 GoalGuard.

MCP 도구는 Skill의 SKILL.md를 read_file로 읽기 전에는 모델에 스키마가 가지 않는다(defer_loading, tool_disclosure="skill").
tool_disclosure="upfront"는 Part 5 비교용으로 MCP 도구를 처음부터 모두 공개한다. Skill 폴더는 그대로 둔다.
에이전트의 파일 도구는 Skill 폴더만 읽고 쓰기는 거절한다. Day04_new/data/에는 닿지 않는다(오염 방지).
MCP 도구는 비동기 전용이다. 에이전트는 ainvoke/astream으로 실행한다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from deepagents import (
    FilesystemMiddleware,
    FilesystemPermission,
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)
from deepagents._models import get_model_identifier, get_model_provider
from deepagents.backends import FilesystemBackend
from fastmcp.client.transports import PythonStdioTransport
from langchain.mcp import MCPAdapter
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from cap_lab.decisions import DecisionBackend, make_decider
from cap_lab.middleware import DeferralSafePromptCaching, GoalGuard
from cap_lab.server.server import FaultPlan
from cap_lab.settings import ROOT, Settings, make_model

SERVER_SCRIPT = ROOT / "cap_lab" / "server" / "server.py"
SKILLS_DIR = ROOT / "skills"

# Day04/build_mcp/agent.py:121의 문장을 그대로 쓴다. 기준선(게이트 끔)이 Day04와 같은 지시를 받게 한다.
SYSTEM_PROMPT = (
    "사용자의 요청을 한국어로 처리한다. 관찰한 결과와 확인하지 못한 내용을 구분한다. "
    "사용자가 제시한 목표·제약·완료 기준을 임의로 추가하거나 바꾸지 않는다."
)
# Skill을 읽는 데 필요한 도구만 연다. write_file·edit_file·delete는 모델에 보이지 않는다.
_FILE_TOOLS = ["ls", "read_file", "glob", "grep"]
# cap_lab/settings.py:18의 변수 이름. 서버도 load_settings로 이 변수가 가리키는 .env에서 판정기 키를 읽는다.
_ENV_FILE_VARIABLE = "DAY04_ENV_FILE"


def server_argv(
    db: Path | str,
    evidence_dir: Path | str,
    *,
    gate: Literal["off", "h1"] = "off",
    threshold: float = 0.5,
    fault: FaultPlan | None = None,
    interface: Literal["rich", "plain"] = "rich",
) -> list[str]:
    """server.py 뒤에 붙일 인자. 스크립트 경로는 build_agent가 붙인다.

    서버는 cwd=Day04_new로 뜨므로 상대 경로는 호출한 쪽의 현재 폴더 기준 절대 경로로 바꿔 넘긴다.
    """
    argv = [
        "--db", str(Path(db).resolve()),
        "--evidence-dir", str(Path(evidence_dir).resolve()),
        "--gate", gate,
        "--gate-threshold", str(threshold),
    ]
    if fault is not None:
        argv += ["--fault", fault.model_dump_json()]
    return argv + ["--interface", interface]


@dataclass
class AgentHandle:
    """build_agent의 결과. 실행이 끝나면 aclose로 MCP 서버 자식 프로세스를 끝낸다."""

    agent: CompiledStateGraph
    tools: list[BaseTool]
    adapter: MCPAdapter
    goal_guard: GoalGuard | None

    async def aclose(self) -> None:
        # stdio 전송은 keep_alive가 기본이라 도구 호출 사이에 자식 프로세스가 살아 있다. close가 끝낸다.
        await self.adapter.client.close()


async def build_agent(
    settings: Settings,
    *,
    server_args: list[str],
    skills_dir: Path,
    gate_h2: bool = False,
    h2_threshold: float = 0.5,
    decider: DecisionBackend | None = None,
    model: BaseChatModel | None = None,
    checkpointer: Checkpointer = None,
    server_env: dict[str, str] | None = None,
    tool_disclosure: Literal["skill", "upfront"] = "skill",
) -> AgentHandle:
    """MCP 서버를 띄우고 Deep Agent를 만든다. model·decider를 주지 않으면 settings의 키로 만든다.

    interrupt(MCP elicitation)를 재개하려면 checkpointer와 config의 thread_id가 필요하다.
    tool_disclosure="skill"은 MCP 도구를 Skill을 읽은 뒤에 공개하고, "upfront"는 처음부터 공개한다.
    """
    # 키가 없으면 자식 프로세스를 띄우기 전에 멈춘다.
    model = model or make_model(settings)
    goal_guard = GoalGuard(decider or make_decider(settings), h2_threshold) if gate_h2 else None
    adapter = MCPAdapter(
        PythonStdioTransport(SERVER_SCRIPT, args=server_args, env=_server_env(server_env), cwd=str(ROOT))
    )
    try:
        tools = await adapter.list_tools()
        if tool_disclosure == "skill":
            tools = [_deferred(tool) for tool in tools]
        _disable_general_purpose_subagent(model)
        backend = FilesystemBackend(root_dir=skills_dir, virtual_mode=True)
        agent = create_deep_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            middleware=[
                # 큰 도구 결과·사용자 메시지를 백엔드 파일로 옮겨 쓰는 기능은 끈다. permissions 검사 없이
                # backend.write로 Skill 폴더에 쓰기 때문이다(deepagents/middleware/_message_eviction.py:275).
                FilesystemMiddleware(
                    backend=backend,
                    tools=_FILE_TOOLS,
                    tool_token_limit_before_evict=None,
                    human_message_token_limit_before_evict=None,
                ),
                # 이름이 같아 기본 캐싱 미들웨어 자리를 대신한다. 지연 도구에 cache_control이 붙으면 API가 400이다.
                DeferralSafePromptCaching(unsupported_model_behavior="ignore"),
                *([goal_guard] if goal_guard else []),
            ],
            skills=["/"],
            permissions=[FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")],
            backend=backend,
            checkpointer=checkpointer,
            name="requirements-evidence-agent",
        )
    except BaseException:
        await adapter.client.close()
        raise
    return AgentHandle(agent, tools, adapter, goal_guard)


def _deferred(tool: BaseTool) -> BaseTool:
    """defer_loading을 켠 사본. Skill이 metadata.include_tools에 이 이름을 적었으므로
    SkillsMiddleware가 그 SKILL.md를 read_file로 읽은 뒤에 스키마를 공개한다(deepagents/middleware/skills.py:986).
    """
    return tool.model_copy(update={"extras": {**(tool.extras or {}), "defer_loading": True}})


def _server_env(extra: dict[str, str] | None) -> dict[str, str]:
    """서버 자식 프로세스에 넘길 환경 변수. 키 값은 넘기지 않는다.

    mcp의 stdio 클라이언트가 PATH·HOME 등 안전한 변수만 물려준다(mcp/client/stdio.py:41).
    여기서는 .env 위치(DAY04_ENV_FILE)가 정해져 있으면 그대로 넘기고, 시험용 변수(extra)를 더한다.
    """
    forwarded = {_ENV_FILE_VARIABLE: os.environ[_ENV_FILE_VARIABLE]} if _ENV_FILE_VARIABLE in os.environ else {}
    return forwarded | (extra or {})


def _disable_general_purpose_subagent(model: BaseChatModel) -> None:
    """Day04/build_mcp/agent.py:47처럼 기본 하위 에이전트(task 도구)를 끈다.

    프로필은 프로세스 전체에 등록된다. 키는 deepagents가 미리 만든 모델의 프로필을 찾는 키와 같다
    (provider:identifier, identifier가 없으면 provider).
    """
    provider, identifier = get_model_provider(model), get_model_identifier(model)
    register_harness_profile(
        f"{provider}:{identifier}" if identifier else provider,
        HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)),
    )
