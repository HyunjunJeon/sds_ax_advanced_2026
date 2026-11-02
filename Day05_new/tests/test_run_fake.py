"""tests/run_fake.py(노트북 오프라인 실행기)와 그 가짜(tests/fakes.py)를 확인한다.

수업 노트북은 아직 없으므로 tmp_path에 합성 노트북을 만들어 실제 python3 kernel로 돌린다.
kernel 실행은 모듈 fixture에서 한 번씩만 하고, 여러 시험이 그 출력(stdout의 표식 줄)을 나눠 읽는다.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import nbformat
import pytest
import run_fake
from eval_lab import evidence, runs
from eval_lab.agent import COMMON_PROMPT
from eval_lab.contracts import Followup, Request, Response
from eval_lab.dataset import fingerprint, load_dataset, load_fixtures
from eval_lab.episodes import execute_episode
from eval_lab.judges import JEV_QUESTIONS, DeepEvalAnthropic, run_agent_metrics
from eval_lab.monitoring import fetch_metrics, metrics_query
from eval_lab.online import Selection, create_root_rule, enqueue_for_review
from eval_lab.replay import DEFAULT_DATASET_NAME, PoolEpisode, to_langfuse_dataset
from fakes import (
    JUDGE_REASON,
    NOTEBOOK_DECIDER_SCRIPT,
    FakeLangfuse,
    NotebookAgentModel,
    NotebookJudgeModel,
    OfflineLangfuseError,
)

DAY05_ROOT = Path(__file__).resolve().parents[1]
RUN_FAKE = DAY05_ROOT / "tests" / "run_fake.py"


# ---------------------------------------------------------------- 합성 노트북

def write_notebook(path: Path, cells: list[tuple[str, str]]) -> Path:
    """(종류, 내용) 목록으로 노트북 파일을 만든다. 종류는 'md' 또는 'code'다."""
    notebook = nbformat.v4.new_notebook()
    notebook.cells = [nbformat.v4.new_markdown_cell(source) if kind == "md" else nbformat.v4.new_code_cell(source)
                      for kind, source in cells]
    nbformat.write(notebook, path)
    return path


def printed(result: run_fake.PassResult, marker: str) -> list:
    """실행한 사본의 stdout에서 '<marker> <JSON>' 줄을 찾아 JSON 값들을 돌려준다."""
    text = "".join(output.get("text", "") for cell in result.executed.cells if cell.cell_type == "code"
                   for output in cell.outputs if output.get("name") == "stdout")
    return [json.loads(line[len(marker) + 1:]) for line in text.splitlines() if line.startswith(marker + " ")]


MAIN_CELLS = [
    ("md", "# run_fake 시험용 합성 노트북"),
    ("code", "RUN_EXERCISE = False\nRUN_OPTIONAL = False"),
    ("code", 'import json\nprint("SWITCH", json.dumps([RUN_EXERCISE, RUN_OPTIONAL]))'),
    ("code", 'from eval_lab.notebook import output_root\nprint("OUTPUT_ROOT", json.dumps(str(output_root())))'),
    ("code", """\
from eval_lab.agent import PROMPTS
from eval_lab.dataset import load_dataset, load_fixtures
from eval_lab.episodes import execute_episode
from eval_lab.notebook import langfuse_or_none
from eval_lab.settings import load_settings, make_agent_model

settings = load_settings()
langfuse = langfuse_or_none(settings)
card = next(c for c in load_dataset(split="dev") if c.metadata.scenario_id == "normal")
artifact = execute_episode(card.input, load_fixtures()[card.fixture_id], followups=card.followups,
                           max_turns=card.max_turns, scenario_id="normal", release="baseline", trial=1, mode="live",
                           prompt=PROMPTS["baseline"], model=make_agent_model(settings), langfuse=langfuse,
                           environment_tag="run-fake-test")
