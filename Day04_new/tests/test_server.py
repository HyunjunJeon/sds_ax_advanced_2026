"""Day04_new MCP 서버 시험. server.py를 실제 stdio 자식 프로세스로 띄운다. 키·네트워크·유료 호출은 없다.

사용자 질문(elicitation)에는 mcp.Client의 elicitation_callback으로 답한다. 2026-07-28 프로토콜에서
서버는 InputRequiredResult를 돌려주고, Client가 콜백의 답을 실어 같은 tools/call을 다시 보낸다(MRTR).
자식 프로세스는 conftest의 네트워크 차단과 환경 변수를 물려받지 않는다. 그래서 모든 실행에
존재하지 않는 DAY04_ENV_FILE을 직접 넘겨 Day04_new/.env의 실제 키를 읽지 못하게 한다.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from cap_lab.decisions import DecisionError
from cap_lab.server import gate as gate_module
from fakes import FakeDecider
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp_types import ElicitResult

DAY04_NEW = Path(__file__).resolve().parents[1]
SERVER = DAY04_NEW / "cap_lab" / "server" / "server.py"
REFERENCE_VERIFY = DAY04_NEW.parent / "Day04" / "build_mcp" / "verify.py"

GOAL = "매주 CSV 매출 자료를 요약하는 프로그램"
CONSTRAINTS = "인터넷 없이 실행하고 CSV 원문을 수정하지 않는다."
TESTABLE = "샘플 CSV의 합계와 생성된 보고서의 합계가 일치한다."


def spawn(tmp_path: Path, *flags: str, fake: str | None = None) -> StdioServerParameters:
    """tmp_path 아래 DB·근거 폴더로 서버를 띄운다. fake를 주면 가짜 판정기를 켠다."""
    env = {"DAY04_ENV_FILE": str(tmp_path / "no-such.env")}
    if fake is not None:
        env |= {"DAY04_ALLOW_FAKE_DECIDER": "1", "DAY04_FAKE_DECIDER": fake}
    return StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER), "--db", str(tmp_path / "sessions.sqlite3"),
              "--evidence-dir", str(tmp_path / "evidence"), *flags],
        env=env,
    )


async def call(client: Client, tool: str, **arguments) -> dict:
    result = await client.call_tool(tool, arguments)
    assert not result.is_error, result.content
    return result.structured_content


def event_payloads(tmp_path: Path, session_id: str) -> list[dict]:
    """채점기가 읽는 근거 파일(event-*.json)의 payload를 순서대로 돌려준다."""
    folder = tmp_path / "evidence" / session_id
    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(folder.glob("event-*.json"))]
    return [record["content"]["payload"] for record in records]


def call_records(tmp_path: Path) -> list[dict]:
    """모든 세션 폴더와 _unassigned의 call-*.json content를 돌려준다."""
    return [json.loads(path.read_text(encoding="utf-8"))["content"]
            for path in (tmp_path / "evidence").glob("*/call-*.json")]


def test_reference_contract_happy_path_and_business_errors(tmp_path):
    async def scenario():
        async with Client(spawn(tmp_path)) as client:
            blank = await call(client, "start_interview", goal="  ")
            assert blank["error"] == "empty_goal"
            missing = await call(client, "get_session", session_id="not-a-real-session")
            assert (missing["success"], missing["error"]) == (False, "session_not_found")

            started = await call(client, "start_interview", goal=GOAL)
            session_id = started["session_id"]
            assert (started["status"], started["next_question"]["field"]) == ("draft", "constraints")
            first = await call(client, "record_answer", session_id=session_id, field="constraints", answer=CONSTRAINTS)
            assert first["next_question"]["field"] == "acceptance_criteria"
            early = await call(client, "freeze_seed", session_id=session_id)
            assert (early["error"], early["missing_fields"]) == ("seed_incomplete", ["acceptance_criteria"])

            ready = await call(client, "record_answer", session_id=session_id,
                               field="acceptance_criteria", answer=TESTABLE)
            assert (ready["status"], ready["seed"], ready["event_count"]) == ("ready", None, 3)
            duplicate = await call(client, "record_answer", session_id=session_id,
                                   field="acceptance_criteria", answer=TESTABLE)
            assert duplicate["event_count"] == 3

            frozen = await call(client, "freeze_seed", session_id=session_id)
            assert frozen["status"] == "frozen"
            assert (frozen["seed"]["goal"], frozen["seed"]["constraints"], frozen["seed"]["acceptance_criteria"]) \
                == (GOAL, CONSTRAINTS, TESTABLE)
            edit = await call(client, "record_answer", session_id=session_id, field="constraints", answer="제약 삭제")
            assert edit["error"] == "seed_frozen"
            after = await call(client, "get_session", session_id=session_id)
            assert (after["event_count"], after["seed"]) == (4, frozen["seed"])
            return session_id

    session_id = asyncio.run(scenario())
    assert [payload.get("answer") for payload in event_payloads(tmp_path, session_id)] \
        == [None, CONSTRAINTS, TESTABLE, None]
    records = call_records(tmp_path)
    assert all(isinstance(record["server_pid"], int) and record["server_pid"] != os.getpid() for record in records)
    assert {record["request"]["name"] for record in records} >= {"start_interview", "record_answer", "freeze_seed"}


async def listed_tools(params: StdioServerParameters) -> dict:
    async with Client(params) as client:
        return {tool.name: tool for tool in (await client.list_tools()).tools}


def hints(tool) -> dict:
    return tool.annotations.model_dump(by_alias=True, exclude_none=True)


def test_tools_list_publishes_annotations_and_get_session_is_not_read_only(tmp_path):
    tools = asyncio.run(listed_tools(spawn(tmp_path)))
    closed_write = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}
    assert hints(tools["start_interview"]) == {**closed_write, "idempotentHint": False}
    assert hints(tools["record_answer"]) == {**closed_write, "idempotentHint": True}
    assert hints(tools["get_session"]) == {**closed_write, "idempotentHint": True}
    assert hints(tools["freeze_seed"]) == {**closed_write, "idempotentHint": True}
    assert hints(tools["save_evidence"]) == {**closed_write, "idempotentHint": True}
    assert hints(tools["list_evidence"]) == {"readOnlyHint": True, "openWorldHint": False}
    assert hints(tools["read_evidence"]) == {"readOnlyHint": True, "openWorldHint": False}


def test_gate_on_opens_record_answer_to_the_world_without_new_model_visible_arguments(tmp_path):
    off = asyncio.run(listed_tools(spawn(tmp_path)))
    on = asyncio.run(listed_tools(spawn(tmp_path, "--gate", "h1", fake="error")))
    assert hints(on["record_answer"])["openWorldHint"] is True
    assert on["record_answer"].input_schema == off["record_answer"].input_schema
    assert set(on["record_answer"].input_schema["properties"]) == {"session_id", "field", "answer"}
    assert on["record_answer"].description == off["record_answer"].description
    assert {name: hints(tool) for name, tool in on.items() if name != "record_answer"} \
        == {name: hints(tool) for name, tool in off.items() if name != "record_answer"}


def test_permission_denied_tool_has_no_side_effect_but_is_recorded(tmp_path):
    fault = json.dumps({"permission_denied": ["save_evidence"]})

    async def scenario():
        async with Client(spawn(tmp_path, "--fault", fault)) as client:
            session_id = (await call(client, "start_interview", goal=GOAL))["session_id"]
            denied = await call(client, "save_evidence", session_id=session_id, title="계획", content="1. CSV를 읽는다.")
            again = await call(client, "save_evidence", session_id=session_id, title="계획", content="1. CSV를 읽는다.")
            listed = await call(client, "list_evidence", session_id=session_id)
            return session_id, denied, again, listed

    session_id, denied, again, listed = asyncio.run(scenario())
    assert (denied["success"], denied["error"]) == (False, "permission_denied")
    assert denied["message"].strip() and again == denied
    assert not [item for item in listed["evidence"] if item["kind"] == "artifact"]
    recorded = [record["result"]["structuredContent"]["error"] for record in call_records(tmp_path)
                if record["request"]["name"] == "save_evidence"]
    assert recorded == ["permission_denied", "permission_denied"]
    assert not list((tmp_path / "evidence" / session_id).glob("artifact-*.json"))


def test_transient_fault_fails_first_calls_without_recording_then_behaves_normally(tmp_path):
    fault = json.dumps({"transient": {"record_answer": 2}})

    async def scenario():
        async with Client(spawn(tmp_path, "--fault", fault)) as client:
            session_id = (await call(client, "start_interview", goal=GOAL))["session_id"]
            failures = [await call(client, "record_answer", session_id=session_id,
                                   field="constraints", answer=CONSTRAINTS) for _ in range(2)]
            between = await call(client, "get_session", session_id=session_id)
            recorded = await call(client, "record_answer", session_id=session_id, field="constraints", answer=CONSTRAINTS)
            return failures, between, recorded

    failures, between, recorded = asyncio.run(scenario())
    for failure in failures:
        assert (failure["success"], failure["error"], failure["retryable"]) == (False, "temporarily_unavailable", True)
    assert between["event_count"] == 1
    assert (recorded["success"], recorded["event_count"], recorded["answers"]) == (True, 2, {"constraints": CONSTRAINTS})


def test_fault_plan_with_unknown_tool_or_shape_stops_the_server_at_startup(tmp_path):
    for fault in ('{"transient": {"no_such_tool": 1}}', '{"transient": {"record_answer": -1}}',
                  '{"slow": ["get_session"]}', "not json"):
        completed = subprocess.run(
            [sys.executable, str(SERVER), "--db", str(tmp_path / "s.sqlite3"), "--evidence-dir", str(tmp_path / "e"),
             "--fault", fault],
            capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, check=False,
            env={**os.environ, "DAY04_ENV_FILE": str(tmp_path / "no-such.env")},
        )
        assert completed.returncode == 2, (fault, completed.stderr)
        assert "--fault 형식이 잘못되었습니다" in completed.stderr


VAGUE = "보고서가 보기 좋게 나오면 완료"
REVISED = "pytest tests/test_report.py가 통과하고 보고서 합계가 샘플 CSV 합계와 같다"


def test_testability_gate_asks_one_score_question_and_passes_at_the_threshold():
    criterion = "샘플 CSV 합계가 보고서 합계와 같다"
    at_threshold = FakeDecider({"testability": 0.5})
    assert gate_module.TestabilityGate(at_threshold, 0.5).check(criterion) == gate_module.GateDecision(0.5, 0.5)
    assert gate_module.TestabilityGate(at_threshold, 0.5).check(criterion).passed is True
    assert gate_module.TestabilityGate(FakeDecider({"testability": 0.49}), 0.5).check(criterion).passed is False
    assert at_threshold.calls == [(criterion, ["testability"]), (criterion, ["testability"])]
    assert gate_module.TESTABILITY.levels == [
        "판정할 수 없다(모호한 표현)", "일부만 판정할 수 있다", "실행 결과로 참/거짓을 판정할 수 있다"]


def test_testability_gate_judges_each_criterion_once_per_process():
    decider = FakeDecider({"testability": 0.2})
    gate = gate_module.TestabilityGate(decider, 0.5)
    gate.check(VAGUE)
    gate.check(VAGUE)
    gate.check(REVISED)
    assert [state for state, _ in decider.calls] == [VAGUE, REVISED]


def test_testability_gate_turns_every_decider_failure_into_gate_unavailable_and_retries_later():
    failing = FakeDecider(error=DecisionError("typesafe: HTTP 500"))
    gate = gate_module.TestabilityGate(failing, 0.5)
    for _ in range(2):
        with pytest.raises(gate_module.GateUnavailable, match="HTTP 500"):
            gate.check(VAGUE)
    assert len(failing.calls) == 2
    with pytest.raises(gate_module.GateUnavailable, match="refused"):
        gate_module.TestabilityGate(FakeDecider({}), 0.5).check(VAGUE)


class LeakyDecider:
    """DecisionError가 아닌 예외를 내는 판정기. 메시지에 비밀처럼 보이는 값을 담는다."""

    name = "leaky"

    def judge(self, state, questions):
        raise RuntimeError("sk-should-not-reach-the-client")


def test_testability_gate_reports_only_the_type_of_an_unexpected_decider_failure():
    with pytest.raises(gate_module.GateUnavailable) as raised:
        gate_module.TestabilityGate(LeakyDecider(), 0.5).check(VAGUE)
    assert "RuntimeError" in str(raised.value)
    assert "sk-should-not-reach-the-client" not in str(raised.value)


def test_fake_decider_needs_the_explicit_switch_and_a_score_script():
    script = {"DAY04_FAKE_DECIDER": '{"testability": 0.25}'}
    assert gate_module.fake_decider_from_env(script) is None
    assert gate_module.fake_decider_from_env({**script, "DAY04_ALLOW_FAKE_DECIDER": "true"}) is None
    armed = gate_module.fake_decider_from_env({**script, "DAY04_ALLOW_FAKE_DECIDER": "1"})
    assert gate_module.TestabilityGate(armed, 0.5).check(VAGUE) == gate_module.GateDecision(0.25, 0.5)
    for broken in ("", "{bad", '{"testability": "high"}'):
        with pytest.raises(ValueError, match="DAY04_FAKE_DECIDER"):
            gate_module.fake_decider_from_env({"DAY04_ALLOW_FAKE_DECIDER": "1", "DAY04_FAKE_DECIDER": broken})


def answering(action: str, content: dict | None = None):
    """elicitation_callback과 받은 질문 목록을 돌려준다."""
    asked = []

    async def callback(context, params):
        asked.append(params)
        return ElicitResult(action=action, content=content)

    return callback, asked


async def start_with_constraints(client: Client) -> str:
    session_id = (await call(client, "start_interview", goal=GOAL))["session_id"]
    await call(client, "record_answer", session_id=session_id, field="constraints", answer=CONSTRAINTS)
    return session_id


def gated_run(tmp_path, *flags, fake, action="accept", content=None, answer=VAGUE):
    """게이트를 켠 서버에서 완료 기준 하나를 기록한다. (session_id, 결과, 받은 질문)을 돌려준다."""
    callback, asked = answering(action, content)

    async def scenario():
        async with Client(spawn(tmp_path, "--gate", "h1", *flags, fake=fake), elicitation_callback=callback) as client:
            session_id = await start_with_constraints(client)
            result = await call(client, "record_answer", session_id=session_id, field="acceptance_criteria", answer=answer)
            return session_id, result

    session_id, result = asyncio.run(scenario())
    return session_id, result, asked


@pytest.mark.parametrize(("flags", "score", "threshold"), [((), 0.9, 0.5), (("--gate-threshold", "0.7"), 0.7, 0.7)])
def test_gate_records_a_testable_criterion_directly_with_agent_source(tmp_path, flags, score, threshold):
    session_id, result, asked = gated_run(tmp_path, *flags, fake=json.dumps({"testability": score}), answer=TESTABLE)
    assert asked == []
    assert (result["status"], result["answers"]["acceptance_criteria"]) == ("ready", TESTABLE)
    assert event_payloads(tmp_path, session_id)[-1] == {
        "field": "acceptance_criteria", "answer": TESTABLE,
        "gate": {"score": score, "threshold": threshold, "source": "agent"}}


def test_gate_asks_the_user_directly_below_threshold_and_records_the_elicited_criterion(tmp_path):
    session_id, result, asked = gated_run(
        tmp_path, "--gate-threshold", "0.7", fake=json.dumps({"testability": 0.69}),
        content={"acceptance_criteria": REVISED})
    assert len(asked) == 1
    assert f'"{VAGUE}"' in asked[0].message
    assert set(asked[0].requested_schema["properties"]) == {"acceptance_criteria"}
    assert (result["status"], result["answers"]["acceptance_criteria"]) == ("ready", REVISED)
    assert event_payloads(tmp_path, session_id)[-1] == {
        "field": "acceptance_criteria", "answer": REVISED,
        "gate": {"score": 0.69, "threshold": 0.7, "source": "elicited", "original": VAGUE}}

    async def restore_from_files_only():
        handed = tmp_path / "handoff"
        params = StdioServerParameters(
            command=sys.executable, env={"DAY04_ENV_FILE": str(tmp_path / "no-such.env")},
            args=[str(SERVER), "--db", str(handed / "new.sqlite3"), "--evidence-dir", str(tmp_path / "evidence")])
        async with Client(params) as client:
            return await call(client, "get_session", session_id=session_id)

    restored = asyncio.run(restore_from_files_only())
    assert (restored["answers"], restored["event_count"]) == (result["answers"], result["event_count"])


@pytest.mark.parametrize("action", ["decline", "cancel"])
def test_gate_records_nothing_when_the_user_declines_to_give_a_testable_criterion(tmp_path, action):
    session_id, result, asked = gated_run(tmp_path, fake=json.dumps({"testability": 0.2}), action=action)
    assert len(asked) == 1
    assert (result["success"], result["error"]) == (False, "criteria_not_testable")
    assert [payload.get("field") for payload in event_payloads(tmp_path, session_id)] == [None, "constraints"]


@pytest.mark.parametrize("fake", ["error", None])
def test_gate_fails_closed_when_the_decider_errors_or_has_no_key(tmp_path, fake):
    session_id, result, asked = gated_run(tmp_path, fake=fake, answer=TESTABLE)
    assert asked == []
    assert (result["success"], result["error"], result["state_saved"]) == (False, "decision_unavailable", False)
    assert len(event_payloads(tmp_path, session_id)) == 2


def test_gate_judges_only_non_blank_acceptance_criteria(tmp_path):
    async def scenario():
        async with Client(spawn(tmp_path, "--gate", "h1", fake="error")) as client:
            session_id = await start_with_constraints(client)
            blank = await call(client, "record_answer", session_id=session_id, field="acceptance_criteria", answer=" ")
            return session_id, blank

    session_id, blank = asyncio.run(scenario())
    assert blank["error"] == "empty_answer"
    assert event_payloads(tmp_path, session_id)[1] == {"field": "constraints", "answer": CONSTRAINTS}


def test_gate_off_never_consults_the_decider(tmp_path):
    async def scenario():
        async with Client(spawn(tmp_path, fake="error")) as client:
            session_id = await start_with_constraints(client)
            return session_id, await call(client, "record_answer", session_id=session_id,
                                          field="acceptance_criteria", answer=VAGUE)

    session_id, result = asyncio.run(scenario())
    assert (result["status"], result["answers"]["acceptance_criteria"]) == ("ready", VAGUE)
    assert event_payloads(tmp_path, session_id)[-1] == {"field": "acceptance_criteria", "answer": VAGUE}


def test_non_finite_gate_threshold_stops_the_server_at_startup(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(SERVER), "--db", str(tmp_path / "s.sqlite3"), "--gate", "h1", "--gate-threshold", "nan"],
        capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, check=False,
        env={**os.environ, "DAY04_ENV_FILE": str(tmp_path / "no-such.env")},
    )
    assert completed.returncode == 2
    assert "--gate-threshold" in completed.stderr and "유한한 숫자" in completed.stderr


def test_server_module_imports_as_a_package_with_the_same_seven_tools(tmp_path):
    from cap_lab.server.server import create_server

    server = create_server(tmp_path / "sessions.sqlite3", tmp_path / "evidence", gate="h1")
    names = {tool.name for tool in asyncio.run(server.list_tools())}
    assert names == {"start_interview", "record_answer", "get_session", "freeze_seed",
                     "list_evidence", "read_evidence", "save_evidence"}


def test_day04_reference_verify_script_passes_against_gate_off_server(tmp_path):
    """Day04의 단계 1~5 계약 검사를 이 서버에 그대로 돌린다. Day04 파일은 읽기만 한다."""
    completed = subprocess.run(
        [sys.executable, str(REFERENCE_VERIFY), "--server", str(SERVER), "--stage", "5"],
        capture_output=True, text=True, timeout=120, check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "5단계 통과" in completed.stdout
