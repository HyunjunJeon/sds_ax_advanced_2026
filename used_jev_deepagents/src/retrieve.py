"""도구와 워크플로 벤치가 쓰는 로컬 BM25·Exa 페치.

planned는 Jev가 연 소스만, naive는 계획을 무시하고 연다(웹은 키가 있을 때).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from src.agent.config import Settings
from src.judge_api import JudgeApi
from src.retriever import CorpusIndex
from src.schemas import GatedPassage, Passage, TurnPlan
from src.tools.exa import ExaClient, ExaError


@dataclass
class SourceFetch:
    """소스 한 번 당긴 뒤 이은 Jev 게이트."""

    name: str
    skipped: bool
    reason: str = ""
    fetch_ms: float = 0.0
    gate_ms: float = 0.0
    hits: int = 0
    gated: list[GatedPassage] = field(default_factory=list)
    error: str = ""


def domains_for(query: str) -> list[str] | None:
    """질문이 알려진 제품을 말하면 공식 문서로 도메인을 고정한다."""
    lowered = query.lower()
    # 포럼·블로그 히트가 공식 API 설명을 밀어내지 못하게 한다.
    if "exa" in lowered:
        return ["exa.ai", "docs.exa.ai"]
    if "typesafe" in lowered:
        return ["typesafe.ai", "docs.typesafe.ai"]
    if "langchain" in lowered or "langgraph" in lowered:
        return ["langchain.com", "docs.langchain.com", "github.com"]
    return None


def fetch_local(
    index: CorpusIndex,
    query: str,
    k: int,
) -> tuple[list[Passage], float]:
    """BM25를 돌리고 (hits, milliseconds)를 돌려준다."""
    started = time.perf_counter()
    hits = index.search(query, k=k)
    return hits, (time.perf_counter() - started) * 1000


def fetch_web(
    settings: Settings,
    query: str,
    *,
    fresh: bool = False,
) -> tuple[list[Passage], float]:
    """Exa를 호출하고 (hits, milliseconds)를 돌려준다."""
    if not settings.exa_api_key:
        raise ExaError("EXA_API_KEY is not set")
    started = time.perf_counter()
    hits = ExaClient(
        settings.exa_api_key,
        max_chars=settings.exa_max_chars,
    ).search(
        query,
        k=settings.web_retrieve_k,
        fresh=fresh,
        include_domains=domains_for(query),
    )
    return hits, (time.perf_counter() - started) * 1000


def retrieve_planned(
    plan: TurnPlan,
    index: CorpusIndex,
    harness: JudgeApi,
    settings: Settings,
    *,
    batched: bool = True,
) -> list[SourceFetch]:
    """Jev가 허용한 소스만 가져온 뒤 게이트한다."""
    rows: list[SourceFetch] = []
    gate = harness.gate_passages if batched else harness.gate_passages_per_item
    if plan.allowed_local:
        hits, fetch_ms = fetch_local(index, plan.query, settings.retrieve_k)
        started = time.perf_counter()
        gated = gate(plan.query, hits)
        rows.append(
            SourceFetch(
                name="local",
                skipped=False,
                fetch_ms=fetch_ms,
                gate_ms=(time.perf_counter() - started) * 1000,
                hits=len(hits),
                gated=gated,
            )
        )
    else:
        rows.append(
            SourceFetch(
                name="local",
                skipped=True,
                reason="Jev skipped the local corpus",
            )
        )
    if plan.allowed_web:
        try:
            hits, fetch_ms = fetch_web(
                settings,
                plan.query,
                # 최신성이 높으면 Exa에 fresh를 켠다. 캐시 창은 클라이언트가 정한다.
                fresh=plan.need_fresh_web >= 0.70,
            )
            started = time.perf_counter()
            gated = gate(plan.query, hits)
            rows.append(
                SourceFetch(
                    name="web",
                    skipped=False,
                    fetch_ms=fetch_ms,
                    gate_ms=(time.perf_counter() - started) * 1000,
                    hits=len(hits),
                    gated=gated,
                )
            )
        except ExaError as exc:
            rows.append(
                SourceFetch(name="web", skipped=True, reason=str(exc), error=str(exc))
            )
    else:
        rows.append(
            SourceFetch(name="web", skipped=True, reason="Jev skipped Exa")
        )
    return rows


def retrieve_naive(
    query: str,
    index: CorpusIndex,
    harness: JudgeApi,
    settings: Settings,
) -> list[SourceFetch]:
    """계획을 무시하고 양쪽을 연 뒤 패시지마다 게이트한다."""
    # 대조군이라 라이브 계획을 쓰지 않는다.
    dummy = TurnPlan(
        query=query,
        kind="investigate",
        kind_probabilities={},
        kind_confidence=1.0,
        complexity=2.0,
        sources="both",
        source_probabilities={},
        source_confidence=1.0,
        need_local=1.0,
        need_web=1.0,
        need_fresh_web=0.5,
        need_search=1.0,
        jailbreak=0.0,
        analysis="chunk_analyst",
        analysis_confidence=1.0,
        model_name=settings.powerful_model,
        needs_subagents=True,
        thinking_effort="high",
        allow_search=True,
        allowed_local=True,
        allowed_web=bool(settings.exa_api_key),
        reason="naive: search every source",
    )
    return retrieve_planned(dummy, index, harness, settings, batched=False)


def kept_passages(rows: list[SourceFetch]) -> list[GatedPassage]:
    """Jev ``route()``를 통과한 패시지."""
    kept: list[GatedPassage] = []
    for row in rows:
        kept.extend(item for item in row.gated if item.route != "exclude")
    return kept


def evidence_block(rows: list[SourceFetch]) -> str:
    """남긴 근거를 한 번의 생성 호출용으로 펼친다."""
    blocks = []
    for item in kept_passages(rows):
        passage = item.passage
        blocks.append(
            f"[{item.route}] {passage.source} ({passage.source_type})\n{passage.text}"
        )
    return "\n\n".join(blocks)
