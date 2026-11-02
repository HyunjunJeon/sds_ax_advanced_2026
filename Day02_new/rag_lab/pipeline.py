"""AutoRAG 후보 흐름: 질의 분해, 넓은 후보, 원 질문 기준 재순위, 컨텍스트 자르기."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import chain, zip_longest
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ValidationError

from rag_lab.corpus import Scope
from rag_lab.retrieval import Retriever

_MAX_QUERIES = 5
_DECOMPOSE_PROMPT = """Split the user question below into search queries for a retrieval system.

Rules:
- Return at most 5 queries; use fewer when fewer cover the question.
- Each query is short, self-contained, and targets one fact or sub-question. Resolve pronouns and keep names, dates, and identifiers.
- Together the queries must cover everything needed to answer the question.
- Keep the question's language.
- Reply with JSON only, no prose: {"queries": ["...", "..."]}

User question: {question}"""


class Reranker(Protocol):
    """(질문, 조각) 점수를 입력 순서대로 돌려준다. 클수록 관련이 높다."""
    def score(self, query: str, texts: list[str]) -> list[float]: ...


class _Decomposition(BaseModel):
    queries: list[str]


@dataclass
class RetrievalRun:
    """chunk_ids는 최종 순위, queries는 검색한 질의, candidates는 pool로 자르기 전 후보 수다."""
    chunk_ids: list[str]
    queries: list[str]
    candidates: int
    warnings: list[str] = field(default_factory=list)


def decompose_question(model: BaseChatModel, question: str) -> list[str]:
    """검색 질의를 최대 5개 만든다. 답을 해석할 수 없으면 질문 하나로 돌아간다(AutoRAG와 같은 대체 경로)."""
    # 프롬프트에 JSON 중괄호가 있어 str.format을 쓸 수 없다.
    reply = model.invoke(_DECOMPOSE_PROMPT.replace("{question}", question)).text
    try:  # 코드 울타리로 감싼 답도 읽도록 바깥 중괄호 사이만 본다.
        parsed = _Decomposition.model_validate_json(reply[reply.find("{"):reply.rfind("}") + 1])
    except ValidationError:
        return [question]
    unique = dict.fromkeys(query.strip() for query in parsed.queries if query.strip())
    return list(unique)[:_MAX_QUERIES] or [question]


def interleave(rankings: list[list[str]]) -> list[str]:
    """순위 목록을 한 칸씩 번갈아 합친다. 같은 키는 처음 나온 자리에 남는다."""
    return [key for key in dict.fromkeys(chain.from_iterable(zip_longest(*rankings))) if key is not None]


def retrieve(question: str, *, retriever: Retriever, scope: Scope | None, reranker: Reranker | None = None,
             queries: list[str] | None = None, pool: int = 50, top_n: int = 25) -> RetrievalRun:
    """원 질문을 먼저 검색하고 질의별 순위를 합쳐 pool로 자른 뒤, 원 질문으로만 재순위해 top_n을 돌려준다.

    질의별 최고 점수를 쓰지 않는 이유: 실제 PDF에서 top-1 적중을 떨어뜨린 것을 측정했다.
    재순위가 실패하면 합친 순서를 유지하고 경고를 남긴다. 경고에는 오류 내용을 넣지 않고 타입 이름만 쓴다.
    """
    searched = list(dict.fromkeys([question, *(queries or [])]))
    merged = interleave([retriever.rank(query, scope, limit=pool) for query in searched])
    ranked, warnings = merged[:pool], []
    if reranker is not None:
        try:
            scores = reranker.score(question, [retriever.chunks[chunk_id].text for chunk_id in ranked])
            # sorted는 안정 정렬이라 동점은 합친 순서를 유지한다.
            ranked = [chunk_id for _, chunk_id in sorted(zip(scores, ranked, strict=True), key=lambda pair: -pair[0])]
        except Exception as error:  # 재순위 모델의 어떤 실패도 검색 자체를 막지 않는다. 경고로 드러낸다.
            warnings.append(f"rerank-failed: {type(error).__name__}")
    return RetrievalRun(ranked[:top_n], searched, len(merged), warnings)


def fit_context[T](items: list[T], max_bytes: int, size: Callable[[T], int]) -> tuple[list[T], list[T]]:
    """순위를 지켜 (남긴 것, 버린 것)을 돌려준다. 합이 max_bytes 이하가 될 때까지 가장 낮은 순위부터 버린다."""
    kept = list(items)
    total = sum(map(size, kept))
    while kept and total > max_bytes:
        total -= size(kept.pop())
    return kept, items[len(kept):]
