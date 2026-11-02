"""수업 비교 변형 시험. Part 2(도구 인터페이스 rich/plain), Part 4(Streamable HTTP 실행), Part 5(도구 공개 skill/upfront).

키·유료 호출·외부 네트워크는 없다. 서버는 실제 server.py를 자식 프로세스로 띄우거나 create_server를 같은
프로세스에서 연결한다. 자식 프로세스에는 존재하지 않는 DAY04_ENV_FILE을 넘겨 Day04_new/.env의 키를 읽지 못하게 한다.
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from cap_lab.agent import SKILLS_DIR, build_agent, server_argv
from cap_lab.experiment import Variant, load_cases, run_case, run_experiment
from cap_lab.server.server import create_server
from cap_lab.settings import Settings
from fakes import FakeChatModel
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp_types import ElicitResult
from pydantic import Field
from test_experiment import FakeLangfuse

DAY04_NEW = Path(__file__).resolve().parents[1]
SERVER = DAY04_NEW / "cap_lab" / "server" / "server.py"
MCP_TOOLS = {
    "start_interview", "record_answer", "get_session", "freeze_seed",
    "list_evidence", "read_evidence", "save_evidence",
}


def spawn(folder: Path, *flags: str) -> StdioServerParameters:
    """folder 아래 DB·근거 폴더로 server.py를 stdio 자식 프로세스로 띄운다."""
    return StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER), "--db", str(folder / "sessions.sqlite3"), "--evidence-dir", str(folder / "evidence"), *flags],
        env={"DAY04_ENV_FILE": str(folder / "no-such.env")},
    )


async def listed_tools(params: StdioServerParameters) -> dict:
    async with Client(params) as client:
        return {tool.name: tool for tool in (await client.list_tools()).tools}


def argument_shape(tools: dict) -> dict:
    """도구마다 (인자 이름, 필수 인자). 두 인터페이스가 같은 인자를 받는지 비교한다."""
    return {name: (set(tool.input_schema["properties"]), tool.input_schema.get("required"))
            for name, tool in tools.items()}


def test_plain_interface_lists_the_same_tools_without_enums_annotations_or_output_schemas(tmp_path):
    rich = asyncio.run(listed_tools(spawn(tmp_path / "rich")))
    plain = asyncio.run(listed_tools(spawn(tmp_path / "plain", "--interface", "plain")))

    assert set(plain) == set(rich) == MCP_TOOLS
    assert argument_shape(plain) == argument_shape(rich)
    assert rich["record_answer"].input_schema["properties"]["field"]["enum"] == ["constraints", "acceptance_criteria"]
    assert all(tool.annotations is not None and tool.output_schema is not None for tool in rich.values())
    assert plain["record_answer"].input_schema["properties"]["field"] == {"title": "Field", "type": "string"}
    assert not [name for name, tool in plain.items() if "enum" in json.dumps(tool.input_schema)]
    assert [name for name, tool in plain.items() if tool.annotations or tool.output_schema] == []
    assert [name for name in MCP_TOOLS if len(plain[name].description) >= len(rich[name].description)] == []


def test_plain_interface_with_the_h1_gate_keeps_resolver_arguments_hidden_from_the_model(tmp_path):
    off = asyncio.run(listed_tools(spawn(tmp_path / "off", "--interface", "plain")))
    on = asyncio.run(listed_tools(spawn(tmp_path / "on", "--interface", "plain", "--gate", "h1")))

    assert on["record_answer"].input_schema == off["record_answer"].input_schema
    assert set(on["record_answer"].input_schema["properties"]) == {"session_id", "field", "answer"}
    assert on["record_answer"].annotations is None


GOAL = "매주 CSV 매출 자료를 요약하는 프로그램"
# 두 인터페이스 모두 인자 검증을 통과해 업무 코드까지 가는 잘못된 호출. 기대 오류 코드는 cap_lab/server/workflow.py에서 왔다.
BUSINESS_FAILURES = [
    ("record_answer", {"session_id": "no-such-session", "field": "constraints", "answer": "인터넷 없이 실행"},
     "session_not_found"),
    ("record_answer", {"session_id": "no-such-session", "field": "acceptance_criteria", "answer": "  "}, "empty_answer"),
    ("start_interview", {"goal": " "}, "empty_goal"),
    ("freeze_seed", {"session_id": "no-such-session"}, "session_not_found"),
]


def wire(result) -> dict:
    """tools/call 결과 중 클라이언트와 모델이 받는 부분."""
    return result.model_dump(mode="json", by_alias=True, exclude_none=True, include={"content", "structured_content", "is_error"})


async def call_in_process(folder: Path, interface: str, calls: list[tuple[str, dict]]) -> list:
    """create_server를 같은 프로세스에서 연결해 calls를 차례로 보낸다. 네트워크를 쓰지 않는다."""
    async with Client(create_server(folder / "sessions.sqlite3", folder / "evidence", interface=interface)) as client:
        return [await client.call_tool(name, arguments) for name, arguments in calls]


def test_invalid_calls_give_the_same_business_error_and_the_same_result_under_both_interfaces(tmp_path):
    calls = [(name, arguments) for name, arguments, _ in BUSINESS_FAILURES]
    rich = asyncio.run(call_in_process(tmp_path / "rich", "rich", calls))
    plain = asyncio.run(call_in_process(tmp_path / "plain", "plain", calls))

    assert [r.structured_content["error"] for r in plain] == [code for _, _, code in BUSINESS_FAILURES]
    assert [r.structured_content["success"] for r in plain] == [False] * len(BUSINESS_FAILURES)
    assert [wire(r) for r in plain] == [wire(r) for r in rich]


def test_a_successful_call_returns_the_same_text_and_structured_content_under_both_interfaces(tmp_path):
    """같은 DB와 근거 폴더를 두 인터페이스 서버가 차례로 읽는다. get_session은 다시 불러도 같은 결과다."""
    (started,) = asyncio.run(call_in_process(tmp_path, "rich", [("start_interview", {"goal": GOAL})]))
    lookup = [("get_session", {"session_id": started.structured_content["session_id"]})]
    (rich,) = asyncio.run(call_in_process(tmp_path, "rich", lookup))
    (plain,) = asyncio.run(call_in_process(tmp_path, "plain", lookup))

    assert rich.structured_content["goal"] == GOAL
    assert wire(plain) == wire(rich)


def test_an_out_of_enum_field_is_a_validation_error_under_rich_and_a_business_error_under_plain(tmp_path):
    """enum이 없으면 잘못된 field가 인자 검증을 지나 업무 코드에서 거절된다. Part 2 비교가 보는 차이다."""
    bad = [("record_answer", {"session_id": "no-such-session", "field": "goal", "answer": GOAL})]
    (rich,) = asyncio.run(call_in_process(tmp_path / "rich", "rich", bad))
    (plain,) = asyncio.run(call_in_process(tmp_path / "plain", "plain", bad))

    assert rich.is_error is True and rich.structured_content is None
    assert "validation error for record_answerArguments" in rich.content[0].text
    assert "literal_error" in rich.content[0].text
    assert plain.is_error is False
    assert (plain.structured_content["success"], plain.structured_content["error"]) == (False, "unknown_field")


def test_plain_interface_still_runs_the_h1_gate_and_records_the_criterion_the_user_gives(tmp_path, monkeypatch):
    """plain 사본도 Resolve 인자(판정·사용자 질문)를 그대로 넘긴다. 낮은 점수면 사용자 답이 기록된다."""
    monkeypatch.setenv("DAY04_ALLOW_FAKE_DECIDER", "1")
    monkeypatch.setenv("DAY04_FAKE_DECIDER", '{"testability": 0.2}')
    revised = "pytest tests/test_report.py가 통과한다"

    async def accept(context, params):
        return ElicitResult(action="accept", content={"acceptance_criteria": revised})

    async def scenario():
        server = create_server(tmp_path / "sessions.sqlite3", tmp_path / "evidence", gate="h1", interface="plain")
        async with Client(server, elicitation_callback=accept) as client:
            started = await client.call_tool("start_interview", {"goal": GOAL})
            session_id = started.structured_content["session_id"]
            await client.call_tool("record_answer", {"session_id": session_id, "field": "constraints", "answer": "없음"})
            return await client.call_tool("record_answer", {"session_id": session_id, "field": "acceptance_criteria",
                                                            "answer": "보기 좋게 나오면 완료"})

    result = asyncio.run(scenario()).structured_content
    assert (result["status"], result["answers"]["acceptance_criteria"]) == ("ready", revised)


# 두 번째 자식 프로세스에서 도는 HTTP 클라이언트. conftest가 이 프로세스의 IP 연결을 막기 때문이다.
# 서버가 아직 포트를 열지 않았으면 ConnectError만 다시 시도한다. 그 밖의 오류는 그대로 낸다.
HTTP_CLIENT = """
import asyncio, json, sys
from httpx2 import ConnectError
from mcp import Client

