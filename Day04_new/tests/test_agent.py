"""build_agent와 GoalGuard 시험. 실제 server.py를 stdio 자식 프로세스로 띄우고 모델과 판정기는 가짜를 쓴다.

키·네트워크·유료 호출은 없다. conftest가 DAY04_ENV_FILE을 없는 파일로 바꾸고, build_agent가 그 값을
서버 자식 프로세스에 넘기므로 서버도 Day04_new/.env의 실제 키를 읽지 못한다.
"""
import asyncio
import json
import shutil
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from cap_lab.agent import SKILLS_DIR, AgentHandle, build_agent, server_argv
from cap_lab.decisions import DecisionError
from cap_lab.middleware import GoalGuard
from cap_lab.server.server import FaultPlan
from cap_lab.settings import Settings
from fakes import FakeChatModel, FakeDecider
from langchain_anthropic import ChatAnthropic
from langchain.agents.middleware import ToolCallRequest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import Field

MCP_TOOLS = {
    "start_interview", "record_answer", "get_session", "freeze_seed",
    "list_evidence", "read_evidence", "save_evidence",
}
SKILL_PATH = "/requirements-interview/SKILL.md"
USER = "목표는 「회의실 예약이 잡히면 참석자에게 알림 메일을 보내는 기능」입니다. 이 문장 그대로 인터뷰를 시작해 주세요."
GOAL = "회의실 예약이 잡히면 참석자에게 알림 메일을 보내는 기능"


def call(name: str, call_id: str, **args) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


async def run_agent(tmp_path: Path, model, skills_dir: Path = SKILLS_DIR, **options) -> tuple[list, AgentHandle]:
    """build_agent로 한 번 실행하고 (전체 메시지, AgentHandle)을 돌려준다. 서버의 DB와 근거 폴더는 tmp_path 아래다."""
    handle = await build_agent(
        Settings(), server_args=server_argv(tmp_path / "sessions.sqlite3", tmp_path / "evidence"),
        skills_dir=skills_dir, model=model, **options,
    )
    try:
        result = await handle.agent.ainvoke({"messages": [{"role": "user", "content": USER}]})
    finally:
        await handle.aclose()
    return result["messages"], handle


def tool_results(messages: list, name: str) -> list[ToolMessage]:
    return [m for m in messages if isinstance(m, ToolMessage) and m.name == name]


def server_calls(tmp_path: Path) -> list[str]:
    """서버가 받은 tools/call 이름. 서버가 모든 호출을 근거 폴더의 call-*.json으로 남긴다."""
    return [json.loads(path.read_text(encoding="utf-8"))["content"]["request"]["name"]
            for path in (tmp_path / "evidence").glob("*/call-*.json")]


def test_server_argv_uses_the_server_flags_and_absolute_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fault = FaultPlan(permission_denied=["save_evidence"], transient={"record_answer": 1})
    argv = server_argv("work/s.sqlite3", "evidence dir", gate="h1", threshold=0.75, fault=fault)
    assert argv[:8] == ["--db", str(tmp_path / "work" / "s.sqlite3"), "--evidence-dir", str(tmp_path / "evidence dir"),
                        "--gate", "h1", "--gate-threshold", "0.75"]
    assert argv[8] == "--fault" and FaultPlan.model_validate_json(argv[9]) == fault
    assert "--fault" not in server_argv(tmp_path / "s.sqlite3", tmp_path / "evidence")


class ToolViewRecorder(FakeChatModel):
    """bind_tools마다 defer_loading이 켜진(스키마를 아직 보내지 않는) 도구 이름도 기록한다."""

    deferred: list[set[str]] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self.deferred.append({
            tool.name for tool in tools
            if isinstance(tool, BaseTool) and (tool.extras or {}).get("defer_loading") is True
        })
        return super().bind_tools(tools, **kwargs)


def test_mcp_tools_are_deferred_until_the_skill_is_read(tmp_path):
    model = ToolViewRecorder.scripted([
        call("read_file", "c1", file_path=SKILL_PATH),
        AIMessage(content="Skill을 읽었습니다."),
    ])
    messages, handle = asyncio.run(run_agent(tmp_path, model))

    assert {tool.name for tool in handle.tools} == MCP_TOOLS
    before, after = model.bound_tools[0], model.bound_tools[1]
    assert model.deferred[0] == MCP_TOOLS
    assert MCP_TOOLS <= set(after) and model.deferred[1] == set()
    # 하위 에이전트(task)와 쓰기 도구는 처음부터 없다.
    assert set(before) - MCP_TOOLS == {"ls", "read_file", "glob", "grep"}
    assert tool_results(messages, "read_file")[0].status != "error"


class ClaudeRequestRecorder(ChatAnthropic):
    """실제 ChatAnthropic이 만들 요청 본문을 기록하고 전송 대신 scripted 답을 돌려준다. 네트워크를 쓰지 않는다."""

    script: list[AIMessage] = Field(default_factory=list)
    payloads: list[dict] = Field(default_factory=list)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.payloads.append(self._get_request_payload(messages, stop=stop, **kwargs))
        return ChatResult(generations=[ChatGeneration(message=self.script.pop(0))])


