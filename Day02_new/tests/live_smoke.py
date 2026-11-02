"""실제 키로 한 턴을 돌린다. 모델 호출 4~10회, 비용이 든다. 답변 내용과 키는 출력하지 않는다.

사용법: uv run --no-sync python Day02_new/tests/live_smoke.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_lab.agent import ask
from rag_lab.corpus import Scope, load_cases, load_corpus
from rag_lab.retrieval import Retriever
from rag_lab.settings import announce, load_settings, make_embeddings, make_model


def smoke_problems(record: dict) -> list[str]:
    problems = list(record["errors"])
    if record["status"] not in {"answered", "insufficient"}:
        problems.append(f"status={record['status']}")
    if not record["loaded_skills"]:
        problems.append("SKILL.md를 읽지 않았습니다.")
    if record["trace"]["counts"].get("search", 0) < 1:
        problems.append("search_knowledge를 부르지 않았습니다.")
    return problems


def main() -> int:
    settings = load_settings()
    print(f"embedding vector length={len(make_embeddings(settings).embed_query('서비스 크레딧'))}")
    announce("live_smoke", model_calls=10)
    case = load_cases()[0]
    record = ask(case["question"], retriever=Retriever(load_corpus()), model=make_model(settings),
                 scope=Scope(case["entity"], date.fromisoformat(case["as_of"])))
    problems = smoke_problems(record)
    for problem in problems:
        print(f"LIVE SMOKE FAIL: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"LIVE SMOKE OK model={settings.model} calls={record['trace']['counts']['model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
