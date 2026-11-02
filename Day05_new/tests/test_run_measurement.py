"""tests/run_measurement.py(PREREG P3 저자 측정)를 키·네트워크 없이 끝까지 돌려 본다.

측정은 --offline으로 돌린다. 모델·Jev·Judge·개선기·Langfuse는 tests/fakes.py의 가짜이고,
에이전트는 시험마다 main(offline_agent=...)으로 바꿔 넣는다.
holdout 초안 4건은 tmp_path의 사본에서만 approved로 바꾼다. data/scenarios.json은 읽기만 한다.
"""
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import pytest
import run_measurement
from eval_lab.dataset import DATA, pending_ids
from eval_lab.rsi import DECISIONS
from eval_lab.traffic import pilot_items, round_items
from fakes import NotebookAgentModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

RUN_MEASUREMENT = Path(run_measurement.__file__)
REAL_SCENARIOS = DATA / "scenarios.json"
OUTPUT_FILES = ("round-1.json", "round-2.json", "holdout.json", "run_manifest.json")


class WriteFirstAgent(NotebookAgentModel):
    """주문 번호가 있는 요청이면 조회도 정책 확인도 없이 begin_cancellation부터 부르는 가짜 에이전트.

    그 뒤의 답(Response 구조화 도구 호출)은 NotebookAgentModel과 같다. 그래서 주문 번호가 있는 Episode마다
    write-before-approval 치명 위반이 생긴다. 게이트가 막아도 막힌 결과를 받고 같은 답을 한다.
    """

    def _reply(self, messages: list[BaseMessage], tool_names: Sequence[str]) -> AIMessage:
        human = [index for index, message in enumerate(messages) if isinstance(message, HumanMessage)]
        order_id = json.loads(messages[human[-1]].text)["order_id"] if human else None
        answered = any(isinstance(message, ToolMessage) for message in messages[human[-1] + 1:]) if human else False
        if "begin_cancellation" in tool_names and order_id and not answered:
            call = {"name": "begin_cancellation", "args": {"order_id": order_id, "expected_version": 1},
                    "id": f"write-first-{self.calls}", "type": "tool_call"}
            return AIMessage(content="", tool_calls=[call],
                             usage_metadata={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        return super()._reply(messages, tool_names)


# ---------------------------------------------------------------- 준비

def write_scenarios(path: Path, *, approve_drafts: bool = True, drop: tuple[str, ...] = ()) -> Path:
    """data/scenarios.json의 사본을 path에 쓴다. 사본에서만 초안을 승인하고(reviewer도 채운다) drop의 사례를 뺀다."""
    cards = json.loads(REAL_SCENARIOS.read_text(encoding="utf-8"))
    kept = []
    for card in cards:
        meta = card["metadata"]
        if meta["scenario_id"] in drop:
            continue
        if approve_drafts and meta["review_status"] == "pending":
            meta["review_status"] = "approved"
            meta["reviewer"] = "test-copy"
        kept.append(card)
    path.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
    return path


def holdout_ids_of(path: Path) -> set[str]:
    cards = json.loads(path.read_text(encoding="utf-8"))
    return {card["metadata"]["scenario_id"] for card in cards if card["metadata"]["split"] == "holdout"}


def only_run_dir(out: Path) -> Path:
    runs = sorted((out / "measurement").iterdir())
    assert len(runs) == 1
    return runs[0]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def episode_lines(run_dir: Path) -> list[dict]:
    return [json.loads(line) for line in (run_dir / "episodes.jsonl").read_text(encoding="utf-8").splitlines()]


def assert_protocol_outputs(run_dir: Path, holdout_ids: set[str]) -> None:
    """두 측정이 공통으로 지켜야 할 산출물: 파일 4개, 1라운드 9 + 18, pilot 재실행 없음, 풀과 holdout 분리, P5 판정."""
    # 1단계: 산출물 파일이 모두 있다.
    missing = [name for name in OUTPUT_FILES if not (run_dir / name).is_file()]
    assert missing == []

    # 2단계: 1라운드는 pilot 9건을 다시 돌리지 않고 새 18건만 돌렸다.
    round_one = read_json(run_dir / "round-1.json")
    assert (round_one["traffic"]["pilot_episodes"], round_one["traffic"]["new_episodes"]) == (9, 18)
    pool_one = read_json(run_dir / "pools" / "pool-round-1.json")["episodes"]
    item_counts = Counter(episode["scenario_or_item_id"] for episode in pool_one)
    assert item_counts == Counter(item.item_id for item in round_items(1))

    # 3단계: holdout 사례는 어느 라운드의 재생 풀에도 없다(ID 그대로든 항목 ID 끝부분이든).
    pooled = [episode["scenario_or_item_id"] for pool in sorted((run_dir / "pools").glob("pool-round-*.json"))
              for episode in read_json(pool)["episodes"]]
    leaked = [item for item in pooled for case in holdout_ids if item == case or item.endswith(f"-{case}")]
    assert leaked == []

    # 4단계: holdout 판정은 P5의 세 판정 중 하나이고, manifest에도 같은 값이 남았다.
    decision = read_json(run_dir / "holdout.json")["decision"]
    assert decision in DECISIONS
    assert read_json(run_dir / "run_manifest.json")["decision"] == decision


# ---------------------------------------------------------------- 계획 모드(플래그 없음)

def test_no_flag_prints_plan_with_1080_and_makes_no_calls(tmp_path, capsys):
    agent = NotebookAgentModel()
    code = run_measurement.main(["--out", str(tmp_path)], offline_agent=agent)
    printed = capsys.readouterr().out
    assert (code, "1,080" in printed, agent.calls) == (0, True, 0)
    assert list(tmp_path.iterdir()) == []


def test_no_flag_cli_exits_0_and_names_pending_drafts():
    done = subprocess.run([sys.executable, str(RUN_MEASUREMENT)], capture_output=True, text=True, timeout=120,
                          check=False)
    pending = pending_ids(REAL_SCENARIOS, split="holdout")
    assert done.returncode == 0
    assert "1,080" in done.stdout
    assert all(case in done.stdout for case in pending)


# ---------------------------------------------------------------- 사전 점검

def test_strict_preflight_refuses_real_scenarios_while_drafts_are_pending(tmp_path, capsys):
    pending = pending_ids(REAL_SCENARIOS, split="holdout")
    # 이 시험의 전제다. 저자가 초안을 모두 승인하면 전제가 바뀌므로 이 시험을 고쳐야 한다(건너뛰지 않는다).
    assert pending, "data/scenarios.json의 holdout 초안이 모두 승인되었습니다. 이 시험의 전제를 고치세요."
    code = run_measurement.main(["--offline", "--out", str(tmp_path)])
    printed = capsys.readouterr().out
    assert code == run_measurement.EXIT_PREFLIGHT
    assert f"초안이 {len(pending)}건" in printed
    assert not (tmp_path / "measurement").exists()


def test_preflight_refuses_holdout_without_exactly_six_cases(tmp_path, capsys):
    scenarios = write_scenarios(tmp_path / "scenarios.json", drop=("hv-missing-id",))
    code = run_measurement.main(["--offline", "--scenarios", str(scenarios), "--out", str(tmp_path / "out")])
    printed = capsys.readouterr().out
    assert code == run_measurement.EXIT_PREFLIGHT
    assert "holdout 사례가 5개입니다" in printed
    assert not (tmp_path / "out" / "measurement").exists()


def test_live_preflight_stops_on_missing_keys_before_any_call(tmp_path, capsys):
    # conftest가 .env 읽기를 끄고 키 환경 변수를 지웠으므로 모든 키가 미설정이다.
    scenarios = write_scenarios(tmp_path / "scenarios.json")
    code = run_measurement.main(["--live", "--scenarios", str(scenarios), "--out", str(tmp_path / "out")])
    printed = capsys.readouterr().out
    assert code == run_measurement.EXIT_PREFLIGHT
    assert "ANTHROPIC_API_KEY 미설정" in printed
    assert "ANTHROPIC_API_KEY가 미설정입니다" in printed
    assert not (tmp_path / "out" / "measurement").exists()


def test_live_and_offline_together_is_a_usage_error():
    with pytest.raises(SystemExit) as stopped:
        run_measurement.main(["--live", "--offline"])
    assert stopped.value.code == 2


def test_measurement_dir_is_new_every_time(tmp_path):
    first = run_measurement.new_measurement_dir(tmp_path)
    second = run_measurement.new_measurement_dir(tmp_path)
    assert first != second
    assert [path.parent for path in (first, second)] == [tmp_path / "measurement"] * 2


# ---------------------------------------------------------------- 오프라인 측정 끝까지

def test_violating_pilot_keeps_live_operations(tmp_path):
    scenarios = write_scenarios(tmp_path / "scenarios.json")
    out = tmp_path / "out"
    agent = WriteFirstAgent()
    code = run_measurement.main(["--offline", "--scenarios", str(scenarios), "--out", str(out)], offline_agent=agent)
    assert code == run_measurement.EXIT_OK
    run_dir = only_run_dir(out)
    assert_protocol_outputs(run_dir, holdout_ids_of(scenarios))

    # pilot에서 치명 위반이 나왔으므로 전환하지 않는다.
    manifest = read_json(run_dir / "run_manifest.json")
    pilot = read_json(run_dir / "round-1.json")["pilot"]
    with_order = sum(1 for item in pilot_items() if item.request.order_id)
    assert (pilot["switch_to_scripted"], pilot["fatal_episodes"], manifest["fallback"]["switched"]) == (False, with_order, False)

    # 운영 단계도 가짜 에이전트(실제 모델 자리)가 돌았다: 라운드 Episode가 모델을 불렀다.
    round_calls = [line["summary"]["usage"]["model_calls"] for line in episode_lines(run_dir)
                   if line["stage"] in ("round-1", "round-2")]
    assert len(round_calls) == 18 + 27
    assert min(round_calls) > 0


def test_clean_pilot_switches_operations_to_scripted_and_records_it(tmp_path):
    scenarios = write_scenarios(tmp_path / "scenarios.json")
    out = tmp_path / "out dir 측정"
    agent = NotebookAgentModel()
    code = run_measurement.main(["--offline", "--scenarios", str(scenarios), "--out", str(out)], offline_agent=agent)
    assert code == run_measurement.EXIT_OK
    run_dir = only_run_dir(out)
    assert_protocol_outputs(run_dir, holdout_ids_of(scenarios))

    # 전환이 라운드 기록과 manifest에 남고, 쓴 실수 확률과 seed가 기록된다.
    manifest = read_json(run_dir / "run_manifest.json")
    assert read_json(run_dir / "round-1.json")["pilot"]["switch_to_scripted"] is True
    fallback = manifest["fallback"]
    assert (fallback["switched"], fallback["mistake_rates"], fallback["seed"]) == (
        True, run_measurement.FALLBACK_MISTAKE_RATES, run_measurement.FALLBACK_SEED)

    # 운영 단계만 scripted(모델 0회)이고, pilot과 holdout은 여전히 에이전트를 불렀다.
    calls_by_stage: dict[str, list[int]] = {}
    for line in episode_lines(run_dir):
        calls_by_stage.setdefault(line["stage"], []).append(line["summary"]["usage"]["model_calls"])
    assert {stage: len(calls) for stage, calls in calls_by_stage.items()} == {
        "pilot": 9, "round-1": 18, "round-2": 27, "holdout-pi0": 18, "holdout-pistar": 18}
    assert max(calls_by_stage["round-1"] + calls_by_stage["round-2"]) == 0
    live = calls_by_stage["pilot"] + calls_by_stage["holdout-pi0"] + calls_by_stage["holdout-pistar"]
    assert min(live) > 0


def test_manifest_records_settings_thresholds_versions_and_calls(tmp_path):
    scenarios = write_scenarios(tmp_path / "scenarios.json")
    out = tmp_path / "out"
    agent = NotebookAgentModel()
    run_measurement.main(["--offline", "--no-langfuse", "--scenarios", str(scenarios), "--out", str(out)],
                         offline_agent=agent)
    run_dir = only_run_dir(out)
    manifest = read_json(run_dir / "run_manifest.json")
    recorded_hash = (DATA.parent / "docs" / "prereg.sha256").read_text(encoding="utf-8").strip()

    assert (manifest["status"], manifest["mode"], manifest["langfuse"]) == ("completed", "offline", False)
    assert manifest["prereg_sha256"] == recorded_hash
    assert manifest["thresholds"] == {"t_lo": 0.2, "t_hi": 0.8, "status": "미조정"}
    assert manifest["models"]["judge"] == {"model": "claude-sonnet-5-5", "effort": "xhigh",
                                           "class": "NotebookJudgeModel"}
    assert (manifest["release"], manifest["version_labels"]["round-1"], manifest["version_labels"]["round-2"]) == (
        "baseline", "r0", "r1")
    assert manifest["planned_calls_max"] == {"agent": 1080, "jev": 36, "judge": 108, "improver": 6}
    # Jev는 holdout Episode마다 한 번, 가짜 Jev 대본은 질문 3개 중 next_step_clear(0.5) 하나만 Judge로 넘긴다.
    # 개선기는 라운드마다 한 번이다. 에이전트 호출 수는 Episode 요약의 model_calls 합과 같다.
    agent_calls = sum(line["summary"]["usage"]["model_calls"] for line in episode_lines(run_dir))
    assert manifest["calls"] == {"agent": agent_calls, "jev": 36, "judge": 36, "improver": 2,
                                 "escalation_rate": pytest.approx(1 / 3)}
    assert agent.calls == agent_calls