def inline_tools(payload: dict) -> set[str]:
    """대화 중간에 tool_addition 블록으로 공개한 도구 이름."""
    return {block["tool"]["definition"]["name"] for message in payload["messages"]
            if isinstance(message["content"], list)
            for block in message["content"] if block.get("type") == "tool_addition"}


def test_claude_request_keeps_mcp_schemas_deferred_until_the_skill_read_adds_them_inline(tmp_path):
    """수업 모델(claude-sonnet-5-5)은 mid_conversation_tools를 지원해 FakeChatModel과 다른 공개 경로를 탄다."""
    model = ClaudeRequestRecorder(model="claude-sonnet-5-5", api_key="offline-test", script=[
        call("read_file", "toolu_1", file_path=SKILL_PATH), AIMessage(content="끝."),
    ])
    asyncio.run(run_agent(tmp_path, model))

    first, second = model.payloads
    deferred = {tool["name"]: tool.get("defer_loading") for tool in first["tools"]}
    assert {name for name, flag in deferred.items() if flag is True} == MCP_TOOLS
    assert set(deferred) - MCP_TOOLS == {"ls", "read_file", "glob", "grep"}
    assert inline_tools(first) == set()
    assert inline_tools(second) == MCP_TOOLS


def guard_script() -> FakeChatModel:
    """Skill을 읽고 목표를 바꿔 start_interview를 부른 뒤 끝내는 모델."""
    return FakeChatModel.scripted([
        call("read_file", "c1", file_path=SKILL_PATH),
        call("start_interview", "c2", goal="회의실 예약 알림 기능 명세 만들기"),
        AIMessage(content="끝."),
    ])


def test_goal_guard_blocks_a_changed_goal_without_calling_the_server(tmp_path):
    decider = FakeDecider({"goal_preserved": 0.2})
    messages, handle = asyncio.run(run_agent(tmp_path, guard_script(), gate_h2=True, decider=decider))

    blocked = tool_results(messages, "start_interview")[0]
    assert json.loads(blocked.content) == {
        "success": False, "error": "goal_changed",
        "message": "사용자가 말한 목표 문장을 바꾸지 말고 그대로 goal에 넣으세요.",
    }
    assert server_calls(tmp_path) == []
    assert [asdict(d) for d in handle.goal_guard.decisions] == [
        {"tool": "start_interview", "probability": 0.2, "threshold": 0.5, "allowed": False, "error": "goal_changed"}]
    (state, questions), = decider.calls
    assert questions == ["goal_preserved"]
    assert USER in state and "회의실 예약 알림 기능 명세 만들기" in state


def test_goal_guard_lets_a_preserved_goal_reach_the_server(tmp_path):
    decider = FakeDecider({"goal_preserved": 0.9})
    messages, handle = asyncio.run(run_agent(tmp_path, guard_script(), gate_h2=True, decider=decider))

    started = tool_results(messages, "start_interview")[0]
    assert started.artifact["structured_content"]["goal"] == "회의실 예약 알림 기능 명세 만들기"
    assert server_calls(tmp_path) == ["start_interview"]
    assert [(d.allowed, d.error) for d in handle.goal_guard.decisions] == [(True, None)]


def test_goal_guard_fails_closed_when_the_decider_errors(tmp_path):
    decider = FakeDecider(error=DecisionError("fake: HTTP 503"))
    messages, handle = asyncio.run(run_agent(tmp_path, guard_script(), gate_h2=True, decider=decider))

    blocked = json.loads(tool_results(messages, "start_interview")[0].content)
    assert (blocked["success"], blocked["error"]) == (False, "decision_unavailable")
    assert server_calls(tmp_path) == []
    assert [asdict(d) for d in handle.goal_guard.decisions] == [
        {"tool": "start_interview", "probability": None, "threshold": 0.5, "allowed": False,
         "error": "decision_unavailable"}]


def sync_request(name: str, goal: str) -> ToolCallRequest:
    return ToolCallRequest(
        tool_call={"name": name, "args": {"goal": goal}, "id": "c9", "type": "tool_call"},
        tool=None, state={"messages": [HumanMessage(content=USER)]}, runtime=None,
    )


def test_goal_guard_sync_wrapper_blocks_and_treats_a_refusal_as_unavailable():
    ran: list[str] = []

    def handler(request):
        ran.append(request.tool_call["name"])
        return ToolMessage(content="ran", tool_call_id=request.tool_call["id"])

    low = GoalGuard(FakeDecider({"goal_preserved": 0.2}))
    assert json.loads(low.wrap_tool_call(sync_request("start_interview", "명세 만들기"), handler).content)["error"] \
        == "goal_changed"
    # script에 없는 질문은 FakeDecider가 refused로 답한다.
    refused = GoalGuard(FakeDecider({}))
    assert json.loads(refused.wrap_tool_call(sync_request("start_interview", GOAL), handler).content)["error"] \
        == "decision_unavailable"
    assert refused.decisions[0].probability is None
    # start_interview가 아닌 도구는 판정 없이 실행한다.
    assert low.wrap_tool_call(sync_request("get_session", GOAL), handler).content == "ran"
    assert ran == ["get_session"] and len(low.decisions) == 1