print("ARTIFACT", json.dumps({"status": artifact.execution_status, "model_calls": artifact.model_calls,
                              "kind": artifact.response.kind, "tools": [e.tool for e in artifact.events]}))"""),
    ("code", """\
import os
from eval_lab import settings as settings_module
from eval_lab.decisions import make_decider
from eval_lab.online import batch_evaluate, online_evaluators
from eval_lab.settings import make_judge_model

try:
    settings_module.make_langfuse(settings)
    made = "client"
except RuntimeError as error:
    made = "미설정" if "미설정" in str(error) else str(error)
print("MAKE_LANGFUSE", json.dumps(made, ensure_ascii=False))
secret_parts = ("API_KEY", "TOKEN", "SECRET", "LANGFUSE", "LANGSMITH", "ANTHROPIC", "OPENROUTER", "TYPESAFE")
print("SECRET_NAMES", json.dumps(sorted(n for n in os.environ if any(p in n.upper() for p in secret_parts))))
if langfuse is not None:
    roots = [o.name for o in langfuse.api.observations.get_many(trace_id=artifact.turns[0].trace_id).data
             if o.parent_observation_id is None]
    evaluators = online_evaluators(decider=make_decider(settings), judge_model=make_judge_model(settings))
    result = batch_evaluate(langfuse, evaluators=evaluators, environment="run-fake-test", max_items=5)
    values = {e.name: e.value for evaluations in result.item_evaluations.values() for e in evaluations}
    print("LANGFUSE", json.dumps({"roots": roots, "processed": result.total_items_processed, "values": values,
                                  "scores": len(langfuse.scores)}, ensure_ascii=False))"""),
]

NETWORK_CELLS = [
    ("md", "# 네트워크 차단 확인"),
    ("code", """\
import json
import socket
server = socket.socket()
server.bind(("127.0.0.1", 0))
server.listen(1)
client = socket.create_connection(server.getsockname(), timeout=2)
client.close()
server.close()
try:
    socket.getaddrinfo("example.com", 443)
    looked_up = "resolved"
except OSError as error:
    looked_up = str(error)
