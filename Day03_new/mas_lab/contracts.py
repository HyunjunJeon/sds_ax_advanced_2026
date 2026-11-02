"""Worker 사이의 입력·반환 계약. 스키마 통과와 근거 검증은 다른 검사다."""
from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from rag_lab.evidence import BudgetExceeded

Status = Literal["complete", "uncertain", "failed"]
Outcome = Literal["answered", "insufficient", "needs_approval", "denied", "human_review", "executed", "out_of_scope"]


class WorkerTask(BaseModel):
    """일을 나눠 보내는 쪽(그래프의 분배 노드)이 Worker에게 주는 것. 전체 대화가 아니라 이 작업에 필요한 만큼만 준다."""
    task_id: str
    goal: str
    facts: dict = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    attempt: int = 1


class WorkerResult(BaseModel):
    """Worker가 돌려주는 것. 요약이 아니라 사실, 근거, 불확실성을 함께 돌려준다."""
    task_id: str = ""
    attempt: int = 1
    status: Status
    facts: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    error: str = ""


class Proposal(BaseModel):
    """모델의 처리 제안. 실행 허가가 아니다."""
    action: Literal["refund", "none"] = "none"
    payment_id: str = ""
    amount: int = 0
    reason: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    idempotency_key: str = ""


class FinalAnswer(BaseModel):
    outcome: Outcome
    text: str
    evidence_refs: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    proposal: Proposal | None = None


class Route(BaseModel):
    """라우터의 판단. path는 비용을, owner는 담당자를, roles는 조사 범위를 정한다."""
    path: Literal["fast", "slow", "out_of_scope"]
    owner: Literal["billing", "technical"] = "billing"
    roles: list[Literal["billing", "policy", "outage"]] = Field(default_factory=list)
    reason: str = ""


_AMOUNT = re.compile(r"(?<![\w-])(?:\d[\d,]*(?:\.\d+)?%|\d{1,3}(?:,\d{3})+|\d{4,})")  # P-7777 같은 번호는 금액이 아니다.
_ANY_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _amounts(text: str) -> set[str]:
    """답에 쓴 금액과 비율."""
    return {n.replace(",", "").removesuffix("%") for n in _AMOUNT.findall(text)}


def _source_numbers(text: str) -> set[str]:
    """출처의 모든 숫자. 조회 결과의 99.3처럼 % 없이 저장된 값도 출처다."""
    return {n.replace(",", "") for n in _ANY_NUMBER.findall(text)}


def validate_result(result: WorkerResult, known_refs: set[str]) -> list[str]:
    """스키마를 통과한 뒤의 검사다. 없는 근거와 근거 없는 완료를 거절한다."""
    problems = [f"등록되지 않은 근거: {r}" for r in result.evidence_refs if r not in known_refs]
    if result.status == "complete" and not result.evidence_refs:
        problems.append("근거 없이 complete입니다.")
    if result.status == "failed" and result.facts:
        problems.append("failed인데 사실을 돌려줬습니다.")
    return problems


def validate_final(final: FinalAnswer, known_refs: set[str], source_text: str) -> list[str]:
    """인용 소속, 금액과 비율의 출처, outcome 일관성을 본다.

    금액과 비율만 검사한다. 날짜처럼 원문에 그대로 없는 계산 결과까지 막으면 올바른 답을 거절한다.
    숫자가 맞아도 문장의 뜻이 맞다는 보장은 아니다.
    """
    problems = [f"등록되지 않은 근거: {r}" for r in final.evidence_refs if r not in known_refs]
    problems += [f"출처에 없는 금액·비율: {n}" for n in sorted(_amounts(final.text) - _source_numbers(source_text))]
    if final.outcome == "answered" and not final.evidence_refs:
        problems.append("근거 없이 answered입니다.")
    if final.outcome == "needs_approval" and (final.proposal is None or final.proposal.action != "refund"):
        problems.append("needs_approval인데 환불 제안이 없습니다.")
    return problems


