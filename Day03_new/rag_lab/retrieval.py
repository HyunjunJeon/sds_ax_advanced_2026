"""BM25, dense, RRF, 점수 융합. 범위(Scope)는 점수 계산 전에 후보를 제한한다."""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from functools import lru_cache
from math import log, log1p

import numpy as np
from kiwipiepy import Kiwi
from langchain_core.embeddings import Embeddings

from rag_lab.corpus import Chunk, Document, Scope, section_chunks

_K1, _B = 1.5, 0.75
_HYBRID_DEPTH = 18  # Day02 09의 조각별 상위 18개와 맞춘다.
_CANDIDATE_DEPTH = 50  # 출처 보강도는 방법별 상위 50개 후보 안에서만 센다.
SAME_SOURCE_CORROBORATION_BONUS = 0.15  # AutoRAG merger.ts와 같은 값이다.
MAX_CORROBORATION_BONUS = 0.3


_kiwi = lru_cache(maxsize=1)(Kiwi)  # 모델 적재가 느려 한 번만 만든다.


def tokenize(text: str) -> list[str]:
    """색인과 질의에 쓰는 토큰. 조사·어미를 버린다."""
    return [t.form.lower() for t in _kiwi().tokenize(text) if t.tag.startswith(("N", "V", "SL", "SN"))]


def content_terms(text: str) -> list[str]:
    """질문의 내용어. 중복을 없애고 순서를 유지한다."""
    terms = [t.form.lower() for t in _kiwi().tokenize(text) if t.tag.startswith(("NN", "SL", "SN"))]
    return list(dict.fromkeys(terms))


class BM25Index:
    """양수 IDF BM25. BM25Okapi의 음수 IDF가 `score > 0`과 만나 후보를 지우는 함정을 피한다."""
    def __init__(self, chunks: list[Chunk], *, tokenizer: Callable[[str], list[str]] = tokenize):
        self.tokenizer = tokenizer
        self.ids = [c.chunk_id for c in chunks]
        self.counts = [Counter(tokenizer(c.text)) for c in chunks]
        self.lengths = [sum(counts.values()) for counts in self.counts]
        self.average_length = sum(self.lengths) / (len(self.lengths) or 1)
        df = Counter(term for counts in self.counts for term in counts)
        self.idf = {term: log(1 + (len(chunks) - n + 0.5) / (n + 0.5)) for term, n in df.items()}

    def search(self, query: str, limit: int = 6,
               allowed_ids: set[str] | None = None) -> list[tuple[str, float]]:
        """df·평균 길이는 전체 조각 기준이고, 점수 계산 대상만 allowed_ids로 제한한다."""
        terms = self.tokenizer(query)
        scored = []
        for chunk_id, counts, length in zip(self.ids, self.counts, self.lengths, strict=True):
            if allowed_ids is not None and chunk_id not in allowed_ids:
                continue
            norm = _K1 * (1 - _B + _B * length / (self.average_length or 1))
            score = sum(self.idf[t] * counts[t] * (_K1 + 1) / (counts[t] + norm) for t in terms if t in counts)
            if score > 0:
                scored.append((chunk_id, score))
        return sorted(scored, key=lambda pair: (-pair[1], pair[0]))[:limit]


class DenseIndex:
    """코사인 유사도 색인."""
    def __init__(self, chunks: list[Chunk], embeddings: Embeddings):
        self.embeddings = embeddings
        self.ids = [c.chunk_id for c in chunks]
        self.vectors = np.asarray(embeddings.embed_documents([c.text for c in chunks]), dtype=float)

    def search(self, query: str, limit: int = 6,
               allowed_ids: set[str] | None = None) -> list[tuple[str, float]]:
        vector = np.asarray(self.embeddings.embed_query(query), dtype=float)
        denominator = np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(vector)
        scores = np.divide(self.vectors @ vector, denominator, out=np.zeros(len(self.ids)), where=denominator > 0)
        scored = [(chunk_id, float(score)) for chunk_id, score in zip(self.ids, scores, strict=True)
                  if allowed_ids is None or chunk_id in allowed_ids]
        return sorted(scored, key=lambda pair: (-pair[1], pair[0]))[:limit]


def rrf(rankings: list[list[str]], weights: list[float] | None = None, constant: int = 60) -> list[str]:
    """점수가 아니라 순위를 합친다. 동점은 키 사전순이다."""
    weights = weights if weights is not None else [1.0] * len(rankings)
    if len(weights) != len(rankings) or constant <= 0 or any(w < 0 for w in weights):
        raise ValueError("검색기별 가중치와 RRF 상수를 확인하세요.")
    scores: dict[str, float] = {}
    for ranking, weight in zip(rankings, weights, strict=True):
        for rank, key in enumerate(dict.fromkeys(ranking), 1):
            scores[key] = scores.get(key, 0) + weight / (constant + rank)
    return sorted(scores, key=lambda key: (-scores[key], key))


