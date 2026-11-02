"""cap_lab/notebook.py 시험. 노트북이 import하는 도우미를 공개 이름으로만 시험한다.

실제 server.py는 stdio 자식 프로세스로 띄우고 모델은 가짜를 쓴다. 키·네트워크·유료 호출은 없다.
"""
import asyncio
import gc
import json
import logging
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import langfuse
import pytest
from langchain_core.messages import AIMessage
from langchain_anthropic._client_utils import _get_default_async_httpx_client
from mcp_types import ElicitResult

from cap_lab import notebook
from cap_lab.experiment import Variant, run_experiment
from cap_lab.scorers import MCP_TOOLS
from cap_lab.settings import ROOT, Settings
from fakes import FakeChatModel
from test_experiment import FakeLangfuse, case_of

_REAL_CONNECT = socket.socket.connect  # conftest의 네트워크 차단이 걸리기 전의 connect다.
DUMMY_ANTHROPIC = "dummy-anthropic-value-1234"
DUMMY_LANGFUSE_SECRET = "dummy-langfuse-secret-5678"
DUMMY_HOST = "https://langfuse.dummy.example"
REPLY = AIMessage(content="MCP는 모델과 도구를 잇는 규약입니다.",
                  usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110})


def test_announce_prints_one_line_with_every_nonzero_part(capsys):
    notebook.announce("Part 1 스모크", model_calls=30, jev_calls=5, runs=6)
    assert capsys.readouterr().out == "[Part 1 스모크] 호출 규모: Claude 약 30회, Jev 최대 5회, 실행 6회입니다. 진행합니다.\n"


def test_announce_omits_the_parts_that_are_zero(capsys):
    notebook.announce("비교", model_calls=12)
    assert capsys.readouterr().out == "[비교] 호출 규모: Claude 약 12회입니다. 진행합니다.\n"
    notebook.announce("판정기 확인", model_calls=0, jev_calls=3)
    assert capsys.readouterr().out == "[판정기 확인] 호출 규모: Jev 최대 3회입니다. 진행합니다.\n"


def test_announce_says_no_paid_call_when_every_count_is_zero(capsys):
    notebook.announce("조립만 하는 셀", model_calls=0)
    out = capsys.readouterr().out
    assert out == "[조립만 하는 셀] 유료 호출 없음. 진행합니다.\n"
    assert "호출 규모: 입니다" not in out


def test_announce_keeps_the_scale_line_when_only_jev_or_runs_are_nonzero(capsys):
    notebook.announce("x", model_calls=9, jev_calls=3, runs=1)
    notebook.announce("x", model_calls=0, runs=2)
    assert capsys.readouterr().out == ("[x] 호출 규모: Claude 약 9회, Jev 최대 3회, 실행 1회입니다. 진행합니다.\n"
                                       "[x] 호출 규모: 실행 2회입니다. 진행합니다.\n")


