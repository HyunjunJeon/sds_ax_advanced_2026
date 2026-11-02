"""검색 측정. 정답표(gold.jsonl)를 읽는 곳은 이 모듈 하나이며, Agent 실행 경로는 이 모듈을 import하지 않는다."""
from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

from rag_lab.corpus import Scope
from rag_lab.retrieval import Retriever
from rag_lab.settings import ROOT


def load_gold(path: Path | None = None) -> dict[str, dict]:
    lines = (path or ROOT / "data/gold.jsonl").read_text(encoding="utf-8").splitlines()
    return {row["id"]: row for row in map(json.loads, filter(str.strip, lines))}


def evaluate_retrieval(retriever: Retriever, cases: list[dict], gold: dict[str, dict], *, k: int,
                       use_scope: bool = True,
                       rank: Callable[[str, Scope | None], list[str]] | None = None) -> list[dict]:
    """조각 순위를 문서로 올려 상위 k개를 본다. 누락(missing)과 오인(out_of_scope)을 행마다 따로 적는다."""
    def rank_all(query: str, scope: Scope | None) -> list[str]:
        return retriever.rank(query, scope, limit=len(retriever.chunks))

    rank = rank or rank_all
    rows = []
    for case in cases:
        scope = Scope(entity=case["entity"], as_of=date.fromisoformat(case["as_of"]))
        chunk_ids = rank(case["question"], scope if use_scope else None)
        ranked_docs = dict.fromkeys(retriever.chunks[chunk_id].doc_id for chunk_id in chunk_ids)
        retrieved = list(ranked_docs)[:k]
        expected = gold[case["id"]]["expected_docs"]
        missing = [doc_id for doc_id in expected if doc_id not in retrieved]
        rows.append({
            "case_id": case["id"], "type": case["type"], "retrieved_docs": retrieved, "expected_docs": expected,
            "missing_docs": missing,
            "out_of_scope_docs": [d for d in retrieved if not retriever.documents[d].applies(scope)],
            "recall": (len(expected) - len(missing)) / len(expected) if expected else None,
        })
    return rows


def recall_by_type(rows: list[dict]) -> list[dict]:
    """유형별 평균 recall(None 제외), 범위 밖 문서 수, 사례 수. 실패 행을 지우지 않는다."""
    summary = []
    for case_type in dict.fromkeys(row["type"] for row in rows):
        group = [row for row in rows if row["type"] == case_type]
        recalls = [row["recall"] for row in group if row["recall"] is not None]
        summary.append({"type": case_type, "cases": len(group),
                        "recall": sum(recalls) / len(recalls) if recalls else None,
                        "out_of_scope": sum(len(row["out_of_scope_docs"]) for row in group)})
    return summary


def mrr(rows: list[dict]) -> tuple[float | None, int]:
    """기대 문서 중 가장 먼저 나온 문서의 순위로 역순위 평균(MRR)을 낸다. 기대 문서가 없는 사례는 제외하고 센 사례 수를 함께 돌려준다.

    top-k 안에 하나도 없으면 그 사례의 역순위는 0이다. 센 사례가 없으면 (None, 0)이다.
    """
    scored = [row for row in rows if row["expected_docs"]]
    reciprocal = [next((1 / rank for rank, doc in enumerate(row["retrieved_docs"], 1) if doc in row["expected_docs"]), 0.0)
                  for row in scored]
    return (sum(reciprocal) / len(scored) if scored else None), len(scored)
