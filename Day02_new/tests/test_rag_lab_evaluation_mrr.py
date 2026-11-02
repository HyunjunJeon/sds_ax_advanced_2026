"""mrr: 손으로 계산한 고정 사례로 값을 확인한다."""
from rag_lab.evaluation import mrr


def row(retrieved: list[str], expected: list[str]) -> dict:
    return {"retrieved_docs": retrieved, "expected_docs": expected}


def test_mrr_averages_first_expected_rank_and_counts_scorable_cases():
    rows = [
        row(["a", "b", "c"], ["a"]),        # 1위 -> 1
        row(["x", "b", "c"], ["c", "b"]),   # 첫 기대 문서 b가 2위 -> 1/2
        row(["x", "y", "z"], ["a"]),        # top-k 안에 없음 -> 0
        row(["a"], []),                     # 기대 문서 없음 -> 제외
    ]
    assert mrr(rows) == ((1 + 0.5 + 0) / 3, 3)


def test_mrr_without_scorable_cases_is_none_and_zero():
    assert mrr([row(["a"], [])]) == (None, 0)
    assert mrr([]) == (None, 0)