def test_key_table_shows_set_or_unset_and_never_a_value(capsys):
    settings = Settings(anthropic_api_key=DUMMY_ANTHROPIC, langfuse_secret_key=DUMMY_LANGFUSE_SECRET,
                        langfuse_host=DUMMY_HOST)
    notebook.key_table(settings)
    out = capsys.readouterr().out
    for name in ("ANTHROPIC_API_KEY", "TYPESAFE_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        assert name in out
    assert out.count("설정됨") == 3
    assert out.count("미설정") == 2
    for value in (DUMMY_ANTHROPIC, DUMMY_LANGFUSE_SECRET, DUMMY_HOST, "dummy"):
        assert value not in out


def test_show_table_prints_every_row_without_truncating(capsys):
    notebook.show_table([{"번호": n, "이름": f"행-{n}"} for n in range(120)], ["번호", "이름"])
    out = capsys.readouterr().out
    assert "행-0" in out and "행-119" in out and "..." not in out


def test_new_workdir_is_created_under_outputs_notebook_with_label_and_timestamp():
    path = notebook.new_workdir("시험-라벨")
    try:
        assert path.is_dir()
        assert path.parent == ROOT / "outputs" / "notebook"
        assert path.name.startswith("시험-라벨-")
        assert len(path.name) == len("시험-라벨-") + len("20260101-120000")
    finally:
        path.rmdir()


def test_connect_server_lists_the_seven_tools_of_the_real_stdio_server(tmp_path):
    async def scenario():
        async with notebook.connect_server(tmp_path) as client:
            return [tool.name for tool in (await client.list_tools()).tools]

    names = asyncio.run(scenario())
    assert len(names) == 7
    assert set(names) == MCP_TOOLS


def test_show_events_lists_the_events_the_server_wrote_for_a_session(tmp_path, capsys):
    async def decline(context, params):
        return ElicitResult(action="decline")

    async def scenario():
        async with notebook.connect_server(tmp_path, elicitation_callback=decline) as client:
            started = await client.call_tool("start_interview", {"goal": "월별 정산표를 만드는 도구"})
            session_id = started.structured_content["session_id"]
            await client.call_tool("record_answer", {"session_id": session_id, "field": "constraints",
                                                     "answer": "원본 이미지는 외부로 보내지 않는다"})
            return session_id

    session_id = asyncio.run(scenario())
    notebook.show_events(tmp_path / "evidence")
    out = capsys.readouterr().out
    assert out.count(session_id[:8]) == 2
    assert out.index("interview_started") < out.index("answer_recorded")
    assert "constraints" in out


def test_show_events_says_so_when_there_is_no_evidence(tmp_path, capsys):
    notebook.show_events(tmp_path / "no-evidence")
    assert "근거 이벤트가 없습니다" in capsys.readouterr().out


@pytest.fixture
def output_root(tmp_path, monkeypatch):
    """new_workdir이 tmp_path 아래에만 쓰게 한다."""
    root = tmp_path / "out"
    root.mkdir()
    monkeypatch.setattr(notebook, "OUTPUT_ROOT", root)
    return root


def run_dev_02(model, repeats=1):
    return notebook.run_small_compare([Variant("A")], ["dev-02"], repeats, label="시험", model=model)


def test_run_small_compare_scores_a_run_and_appends_one_json_line_per_run(output_root):
    rows = run_dev_02(FakeChatModel.scripted([REPLY, REPLY]), repeats=2)

    assert [(r["variant"], r["repeat"], r["case_id"]) for r in rows] == [("A", 1, "dev-02"), ("A", 2, "dev-02")]
    row = rows[0]
    assert row["trigger_ok"] is True
    assert row["frozen_ok"] is None  # dev-02는 명세를 확정하지 않아 이 검사가 해당 없음이다.
    assert (row["model_calls"], row["input_tokens"]) == (1.0, 100.0)
    assert row["error"] is None and row["first_failure"] is None
    [workdir] = list(output_root.iterdir())
    assert workdir.name.startswith("시험-")
    lines = [json.loads(line) for line in (workdir / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    assert lines[0]["case_id"] == "dev-02" and lines[0]["trigger_ok"] is True and lines[0]["frozen_ok"] is None


def test_run_small_compare_refuses_a_holdout_case_before_running_anything(output_root):
    with pytest.raises(ValueError, match="dev"):
        notebook.run_small_compare([Variant("A")], ["dev-02", "ho-01"], 1, label="시험",
                                   model=FakeChatModel.scripted([REPLY]))
    assert list(output_root.iterdir()) == []


def test_run_small_compare_refuses_an_unknown_case_id(output_root):
    with pytest.raises(ValueError, match="dev-99"):
        notebook.run_small_compare([Variant("A")], ["dev-99"], 1, label="시험", model=FakeChatModel.scripted([]))


def test_run_small_compare_keeps_an_errored_run_as_a_row_with_unchecked_scores(output_root):
    rows = run_dev_02(FakeChatModel.scripted([]))

    assert len(rows) == 1
    assert rows[0]["error"]
    assert rows[0]["trigger_ok"] is None
    [workdir] = list(output_root.iterdir())
    assert len((workdir / "rows.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_run_small_compare_never_contacts_langfuse_even_when_its_keys_are_set(tmp_path, output_root, monkeypatch):
    env_file = tmp_path / "langfuse.env"
    env_file.write_text(f"LANGFUSE_PUBLIC_KEY=pk-dummy\nLANGFUSE_SECRET_KEY={DUMMY_LANGFUSE_SECRET}\n"
                        f"LANGFUSE_HOST={DUMMY_HOST}\n", encoding="utf-8")
    monkeypatch.setenv("DAY04_ENV_FILE", str(env_file))
    created = []
    monkeypatch.setattr(langfuse.Langfuse, "__init__", lambda self, *a, **k: created.append(1))

    rows = run_dev_02(FakeChatModel.scripted([REPLY]))

    assert rows[0]["error"] is None
    assert created == []
    assert DUMMY_LANGFUSE_SECRET not in (next(output_root.iterdir()) / "rows.jsonl").read_text(encoding="utf-8")


def test_pass_rate_table_keeps_none_out_of_both_counts():
    rows = [
        {"variant": "A", "x_ok": True}, {"variant": "A", "x_ok": True}, {"variant": "A", "x_ok": False},
        {"variant": "A", "x_ok": None}, {"variant": "B", "x_ok": None},
    ]
    table = {(r["variant"], r["score"]): r for r in notebook.pass_rate_table(rows, ["x_ok"])}

    a = table[("A", "x_ok")]
    assert (a["passed"], a["checked"], a["unchecked"]) == (2, 3, 1)
    assert a["rate"] == pytest.approx(2 / 3)
    assert (a["ci_low"], a["ci_high"]) == pytest.approx((0.2077, 0.9385), abs=1e-3)  # n=3, 성공 2의 Wilson 95% 구간
    b = table[("B", "x_ok")]
    assert (b["passed"], b["checked"], b["unchecked"]) == (0, 0, 1)
    assert (b["rate"], b["ci_low"], b["ci_high"]) == (None, None, None)


def test_pass_rate_table_rejects_a_numeric_score_and_a_name_no_row_has():
    with pytest.raises(ValueError, match="model_calls"):
        notebook.pass_rate_table([{"variant": "A", "model_calls": 3.0}], ["model_calls"])
    with pytest.raises(ValueError, match="typo_ok"):
        notebook.pass_rate_table([{"variant": "A", "x_ok": True}], ["typo_ok"])


def test_run_small_compare_also_works_inside_a_running_event_loop_like_a_notebook_cell(output_root):
    async def notebook_cell():
        return run_dev_02(FakeChatModel.scripted([REPLY]))

    rows = asyncio.run(notebook_cell())
    assert [row["error"] for row in rows] == [None]


class _MessagesHandler(BaseHTTPRequestHandler):
    """Anthropic Messages API 응답 하나를 돌려주는 로컬 서버. 연결을 유지해 실제 HTTP 풀이 재사용되게 한다."""
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        body = json.dumps({
            "id": "msg_test", "type": "message", "role": "assistant", "model": "test-model",
            "content": [{"type": "text", "text": "MCP는 모델과 도구를 잇는 규약입니다."}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 100, "output_tokens": 10},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def local_messages_api(monkeypatch):
    """진짜 ChatAnthropic이 127.0.0.1의 가짜 Messages API로 가게 한다. 네트워크와 키는 쓰지 않는다."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MessagesHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    address = ("127.0.0.1", server.server_port)
    guarded_connect = socket.socket.connect

    def connect_to_local_server_only(sock, target):
        # conftest의 차단은 그대로 두고, 이 시험 서버 한 곳으로만 연결을 연다.
        return _REAL_CONNECT(sock, target) if target == address else guarded_connect(sock, target)

    monkeypatch.setattr(socket.socket, "connect", connect_to_local_server_only)
    monkeypatch.setattr(notebook, "load_settings", lambda: Settings(anthropic_api_key=DUMMY_ANTHROPIC))
    monkeypatch.setattr("cap_lab.settings._API_URL", f"http://127.0.0.1:{server.server_port}")
    yield
    server.shutdown()
    server.server_close()


def test_run_small_compare_over_two_cases_has_no_connection_error_in_a_notebook_cell(output_root, local_messages_api):
    async def notebook_cell():
        return notebook.run_small_compare([Variant("A")], ["dev-01", "dev-02"], 1, label="루프")

    rows = asyncio.run(notebook_cell())
    assert [(row["case_id"], row["error"]) for row in rows] == [("dev-01", None), ("dev-02", None)]


def test_two_run_small_compare_calls_in_one_kernel_both_reach_the_api(output_root, local_messages_api):
    async def notebook_cell():
        first = notebook.run_small_compare([Variant("A")], ["dev-02"], 1, label="루프1")
        second = notebook.run_small_compare([Variant("A")], ["dev-02"], 1, label="루프2")
        return first + second

    rows = asyncio.run(notebook_cell())
    assert [row["error"] for row in rows] == [None, None]


def test_three_runs_in_a_notebook_cell_leave_no_unretrieved_task_exception(output_root, local_messages_api, caplog):
    async def notebook_cell():
        rows = []
        for case_id in ("dev-01", "dev-02", "dev-03"):
            rows += notebook.run_small_compare([Variant("A")], [case_id], 1, label=f"소음-{case_id}")
            gc.collect()
        return rows

    # 앞선 시험이 남긴 클라이언트가 이 시험 중에 수거되어 경고를 내지 않도록, 실행 중인 루프가 없을 때 미리 치운다.
    _get_default_async_httpx_client.cache_clear()
    gc.collect()
    with caplog.at_level(logging.ERROR, logger="asyncio"):
        rows = asyncio.run(notebook_cell())
        gc.collect()
    assert [row["error"] for row in rows] == [None, None, None]
    assert [r.getMessage() for r in caplog.records if "Task exception was never retrieved" in r.getMessage()] == []


def test_run_experiment_langfuse_repeats_each_reach_the_api_from_their_own_event_loop(tmp_path, local_messages_api):
    # Langfuse의 run_experiment는 호출마다 asyncio.run을 새로 돈다. FakeLangfuse가 그것을 흉내 낸다.
    settings = Settings(anthropic_api_key=DUMMY_ANTHROPIC)
    run_names = asyncio.run(run_experiment(Variant("L"), [case_of("dev-01")], 2, settings=settings,
                                           mirror_dir=tmp_path / "runs", client=FakeLangfuse()))
    errors = [json.loads(line)["error"] for name in run_names
              for line in (tmp_path / "runs" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert errors == [None, None]
