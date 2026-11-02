"""실행과 채점을 분리하고 같은 조건의 원자료를 비교한다.

`Day05/business_lab/lesson_runs.py`를 이식했다. 모든 예정 시도를 기록하고, 기록의 해시를 확인한 후
재채점한다. 모델 호출 함수는 비용을 먼저 알린다.

원본과 다른 점:
- 모델·Judge·Langfuse 클라이언트를 이 모듈이 만들지 않는다. 호출한 쪽이 넘긴다
  (노트북은 eval_lab.settings의 make_agent_model, make_judge_model, make_langfuse를 쓴다).
- 실행 조건(execution_contract)은 넘겨받은 모델 객체에서 읽는다. ChatAnthropic은 temperature를
  보내지 않으므로 temperature 대신 effort(reasoning_effort)를 비교 조건으로 고정한다.
- Langfuse 기록은 Episode마다 root observation 하나다(episodes.execute_episode). Dataset 실험
  (run_experiment) 경로는 이 모듈에 없다.
- 하네스 게이트(gate)를 넘길 수 있다. 게이트는 Prompt처럼 비교 대상 변수이므로 이름만 따로 기록한다.
"""

import hashlib
import inspect
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from eval_lab.agent import MAX_MODEL_CALLS, RECURSION_LIMIT, Gate
from eval_lab.contracts import Artifact, Scenario, Verdict
from eval_lab.dataset import fingerprint
from eval_lab.environment import MAX_TOOL_CALLS, WRITE_TOOLS
from eval_lab.episodes import execute_episode
from eval_lab.evaluators import (
    EVALUATOR_VERSION,
    RESPONSE_RUBRIC_VERSION,
    evaluate,
    judge_response,
)
from eval_lab.reporting import compare
from eval_lab.storage import make_run_id, save_run_report

PACKAGE = Path(__file__).parent
# 실행 결과에 영향을 주는 코드. 이 파일들의 해시가 다르면 두 원자료를 비교하지 않는다.
# settings.py는 넣지 않는다. 모델 설정은 execution_contract가 넘겨받은 모델 객체에서 직접 읽는다.
EXECUTION_FILES = ("agent.py", "environment.py", "contracts.py", "episodes.py")
# 채점 결과에 영향을 주는 코드.
EVALUATION_FILES = ("evaluators.py", "runs.py", "reporting.py")
# baseline과 candidate가 같아야 하는 실행 조건. Prompt와 게이트는 비교 대상이라 넣지 않는다.
PROTOCOL_KEYS = ("agent_model", "agent_effort", "agent_endpoint_hash", "mode", "max_model_calls",
                 "max_tool_calls", "recursion_limit", "max_tokens", "timeout_seconds", "max_retries",
                 "code_hashes", "lock_hash", "repeats")


def model_label(model) -> str | None:
    """모델 객체의 이름. ChatAnthropic은 model, 다른 채팅 모델은 model_name, 없으면 클래스 이름이다."""
    if model is None:
        return None
    return getattr(model, "model", None) or getattr(model, "model_name", None) or type(model).__name__


def gate_label(gate: Gate | None) -> str | None:
    """게이트를 기록할 이름. 게이트가 없으면 None, 있으면 함수 이름(없으면 클래스 이름)이다."""
    if gate is None:
        return None
    return getattr(gate, "__name__", None) or type(gate).__name__


def execution_contract(mode: str, model=None) -> dict:
    """비교에서 고정할 실행 설정. Prompt와 게이트는 별도 기록하므로 이 값에는 넣지 않는다.

    live면 넘겨받은 모델 객체에서 이름, effort, 엔드포인트(해시만), max_tokens, 제한 시간, 재시도를 읽는다.
    scripted면 모델 관련 값은 모두 None이다. 키 값은 읽지도 기록하지도 않는다.
    """
    # 1단계: 모델 설정을 읽는다. scripted에는 모델이 없다.
    is_live = mode == "live"
    endpoint = getattr(model, "anthropic_api_url", None) if is_live else None
    contract = {
        "mode": mode,
        "agent_model": model_label(model) if is_live else None,
        "agent_effort": getattr(model, "reasoning_effort", None) if is_live else None,
        "agent_endpoint_hash": fingerprint(endpoint),
        "max_model_calls": MAX_MODEL_CALLS,
        "max_tool_calls": MAX_TOOL_CALLS,
        "recursion_limit": RECURSION_LIMIT,
        "max_tokens": getattr(model, "max_tokens", None) if is_live else None,
        "timeout_seconds": getattr(model, "default_request_timeout", None) if is_live else None,
        "max_retries": getattr(model, "max_retries", None) if is_live else None,
    }
    # 2단계: 실행 코드와 잠금 파일의 해시를 고정한다.
    contract["code_hashes"] = {name: hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest()
                               for name in EXECUTION_FILES}
    contract["lock_hash"] = hashlib.sha256((PACKAGE.parent.parent / "uv.lock").read_bytes()).hexdigest()
    return contract


