"""환불 쓰기 게이트. 원장에 닿는 길은 gate_answer 하나이고, 판정은 코드가 한다."""
from __future__ import annotations

import re

from mas_lab.contracts import FinalAnswer, Outcome, Proposal
from mas_lab.desk import Desk
from mas_lab.ledger import GateDecision, check_refund, execute_approved

_BLOCKED = {"deny": "denied", "human_review": "human_review"}
# 질문의 결제 번호: P-7001, p-7001, P7001, p7001. "p7001을"처럼 조사가 바로 붙는다. 한글도 \w라 \b로는 끊지 못해 뒤는 ASCII 영문·숫자만 본다.
# 앞에 영문·숫자·하이픈이 붙은 꼴(XP-7001)은 읽지 않는다. 하이픈이 없는 꼴은 4자리 이상이고 영문·숫자가 뒤따르지 않을 때만 번호다. p99, p50, p7001a는 그냥 말이다.
_PAYMENT_ID = re.compile(r"(?<![A-Za-z0-9-])[Pp](?:-|(?=\d{4,}(?![A-Za-z0-9])))(\d+)")
_NOT_EXECUTED = "환불 제안이 없어 아무것도 실행하지 않았습니다. 사람이 확인합니다."
_UNCHECKED = "제안이 없고 질문이 아는 결제를 가리키지 않거나 모르는 번호가 섞여 코드 게이트가 이 판단을 검사하지 못했습니다."


def _named_payments(question: str) -> set[str]:
    return {f"P-{digits}" for digits in _PAYMENT_ID.findall(question)}


def refund_decision(proposal: Proposal, desk: Desk, question: str) -> GateDecision:
    """check_refund에 질문과의 대조를 더한다. 고객이 말한 결제와 다른 제안은 정책을 통과해도 사람이 승인하기 전에는 실행하지 않는다."""
    decision = check_refund(proposal, desk.payments(), desk.scope.as_of)
    named = _named_payments(question)
    if not named or proposal.payment_id in named or decision.decision in _BLOCKED:
        return decision
    reason = f"질문이 가리킨 결제({', '.join(sorted(named))})와 제안한 결제({proposal.payment_id})가 달라 승인 전에는 실행하지 않습니다."
    return GateDecision(decision="needs_approval", reasons=[*decision.reasons, reason])


def gate_answer(final: FinalAnswer, desk: Desk, *, approved: bool | None = None, request_id: str = "req", question: str = "") -> FinalAnswer:
    """모든 구조의 쓰기 경로. 어떤 구조도 이 함수를 지나지 않고 원장에 닿지 못한다."""
    proposal = final.proposal
    if proposal is None or proposal.action != "refund":
        return check_named_payment(final, desk, question)
    proposal = proposal.model_copy(update={"idempotency_key": f"{request_id}:{proposal.payment_id}"})
    decision = refund_decision(proposal, desk, question)
    result = execute_approved(proposal, decision, desk.ledger, approved=bool(approved))
    if result["executed"]:
        outcome = "executed"
    elif decision.decision == "needs_approval":
        outcome = "denied" if approved is False else "needs_approval"
    else:
        outcome = _BLOCKED[decision.decision]
    return _settle(final.model_copy(update={"proposal": proposal}), desk, outcome, _notes(proposal.payment_id, decision),
                   blocked=decision.decision in _BLOCKED, events=[("gate", decision.model_dump())])


