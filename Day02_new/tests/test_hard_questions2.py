"""두 번째 동결 질문 파일(cases_hard2/gold_hard2)의 형식 검사. 검색은 실행하지 않는다."""
import json
from collections import Counter

from rag_lab.corpus import load_cases, load_corpus
from rag_lab.evaluation import load_gold
from rag_lab.settings import ROOT

CASES = ROOT / "data/cases_hard2.jsonl"
GOLD = ROOT / "data/gold_hard2.jsonl"
KINDS = {"no-keyword", "everyday", "multi-doc", "rank-order"}


def test_pair_up_with_same_fields_as_originals():
    cases, gold = load_cases(CASES), load_gold(GOLD)
    assert 18 <= len(cases) <= 24
    assert [c["id"] for c in cases] == list(gold)
    assert all(set(c) == set(load_cases()[0]) and c["namespace"] == "business" for c in cases)
    assert {c["type"] for c in cases} <= KINDS
    assert all(Counter(c["type"] for c in cases)[k] >= 3 for k in KINDS)
    original = next(iter(load_gold().values()))
    assert all(set(original) <= set(row) for row in gold.values())


def test_ids_are_unique_and_not_reused():
    ids = [json.loads(line)["id"] for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(ids) == len(set(ids))
    earlier = {c["id"] for c in load_cases()} | {c["id"] for c in load_cases(ROOT / "data/cases_hard.jsonl")}
    assert not set(ids) & earlier
    questions = {c["question"] for c in load_cases(ROOT / "data/cases_hard.jsonl")} | {c["question"] for c in load_cases()}
    assert not {c["question"] for c in load_cases(CASES)} & questions


def test_gold_rows_are_drafts_with_reason_and_known_documents():
    known = set(load_corpus())
    for row in load_gold(GOLD).values():
        assert row["review_status"] == "draft" and row["reason"].strip()
        assert row["expected_docs"] and set(row["expected_docs"]) <= known
        assert row["abstain"] == (not row["expected_docs"])
