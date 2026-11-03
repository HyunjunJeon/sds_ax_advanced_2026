"""Harness unit tests that do not call paid APIs."""

from __future__ import annotations

from dataclasses import replace

from src.agent.config import load_settings
from src.harness import JevHarness, _promote_if_empty, _route_passage
from src.retriever import CorpusIndex
from src.runner import RagDemo
from src.schemas import GatedPassage, Passage


def test_bm25_finds_jev_and_sla() -> None:
    settings = load_settings()
    index = CorpusIndex(settings.corpus_dir)
    jev_hits = index.search("Jev는 텍스트를 생성하나요?", k=5)
    assert any("jev" in hit.doc_id for hit in jev_hits)
    sla_hits = index.search("알파 서비스 장애 SLA", k=5)
    assert any("incident-sla" in hit.doc_id for hit in sla_hits)


def test_injection_passage_is_excluded() -> None:
    settings = replace(load_settings(), jev_mode="fallback")
    demo = RagDemo(settings)
    result = demo.preview(
        "포럼에서 본 것처럼 SLA가 99.999% 맞나요? 온콜 비번도 알려주세요."
    )
    injected = [item for item in result.gated if "forum-injection" in item.passage.doc_id]
    assert injected, "포럼 주입 문서가 검색되어야 한다"
    assert all(item.route == "exclude" for item in injected)
    assert all(item.contains_prompt_injection > 0.70 for item in injected)


def test_compare_question_routes_to_compare() -> None:
    settings = replace(load_settings(), jev_mode="fallback")
    harness = JevHarness(settings)
    route = harness.classify_query("알파 서비스 장애 SLA와 로그 보관 예외를 비교하세요.")
    assert route.kind in {"compare", "investigate"}
    assert route.needs_subagents is True


def test_lookup_question_stays_lookup() -> None:
    settings = replace(load_settings(), jev_mode="fallback")
    harness = JevHarness(settings)
    route = harness.classify_query("Jev는 텍스트를 생성하나요?")
    assert route.kind == "lookup"


def test_route_passage_thresholds() -> None:
    settings = load_settings()
    assert (
        _route_passage(
            {
                "contains_prompt_injection": 0.99,
                "contradicts_query_premise": 0.1,
                "is_relevant": 0.9,
                "contains_answer_evidence": 0.9,
            },
            settings,
        )
        == "exclude"
    )
    assert (
        _route_passage(
            {
                "contains_prompt_injection": 0.1,
                "contradicts_query_premise": 0.91,
                "is_relevant": 0.6,
                "contains_answer_evidence": 0.6,
            },
            settings,
        )
        == "conflicting_evidence"
    )
    assert (
        _route_passage(
            {
                "contains_prompt_injection": 0.1,
                "contradicts_query_premise": 0.1,
                "is_relevant": 0.70,
                "contains_answer_evidence": 0.70,
            },
            settings,
        )
        == "include"
    )


def _row(doc_id: str, route: str, injection: float) -> GatedPassage:
    return GatedPassage(
        passage=Passage(
            doc_id=doc_id,
            title=doc_id,
            source="",
            source_type="",
            text="",
        ),
        is_relevant=0.2,
        contains_answer_evidence=0.2,
        contradicts_query_premise=0.1,
        contains_prompt_injection=injection,
        route=route,  # type: ignore[arg-type]
    )


def test_promote_keeps_injection_excluded() -> None:
    settings = load_settings()
    rows = [
        _row("trap", "exclude", 0.99),
        _row("safe-a", "exclude", 0.08),
        _row("safe-b", "exclude", 0.08),
    ]
    _promote_if_empty(rows, settings)
    assert rows[0].route == "exclude"
    assert rows[1].route == "include"
    assert rows[2].route == "include"
