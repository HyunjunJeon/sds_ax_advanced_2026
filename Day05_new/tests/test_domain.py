"""주문 취소 업무 영역(eval_lab)의 이식 동등성과 데이터 계약을 확인한다. 모델·네트워크 호출은 없다.

Day05/business_lab은 읽기 전용 기준으로만 불러온다. 이식한 평가자가 원본과 같은 판정을 내는지가 핵심이다.
"""

import json
import sys
from pathlib import Path

import pytest
from eval_lab import evaluators as new_evaluators
from eval_lab.contracts import Artifact, GateDecision, GateEvent
from eval_lab.dataset import DATA, load_dataset, load_fixtures, pending_ids
from eval_lab.environment import OrderEnvironment
from eval_lab.reporting import compare

REPO_ROOT = Path(__file__).resolve().parents[2]
DAY05_ROOT = REPO_ROOT / "Day05"

HOLDOUT_DRAFT_IDS = {"hv-timeout-after", "hv-foreign-order", "hv-shipping-race", "hv-missing-id"}


# ---------------------------------------------------------------- 원본(Day05) 불러오기

@pytest.fixture
def old_evaluators(monkeypatch):
    """Day05/business_lab.evaluators를 읽기 전용으로 불러온다.

    business_lab/__init__.py는 .env를 읽어 환경 변수에 올린다. 시험은 키를 만지지 않으므로
    dotenv.load_dotenv를 빈 함수로 바꾼 상태에서 import하고, 끝나면 모듈 캐시를 지운다.
    """
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.syspath_prepend(str(DAY05_ROOT))
    for name in [n for n in sys.modules if n == "business_lab" or n.startswith("business_lab.")]:
        monkeypatch.delitem(sys.modules, name)
    import business_lab.evaluators as module

    yield module
    for name in [n for n in sys.modules if n == "business_lab" or n.startswith("business_lab.")]:
        sys.modules.pop(name, None)


@pytest.fixture
def old_contracts(old_evaluators):
    """원본 Artifact 클래스. 이식본과 클래스가 달라 dict를 거쳐 옮긴다."""
    import business_lab.contracts as module

    return module


# ---------------------------------------------------------------- 합성 Artifact

def run_scripted(scenario, fixtures: dict):
    """시나리오 하나를 모델 없이 규칙대로 실행해 (환경, 초기 상태)를 돌려준다.

    규칙: 조회 -> 정책 확인 -> 취소 시작 -> 환불(TIMEOUT이면 원장 조회 후 같은 키로 재시도)
    -> 재고 복원 -> 완료 -> 최종 조회. 어디서든 ok가 아니면 그 자리에서 멈춘다.
    """
    env = OrderEnvironment(fixtures[scenario.fixture_id])
    initial_state = env.snapshot()
    oid = scenario.input.order_id
    if oid is None:
        return env, initial_state

    env.call("get_order", order_id=oid)
    policy = env.call("check_cancel_policy", order_id=oid)
    if policy.get("status") != "ok" or policy.get("allowed") is not True:
        return env, initial_state
    begin = env.call("begin_cancellation", order_id=oid, expected_version=policy["order_version"])
    if begin.get("status") != "ok":
        return env, initial_state

    payment = env.call("get_payment", order_id=oid)["payment"]
    amount = payment["captured_cents"] - payment["refunded_cents"]
    key = f"refund-{scenario.input.request_id}"
    refund = env.call("refund_payment", order_id=oid, amount_cents=amount, idempotency_key=key)
    if refund.get("code") == "TIMEOUT":
        observed = env.call("get_payment", order_id=oid)["payment"]
        if observed["captured_cents"] != observed["refunded_cents"]:
            env.call("refund_payment", order_id=oid, amount_cents=amount, idempotency_key=key)
    env.call("release_stock", order_id=oid, idempotency_key=f"release-{scenario.input.request_id}")
    env.call("complete_cancellation", order_id=oid)
    env.call("get_order", order_id=oid)
    return env, initial_state


def build_artifact(scenario, env, initial_state, *, trial: int = 1) -> dict:
    """환경이 기록한 근거로 Artifact dict를 만든다. 응답은 기대 응답 유형을 그대로 쓴다."""
    final_state = env.snapshot()
    expected = scenario.expected_output
    return {
        "artifact_id": f"art-{scenario.metadata.scenario_id}-{trial}",
        "scenario_id": scenario.metadata.scenario_id,
        "release": "baseline",
        "trial": trial,
        "request": scenario.input.model_dump(),
        "execution_status": "completed",
        "initial_state": initial_state,
        "final_state": final_state,
        "events": [event.model_dump() for event in env.events],
        "response": {
            "kind": expected.response_kind,
            "message": "처리 결과를 안내합니다.",
            "order_id": scenario.input.order_id,
            "refund_cents": final_state["payments"].get(scenario.input.order_id, {}).get("refunded_cents"),
        },
        "elapsed_seconds": 0.5,
    }