async def main(url):
    for _ in range(150):
        try:
            async with Client(url) as client:
                tools = sorted(tool.name for tool in (await client.list_tools()).tools)
                blank = await client.call_tool("start_interview", {"goal": " "})
                print(json.dumps({"tools": tools, "blank": blank.structured_content}))
                return
        except* ConnectError:
            pass  # 서버가 아직 포트를 열지 않았다. 잠시 뒤 다시 연결한다.
        await asyncio.sleep(0.2)
    sys.exit("30초 안에 서버에 연결하지 못했습니다.")

asyncio.run(main(sys.argv[1]))
"""


def free_loopback_port() -> int:
    """127.0.0.1의 빈 포트. conftest는 connect만 막으므로 bind는 된다."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_streamable_http_serves_the_same_tools_on_loopback(tmp_path):
    port = free_loopback_port()
    server = subprocess.Popen(
        [sys.executable, str(SERVER), "--db", str(tmp_path / "sessions.sqlite3"), "--evidence-dir",
         str(tmp_path / "evidence"), "--transport", "streamable-http", "--port", str(port)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
        env={**os.environ, "DAY04_ENV_FILE": str(tmp_path / "no-such.env")},
    )
    try:
        client = subprocess.run(
            [sys.executable, "-c", HTTP_CLIENT, f"http://127.0.0.1:{port}/mcp"],
            capture_output=True, text=True, timeout=90, stdin=subprocess.DEVNULL, check=False,
        )
    finally:
        server.terminate()
        _, server_log = server.communicate(timeout=30)

    assert client.returncode == 0, client.stderr + server_log
    listed = json.loads(client.stdout)
    assert listed["tools"] == sorted(MCP_TOOLS)
    assert (listed["blank"]["success"], listed["blank"]["error"]) == (False, "empty_goal")
    assert f"Uvicorn running on http://127.0.0.1:{port}" in server_log
    # HTTP로 온 호출도 stdio와 같이 근거 폴더의 호출 기록으로 남는다.
    assert len(list((tmp_path / "evidence").glob("*/call-*.json"))) == 1


@pytest.mark.parametrize("flags", [
    ("--transport", "sse"), ("--interface", "poor"), ("--port", "0"), ("--port", "65536"), ("--port", "http"),
])
def test_unknown_transport_interface_or_port_stops_the_server_at_startup(tmp_path, flags):
    completed = subprocess.run(
        [sys.executable, str(SERVER), "--db", str(tmp_path / "s.sqlite3"), *flags],
        capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, check=False,
        env={**os.environ, "DAY04_ENV_FILE": str(tmp_path / "no-such.env")},
    )
    assert completed.returncode == 2, completed.stderr
    assert f"argument {flags[0]}" in completed.stderr


class DisclosureRecorder(FakeChatModel):
    """bind_tools마다 defer_loading이 켜진(스키마를 아직 보내지 않는) 도구 이름도 기록한다."""

    deferred: list[set[str]] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self.deferred.append({
            tool.name for tool in tools
            if isinstance(tool, BaseTool) and (tool.extras or {}).get("defer_loading") is True
        })
        return super().bind_tools(tools, **kwargs)


def server_calls(folder: Path) -> list[str]:
    """서버가 실제로 받은 tools/call 이름. 서버가 모든 호출을 근거 폴더의 call-*.json으로 남긴다."""
    return [json.loads(path.read_text(encoding="utf-8"))["content"]["request"]["name"]
            for path in (folder / "evidence").glob("*/call-*.json")]


async def start_without_reading_the_skill(tmp_path: Path, tool_disclosure: str) -> tuple[DisclosureRecorder, list]:
    """Skill을 읽지 않고 바로 start_interview를 부르는 모델로 한 번 실행한다."""
    model = DisclosureRecorder.scripted([
        AIMessage(content="", tool_calls=[{"name": "start_interview", "args": {"goal": GOAL}, "id": "c1",
                                           "type": "tool_call"}]),
        AIMessage(content="끝."),
    ])
    handle = await build_agent(
        Settings(), server_args=server_argv(tmp_path / "sessions.sqlite3", tmp_path / "evidence"),
        skills_dir=SKILLS_DIR, model=model, tool_disclosure=tool_disclosure,
    )
    try:
        result = await handle.agent.ainvoke({"messages": [{"role": "user", "content": f"목표는 「{GOAL}」입니다."}]})
    finally:
        await handle.aclose()
    return model, [m for m in result["messages"] if isinstance(m, ToolMessage) and m.name == "start_interview"]


@pytest.mark.parametrize(("tool_disclosure", "deferred"), [("skill", MCP_TOOLS), ("upfront", set())])
def test_disclosure_changes_only_what_the_model_sees_and_a_called_tool_runs_under_both(
        tmp_path, tool_disclosure, deferred):
    """defer_loading은 스키마를 숨길 뿐 호출을 막지 않는다. 이름으로 부르면 Skill을 읽기 전에도 서버까지 간다."""
    model, (started,) = asyncio.run(start_without_reading_the_skill(tmp_path, tool_disclosure))

    assert MCP_TOOLS <= set(model.bound_tools[0])
    assert model.deferred[0] == deferred
    assert started.status == "success"
    assert server_calls(tmp_path) == ["start_interview"]


class ClaudeRequestRecorder(ChatAnthropic):
    """실제 ChatAnthropic이 만들 요청 본문을 기록하고 전송 대신 바로 답한다. 네트워크를 쓰지 않는다."""

    payloads: list[dict] = Field(default_factory=list)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.payloads.append(self._get_request_payload(messages, stop=stop, **kwargs))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="끝."))])


