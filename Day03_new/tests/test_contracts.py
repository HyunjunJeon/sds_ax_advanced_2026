import pytest
from pydantic import ValidationError

from mas_lab.contracts import (FailureKind, FinalAnswer, Proposal, WorkerResult, classify_failure, join_results, merge_results,
                               next_action, plan_hash, trim_payload, validate_final, validate_result)
from rag_lab.evidence import BudgetExceeded


def test_merge_results_rejects_conflict_and_accepts_same_value():
    assert merge_results({"a": 1}, {"a": 1, "b": 2}) == {"a": 1, "b": 2}
    with pytest.raises(ValueError, match="상충"):
        merge_results({"a": 1}, {"a": 2})


def test_schema_and_evidence_are_different_checks():
    with pytest.raises(ValidationError):
        WorkerResult(status="done")
    forged = WorkerResult(status="complete", facts=["x"], evidence_refs=["lookup_outage: 8월 장애"])
    assert any("등록되지 않은" in p for p in validate_result(forged, {"F-AV-2026-08"}))
    assert any("근거 없이" in p for p in validate_result(WorkerResult(status="complete"), set()))
    assert validate_result(WorkerResult(status="complete", facts=["x"], evidence_refs=["E-1"]), {"E-1"}) == []


def test_validate_final_checks_amounts_against_sources():
    source = '{"availability_percent": 99.3, "credit": 150000} 해당 월 기본 이용료 15%'
    ok = FinalAnswer(outcome="answered", text="가용률 99.3%, 15%, 150,000원입니다.", evidence_refs=["E-1"])
    assert validate_final(ok, {"E-1"}, source) == []
    wrong = FinalAnswer(outcome="answered", text="크레딧은 180,000원입니다.", evidence_refs=["E-1"])
    assert validate_final(wrong, {"E-1"}, source) == ["출처에 없는 금액·비율: 180000"]


def test_payment_numbers_are_not_amounts():
    final = FinalAnswer(outcome="insufficient", text="P-7777을 찾지 못했습니다.")
    assert validate_final(final, set(), "") == []


def test_needs_approval_requires_a_proposal():
    bare = FinalAnswer(outcome="needs_approval", text="승인이 필요합니다.")
    assert any("환불 제안" in p for p in validate_final(bare, set(), ""))
    with_proposal = bare.model_copy(update={"proposal": Proposal(action="refund", payment_id="P-9002", amount=1)})
    assert validate_final(with_proposal, set(), "") == []


def test_join_results_exposes_missing_failed_and_latest_attempt():
    done = WorkerResult(status="complete", facts=["x"], evidence_refs=["E"])
    failed = WorkerResult(status="failed", error="TimeoutError")
    info = join_results({"billing": done, "outage": failed}, ["billing", "outage", "policy"])
    assert not info["ready"] and info["failed"] == ["outage"] and info["missing"] == ["policy"]
    recovered = join_results({"billing": done, "outage": failed, "outage#2": done}, ["billing", "outage"])
    assert recovered["ready"] and recovered["failed"] == []


def test_join_results_is_not_ready_for_a_failure_alone_or_a_missing_task_alone():
    done = WorkerResult(status="complete", facts=["x"], evidence_refs=["E"])
    failed_only = join_results({"billing": done, "outage": WorkerResult(status="failed", error="TimeoutError")}, ["billing", "outage"])
    missing_only = join_results({"billing": done}, ["billing", "policy"])
    assert (failed_only["missing"], failed_only["failed"]) == ([], ["outage"])
    assert failed_only["ready"] is False
    assert (missing_only["missing"], missing_only["failed"]) == (["policy"], [])
    assert missing_only["ready"] is False


def test_trim_payload_keeps_refs_and_uncertainty_until_the_end():
    result = WorkerResult(status="complete", facts=["사실 하나", "사실 둘"], evidence_refs=["E-1"], uncertainty=["미확인"])
    quotes = {"E-1": "가" * 300, "E-2": "나" * 300}
    full = trim_payload(result, quotes, 100000)
    assert full["dropped"] == [] and not full["over_budget"]
    tiny = trim_payload(result, quotes, 10)
    assert tiny["over_budget"] and tiny["payload"]["evidence_refs"] == ["E-1"] and tiny["payload"]["uncertainty"] == ["미확인"]
    assert tiny["dropped"][0].startswith("인용:") and tiny["payload"]["quotes"] == {} and tiny["payload"]["facts"] == []


def test_plan_hash_is_order_insensitive_for_keys_and_sensitive_to_values():
    assert plan_hash({"a": 1, "b": 2}) == plan_hash({"b": 2, "a": 1})
    assert plan_hash({"a": 1}) != plan_hash({"a": 2})


@pytest.mark.parametrize(("kind", "retries", "budget", "action"), [
    (FailureKind.PASS, 0, False, "respond"), (FailureKind.INSUFFICIENT, 1, True, "reinvestigate"),
    (FailureKind.INSUFFICIENT, 0, True, "stop_with_reason"), (FailureKind.POLICY_DENIED, 3, True, "stop_with_reason"),
    (FailureKind.SYSTEM_ERROR, 1, True, "retry"), (FailureKind.SYSTEM_ERROR, 0, True, "escalate"),
    (FailureKind.BUDGET_EXCEEDED, 3, True, "stop_with_reason")])
def test_next_action_depends_on_failure_kind(kind, retries, budget, action):
    assert next_action(kind, retries_left=retries, budget_left=budget) == action


def test_classify_failure():
    answer = FinalAnswer(outcome="answered", text="x")
    assert classify_failure(BudgetExceeded("x"), None, []) is FailureKind.BUDGET_EXCEEDED
    assert classify_failure(TimeoutError(), None, []) is FailureKind.SYSTEM_ERROR
    assert classify_failure(None, answer, []) is FailureKind.PASS
    assert classify_failure(None, answer, ["문제"]) is FailureKind.INSUFFICIENT
    assert classify_failure(None, answer.model_copy(update={"outcome": "denied"}), []) is FailureKind.POLICY_DENIED