def verdict_dicts(verdicts) -> list[dict]:
    return [v.model_dump() for v in verdicts]


# ---------------------------------------------------------------- 데이터 계약

def test_dev_split_has_nine_approved_scenarios():
    scenarios = load_dataset(split="dev")
    assert len(scenarios) == 9
    assert all(s.metadata.review_status == "approved" for s in scenarios)
    assert not HOLDOUT_DRAFT_IDS & {s.metadata.scenario_id for s in scenarios}


def test_holdout_is_blocked_while_drafts_are_pending():
    with pytest.raises(ValueError, match="검수가 끝나지 않은 시나리오"):
        load_dataset(split="holdout")


def test_holdout_drafts_are_pending_new_families():
    rows = json.loads((DATA / "scenarios.json").read_text())
    drafts = [row for row in rows if row["metadata"]["scenario_id"] in HOLDOUT_DRAFT_IDS]
    assert {row["metadata"]["scenario_id"] for row in drafts} == HOLDOUT_DRAFT_IDS
    dev_families = {row["metadata"]["family_id"] for row in rows if row["metadata"]["split"] == "dev"}
    for row in drafts:
        meta = row["metadata"]
        assert meta["split"] == "holdout"
        assert meta["review_status"] == "pending"
        assert meta["reviewer"] == ""
        assert "저자 검수 대기" in meta["review_reason"]
        assert meta["family_id"] not in dev_families


def test_scenario_sources_point_to_files_inside_day05_new():
    rows = json.loads((DATA / "scenarios.json").read_text())
    assert len(rows) == 15
    for row in rows:
        source = row["metadata"]["source"]
        assert "business_lab/" not in source
        assert (DATA.parent / source.split("#")[0]).is_file(), source


def test_approved_only_holdout_returns_exactly_the_approved_cards():
    ids = {s.metadata.scenario_id for s in load_dataset(split="holdout", approved_only=True)}
    assert ids == {"resume-pending", "not-found"}


def test_pending_ids_lists_the_four_holdout_drafts_sorted():
    assert pending_ids(split="holdout") == sorted(HOLDOUT_DRAFT_IDS)
    assert pending_ids(split="dev") == []


def test_approved_only_dev_matches_strict_dev():
    strict = [s.metadata.scenario_id for s in load_dataset(split="dev")]
    relaxed = [s.metadata.scenario_id for s in load_dataset(split="dev", approved_only=True)]
    assert relaxed == strict


def test_approved_only_still_rejects_when_no_card_is_approved(tmp_path):
    rows = json.loads((DATA / "scenarios.json").read_text())
    drafts = [r for r in rows if r["metadata"]["scenario_id"] in HOLDOUT_DRAFT_IDS]
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps(drafts))
    with pytest.raises(ValueError, match="선택한 분할에 시나리오가 없습니다"):
        load_dataset(path, split="holdout", approved_only=True)


def test_every_fixture_id_exists():
    fixtures = load_fixtures()
    rows = json.loads((DATA / "scenarios.json").read_text())
    missing = [row["fixture_id"] for row in rows if row["fixture_id"] not in fixtures]
    assert missing == []


def test_artifact_without_gate_events_validates_with_empty_list():
    scenario = load_dataset(split="dev")[0]
    env, initial_state = run_scripted(scenario, load_fixtures())
    artifact = Artifact.model_validate(build_artifact(scenario, env, initial_state))
    assert artifact.gate_events == []


def test_artifact_accepts_gate_events():
    decision = GateDecision(action="block", rule_id="r1", reason="다른 고객 주문")
    event = GateEvent(event_id="g1", turn_index=1, tool="begin_cancellation", args={"order_id": "x"}, decision=decision)
    assert event.decision.action == "block"
    assert GateDecision(action="allow").rule_id is None
    with pytest.raises(ValueError):
        GateDecision(action="deny")


def test_environment_starts_with_empty_gate_events():
    env = OrderEnvironment(next(iter(load_fixtures().values())))
    assert env.gate_events == []


@pytest.mark.parametrize("scenario_id", sorted(HOLDOUT_DRAFT_IDS))
def test_holdout_draft_expectation_matches_scripted_run(scenario_id):
    """초안의 기대 상태가 새 숫자와 일치하는지, 규칙 실행 상태에서 상태 요약으로 확인한다."""
    rows = json.loads((DATA / "scenarios.json").read_text())
    fixtures = load_fixtures()
    row = next(r for r in rows if r["metadata"]["scenario_id"] == scenario_id)
    from eval_lab.contracts import Scenario

    scenario = Scenario.model_validate(row)
    env, _ = run_scripted(scenario, fixtures)
    actual = new_evaluators.state_summary(env.snapshot())
    assert actual == scenario.expected_output.final_state