def save_recording(report: dict, out: Path) -> None:
    """평가 전에 저장한다. 해시는 원자료의 실수로 인한 변경을 검출하며 전자서명은 아니다."""
    report.pop("recording_hash", None)
    report["recording_hash"] = fingerprint(report)
    save_run_report(report, out)


def read_recording(path: Path) -> dict:
    """저장한 원자료를 읽는다. 기록 해시나 데이터 스냅샷 해시가 맞지 않으면 ValueError를 낸다."""
    data = json.loads(path.read_text())
    expected_hash = data.get("recording_hash")
    body = {k: v for k, v in data.items() if k != "recording_hash"}
    if data.get("kind") != "recording" or expected_hash != fingerprint(body):
        raise ValueError("실행 원자료가 아니거나 기록 내용이 변경됐습니다.")
    if data["snapshot_hash"] != fingerprint(data["snapshot"]):
        raise ValueError("실행에 사용한 데이터 스냅샷이 변경됐습니다.")
    return data


def record_release(frozen: dict, *, release: str, prompt: str, repeats: int, mode: str, out: Path,
                   model=None, langfuse=None, gate: Gate | None = None) -> dict:
    """동결 데이터의 한 Agent 버전을 실행한다. 평가하지 않는다. 실패한 시도도 원자료에 남긴다.

    계약:
    - mode="live"면 model이 필요하다(eval_lab.settings.make_agent_model로 만든다). 없으면 ValueError.
    - langfuse를 넘기면 Episode마다 root observation 하나를 남기고 행에 trace_id를 적는다.
    - gate를 넘기면 모든 도구 호출이 게이트를 거친다. 게이트 이름은 config["gate"]에 남는다.
    - 실행 직전에 시도 수와 최대 모델 호출 규모를 출력한다.
    """
    # 1단계: 입력과 동결 상태를 확인한다.
    if release not in {"baseline", "candidate"} or repeats < 1 or mode not in {"live", "scripted"}:
        raise ValueError("실행 버전·반복·mode이 유효하지 않습니다.")
    if frozen["snapshot_hash"] != fingerprint(frozen["snapshot"]):
        raise ValueError("데이터가 동결 후 변경됐습니다.")
    cards = [Scenario.model_validate(c) for c in frozen["snapshot"]["cards"]]
    if not cards or any(c.metadata.review_status != "approved" for c in cards):
        raise ValueError("승인된 문항이 필요합니다.")

    # 2단계: 실행 규모를 먼저 알린다.
    attempts = len(cards) * repeats
    if mode == "live":
        if model is None:
            raise ValueError("live 실행에는 model이 필요합니다. eval_lab.settings.make_agent_model로 만들어 넘기세요.")
        print(f"이 실행은 {len(cards)}문항 × {repeats}회 × 1버전 = {attempts}시도, "
              f"Agent 최대 약 {attempts * MAX_MODEL_CALLS}회, Judge 0회입니다. 재시도로 증가할 수 있습니다.")
    else:
        print("모델 0회: scripted 계약 검증이며 LLM 성능 측정이 아닙니다.")
    if langfuse is not None:
        print(f"Langfuse에 Episode {attempts}개의 trace(root observation과 업무 observation)를 기록합니다. "
              "점수는 채점 단계에서 붙입니다.")

    # 3단계: 실행 전에 계획과 조건을 저장한다. 중간에 멈춰도 무엇을 하려 했는지 남는다.
    report = {"run_id": make_run_id(), "kind": "recording", "mode": mode, "release": release,
              "snapshot_hash": frozen["snapshot_hash"], "snapshot": deepcopy(frozen["snapshot"]),
              "dataset_run_id": frozen["run_id"], "status": "planned", "rows": [],
              "started_at": datetime.now(UTC).isoformat(),
              "config": {**execution_contract(mode, model), "repeats": repeats, "prompt": prompt,
                         "gate": gate_label(gate)},
              "plan": [{"scenario_id": c.metadata.scenario_id, "release": release, "trial": t,
                        "slice": c.metadata.slice, "split": c.metadata.split}
                       for t in range(1, repeats + 1) for c in cards]}
    save_recording(report, out)

    def attempt(card: Scenario, trial: int) -> None:
        artifact = execute_episode(card.input, report["snapshot"]["fixtures"][card.fixture_id],
                                   followups=card.followups, max_turns=card.max_turns,
                                   scenario_id=card.metadata.scenario_id, release=release, trial=trial,
                                   mode=mode, prompt=prompt, model=model, langfuse=langfuse, gate=gate)
        # root observation은 Episode가 끝나면 닫히므로, 턴 기록에 남은 trace ID를 쓴다.
        trace_id = next((turn.trace_id for turn in artifact.turns if turn.trace_id), None)
        report["rows"].append({"artifact": artifact.model_dump(), "trace_id": trace_id, "verdicts": []})
        save_recording(report, out)

    # 4단계: 모든 예정 시도를 실행한다. 실패해도 지금까지의 행을 저장한다.
    try:
        report["status"] = "running"
        for trial in range(1, repeats + 1):
            for card in cards:
                attempt(card, trial)
        report["status"] = "completed"
    except Exception as exc:
        report.update(status="interrupted", error_type=type(exc).__name__)
        raise
    finally:
        report["ended_at"] = datetime.now(UTC).isoformat()
        save_recording(report, out)
        if langfuse is not None:
            langfuse.flush()
    return report