@pytest.mark.parametrize(("tool_disclosure", "deferred"), [("skill", MCP_TOOLS), ("upfront", set())])
def test_the_first_claude_request_defers_mcp_schemas_only_under_skill_disclosure(tmp_path, tool_disclosure, deferred):
    model = ClaudeRequestRecorder(model=Settings().model, api_key="offline-test")

    async def first_request() -> dict:
        handle = await build_agent(
            Settings(), server_args=server_argv(tmp_path / "sessions.sqlite3", tmp_path / "evidence"),
            skills_dir=SKILLS_DIR, model=model, tool_disclosure=tool_disclosure,
        )
        try:
            await handle.agent.ainvoke({"messages": [{"role": "user", "content": "MCP가 뭔가요?"}]})
        finally:
            await handle.aclose()
        (payload,) = model.payloads
        return payload

    sent = {tool["name"]: tool.get("defer_loading") for tool in asyncio.run(first_request())["tools"]}
    assert MCP_TOOLS <= set(sent)
    assert {name for name, flag in sent.items() if flag is True} == deferred


def test_server_argv_starts_the_agents_server_with_the_chosen_interface(tmp_path):
    async def record_answer_tool(interface: str) -> BaseTool:
        folder = tmp_path / interface
        handle = await build_agent(
            Settings(), server_args=server_argv(folder / "sessions.sqlite3", folder / "evidence", interface=interface),
            skills_dir=SKILLS_DIR, model=FakeChatModel.scripted([]),
        )
        await handle.aclose()
        return next(tool for tool in handle.tools if tool.name == "record_answer")

    rich, plain = asyncio.run(record_answer_tool("rich")), asyncio.run(record_answer_tool("plain"))
    assert rich.args["field"]["enum"] == ["constraints", "acceptance_criteria"]
    assert plain.args["field"] == {"title": "Field", "type": "string"}
    assert plain.description == "답변을 기록한다."