# ---------------------------------------------------------------- 이식 동등성

def test_evaluate_equals_original_for_every_dev_scenario(old_evaluators, old_contracts):
    fixtures = load_fixtures()
    for scenario in load_dataset(split="dev"):
        env, initial_state = run_scripted(scenario, fixtures)
        data = build_artifact(scenario, env, initial_state)
        expected_output = scenario.expected_output.model_dump()

        new = new_evaluators.evaluate(Artifact.model_validate(data), expected_output)
        old = old_evaluators.evaluate(old_contracts.Artifact.model_validate(data), expected_output)

        assert verdict_dicts(new) == verdict_dicts(old), scenario.metadata.scenario_id


def _policy_of(verdicts):
    return next(v for v in verdicts if v.name == "policy")


def _both_policy_verdicts(old_evaluators, old_contracts, scenario, env, initial_state):
    data = build_artifact(scenario, env, initial_state)
    expected_output = scenario.expected_output.model_dump()
    new = new_evaluators.evaluate(Artifact.model_validate(data), expected_output)
    old = old_evaluators.evaluate(old_contracts.Artifact.model_validate(data), expected_output)
    return _policy_of(new), _policy_of(old)


def test_write_before_policy_check_fails_in_both(old_evaluators, old_contracts):
    scenario = next(s for s in load_dataset(split="dev") if s.metadata.scenario_id == "normal")
    env = OrderEnvironment(load_fixtures()[scenario.fixture_id])
    initial_state = env.snapshot()
    # 정책 확인 없이 곧바로 취소 시작: 선행 조건 위반이다.
    env.call("begin_cancellation", order_id=scenario.input.order_id, expected_version=1)

    new, old = _both_policy_verdicts(old_evaluators, old_contracts, scenario, env, initial_state)
    assert new.status == "FAIL" and old.status == "FAIL"
    assert new.model_dump()["reason"] == old.model_dump()["reason"]


def test_write_on_other_customers_order_fails_in_both(old_evaluators, old_contracts):
    scenario = next(s for s in load_dataset(split="dev") if s.metadata.scenario_id == "foreign-order")
    env = OrderEnvironment(load_fixtures()[scenario.fixture_id])
    initial_state = env.snapshot()
    # 인증 고객이 아닌 다른 고객의 주문에 쓰기를 시도한다. 서비스는 거절하지만 시도 자체가 위반이다.
    result = env.call("begin_cancellation", order_id=scenario.input.order_id, expected_version=1)
    assert result["status"] == "denied"

    new, old = _both_policy_verdicts(old_evaluators, old_contracts, scenario, env, initial_state)
    assert new.status == "FAIL" and old.status == "FAIL"


# ---------------------------------------------------------------- reporting.compare

def _row(release, scenario_id, trial, passed):
    names = ["outcome", "side_effects", "policy", "recovery", "response_contract"]
    verdicts = [{"name": n, "status": "PASS", "passed": True, "reason": "", "evidence_ids": []} for n in names]
    if not passed:
        verdicts[0] = {"name": "outcome", "status": "FAIL", "passed": False, "reason": "", "evidence_ids": []}
    artifact = {"release": release, "scenario_id": scenario_id, "trial": trial, "execution_status": "completed",
                "cost_usd": None, "events": [], "model_calls": 0, "elapsed_seconds": 1.0}
    return {"artifact": artifact, "verdicts": verdicts}


def test_compare_pass_at_k_and_pass_all_k():
    # baseline: 사례 a는 2회 중 1회 통과, 사례 b는 2회 모두 실패. candidate는 전부 통과.
    outcomes = {("baseline", "a", 1): True, ("baseline", "a", 2): False,
                ("baseline", "b", 1): False, ("baseline", "b", 2): False}
    outcomes.update({("candidate", sid, t): True for sid in "ab" for t in (1, 2)})
    plan = [{"release": r, "scenario_id": s, "trial": t, "slice": "s"} for (r, s, t) in outcomes]
    rows = [_row(r, s, t, passed) for (r, s, t), passed in outcomes.items()]

    result = compare({"plan": plan, "rows": rows, "mode": "scripted"})

    baseline = result["summaries"]["baseline"]
    candidate = result["summaries"]["candidate"]
    assert baseline["pass_at_k"] == 0.5
    assert baseline["pass_all_k"] == 0.0
    assert baseline["pass_rate"] == 0.25
    assert candidate["pass_at_k"] == 1.0 and candidate["pass_all_k"] == 1.0
    assert result["integrity_errors"] == []
    assert {p["scenario_id"]: p["change"] for p in result["pairs"]} == {"a": "improved", "b": "improved"}