def merge_results(left: dict | None, right: dict | None) -> dict:
    """동시 Worker의 결과를 작업 ID로 합친다. 같은 값의 재전달은 통과, 상충은 거절한다."""
    merged = dict(left or {})
    for task_id, result in (right or {}).items():
        if task_id in merged and merged[task_id] != result:
            raise ValueError(f"같은 작업 ID의 상충 결과: {task_id}")
        merged[task_id] = result
    return merged


def _latest(results: dict, task_id: str):
    attempts = {1 if k == task_id else int(k.split("#")[1]): v for k, v in results.items()
                if k == task_id or k.startswith(task_id + "#")}
    return attempts[max(attempts)] if attempts else None


def join_results(results: dict, required: list[str]) -> dict:
    """필수 작업별 상태를 드러낸다. 재시도는 outage#2처럼 새 키로 쓰고 같은 작업의 마지막 시도를 읽는다.

    동시에 도는 두 시도의 늦은 도착까지 판별하지는 않는다.
    """
    rows, buckets = [], {"failed": [], "uncertain": [], "missing": []}
    for task_id in required:
        result = _latest(results, task_id)
        status = "결과 없음" if result is None else result.status
        rows.append({"작업": task_id, "상태": status, "사실 수": len(result.facts) if result else 0,
                     "근거 수": len(result.evidence_refs) if result else 0})
        if result is None:
            buckets["missing"].append(task_id)
        elif result.status != "complete":
            buckets[result.status].append(task_id)
    return {"ready": not buckets["failed"] and not buckets["missing"], "rows": rows, **buckets}


def trim_payload(result: WorkerResult, quotes: dict[str, str], max_bytes: int) -> dict:
    """정해진 순서로 항목 단위로 줄인다. 문장 중간을 자르지 않고, 근거 참조와 불확실성은 끝까지 남긴다."""
    payload = {"facts": list(result.facts), "evidence_refs": list(result.evidence_refs),
               "uncertainty": list(result.uncertainty), "quotes": dict(quotes)}
    dropped: list[str] = []

    def size() -> int:
        return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    while size() > max_bytes and payload["quotes"]:
        dropped.append("인용:" + payload["quotes"].popitem()[0])
    while size() > max_bytes and payload["facts"]:
        dropped.append("사실:" + payload["facts"].pop()[:20])
    return {"payload": payload, "bytes": size(), "dropped": dropped, "over_budget": size() > max_bytes}


def plan_hash(plan: dict | BaseModel) -> str:
    """분해가 같은지 증명한다. dict나 BaseModel을 정렬된 JSON으로 만들어 해시한다."""
    data = plan.model_dump() if isinstance(plan, BaseModel) else plan
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


class FailureKind(StrEnum):
    PASS = "pass"
    INSUFFICIENT = "insufficient"
    POLICY_DENIED = "policy_denied"
    SYSTEM_ERROR = "system_error"
    BUDGET_EXCEEDED = "budget_exceeded"


def classify_failure(error: Exception | None, final: FinalAnswer | None, problems: list[str]) -> FailureKind:
    if isinstance(error, BudgetExceeded):
        return FailureKind.BUDGET_EXCEEDED
    if error is not None or final is None:
        return FailureKind.SYSTEM_ERROR
    if final.outcome in {"denied", "human_review"}:
        return FailureKind.POLICY_DENIED
    if problems or final.outcome == "insufficient":
        return FailureKind.INSUFFICIENT
    return FailureKind.PASS


def next_action(kind: FailureKind, *, retries_left: int, budget_left: bool) -> str:
    """실패했다고 무조건 다시 부르지 않는다. 종류마다 다음 행동이 다르다."""
    if kind is FailureKind.PASS:
        return "respond"
    if kind is FailureKind.INSUFFICIENT:
        return "reinvestigate" if retries_left > 0 and budget_left else "stop_with_reason"
    if kind is FailureKind.SYSTEM_ERROR:
        return "retry" if retries_left > 0 and budget_left else "escalate"
    return "stop_with_reason"