def test_file_tools_cannot_reach_the_data_folder(tmp_path):
    """Skill 폴더를 뿌리로 둔 백엔드라 data/는 상대·절대·가상 경로 어느 쪽으로도 보이지 않는다.

    대조: 뿌리를 Day04_new로 바꾸면 /data/cases.jsonl을 읽고 glob이 data/의 두 파일을 찾는다(작성 시 확인).
    """
    model = FakeChatModel.scripted([
        call("read_file", "c1", file_path="/../data/cases.jsonl"),
        call("read_file", "c2", file_path=str(SKILLS_DIR.parent / "data" / "cases.jsonl")),
        call("read_file", "c3", file_path="/data/cases.jsonl"),
        call("glob", "c4", pattern="**/*.jsonl"),
        AIMessage(content="끝."),
    ])
    messages, _ = asyncio.run(run_agent(tmp_path, model))

    reads, (found,) = tool_results(messages, "read_file"), tool_results(messages, "glob")
    assert [m.status for m in reads] == ["error", "error", "error"]
    assert found.content == "No files found"
    # cases.jsonl의 첫 사례 ID. 내용이 조금이라도 새면 보인다.
    assert not any("dev-01" in str(m.content) for m in messages)


def test_a_large_tool_result_is_not_written_into_the_skills_folder(tmp_path):
    """deepagents는 큰 도구 결과를 백엔드의 /large_tool_results/에 permissions 검사 없이 쓴다. build_agent는 그 기능을 끈다."""
    skills = tmp_path / "skills"
    shutil.copytree(SKILLS_DIR, skills)
    goal = "가" * 90_000  # 기본 한도 20000토큰(문자 4개 = 1토큰)을 넘는다.
    model = FakeChatModel.scripted([call("start_interview", "c1", goal=goal), AIMessage(content="끝.")])
    messages, _ = asyncio.run(run_agent(tmp_path, model, skills_dir=skills))

    assert [p.relative_to(skills).as_posix() for p in skills.rglob("*") if p.is_file()] \
        == ["requirements-interview/SKILL.md"]
    assert goal in str(tool_results(messages, "start_interview")[0].content)


class ConversationModel(FakeChatModel):
    """steps의 함수가 지금까지의 대화를 받아 다음 AIMessage를 만든다. 세션 ID처럼 실행 중에 생기는 값을 인자에 넣는다."""

    steps: list[Callable[[list[BaseMessage]], AIMessage]] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(generations=[ChatGeneration(message=self.steps.pop(0)(messages))])


def session_id_of(messages: list[BaseMessage]) -> str:
    started = [m for m in messages if isinstance(m, ToolMessage) and m.name == "start_interview"]
    return started[-1].artifact["structured_content"]["session_id"]


def test_server_elicitation_surfaces_as_an_interrupt_and_resume_records_the_users_text(tmp_path):
    elicited = "샘플 예약 1건을 넣으면 참석자 수만큼 메일 발송 기록이 생긴다."
    model = ConversationModel(messages=iter([]), steps=[
        lambda _: call("read_file", "c1", file_path=SKILL_PATH),
        lambda _: call("start_interview", "c2", goal=GOAL),
        lambda history: call("record_answer", "c3", session_id=session_id_of(history),
                             field="acceptance_criteria", answer="잘 되면 완료"),
        lambda _: AIMessage(content="완료 기준을 기록했습니다."),
    ])
    config = {"configurable": {"thread_id": "elicitation"}}

    async def scenario():
        handle = await build_agent(
            Settings(), skills_dir=SKILLS_DIR, model=model, checkpointer=InMemorySaver(),
            server_args=server_argv(tmp_path / "sessions.sqlite3", tmp_path / "evidence", gate="h1"),
            server_env={"DAY04_ALLOW_FAKE_DECIDER": "1", "DAY04_FAKE_DECIDER": '{"testability": 0.2}'},
        )
        try:
            updates = [update async for update in handle.agent.astream(
                {"messages": [{"role": "user", "content": USER}]}, config, stream_mode="updates")]
            (pending,), = [update["__interrupt__"] for update in updates if "__interrupt__" in update]
            (request,) = pending.value["requests"]
            answer = {request["key"]: {"action": "accept", "content": {"acceptance_criteria": elicited}}}
            final = await handle.agent.ainvoke(Command(resume={"responses": answer}), config)
        finally:
            await handle.aclose()
        return pending.value, final["messages"]

    interrupt, messages = asyncio.run(scenario())
    assert (interrupt["type"], interrupt["tool_name"]) == ("mcp_elicitation", "record_answer")
    assert "잘 되면 완료" in interrupt["requests"][0]["message"]
    recorded = tool_results(messages, "record_answer")[-1].artifact["structured_content"]
    assert recorded["answers"]["acceptance_criteria"] == elicited
