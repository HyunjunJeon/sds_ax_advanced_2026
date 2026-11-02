"""채점기가 가정한 도구 호출 모양을 실제 경로에서 확인한다.

실제 cap_lab 서버(stdio)와 MCP 어댑터를 거치고 모델·판정기만 가짜다. 키·네트워크·유료 호출은 없다.
오류 문자열을 손으로 쓰지 않는다. RunRecord.tool_calls에 실제로 들어온 값에 채점기를 적용한다.
관찰한 모양: 입력 검증 실패는 result가 텍스트 블록 목록([{"type": "text", "text": "Error executing tool
<이름>: 1 validation error for <이름>Arguments ..."}])이고 ok=False이다. 서버 업무 오류와 GoalGuard 차단은
result가 success=false dict이고 ok=False이다.
"""
import asyncio
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from cap_lab.experiment import Variant, run_case
from cap_lab.scorers import MCP_TOOLS, RunRecord, args_valid, tool_selection_ok
from cap_lab.settings import Settings
from fakes import FakeChatModel, FakeDecider
from test_agent import GOAL, SKILL_PATH, USER, call, run_agent, server_calls

END = AIMessage(content="끝.")


def drive(tmp_path: Path, script: list[AIMessage], expect: dict, **variant) -> RunRecord:
    case = {"id": "real", "turns": [USER], "expect": expect}
    decider = variant.pop("decider", None)
    return asyncio.run(run_case(
        case, variant=Variant("real", **variant), settings=Settings(), workdir=tmp_path, repeat=1,
        model=FakeChatModel.scripted([call("read_file", "r0", file_path=SKILL_PATH), *script, END]),
        decider=decider,
    ))


def the_call(record: RunRecord, call_id: str) -> dict:
    return next(c for c in record.tool_calls if c["id"] == call_id)


INVALID_CALLS = [
    pytest.param(call("start_interview", "bad", goal=123), "start_interview", "string_type", id="wrong_type"),
    pytest.param(call("start_interview", "bad"), "start_interview", "missing", id="missing_required"),
    pytest.param(
        call("record_answer", "bad", session_id="f" * 32, field="bogus", answer="x"),
        "record_answer", "literal_error", id="enum_outside_literal",
    ),
]


@pytest.mark.parametrize(("message", "tool", "kind"), INVALID_CALLS)
def test_a1_real_input_validation_failure_is_recorded_and_flagged(tmp_path, message, tool, kind):
    record = drive(tmp_path, [message], {})

    bad = the_call(record, "bad")
    assert record.error is None and bad["ok"] is False
    (block,) = bad["result"]
    assert block["type"] == "text"
    assert block["text"].startswith(f"Error executing tool {tool}: 1 validation error for {tool}Arguments")
    assert f"[type={kind}," in block["text"]
    score = args_valid(record)
    # 가짜 session_id 때문에 다른 이유로도 실패할 수 있으니 검증 오류가 원인으로 적혔는지까지 본다.
    assert score.value is False and "입력 검증 오류가 난 호출" in score.comment


def test_a1_valid_call_is_not_flagged(tmp_path):
    record = drive(tmp_path, [call("start_interview", "ok", goal=GOAL)], {})

    assert the_call(record, "ok")["ok"] is True
    assert args_valid(record).value is True


def test_a1_server_business_failure_is_not_an_input_validation_failure(tmp_path):
    record = drive(tmp_path, [call("get_session", "gone", session_id="f" * 32)], {})

    gone = the_call(record, "gone")
    assert gone["ok"] is False and gone["result"]["error"] == "session_not_found"
    # 서버가 만들지 않은 session_id 인자라는 다른 이유로 실패한다. 검증 오류로 읽히면 안 된다.
    assert "검증 오류" not in args_valid(record).comment


def test_a2_goal_guard_block_is_a_business_failure_that_never_reached_the_server(tmp_path):
    expect = {"must_call": ["start_interview"]}
    record = drive(
        tmp_path, [call("start_interview", "blocked", goal="다른 목표")], expect,
        gate_h2=True, decider=FakeDecider({"goal_preserved": 0.2}),
    )

    blocked = the_call(record, "blocked")
    assert blocked["ok"] is False
    assert blocked["result"]["success"] is False and blocked["result"]["error"] == "goal_changed"
    assert server_calls(tmp_path / "real-r1" / "real") == []
    assert [(d["gate"], d["allowed"]) for d in record.gate_decisions] == [("h2", False)]
    assert args_valid(record).value is True
    # 에이전트가 도구를 골랐는지를 보는 채점이라 차단된 시도도 선택으로 센다(서버 도달 여부는 보지 않는다).
    assert tool_selection_ok(record).value is True


def test_a3_recorded_tool_names_are_the_bare_mcp_names(tmp_path):
    script = [
        call("start_interview", "n1", goal=GOAL),
        call("get_session", "n2", session_id="f" * 32),
        call("list_evidence", "n3"),
    ]
    record = drive(tmp_path, script, {})

    names = [c["name"] for c in record.tool_calls if c["name"] != "read_file"]
    assert names == ["start_interview", "get_session", "list_evidence"]
    assert set(names) <= MCP_TOOLS
    assert all(not c["name"].startswith(("mcp", "functions")) and "__" not in c["name"] for c in record.tool_calls)


def test_a3_tool_names_match_before_the_recorder_through_build_agent(tmp_path):
    """build_agent가 돌려주는 도구와 ToolMessage 이름이 이미 접두어 없는 MCP 이름이다. 기록 단계가 바꾼 것이 아니다."""
    model = FakeChatModel.scripted([call("read_file", "r0", file_path=SKILL_PATH), call("list_evidence", "n1"), END])
    messages, handle = asyncio.run(run_agent(tmp_path, model))

    assert {tool.name for tool in handle.tools} == MCP_TOOLS
    assert [m.name for m in messages if m.type == "tool"] == ["read_file", "list_evidence"]
