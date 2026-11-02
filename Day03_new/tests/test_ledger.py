from datetime import date

import pytest

from mas_lab.contracts import Proposal
from mas_lab.desk import load_billing
from mas_lab.ledger import APPROVAL_THRESHOLD, REFUND_WINDOW_DAYS, GateDecision, PaymentLedger, ResponseLost, check_refund, execute_approved
from rag_lab.settings import ROOT

AS_OF = date(2026, 9, 8)


def refund(payment_id, amount):
    return Proposal(action="refund", payment_id=payment_id, amount=amount)


@pytest.mark.parametrize(("entity", "payment_id", "amount", "decision"), [
    ("알파", "P-9002", 1200000, "needs_approval"), ("알파", "P-9001", 1200000, "deny"), ("알파", "P-8101", 1000000, "deny"),
    ("알파", "P-7002", 1000000, "human_review"), ("베타", "P-5002", 300000, "allow"), ("알파", "P-5002", 300000, "deny"),
    ("알파", "P-7777", 1000, "deny"), ("알파", "P-9002", 999, "deny")])
def test_gate_decisions(entity, payment_id, amount, decision):
    assert check_refund(refund(payment_id, amount), load_billing(entity), AS_OF).decision == decision


def test_gate_constants_match_the_policy_document():
    text = (ROOT / "data/business/billing-policy.md").read_text(encoding="utf-8")
    assert f"결제일부터 {REFUND_WINDOW_DAYS}일 이내" in text
    assert APPROVAL_THRESHOLD == 1_000_000 and "100만원을 초과하면 재무 담당자 승인" in text


@pytest.mark.parametrize(("decision", "approved", "executed"), [
    ("allow", False, True), ("needs_approval", False, False), ("needs_approval", True, True),
    ("deny", True, False), ("human_review", True, False)])
def test_execute_only_when_permitted(decision, approved, executed):
    ledger = PaymentLedger()
    result = execute_approved(refund("P-1", 10), GateDecision(decision=decision, reasons=[]), ledger, approved=approved)
    assert result["executed"] is executed and len(ledger.refunds) == int(executed)


def test_lost_response_duplicates_without_key_and_not_with_key():
    without = PaymentLedger()
    with pytest.raises(ResponseLost):
        without.refund("P-1", 10, lose_response=True)
    without.refund("P-1", 10)
    assert len(without.refunds) == 2
    keyed = PaymentLedger()
    with pytest.raises(ResponseLost):
        keyed.refund("P-1", 10, idempotency_key="k", lose_response=True)
    assert keyed.find("k") is not None
    assert keyed.refund("P-1", 10, idempotency_key="k")["refund_id"] == "R-0001" and len(keyed.refunds) == 1