print("LOOPBACK", json.dumps(["connected", looked_up], ensure_ascii=False))"""),
    ("code", 'import urllib.request\nurllib.request.urlopen("https://example.com", timeout=2)'),
    ("code", 'print("UNREACHED", "[]")'),
]


@pytest.fixture(scope="module")
def main_runs(tmp_path_factory):
    """합성 노트북을 세 가지 실행 조건으로 한 번씩 돌린다. 셸에 키가 남아 있는 상황을 흉내 낸다."""
    path = write_notebook(tmp_path_factory.mktemp("main") / "main.ipynb", MAIN_CELLS)
    before = path.read_bytes()
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ANTHROPIC_API_KEY", "shell-secret-must-not-leak")
        patch.setenv("RUN_FAKE_TEST_API_KEY", "shell-secret-must-not-leak")
        results = {(langfuse, switches): run_fake.run_pass(path, langfuse=langfuse, switches=switches)
                   for langfuse, switches in run_fake.PASSES}
    return SimpleNamespace(path=path, before=before, results=results)


@pytest.fixture(scope="module")
def blocked_run(tmp_path_factory):
    path = write_notebook(tmp_path_factory.mktemp("network") / "net.ipynb", NETWORK_CELLS)
    return run_fake.run_pass(path, langfuse="none", switches=False)


# ---------------------------------------------------------------- 실행 결과와 출력 형식

def test_every_pass_of_the_synthetic_notebook_is_ok(main_runs):
    lines = [result.line() for result in main_runs.results.values()]
    for line in lines:
        assert re.fullmatch(r"OK main\.ipynb langfuse=(fake|none) switches=(on|off) cells=5 \d+\.\ds", line), line
    assert [line.split()[2:4] for line in lines] == [["langfuse=fake", "switches=off"], ["langfuse=none", "switches=off"],
                                                    ["langfuse=fake", "switches=on"]]


def test_live_episode_runs_on_the_fake_agent(main_runs):
    """(1) live Episode가 가짜 에이전트로 끝까지 돈다: get_order 한 번 뒤 escalated 응답, 모델 호출 2회."""
    for result in main_runs.results.values():
        assert printed(result, "ARTIFACT") == [{"status": "completed", "model_calls": 2, "kind": "escalated",
                                                "tools": ["get_order"]}]


def test_network_outside_loopback_fails_the_pass(blocked_run):
    """(2) 바깥 주소 연결은 OSError로 막혀 그 셀에서 FAIL이 된다. 루프백 연결은 그대로 된다."""
    assert not blocked_run.ok
    assert blocked_run.failed_cell == 2  # 저장본 기준 번호(주입 셀 제외)
    assert blocked_run.line().startswith("FAIL net.ipynb langfuse=none switches=off cell=2 URLError: ")
    assert "run_fake: 네트워크 차단" in blocked_run.line()
    assert printed(blocked_run, "LOOPBACK") == [["connected", "run_fake: 네트워크 차단"]]
    assert printed(blocked_run, "UNREACHED") == []


def test_langfuse_none_takes_the_local_path(main_runs):
    """(3) langfuse=none: 실제 make_langfuse가 미설정 RuntimeError를 내고 Langfuse 경로는 돌지 않는다."""
    result = main_runs.results[("none", False)]
    assert printed(result, "MAKE_LANGFUSE") == ["미설정"]
    assert printed(result, "LANGFUSE") == []


def test_langfuse_fake_records_root_and_batch_evaluates(main_runs):
    """(3) langfuse=fake: Episode가 root observation을 남기고 batch_evaluate가 평가를 돌려준다.

    의미 판정은 Jev 대본(0.9 통과, 0.5 Judge로, 0.1 실패)과 Judge의 PASS를 따른다.
    """
    for key in (("fake", False), ("fake", True)):
        result = main_runs.results[key]
        assert printed(result, "MAKE_LANGFUSE") == ["client"]
        (langfuse,) = printed(result, "LANGFUSE")
        assert langfuse["roots"] == ["episode"]
        assert langfuse["processed"] == 1
        assert {name: langfuse["values"][name] for name in NOTEBOOK_DECIDER_SCRIPT} == {
            "message_consistent": "PASS", "next_step_clear": "PASS", "clarify_when_needed": "FAIL"}
        assert {"trajectory_status", "fatal_count", "warn_count", "blocked_attempts"} <= set(langfuse["values"])
        assert langfuse["scores"] == 7  # 궤적 점수 4개 + 의미 점수 3개가 create_score로 쌓였다.


def test_stored_notebook_bytes_are_unchanged(main_runs):
    """(4) 세 번 실행한 뒤에도 저장본은 한 바이트도 바뀌지 않는다."""
    assert main_runs.path.read_bytes() == main_runs.before


def test_switches_on_flips_run_flags_in_the_copy_only(main_runs):
    """(5) switches=on은 사본의 RUN_EXERCISE·RUN_OPTIONAL만 True로 바꾼다."""
    assert printed(main_runs.results[("fake", False)], "SWITCH") == [[False, False]]
    assert printed(main_runs.results[("none", False)], "SWITCH") == [[False, False]]
    assert printed(main_runs.results[("fake", True)], "SWITCH") == [[True, True]]
    assert "RUN_OPTIONAL = False" in main_runs.path.read_text(encoding="utf-8")


def test_output_root_is_a_temporary_folder_outside_day05_outputs(main_runs):
    """(6) kernel 안의 DAY05_OUTPUT_ROOT는 Day05_new/outputs 밖의 실행별 임시 폴더이고, 실행 뒤 지워진다."""
    roots = [Path(printed(result, "OUTPUT_ROOT")[0]) for result in main_runs.results.values()]
    assert len(set(roots)) == 3
    for root in roots:
        assert not root.is_relative_to(DAY05_ROOT / "outputs")
        assert not root.is_relative_to(DAY05_ROOT)
        assert not root.parent.exists()


def test_kernel_environment_has_no_secret_names(main_runs):
    """셸에 남은 키 이름도, Day05_new/.env를 읽는 deepeval import도 kernel 환경에 비밀 이름을 남기지 않는다."""
    for result in main_runs.results.values():
        assert printed(result, "SECRET_NAMES") == [[]]


# ---------------------------------------------------------------- CLI

def test_cli_prints_pass_lines_and_summary(tmp_path):
    """경로에 공백·한글이 있어도 세 번 모두 OK면 종료 코드 0이다."""
    path = write_notebook(tmp_path / "작은 노트북.ipynb", [("code", "print(1)")])
    completed = subprocess.run([sys.executable, str(RUN_FAKE), str(path)], capture_output=True, text=True,
                               timeout=300, check=False)
    lines = completed.stdout.splitlines()
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert [line.rsplit(" ", 1)[0] for line in lines[:3]] == [
        "OK 작은 노트북.ipynb langfuse=fake switches=off cells=1",
        "OK 작은 노트북.ipynb langfuse=none switches=off cells=1",
        "OK 작은 노트북.ipynb langfuse=fake switches=on cells=1"]
    assert lines[3:] == ["run_fake: 3/3 OK"]


def test_missing_and_unreadable_notebooks_fail_without_a_kernel(tmp_path, capsys):
    broken = tmp_path / "broken.ipynb"
    broken.write_text("{not json", encoding="utf-8")
    assert run_fake.main([str(tmp_path / "missing.ipynb"), str(broken)]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "FAIL missing.ipynb langfuse=fake switches=off cell=- FileNotFoundError: 파일이 없습니다"
    assert lines[3] == "FAIL broken.ipynb langfuse=fake switches=off cell=- NotJSONError: 노트북을 읽을 수 없습니다"
    assert len(lines) == 7 and lines[-1] == "run_fake: 0/6 OK"


def test_all_counts_each_missing_course_notebook_as_three_failures(tmp_path, capsys):
    assert run_fake.main(["--all"], day_dir=tmp_path) == 1
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == len(run_fake.NOTEBOOKS) * 3 + 1
    assert lines[0].startswith("FAIL 00-Setup.ipynb langfuse=fake switches=off cell=- ")
    assert lines[-2].startswith("FAIL 06-Lab-Self-Improving-Agent.ipynb langfuse=fake switches=on cell=- ")
    assert lines[-1] == "run_fake: 0/24 OK"


@pytest.mark.parametrize("argv", [[], ["--all", "x.ipynb"]])
def test_cli_needs_paths_or_all_but_not_both(argv):
    with pytest.raises(SystemExit) as stopped:
        run_fake.main(argv)
    assert stopped.value.code == 2


# ---------------------------------------------------------------- 가짜 모델과 Jev 대본

def test_decider_script_names_the_jev_questions():
    assert set(NOTEBOOK_DECIDER_SCRIPT) == {question.name for question in JEV_QUESTIONS}


def test_agent_scopes_the_lookup_to_the_latest_request():
    """되묻기 뒤 후속 입력에 주문 번호가 오면 그 턴에서 다시 get_order부터 한다(이전 턴의 ToolMessage를 보지 않는다)."""
    card = next(c for c in load_dataset(split="dev") if c.metadata.scenario_id == "normal")
    followup = Followup(request=Request(message="주문 번호는 order-a입니다.", order_id="order-a", request_id="r-2"))
    first = Request(message="주문을 취소하고 싶습니다.", order_id=None, request_id="r-1")
    model = NotebookAgentModel()
    artifact = execute_episode(first, load_fixtures()[card.fixture_id], followups=[followup], max_turns=2,
                               scenario_id="normal", release="baseline", trial=1, mode="live", prompt=COMMON_PROMPT,
                               model=model)
    assert [turn.response.kind for turn in artifact.turns] == ["clarification", "escalated"]
    assert [event.tool for event in artifact.events] == ["get_order"]
    assert artifact.model_calls == model.calls == 3
    assert (artifact.input_tokens, artifact.output_tokens) == (0, 0)


def test_agent_answers_with_response_tool_only_and_with_text_when_unbound():
    from langchain.agents import create_agent
    from langchain.agents.structured_output import ToolStrategy

    agent = create_agent(model=NotebookAgentModel(), tools=[], response_format=ToolStrategy(Response))
    for order_id, kind in (("order-a", "escalated"), (None, "clarification")):
        request = Request(message="취소해 주세요.", order_id=order_id, request_id="r-1")
        result = agent.invoke({"messages": [{"role": "user", "content": request.model_dump_json()}]})
        assert (result["structured_response"].kind, result["structured_response"].order_id) == (kind, order_id)
    assert NotebookAgentModel().invoke("안녕하세요").content.startswith("가짜 에이전트 응답")


def test_judge_fake_fills_deepeval_schemas():
    """DeepEval 지표는 가짜 Judge의 스키마 JSON으로 측정되고, 시험 사례 필드가 모자란 지표는 error로 보고된다."""
    from deepeval.metrics import (
        StepEfficiencyMetric,
        TaskCompletionMetric,
        ToolCorrectnessMetric,
    )

    card = next(c for c in load_dataset(split="dev") if c.metadata.scenario_id == "normal")
    artifact = execute_episode(card.input, load_fixtures()[card.fixture_id], followups=[], max_turns=1,
                               scenario_id="normal", release="baseline", trial=1, mode="live", prompt=COMMON_PROMPT,
                               model=NotebookAgentModel())
    judge = DeepEvalAnthropic(NotebookJudgeModel())
    results = run_agent_metrics(artifact, [TaskCompletionMetric(model=judge, async_mode=False),
                                           StepEfficiencyMetric(model=judge, async_mode=False),
                                           ToolCorrectnessMetric(model=judge, async_mode=False)])
    assert [(r["metric"], r["status"]) for r in results] == [
        ("TaskCompletionMetric", "measured"), ("StepEfficiencyMetric", "measured"), ("ToolCorrectnessMetric", "error")]
    assert results[0]["score"] == 1.0
    assert "expected_tools" in results[2]["reason"]


def test_judge_fake_answers_the_semantic_judge_prompt_with_pass():
    from eval_lab.judges import _judge_prompt, _parse_judge

    reply = NotebookJudgeModel().invoke(_judge_prompt("[요청]\n고객 메시지: 취소", JEV_QUESTIONS[1]))
    assert _parse_judge(reply.content) == (True, JUDGE_REASON)


# ---------------------------------------------------------------- FakeLangfuse와 eval_lab의 Langfuse 경로

@pytest.fixture
def recorded(tmp_path):
    """scripted Episode 하나를 FakeLangfuse에 기록한다. Langfuse 자원 싱글턴은 앞뒤로 비운다."""
    from langfuse._client.resource_manager import LangfuseResourceManager

    LangfuseResourceManager.reset()
    client = FakeLangfuse()
    card = next(c for c in load_dataset(split="dev") if c.metadata.scenario_id == "normal")
    snapshot = {"cards": [card.model_dump()], "fixtures": {card.fixture_id: load_fixtures()[card.fixture_id]}}
    frozen = {"run_id": "fake-frozen", "snapshot": snapshot, "snapshot_hash": fingerprint(snapshot)}
    raw = runs.record_release(frozen, release="baseline", prompt=COMMON_PROMPT, repeats=1, mode="scripted",
                              out=tmp_path / "raw.json", langfuse=client)
    yield client, raw
    LangfuseResourceManager.reset()


def test_fetch_observations_finds_every_service_observation(recorded):
    client, raw = recorded
    (trace,) = evidence.fetch_observations(client, raw).values()
    assert trace["missing_service_observation_ids"] == []
    assert {o["name"] for o in trace["observations"]} >= {"episode", "turn-1", "service.get_order"}


def test_metrics_api_counts_root_observations(recorded):
    client, raw = recorded
    query = metrics_query(metrics=[("count", "count"), ("latency", "p95"), ("totalCost", "sum")],
                          dimensions=["version"], from_ts=raw["started_at"], to_ts="2999-01-01T00:00:00+00:00")
    (row,) = fetch_metrics(client, query)
    assert row["version"] == "baseline" and row["count_count"] == 1
    assert row["p95_latency"] > 0 and row["sum_totalCost"] is None
    with pytest.raises(OfflineLangfuseError, match="scores-numeric"):
        fetch_metrics(client, metrics_query(view="scores-numeric", metrics=[("count", "count")],
                                            from_ts="2000-01-01T00:00:00Z", to_ts="2999-01-01T00:00:00Z"))


def test_queue_dataset_rule_and_auth_round_trip(recorded):
    client, raw = recorded
    trace_id = raw["rows"][0]["trace_id"]
    first = enqueue_for_review(client, "day05-review", [Selection(0, trace_id, "r"), Selection(1, None, "r")])
    assert first == {"queue_id": "offline-queue-1", "enqueued": 1, "skipped": 1}
    assert enqueue_for_review(client, "day05-review", [])["queue_id"] == "offline-queue-1"

    episode = PoolEpisode(episode_id="e-1", scenario_or_item_id="normal", events=raw["rows"][0]["artifact"]["events"],
                          fatal=False, first_violation_index=None, normal=True, source=trace_id)
    ids = to_langfuse_dataset(client, [episode], round_no=1)
    assert [item.id for item in client.get_dataset(DEFAULT_DATASET_NAME).items] == ids

    assert create_root_rule(client, evaluator_id="ev-1", environment="day05_new", sampling=0.5).id == "offline-rule-1"
    assert client.evaluation_rules[0].enabled is False
    assert client.auth_check() is True


def test_unsupported_api_names_the_method(recorded):
    client, _ = recorded
    with pytest.raises(OfflineLangfuseError, match=r"api\.prompts"):
        client.api.prompts.get("x")
    with pytest.raises(OfflineLangfuseError, match=r"api\.datasets\.delete_run"):
        client.api.datasets.delete_run("d", "r")
    with pytest.raises(OfflineLangfuseError, match="async_api"):
        client.async_api.projects.get()


def test_dataset_experiment_runs_through_the_offline_api(recorded):
    """create_dataset·create_dataset_item·get_dataset·run_experiment가 실제 SDK 코드로 돌고 run 항목과 점수가 쌓인다."""
    from langfuse import Evaluation

    client, _ = recorded
    client.create_dataset(name="golden-v1")
    for number in range(3):
        client.create_dataset_item(dataset_name="golden-v1", input={"q": number}, expected_output={"a": number},
                                   id=f"item-{number}")

    def exact(*, input, output, expected_output=None, **kwargs):
        return Evaluation(name="exact", value=float(output == expected_output))

    result = client.get_dataset("golden-v1").run_experiment(
        name="exp-1", task=lambda *, item, **kwargs: {"a": item.input["q"]}, evaluators=[exact])
    assert [[e.value for e in item.evaluations] for item in result.item_results] == [[1.0], [1.0], [1.0]]
    # run_experiment는 항목을 동시에 처리하므로 기록 순서는 정해져 있지 않다.
    assert sorted(run_item.dataset_item_id for run_item in client.dataset_run_items) == ["item-0", "item-1", "item-2"]
    assert [score["name"] for score in client.scores] == ["exact", "exact", "exact"]
