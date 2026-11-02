"""근거 단위, 호출 예산, 턴 범위 검색. 고객과 기준일은 도구 인자가 아니라 호출자의 값이다."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass, field

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel

from rag_lab.corpus import _COMMON_ENTITY, Document, Scope, _scope_json
from rag_lab.pipeline import Reranker, fit_context, retrieve
from rag_lab.retrieval import Retriever, content_terms, tokenize


class BudgetExceeded(RuntimeError):
    """예산을 넘으면 실행을 멈춘다. 드러내야 할 실패다."""


@dataclass
class Budget:
    max_tool_calls: int = 18
    max_model_calls: int = 10
    max_searches: int = 3
    max_reads: int = 18
    max_context_bytes: int = 24000
    max_seconds: float = 180
    max_decision_calls: int = 6  # 모델 예산과 따로 센다. judge 호출 1회가 1이다.
    started: float = field(default_factory=time.monotonic)
    counts: dict[str, int] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def remaining(self) -> float:
        remaining = self.max_seconds - (time.monotonic() - self.started)
        if remaining <= 0:
            raise BudgetExceeded("턴 실행 시간 한도를 초과했습니다.")
        return remaining

    def consume(self, kind: str, **details) -> None:
        limits = {"tool": self.max_tool_calls, "model": self.max_model_calls, "search": self.max_searches, "read": self.max_reads, "decision": self.max_decision_calls}  # 그 외 kind는 기록만 한다.
        with self.lock:  # 병렬 도구 호출에서도 한도를 정확히 센다.
            self.remaining()
            if kind in limits:
                if self.counts.get(kind, 0) >= limits[kind]:
                    raise BudgetExceeded(f"{kind} 호출 한도를 초과했습니다.")
                self.counts[kind] = self.counts.get(kind, 0) + 1
            self.events.append({"event": kind, "seconds": round(time.monotonic() - self.started, 3), **details})

    def report(self) -> dict:
        return {"counts": dict(self.counts), "elapsed_seconds": round(time.monotonic() - self.started, 3),
                "max_context_bytes": self.max_context_bytes, "events": list(self.events)}


class Evidence(BaseModel):
    evidence_id: str
    doc_id: str
    title: str
    source: str
    start_line: int
    end_line: int
    quote: str  # 원문 그대로. 색인용 가공을 넣지 않는다.
    content_hash: str
    version: str


def _listed_bytes(item: Evidence) -> int:
    """JSON 배열에서 항목 하나가 차지하는 바이트. 구분자 ", "와 빈 배열 "[]"가 모두 2바이트라 합이 곧 배열 크기다."""
    return len(json.dumps(item.model_dump(), ensure_ascii=False).encode("utf-8")) + 2


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _evidence(doc: Document, start_line: int, end_line: int, quote: str) -> Evidence:
    return Evidence(evidence_id="E-" + _sha256(f"{doc.doc_id}:{start_line}:{quote}")[:12], doc_id=doc.doc_id, title=doc.title,
                    source=doc.source, start_line=start_line, end_line=end_line, quote=quote, content_hash=_sha256(quote), version=doc.version)


@dataclass(frozen=True)
class Sufficiency:
    coverage: float
    covered: list[str]
    missing_terms: list[str]
    out_of_scope_terms: list[str]
    threshold: float

    @property
    def low_coverage(self) -> bool:
        return self.coverage < self.threshold


def assess_sufficiency(question: str, quotes: list[str], scope: Scope, known_entities: set[str], threshold: float = 0.5) -> Sufficiency:
    """판결이 아니라 신호다. 임계값 0.5는 12개 사례로 정한 값이며 일반 규칙이 아니다."""
    terms = content_terms(question)
    found = set(tokenize("\n".join(quotes)))
    covered = [term for term in terms if term in found]
    outside = sorted(n for n in known_entities - {scope.entity, _COMMON_ENTITY} if n in question)
    return Sufficiency(len(covered) / len(terms) if terms else 0.0, covered,
                       [term for term in terms if term not in found], outside, threshold)


class RetrievalContext:
    """한 턴의 검색 상태. 이번 턴에 등록된 근거만 인용할 수 있다."""
    def __init__(self, retriever: Retriever, scope: Scope, budget: Budget | None = None, reranker: Reranker | None = None):
        self.retriever, self.scope, self.reranker = retriever, scope, reranker
        self.budget = budget or Budget()
        self.evidence: dict[str, Evidence] = {}
        self.loaded_skills: set[str] = set()
        self.search_count = 0

    def _context_bytes(self) -> int:
        return sum(map(_listed_bytes, self.evidence.values())) or 2

    def _admit(self, candidates: list[Evidence]) -> list[Evidence]:
        """순위 순서의 후보를 등록하고 등록된 것만 돌려준다. 한도를 넘으면 그 아래 순위의 새 근거도 모두 버린다."""
        with self.budget.lock:
            new = [item for item in candidates if item.evidence_id not in self.evidence]
            room = self.budget.max_context_bytes - sum(map(_listed_bytes, self.evidence.values()))
            kept, dropped = fit_context(new, room, _listed_bytes)
            for item in dropped:
                self.budget.consume("context_excluded", doc_id=item.doc_id, reason="context_bytes")
            self.evidence.update((item.evidence_id, item) for item in kept)
            return [item for item in candidates if item.evidence_id in self.evidence]

    def _fetch(self, query: str, limit: int, max_limit: int, queries: list[str] | None = None) -> dict:
        if not query.strip() or len(query) > 1500 or not 1 <= limit <= max_limit:
            return {"status": "invalid_input", "message": f"검색어 1~1500자, limit 1~{max_limit} 범위가 필요합니다."}
        self.budget.consume("search", query=query)
        self.search_count += 1
        documents = self.retriever.documents
        run = retrieve(query, retriever=self.retriever, scope=self.scope, reranker=self.reranker, queries=queries, top_n=limit)
        for warning in run.warnings:
            self.budget.consume("retrieval_warning", warning=warning)
        candidates = [_evidence(documents[c.doc_id], c.start_line, c.end_line, c.text) for c in map(self.retriever.chunks.get, run.chunk_ids)]
        items = self._admit(candidates)
        found = {item.doc_id for item in items}
        families = {documents[doc_id].family for doc_id in found} - {None}
        related = sorted(d.doc_id for d in documents.values()
                         if d.family in families and d.applies(self.scope) and d.doc_id not in found)
        sufficiency = assess_sufficiency(query, [item.quote for item in items], self.scope, {d.entity for d in documents.values()})
        status = "found" if items else "context_budget" if candidates else "no_evidence"
        return {"status": status, "evidence": [item.model_dump() for item in items], "related_docs": related,
                "sufficiency": {**asdict(sufficiency), "low_coverage": sufficiency.low_coverage},
                "scope": _scope_json(self.scope), "context_bytes": self._context_bytes(), "note": "검색 성공은 답변 가능을 뜻하지 않습니다."}

    def search(self, query: str, limit: int = 6) -> dict:
        return self._fetch(query, limit, max_limit=10)

    def prefetch(self, question: str, queries: list[str], top_n: int = 25) -> dict:
        """미리 검색. 모든 질의의 후보를 합쳐 원 질문으로만 재순위하고 search 예산은 1만 쓴다. 상한 50은 retrieve의 pool이다."""
        return self._fetch(question, top_n, max_limit=50, queries=queries)

    def read_more(self, doc_id: str, start_line: int = 1, line_count: int = 60) -> dict:
        doc = self.retriever.documents.get(doc_id)
        if doc is None or not doc.applies(self.scope):
            return {"status": "out_of_scope", "doc_id": doc_id}
        if start_line < 1 or not 1 <= line_count <= 120:
            return {"status": "invalid_input", "message": "start_line >= 1, line_count 1~120 범위가 필요합니다."}
        self.budget.consume("read", doc_id=doc_id, start_line=start_line, line_count=line_count)
        lines = doc.text.split("\n")[start_line - 1:start_line - 1 + line_count]
        if not "".join(lines).strip():
            return {"status": "no_evidence", "doc_id": doc_id}
        item = _evidence(doc, start_line, start_line + len(lines) - 1, "\n".join(lines))
        if not self._admit([item]):
            return {"status": "context_budget", "doc_id": doc_id}
        return {"status": "found", "evidence": item.model_dump()}


def make_search_tools(context: RetrievalContext) -> list[BaseTool]:
    @tool
    def search_knowledge(query: str, limit: int = 6) -> dict:
        """업무 문서를 검색해 원문 인용과 evidence_id를 돌려준다. 고객과 기준일은 호출자가 정한 범위를 따른다."""
        return context.search(query, limit)

    @tool
    def read_evidence(doc_id: str, start_line: int = 1, line_count: int = 60) -> dict:
        """범위 안 문서의 원문을 행 단위로 읽어 근거로 등록한다. 행은 1부터다. 예외·각주·개별 약정을 확인할 때 쓴다."""
        return context.read_more(doc_id, start_line, line_count)

    return [search_knowledge, read_evidence]