def check_episode(artifact: Artifact, card: Scenario) -> Verdict:
    """첫 질문의 적절성과 전체 Episode의 종료 조건을 따로 확인한다."""
    expected_requests = [card.input, *[f.request for f in card.followups]]
    turns = artifact.turns
    if any(t.response is None for t in turns) or not turns:
        return Verdict(name="episode", status="INSUFFICIENT_EVIDENCE", passed=None, reason="턴 응답 근거 누락")
    ok = len(turns) == len(expected_requests)
    for index, turn in enumerate(turns):
        ok &= index < len(expected_requests) and turn.request == expected_requests[index]
        if index < len(card.followups):
            ok &= turn.response.kind == card.followups[index].when_response
        if turn.request.order_id is None:
            ok &= not any(e.tool in WRITE_TOOLS for e in artifact.events if e.event_id in turn.event_ids)
    return Verdict(name="episode", status="PASS" if ok else "FAIL", passed=bool(ok),
                   reason="턴별 입력·추가 질문·대상 확인 전 쓰기·최종 턴 도달을 검사")


def grade_recording(raw: dict, *, judge=None, extra_check=None) -> dict:
    """저장된 원자료를 채점한다. Agent는 재실행하지 않는다.

    계약:
    - judge는 호출한 쪽이 넘긴 DeepEval 호환 판사다. 넘기면 행마다 실제 모델 호출이 있다(먼저 규모를 알린다).
    - judge가 None이고 원자료가 live면 response_semantics를 INSUFFICIENT_EVIDENCE("Judge 미실행")로 남긴다.
    - extra_check는 고유한 이름의 Verdict를 돌려줘야 한다. 어기거나 예외가 나면 EVALUATOR_ERROR로 남긴다.
    """
    # 1단계: 원자료를 복사하고 채점 조건을 기록한다.
    report = deepcopy(raw)
    report.update(run_id=make_run_id(), kind="scored_recording", source_run_id=raw["run_id"],
                  source_recording_hash=report.pop("recording_hash"),
                  evaluator_version=EVALUATOR_VERSION)
    config = report["config"]
    config["response_rubric_version"] = RESPONSE_RUBRIC_VERSION
    config["evaluator_hash"] = fingerprint({
        name: hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() for name in EVALUATION_FILES})
    config["judge_model"] = judge.get_model_name() if judge is not None else None
    judge_keys = ("temperature", "reasoning_effort", "timeout", "max_retries", "structured_method")
    config["judge_settings"] = {k: getattr(judge, k, None) for k in judge_keys} if judge is not None else None
    if judge is not None:
        config["judge_endpoint_hash"] = fingerprint(getattr(judge, "base_url", None))
        print(f"이 채점은 Agent 재실행 0회, Judge 약 {len(raw['rows'])}~{len(raw['rows']) * 3}회입니다.")
    config["learner_hash"] = (hashlib.sha256(Path(inspect.getsourcefile(extra_check)).read_bytes()).hexdigest()
                              if extra_check else None)

    # 2단계: 행마다 업무 평가기, Episode 검사, 추가 검사, Judge 순으로 판정한다.
    cards = {c["metadata"]["scenario_id"]: Scenario.model_validate(c) for c in raw["snapshot"]["cards"]}
    for row in report["rows"]:
        artifact = Artifact.model_validate(row["artifact"])
        card = cards[artifact.scenario_id]
        checks = evaluate(artifact, card.expected_output.model_dump())
        checks.append(check_episode(artifact, card))
        if extra_check:
            try:
                check = extra_check(artifact)
                if not isinstance(check, Verdict) or check.name in {c.name for c in checks}:
                    raise ValueError("추가 평가기는 고유한 이름의 Verdict를 반환해야 합니다.")
                checks.append(check)
            except Exception as exc:  # noqa: BLE001 - 수강생 평가기의 실패를 EVALUATOR_ERROR로 남긴다.
                checks.append(Verdict(name="learner_check", status="EVALUATOR_ERROR", passed=None,
                                      reason=type(exc).__name__))
        if judge is not None:
            checks.append(judge_response(artifact, judge, card.expected_output))
        elif raw["mode"] == "live":
            checks.append(Verdict(name="response_semantics", status="INSUFFICIENT_EVIDENCE", passed=None,
                                  reason="Judge 미실행"))
        row["verdicts"] = [c.model_dump() for c in checks]
    return report