def test_run_case_starts_the_server_and_the_agent_the_variant_names(tmp_path):
    """잘못된 field 하나를 보내는 같은 모델을 두 변형으로 실행한다. 차이는 변형의 interface와 tool_disclosure에서만 온다."""
    case = next(case for case in load_cases(split="dev") if case["id"] == "dev-01")
    bad_field = AIMessage(content="", tool_calls=[{
        "name": "record_answer", "args": {"session_id": "no-such-session", "field": "goal", "answer": GOAL},
        "id": "c1", "type": "tool_call"}])

    def run(variant: Variant):
        model = DisclosureRecorder.scripted([bad_field, AIMessage(content="끝.")])
        record = asyncio.run(run_case(case, variant=variant, settings=Settings(), workdir=tmp_path, repeat=1, model=model))
        return model, record

    rich_model, rich = run(Variant("A"))
    plain_model, plain = run(Variant("P", interface="plain", tool_disclosure="upfront"))

    assert (rich.error, plain.error) == (None, None)
    assert (rich_model.deferred[0], plain_model.deferred[0]) == (MCP_TOOLS, set())
    (rich_call,), (plain_call,) = rich.tool_calls, plain.tool_calls
    assert rich_call["ok"] is False and "literal_error" in str(rich_call["result"])
    assert plain_call["ok"] is False
    assert (plain_call["result"]["success"], plain_call["result"]["error"]) == (False, "unknown_field")


@pytest.mark.parametrize(("variant", "expected"), [
    (Variant("A"), ("rich", "skill")),
    (Variant("P", interface="plain", tool_disclosure="upfront"), ("plain", "upfront")),
])
def test_run_metadata_records_the_interface_and_the_tool_disclosure(tmp_path, variant, expected):
    concept = {"id": "t-01", "split": "dev", "stage": "S1", "kind": "should_not_trigger", "turns": ["MCP가 뭔가요?"],
               "elicitation": {}, "fault": None, "requires": None,
               "expect": {"skill_read": False, "must_not_call": ["start_interview"]}}
    client = FakeLangfuse()
    asyncio.run(run_experiment(variant, [concept], 1, settings=Settings(), mirror_dir=tmp_path / "runs", client=client,
                               model=FakeChatModel.scripted([AIMessage(content="개념만 설명합니다.")])))

    (experiment,) = client.experiments
    assert (experiment["metadata"]["interface"], experiment["metadata"]["tool_disclosure"]) == expected
