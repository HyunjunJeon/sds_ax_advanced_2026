"""턴 state는 질문·첨부 메타·코퍼스 제목만 담는다."""

from __future__ import annotations

from dataclasses import replace

from src.agent.config import load_settings
from src.attachments import AttachedFile
from src.harness import JevHarness, _build_turn_plan
from src.jev import AskResult, _routing_text
from src.middleware.turn_plan import forced_search_message
from src.turn_state import build_turn_state


def test_turn_state_is_named_and_has_no_pdf_body() -> None:
    settings = load_settings()
    attached = [
        AttachedFile(
            filename="01_vLLM_Basic.pdf",
            mime_type="application/pdf",
            data=b"%PDF",
            text="PagedAttention",
            pages=48,
        )
    ]
    state = build_turn_state("vLLM 은 어떤 서비스인가요?", settings, attached)
    assert state["question"] == "vLLM 은 어떤 서비스인가요?"
    assert state["attached"][0]["filename"] == "01_vLLM_Basic.pdf"
    assert state["attached"][0]["pages"] == 48
    assert "PagedAttention" not in str(state["attached"])
    assert state["available_sources"]["user_attachment"] is True
    assert any("Jev" in topic or "jev" in topic.lower() for topic in state["corpus_topics"])
    assert _routing_text(state) == "vLLM 은 어떤 서비스인가요?"


def test_fallback_plan_is_not_poisoned_by_corpus_topics() -> None:
    """state에 Jev/SLA 제목이 있어도 인사 질문은 other로 남는다."""
    harness = JevHarness(replace(load_settings(), jev_mode="fallback"))
    plan = harness.plan_turn("고마워요, 잘 이해했어요.")
    assert plan.kind == "other"
    assert plan.allow_search is False
    assert plan.allowed_attachment is False


def test_attachment_noul_opens_allowed_attachment() -> None:
    result = AskResult(
        choices={
            "kind": "investigate",
            "sources": "none",
            "analysis": "self_read",
        },
        nouls={
            "need_local": 0.10,
            "need_web": 0.10,
            "need_fresh_web": 0.10,
            "need_search": 0.10,
            "need_attachment": 0.88,
            "jailbreak": 0.05,
        },
        scores={"complexity": 1.2},
        confidence={"kind": 0.80, "sources": 0.70, "analysis": 0.70},
        probabilities={"kind": {}, "sources": {}},
    )
    plan = _build_turn_plan(
        "vLLM 은 어떤 서비스인가요?",
        result,
        replace(load_settings(), jev_mode="fallback"),
        attached_present=True,
    )
    assert plan.allowed_attachment is True
    assert plan.allow_search is False


def test_forced_search_when_plan_allows_local_and_model_skipped() -> None:
    harness = JevHarness(replace(load_settings(), jev_mode="fallback"))
    plan = harness.plan_turn("Jev는 텍스트를 생성하나요?")
    assert plan.allowed_local is True
    forced = forced_search_message(
        plan,
        has_tool_calls=False,
        has_evidence=False,
        already_forced=False,
    )
    assert forced is not None
    assert forced.tool_calls[0]["name"] == "search_documentation"
    assert forced_search_message(
        plan,
        has_tool_calls=True,
        has_evidence=False,
        already_forced=False,
    ) is None
    assert forced_search_message(
        plan,
        has_tool_calls=False,
        has_evidence=True,
        already_forced=False,
    ) is None


def test_chitchat_is_not_forced_to_search() -> None:
    harness = JevHarness(replace(load_settings(), jev_mode="fallback"))
    plan = harness.plan_turn("안녕")
    assert (
        forced_search_message(
            plan,
            has_tool_calls=False,
            has_evidence=False,
            already_forced=False,
        )
        is None
    )