def check_named_payment(final: FinalAnswer, desk: Desk, question: str) -> FinalAnswer:
    """제안 없이 낸 답을 질문이 가리킨 결제와 대조한다. 번호는 질문에서만 읽고(답 본문은 검사받는 쪽의 주장이다), 판정만 받은 탐침은 allow여도 실행하지 않는다. 검사하지 못한 환불 질문은 desk에서 번호 목록마다 gate_skipped 사건 하나를 남기고 답은 바꾸지 않는다."""
    if final.outcome == "out_of_scope" or (final.proposal and final.proposal.action == "refund"):
        return final
    payments, named = {p["payment_id"]: p for p in desk.payments()}, _named_payments(question)
    checkable, claims_a_block = bool(named) and named <= payments.keys(), final.outcome in _BLOCKED.values()
    if not checkable and claims_a_block:
        return _settle(final, desk, final.outcome, [_UNCHECKED], blocked=False, events=[("gate_skipped", {"named": sorted(named)})])
    if not checkable:  # 막는 레이블을 단 답은 위에서 끝났다. 여기 남은 답은 레이블이 막지 않으니 답은 그대로 두고 검사하지 못했다는 흔적만 남긴다.
        unchecked = sorted(named)  # 같은 번호 목록의 사건만 이미 쓴 것이다. hybrid는 turn마다 같은 desk에서 부르고, runner는 그래프 뒤에 다시 부른다.
        if "환불" in question and not any(event["kind"] == "gate_skipped" and event["named"] == unchecked for event in desk.trace.events):
            desk.trace.event("gate_skipped", "code", named=unchecked)
        return final
    if not (claims_a_block or "환불" in question):
        return final
    probes = {payment_id: check_refund(Proposal(action="refund", payment_id=payment_id, amount=payments[payment_id]["amount"]), desk.payments(), desk.scope.as_of)
              for payment_id in sorted(named)}
    decisions = {decision.decision for decision in probes.values()}
    notes = [note for payment_id, decision in probes.items() for note in _notes(payment_id, decision)]
    if decisions - _BLOCKED.keys():
        notes.append(_NOT_EXECUTED)
    # 탐침은 모두 denied나 human_review로 끝나므로 어느 쪽이든 코드가 막은 답이다.
    return _settle(final, desk, "denied" if decisions == {"deny"} else "human_review", notes, blocked=True,
                   events=[("gate", {"probe": True, "payment_id": payment_id, **decision.model_dump()}) for payment_id, decision in probes.items()])


def _notes(payment_id: str, decision: GateDecision) -> list[str]:
    return [f"{payment_id or '결제 번호 없음'}: {reason}" for reason in decision.reasons]


def _settle(final: FinalAnswer, desk: Desk, outcome: Outcome, notes: list[str], *, blocked: bool, events: list[tuple[str, dict]]) -> FinalAnswer:
    """코드 판정을 답에 옮긴다. runner가 그래프 뒤에 다시 부르므로 이미 옮긴 답에는 문장도 불확실성도 사건도 더하지 않는다."""
    fresh = [note for note in notes if note not in final.uncertainty]
    if fresh or outcome != final.outcome:
        for kind, details in events:
            desk.trace.event(kind, "code", **details)
    update = {"outcome": outcome, "uncertainty": [*final.uncertainty, *fresh]}
    if blocked and outcome != final.outcome:  # 게이트가 거절한 결론을 고객이 읽지 않게 한다.
        update |= {"text": " ".join(notes), "uncertainty": notes, "proposal": final.proposal if final.proposal and final.proposal.action == "refund" else None}
        desk._register(f"F-GATE-{outcome}", update["text"])
        desk.trace.event("gate_text_replaced", "code", replaced=final.text[:80], dropped_uncertainty=[line for line in final.uncertainty if line not in notes])
        return final.model_copy(update=update)
    missing = [note for note in notes if note.rpartition(": ")[2] not in final.text] if blocked else []  # 비교는 번호 뺀 이유 문장으로 한다.
    if missing:
        appended = " ".join(missing)
        update["text"] = f"{final.text} {appended}"
        desk._register(f"F-GATE-{outcome}", appended)  # 코드가 쓴 문장만 출처다. 모델 문장의 숫자를 출처로 올리면 금액 검사가 뚫린다.
        desk.trace.event("gate_text_appended", "code", appended=missing)
    return final.model_copy(update=update)
