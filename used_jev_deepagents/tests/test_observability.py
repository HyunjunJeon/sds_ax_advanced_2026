"""Langfuse 페이로드와 마스킹. 네트워크는 타지 않는다."""

from __future__ import annotations

from dataclasses import replace

from src.agent.config import load_settings
from src.harness import _build_turn_plan
from src.jev import AskResult
from src.observability import (
    DATASET_NAME,
    bind_thread_session,
    conversation_title,
    explain_plan,
    extract_user_text,
    gold_dataset_records,
    human_session_name,
    instrument_graph,
    item_question,
    jev_observation_payload,
    jev_stage_label,
    langfuse_run_config,
    mask_value,
    resolve_session_id,
    turn_metadata,
)
from src.quality import CASES, CONVERSATION_ORDER, conversation_cases
from src.schemas import DecisionTrace


def test_gold_dataset_covers_demo_labels() -> None:
    records = gold_dataset_records()
    labels = [item["id"] for item in records]
    assert labels == [f"{DATASET_NAME}:{case.label}" for case in CASES]
    assert [item["input"]["question"] for item in records] == [
        case.question for case in CASES
    ]
    assert DATASET_NAME == "jev-rag-gold"


def test_item_question_reads_dataset_payload() -> None:
    assert item_question({"input": {"question": "안녕", "label": "x"}}) == "안녕"
    assert item_question(type("Item", (), {"input": {"question": "Q"}})()) == "Q"


def test_mask_value_redacts_pdf_and_truncates() -> None:
    assert mask_value("data:application/pdf;base64,AAA") == "[redacted-binary]"
    long = "가" * 5000
    masked = mask_value(long)
    assert masked.startswith("가")
    assert masked.endswith("[5000 chars]")
    nested = mask_value({"file": "data:application/octet-stream;base64,xx"})
    assert nested["file"] == "[redacted-binary]"


def test_turn_metadata_keeps_routing_fields() -> None:
    result = AskResult(
        choices={
            "kind": "lookup",
            "sources": "local",
            "analysis": "self_read",
            "thinking": "low",
        },
        nouls={
            "need_local": 0.80,
            "need_web": 0.10,
            "need_fresh_web": 0.10,
            "need_search": 0.80,
            "jailbreak": 0.05,
        },
        scores={"complexity": 0.4},
        confidence={"kind": 0.90, "sources": 0.80, "analysis": 0.80},
        probabilities={"kind": {}, "sources": {}},
    )
    plan = _build_turn_plan(
        "Jev는 텍스트를 생성하나요?",
        result,
        replace(load_settings(), jev_mode="fallback"),
    )
    meta = turn_metadata(plan, graph="agent", engine="jev")
    assert meta["kind"] == "lookup"
    assert meta["sources"] == "local"
    assert meta["graph"] == "agent"
    assert "query" not in meta


def test_instrument_graph_is_noop_when_disabled() -> None:
    sentinel = object()
    assert instrument_graph(sentinel, "agent") is sentinel


def test_resolve_session_id_prefers_env(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_SESSION_ID", "suite-1")
    assert resolve_session_id({"thread_id": "thread-9"}) == "suite-1"
    monkeypatch.delenv("LANGFUSE_SESSION_ID", raising=False)
    assert resolve_session_id({"thread_id": "thread-9"}) == "thread-9"


def test_conversation_is_one_ordered_dialogue() -> None:
    labels = [case.label for case in conversation_cases()]
    assert labels == list(CONVERSATION_ORDER)
    assert set(labels) == {case.label for case in CASES}


def test_explain_plan_reads_like_a_turn() -> None:
    result = AskResult(
        choices={
            "kind": "lookup",
            "sources": "local",
            "analysis": "self_read",
            "thinking": "low",
        },
        nouls={
            "need_local": 0.80,
            "need_web": 0.10,
            "need_fresh_web": 0.10,
            "need_search": 0.80,
            "jailbreak": 0.05,
        },
        scores={"complexity": 0.4},
        confidence={"kind": 0.90, "sources": 0.80, "analysis": 0.80},
        probabilities={"kind": {}, "sources": {}},
    )
    plan = _build_turn_plan(
        "Jev는 텍스트를 생성하나요?",
        result,
        replace(load_settings(), jev_mode="fallback"),
    )
    text = explain_plan(plan)
    assert "한 가지 사실" in text
    assert "로컬 문서만" in text
    assert conversation_title(plan.query) == "Jev는 텍스트를 생성하나요?"
    assert extract_user_text({"messages": [{"content": "안녕"}]}) == "안녕"


def test_langfuse_run_config_sets_session_metadata(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_SESSION_ID", "suite-2")
    config = langfuse_run_config(None, "gold")
    assert config["metadata"]["langfuse_session_id"] == "suite-2"
    assert "gold" in config["metadata"]["langfuse_tags"]


def test_jev_observation_shows_closed_questions() -> None:
    trace = DecisionTrace(
        stage="turn_plan",
        questions={"kind": {"type": "choice", "instructions": "질문 종류"}},
        answers={"choices": {"kind": "lookup"}, "nouls": {"need_local": 0.8}},
        elapsed_ms=12.34,
        live=True,
        note="before_agent 팬아웃",
    )
    name, payload_in, payload_out = jev_observation_payload(trace)
    assert name == "Jev · 턴 판단"
    assert jev_stage_label("passage_batch") == "Jev · 패시지 게이트"
    assert payload_in["questions"]["kind"]["type"] == "choice"
    assert payload_out["choices"]["kind"] == "lookup"
    assert payload_out["live"] is True
    assert payload_out["elapsed_ms"] == 12.3


def test_thread_session_stays_stable(monkeypatch) -> None:
    monkeypatch.delenv("LANGFUSE_SESSION_ID", raising=False)
    bind_thread_session("thread-a", "대화 2026-09-18 17:20 · 고마워요")
    assert resolve_session_id({"thread_id": "thread-a"}) == (
        "대화 2026-09-18 17:20 · 고마워요"
    )
    first = human_session_name("thread-b", "Jev는 텍스트를 생성하나요?")
    second = human_session_name("thread-b", "다른 질문")
    assert first == second
    assert first.startswith("대화 ")
    assert "Jev는 텍스트를 생성하나요?" in first
