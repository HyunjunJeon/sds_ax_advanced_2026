import json
from datetime import date

import pytest

from mas_lab.desk import Desk, load_billing, load_outage
from mas_lab.runner import build_retriever
from rag_lab.corpus import Scope, load_cases, load_corpus


def by_name(desk, role="all"):
    return {t.name: t for t in desk.tools(role)}


@pytest.mark.parametrize(("role", "names"), [("billing", {"lookup_payments"}), ("policy", {"search_knowledge", "read_evidence"}),
                                             ("outage", {"lookup_availability"}), ("writer", {"calculate_credit"})])
def test_roles_have_fixed_tools(desk, role, names):
    assert set(by_name(desk, role)) == names


def test_no_tool_lets_the_model_widen_the_scope(desk):
    for item in desk.tools("all"):
        assert not {"entity", "as_of", "customer"} & set(item.args), item.name


def test_lookup_returns_only_scope_customer_and_registers_refs(desk):
    tools = by_name(desk)
    found = tools["lookup_payments"].invoke({"invoice_id": "INV-2026-08"})
    assert [p["payment_id"] for p in found["payments"]] == ["P-9001", "P-9002"] and "F-P-9002" in desk.known_refs()
    assert tools["lookup_payments"].invoke({"payment_id": "P-5002"})["status"] == "not_found"
    assert tools["lookup_availability"].invoke({"month": "2026-08"})["availability_percent"] == 99.3
    assert tools["calculate_credit"].invoke({"base_fee": 1000000, "credit_percent": 15})["credit"] == 150000
    assert "99.3" in desk.source_text() and "150000" in desk.source_text()


def test_faults_are_once_or_always(scope_alpha):
    once = Desk(scope_alpha, build_retriever(), faults={"lookup_availability": "timeout_once"})
    tool = by_name(once)["lookup_availability"]
    with pytest.raises(TimeoutError):
        tool.invoke({"month": "2026-08"})
    assert tool.invoke({"month": "2026-08"})["status"] == "found"
    always = Desk(scope_alpha, build_retriever(), faults={"lookup_payments": "timeout_always"})
    for _ in range(2):
        with pytest.raises(TimeoutError):
            by_name(always)["lookup_payments"].invoke({})
    assert [e["kind"] for e in once.trace.events if e["kind"] == "fault_injected"] == ["fault_injected"]


def test_search_respects_scope(desk):
    found = desk.context.search("서비스 크레딧 신청 기한", 6)
    docs = {e["doc_id"] for e in found["evidence"]}
    assert "sla-a-amendment" in docs and "sla-b" not in docs and "sla-a-v1" not in docs
    beta = Desk(Scope("베타", date(2026, 9, 8)), build_retriever()).context.search("서비스 크레딧 신청", 6)
    assert "sla-a-v2" not in {e["doc_id"] for e in beta["evidence"]}


def test_data_contract():
    assert {c["type"] for c in load_cases()} == {"simple", "complex", "insufficient", "approval", "scope", "followup"}
    p = {x["payment_id"]: x for x in load_billing("알파")}
    assert p["P-9002"]["invoice_id"] == p["P-9001"]["invoice_id"] and p["P-9002"]["base_fee_part"] == 1000000
    assert load_outage("베타")["2026-08"]["availability_percent"] == 99.7 and load_billing("없음") == []
    assert "billing-policy" in load_corpus()
    assert "gold" not in json.dumps(load_cases()[0], ensure_ascii=False)
