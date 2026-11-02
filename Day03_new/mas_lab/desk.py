"""고객 요청 창구의 사실과 도구. 고객과 기준일은 도구 인자가 아니라 호출자의 값이다."""
from __future__ import annotations

import json
import threading

from langchain_core.tools import BaseTool, tool

from mas_lab.ledger import PaymentLedger
from mas_lab.trace import Trace
from rag_lab.corpus import Scope
from rag_lab.evidence import Budget, RetrievalContext, make_search_tools
from rag_lab.retrieval import Retriever
from rag_lab.settings import ROOT


def _read(name: str, entity: str):
    data = json.loads((ROOT / "data" / "support" / name).read_text(encoding="utf-8"))
    return data.get(entity)


def load_billing(entity: str) -> list[dict]:
    """수업용 가상 결제 사실. 고객이 없으면 빈 목록이다."""
    return _read("billing.json", entity) or []


def load_outage(entity: str) -> dict:
    """수업용 가상 가용률 사실. 고객이 없으면 빈 dict다."""
    return _read("outage.json", entity) or {}


class Desk:
    """한 실행의 범위, 예산, 근거, 원장. 실행마다 새로 만들어 서로 섞이지 않게 한다."""

    def __init__(self, scope: Scope, retriever: Retriever, *, budget: Budget | None = None,
                 trace: Trace | None = None, faults: dict[str, str] | None = None):
        self.scope, self.budget = scope, budget or Budget()
        self.trace = trace or Trace()
        self.context = RetrievalContext(retriever, scope, self.budget)
        self.ledger = PaymentLedger()
        self.fact_refs: dict[str, str] = {}
        self.faults = dict(faults or {})
        self._lock = threading.Lock()
        self._search_tools = make_search_tools(self.context)

    def payments(self) -> list[dict]:
        return load_billing(self.scope.entity)

    def _inject(self, name: str) -> None:
        """제어 경로 확인용 오류 주입. 장애율 측정이 아니다."""
        with self._lock:
            kind = self.faults.get(name)
            if kind == "timeout_once":
                self.faults.pop(name)
        if kind:
            self.trace.event("fault_injected", name, fault=kind)
            raise TimeoutError(f"{name}: 주입한 시간 초과")

    def _register(self, ref: str, fact: object) -> None:
        with self._lock:
            self.fact_refs[ref] = json.dumps(fact, ensure_ascii=False)

    def known_refs(self) -> set[str]:
        return set(self.context.evidence) | set(self.fact_refs)

    def source_text(self) -> str:
        """등록된 근거 원문과 조회한 사실. 숫자 출처 검사에 쓴다."""
        return "\n".join([*(e.quote for e in self.context.evidence.values()), *self.fact_refs.values()])

    def tools(self, role: str = "all") -> list[BaseTool]:
        """역할별로 도구를 나눈다. role: billing | policy | outage | writer | all"""
        desk = self

        @tool
        def lookup_payments(invoice_id: str = "", payment_id: str = "") -> dict:
            """현재 고객의 결제를 조회한다. 청구서나 결제 번호로 좁힐 수 있다. 결과의 fact_ref를 근거로 인용한다."""
            desk._inject("lookup_payments")
            desk.trace.event("tool", "lookup_payments", invoice_id=invoice_id, payment_id=payment_id)
            rows = [{**p, "fact_ref": f"F-{p['payment_id']}"} for p in desk.payments()
                    if (not invoice_id or p["invoice_id"] == invoice_id)
                    and (not payment_id or p["payment_id"] == payment_id)]
            for row in rows:
                desk._register(row["fact_ref"], row)
            return {"status": "found" if rows else "not_found", "payments": rows}

        @tool
        def lookup_availability(month: str) -> dict:
            """현재 고객의 월간 가용률과 장애 사건을 조회한다. month 형식은 2026-08이다. 결과의 fact_ref를 근거로 인용한다."""
            desk._inject("lookup_availability")
            desk.trace.event("tool", "lookup_availability", month=month)
            fact = load_outage(desk.scope.entity).get(month)
            if fact is None:
                return {"status": "not_found", "month": month}
            row = {**fact, "month": month, "fact_ref": f"F-AV-{month}"}
            desk._register(row["fact_ref"], row)
            return {"status": "found", **row}

        @tool
        def calculate_credit(base_fee: int, credit_percent: int) -> dict:
            """기본 이용료에 크레딧 비율을 곱한다. 비율은 원문을 읽고 호출자가 고른다. 결과의 fact_ref를 근거로 인용한다."""
            desk.trace.event("tool", "calculate_credit", base_fee=base_fee, credit_percent=credit_percent)
            row = {"base_fee": base_fee, "credit_percent": credit_percent, "credit": base_fee * credit_percent // 100,
                   "fact_ref": f"F-CALC-{base_fee}-{credit_percent}"}
            desk._register(row["fact_ref"], row)
            return row

        search = self._search_tools
        by_role = {"billing": [lookup_payments], "policy": search, "outage": [lookup_availability],
                   "writer": [calculate_credit],
                   "all": [lookup_payments, lookup_availability, calculate_credit, *search]}
        return list(by_role[role])