def assert_same_protocol(base: dict, candidate: dict) -> None:
    """baseline과 candidate 원자료가 같은 데이터·모델·코드·예산·반복 조건인지 확인한다. 다르면 ValueError."""
    if base["release"] != "baseline" or candidate["release"] != "candidate":
        raise ValueError("baseline과 candidate의 원자료가 필요합니다.")
    same_snapshot = base["snapshot_hash"] == candidate["snapshot_hash"]
    differing = [key for key in PROTOCOL_KEYS if base["config"].get(key) != candidate["config"].get(key)]
    if not same_snapshot or differing:
        raise ValueError("데이터·모델·업무 코드·예산·반복 조건이 다릅니다. 같은 조건으로 다시 실행하세요.")


def compare_scored(base: dict, candidate: dict) -> dict:
    """같은 판정 기준으로 채점한 두 버전의 모든 시도를 비교한다.

    Prompt와 게이트가 모두 같으면 바뀐 것이 없으므로 HOLD다.
    """
    # 1단계: 실행 조건과 채점 조건이 같은지 확인한다.
    assert_same_protocol(base, candidate)
    for key in ("response_rubric_version", "evaluator_hash", "judge_model", "judge_settings",
                "judge_endpoint_hash", "learner_hash"):
        if base["config"].get(key) != candidate["config"].get(key):
            raise ValueError("평가기·Judge·수강생 평가 코드가 다릅니다. 두 원자료를 함께 재채점하세요.")

    # 2단계: 두 버전의 행을 합쳐 비교한다.
    report = {"run_id": make_run_id(), "kind": "comparison", "mode": base["mode"],
              "snapshot_hash": base["snapshot_hash"], "snapshot": base["snapshot"],
              "config": base["config"], "source_runs": [base["source_run_id"], candidate["source_run_id"]],
              "evaluation_run_ids": [base["run_id"], candidate["run_id"]],
              "prompts": {"baseline": base["config"]["prompt"], "candidate": candidate["config"]["prompt"]},
              "gates": {"baseline": base["config"].get("gate"), "candidate": candidate["config"].get("gate")},
              "plan": [*base["plan"], *candidate["plan"]], "rows": [*base["rows"], *candidate["rows"]]}
    report["comparison"] = compare(report)

    # 3단계: 반복 단위 전이를 센다.
    transitions = {"improved": 0, "regressed": 0, "stable_pass": 0, "still_failing": 0, "uncomparable": 0}
    for pair in report["comparison"]["pairs"]:
        if pair["change"] == "uncomparable":
            bucket = "uncomparable"
        else:
            b, c = pair["baseline"]["all_pass"], pair["candidate"]["all_pass"]
            bucket = {(False, True): "improved", (True, False): "regressed",
                      (True, True): "stable_pass", (False, False): "still_failing"}[b, c]
        transitions[bucket] += 1
    report["comparison"]["all_repeat_transitions"] = transitions

    # 4단계: 후보가 바꾼 것이 없으면 판정을 보류한다.
    same_prompt = base["config"]["prompt"] == candidate["config"]["prompt"]
    same_gate = base["config"].get("gate") == candidate["config"].get("gate")
    if same_prompt and same_gate:
        report["comparison"]["decision"] = "HOLD"
        report["comparison"]["decision_reasons"].append("후보 프롬프트·게이트 변경 없음")
    return report
