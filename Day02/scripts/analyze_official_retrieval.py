"""09의 공식 코퍼스 BM25를 재현하고 누락을 진단한다. API·모델 호출 없음.

검색 완료 뒤에만 gold를 읽는다. 순위·필터·K는 09와 같으며 변경하지 않는다.
점수는 문서별 최고 청크 점수다. 결과는 outputs/retrieval-audit/에 보존한다.
"""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from day02.corpus import load_corpus, sha256
from day02.ranking import KoreanBM25
from day02.settings import write_json

ROOT = Path(__file__).resolve().parents[1]
CORPUS = "official-2026-10"


def main():
    spec = importlib.util.spec_from_file_location("compare09", ROOT / "09_compare.py")
    compare = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compare)
    corpus = load_corpus(ROOT, CORPUS)
    catalog = corpus.catalog()
    cases = compare.load_jsonl(corpus.cases_path)
    rows = []
    for case in cases:
        allowed = compare.scope_filter(catalog, case)
        documents = {r["metadata"]["doc_id"]: (ROOT / r["path"]).read_text(encoding="utf-8")
                     for r in catalog if r["metadata"]["doc_id"] in allowed}
        for chunking in ("bounded", "fixed"):
            units = {f"{doc}:{i}": chunk for doc, text in documents.items()
                     for i, chunk in enumerate(compare.chunk_texts(text, chunking), 1)}
            row = {"case_id": case["id"], "chunking": chunking, "as_of": case["as_of"],
                   "eligible_docs": list(documents), "chunk_count": len(units),
                   "retrieved": [], "scores": {}, "overlap_tokens": {}, "status": "ok"}
            try:
                if units:
                    index = KoreanBM25(units, user_words=["크레딧", "추가약정", "가용률"])
                    tokens = index.tokens(case["question"])
                    row["query_tokens"] = tokens
                    scores = index.index.get_scores(tokens)
                    for key, score in zip(index.keys, scores, strict=True):
                        doc = key.rsplit(":", 1)[0]
                        row["scores"][doc] = max(row["scores"].get(doc, float("-inf")), float(score))
                        row["overlap_tokens"][doc] = sorted(set(row["overlap_tokens"].get(doc, [])) |
                                                           (set(tokens) & set(index.tokens(units[key]))))
                    row["retrieved"] = list(dict.fromkeys(
                        key.rsplit(":", 1)[0] for key in index.search(case["question"], 18)
                    ))[:compare.K]
            except Exception as exc:
                row.update(status="error", error_type=type(exc).__name__)
            rows.append(row)
    # 사후 진단: 기대 문서는 검색·토큰화·순위에 전달하지 않는다.
    gold = {g["id"]: g for g in compare.load_jsonl(corpus.gold_path)}
    for row in rows:
        expected = gold[row["case_id"]]["expected_docs"]
        row["expected_docs"] = expected
        row["missing_docs"] = sorted(set(expected) - set(row["retrieved"]))
        row["recall"] = compare.recall(row["retrieved"], expected)
        row["evaluation_basis"] = gold[row["case_id"]]["review_status"]
    out = ROOT / "outputs/retrieval-audit" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True)
    write_json(out / "audit.json", {"corpus": corpus.provenance(), "cases_sha256": sha256(corpus.cases_path),
                                   "gold_sha256": sha256(corpus.gold_path), "k": compare.K,
                                   "lock_sha256": sha256(ROOT.parent / "uv.lock"), "rows": rows})
    print(f"진단 결과: {out / 'audit.json'}")
    for row in rows:
        if row["missing_docs"]:
            print(json.dumps(row, ensure_ascii=False))
    return int(any(r["status"] == "error" for r in rows))


if __name__ == "__main__":
    raise SystemExit(main())
