"""동결한 어려운 질문 파일의 형식 검사. 검색은 실행하지 않는다."""
from rag_lab.corpus import load_cases, load_corpus
from rag_lab.evaluation import load_gold
from rag_lab.settings import ROOT

CASES = ROOT / "data/cases_hard.jsonl"
GOLD = ROOT / "data/gold_hard.jsonl"


def test_hard_files_pair_up_with_same_fields_as_originals():
    cases, gold = load_cases(CASES), load_gold(GOLD)
    assert 12 <= len(cases) <= 16
    assert [c["id"] for c in cases] == list(gold)
    assert all(set(c) == set(load_cases()[0]) and c["namespace"] == "business" for c in cases)
    original = next(iter(load_gold().values()))
    assert all(set(original) <= set(row) for row in gold.values())


def test_gold_rows_are_drafts_with_reason_and_known_documents():
    known = set(load_corpus())
    for row in load_gold(GOLD).values():
        assert row["review_status"] == "draft" and row["reason"].strip()
        assert set(row["expected_docs"]) <= known
        assert row["abstain"] == (not row["expected_docs"])


def test_originals_are_unchanged_by_default_paths():
    assert len(load_cases()) == 12 and len(load_gold()) == 12