def _fusion_scores(dense: list[tuple[str, float]], sparse: list[tuple[str, float]],
                   dense_weight: float) -> dict[str, float]:
    dense_scores, sparse_scores = dict(dense), dict(sparse)
    low, high = min(dense_scores.values(), default=0.0), max(dense_scores.values(), default=0.0)
    top = max(sparse_scores.values(), default=0.0)
    fused = {}
    for key in dense_scores.keys() | sparse_scores.keys():
        near = (dense_scores[key] - low) / (high - low) if key in dense_scores and high > low else 0.0
        lexical = sparse_scores.get(key, 0.0) / top if top > 0 else 0.0
        fused[key] = dense_weight * near + (1 - dense_weight) * lexical
    return fused


def fuse_scores(dense: list[tuple[str, float]], sparse: list[tuple[str, float]],
                dense_weight: float = 0.7) -> list[str]:
    """밀집은 min-max, BM25는 최댓값으로 나눠 0~1로 맞춘 뒤 볼록 결합한다. 없는 쪽 점수는 0, 동점은 키 사전순이다."""
    fused = _fusion_scores(dense, sparse, dense_weight)
    return sorted(fused, key=lambda key: (-fused[key], key))


def corroborate(scores: dict[str, float], sources: dict[str, str], methods: dict[str, set[str]]) -> list[str]:
    """출처 보강도(AutoRAG merger.ts). 같은 출처의 다른 조각 수 + 그 출처를 찾은 다른 방법 수가 많을수록 점수에 가산한다. 동점은 입력 순서다."""
    chunks_per_source: dict[str, int] = {}
    methods_per_source: dict[str, set[str]] = {}
    for key in scores:
        chunks_per_source[sources[key]] = chunks_per_source.get(sources[key], 0) + 1
        methods_per_source.setdefault(sources[key], set()).update(methods[key])

    def boosted(key: str) -> float:
        extra = chunks_per_source[sources[key]] - 1 + len(methods_per_source[sources[key]]) - 1
        bonus = min(MAX_CORROBORATION_BONUS, log1p(extra) * SAME_SOURCE_CORROBORATION_BONUS) if extra > 0 else 0.0
        return scores[key] + bonus
    return sorted(scores, key=lambda key: -boosted(key))


class Retriever:
    """mode는 bm25, dense, hybrid, fusion. dense·hybrid·fusion에는 임베딩이 반드시 필요하다."""
    def __init__(self, documents: dict[str, Document], *,
                 chunker: Callable[[Document], list[Chunk]] = section_chunks,
                 embeddings: Embeddings | None = None, mode: str = "bm25", corroboration: bool = True):
        if mode not in {"bm25", "dense", "hybrid", "fusion"}:
            raise ValueError(f"알 수 없는 검색 방식입니다: {mode}")
        if mode != "bm25" and embeddings is None:
            raise ValueError(f"{mode} 검색에는 embeddings가 필요합니다.")
        self.documents = documents
        self.mode = mode
        self.corroboration = corroboration
        chunks = [chunk for doc in documents.values() for chunk in chunker(doc)]
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.bm25 = BM25Index(chunks) if mode != "dense" else None
        self.dense = DenseIndex(chunks, embeddings) if mode != "bm25" else None

    def rank(self, query: str, scope: Scope | None, limit: int = 6) -> list[str]:
        """scope가 있으면 적용 문서의 조각만 후보다. scope=None은 비교 측정 전용이다."""
        allowed = None if scope is None else {
            c.chunk_id for c in self.chunks.values() if self.documents[c.doc_id].applies(scope)}
        if self.mode == "fusion":  # 범위가 허용한 모든 조각을 점수로 합친다. 순위 컷이 점수를 버리지 않는다.
            everything = len(self.chunks)
            dense, sparse = self.dense.search(query, everything, allowed), self.bm25.search(query, everything, allowed)
            order = fuse_scores(dense, sparse)
            if not self.corroboration:
                return order[:limit]
            scores = _fusion_scores(dense, sparse, 0.7)
            found = {"dense": [k for k, _ in dense[:_CANDIDATE_DEPTH]], "bm25": [k for k, _ in sparse[:_CANDIDATE_DEPTH]]}
            seen = {k: {m for m, ids in found.items() if k in ids} for ids in found.values() for k in ids}
            top = [k for k in order if k in seen]
            sources = {k: self.chunks[k].doc_id for k in top}
            ranked = corroborate({k: scores[k] for k in top}, sources, seen)
            return (ranked + [k for k in order if k not in seen])[:limit]
        depth = _HYBRID_DEPTH if self.mode == "hybrid" else limit
        rankings = [[chunk_id for chunk_id, _ in index.search(query, depth, allowed)]
                    for index in (self.bm25, self.dense) if index is not None]
        return rrf(rankings)[:limit] if self.mode == "hybrid" else rankings[0]
