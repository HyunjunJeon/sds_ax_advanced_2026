"""쓰기 실행 층. 저장소 밖으로 아무것도 나가지 않는 가짜 결제 시스템과 코드 게이트다."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from mas_lab.contracts import Proposal

# data/business/billing-policy.md의 규칙과 같은 값이다. 테스트가 원문 행과 대조한다.
REFUND_WINDOW_DAYS = 90
APPROVAL_THRESHOLD = 1_000_000


class ResponseLost(TimeoutError):
    """외부 호출은 성공했지만 응답을 받지 못했다."""


class GateDecision(BaseModel):
    decision: Literal["allow", "needs_approval", "deny", "human_review"]
    reasons: list[str]


class PaymentLedger:
    """멱등은 이 '외부 시스템'이 강제한다. 실제 결제 API가 같은 보장을 준다고 가정하면 안 된다."""

    def __init__(self):
        self.refunds: list[dict] = []

    def find(self, idempotency_key: str) -> dict | None:
        """외부 결과 조회. 응답이 유실되면 재시도 전에 먼저 부른다."""
        return next((r for r in self.refunds if idempotency_key and r["idempotency_key"] == idempotency_key), None)

    def refund(self, payment_id: str, amount: int, *, idempotency_key: str = "", lose_response: bool = False) -> dict:
        record = self.find(idempotency_key)
        if record is None:
            record = {"refund_id": f"R-{len(self.refunds) + 1:04d}", "payment_id": payment_id, "amount": amount,
                      "idempotency_key": idempotency_key}
            self.refunds.append(record)
        if lose_response:
            raise ResponseLost(f"{record['refund_id']} 기록 뒤 응답 유실")
        return record


def check_refund(proposal: Proposal, payments: list[dict], as_of: date) -> GateDecision:
    """모델의 제안을 코드로 검사한다. payments는 현재 고객 범위의 결제뿐이다."""
    def decide(decision: str, reason: str) -> GateDecision:
        return GateDecision(decision=decision, reasons=[reason])

    if proposal.action != "refund":
        return decide("deny", "환불 제안이 아닙니다.")
    payment = next((p for p in payments if p["payment_id"] == proposal.payment_id), None)
    if payment is None:
        return decide("deny", f"이 고객의 결제에서 {proposal.payment_id}를 찾지 못했습니다.")
    same_invoice = sorted((p for p in payments if p["invoice_id"] == payment["invoice_id"]),
                          key=lambda p: p["approved_at"])
    if len(same_invoice) < 2:
        return decide("deny", f"청구서 {payment['invoice_id']}의 결제가 1건이라 중복 결제가 아닙니다.")
    if same_invoice[0]["payment_id"] == proposal.payment_id:
        return decide("deny", "먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.")
    if proposal.amount != payment["amount"]:
        return decide("deny", f"제안 금액 {proposal.amount}가 결제 금액 {payment['amount']}와 다릅니다.")
    if (as_of - datetime.fromisoformat(payment["approved_at"]).date()).days > REFUND_WINDOW_DAYS:
        return decide("human_review", f"결제일부터 {REFUND_WINDOW_DAYS}일이 지나 재무 담당자 심사로 넘깁니다.")
    if proposal.amount > APPROVAL_THRESHOLD:
        return decide("needs_approval", f"환불액이 {APPROVAL_THRESHOLD:,}원을 초과해 재무 담당자 승인이 필요합니다.")
    return decide("allow", "정책 검증을 통과했습니다.")


def execute_approved(proposal: Proposal, decision: GateDecision, ledger: PaymentLedger, *,
                     approved: bool = False, lose_response: bool = False) -> dict:
    """allow이거나, needs_approval에 승인이 있을 때만 원장을 부른다. 모델에게 도구로 주지 않는다."""
    permitted = decision.decision == "allow" or (decision.decision == "needs_approval" and approved)
    if not permitted:
        return {"executed": False, "decision": decision.decision, "reasons": decision.reasons}
    record = ledger.refund(proposal.payment_id, proposal.amount, idempotency_key=proposal.idempotency_key,
                           lose_response=lose_response)
    return {"executed": True, "decision": decision.decision, "record": record}
