"""실제 로컬 교차 인코더의 계약. 처음 실행하면 모델 파일을 내려받지만 API 비용은 없다."""
import pytest
from rag_lab.rerank import CrossEncoderReranker
from rag_lab.settings import Settings, make_reranker

QUERY = "서비스 크레딧은 언제까지 신청하나요?"
RELEVANT = "서비스 크레딧 신청 기한은 장애가 발생한 달의 다음 달 20일까지다."
IRRELEVANT = "출장 숙박비 한도는 1박 15만 원이다."


@pytest.fixture(scope="module")
def reranker() -> CrossEncoderReranker:
    return make_reranker(Settings(api_key=""))


def test_relevant_passage_outranks_irrelevant_one(reranker):
    relevant, irrelevant = reranker.score(QUERY, [RELEVANT, IRRELEVANT])
    assert relevant > irrelevant


def test_scores_follow_input_order(reranker):
    forward = reranker.score(QUERY, [RELEVANT, IRRELEVANT])
    backward = reranker.score(QUERY, [IRRELEVANT, RELEVANT])
    assert backward == pytest.approx(forward[::-1], abs=1e-3)


def test_batches_keep_input_order_and_count(reranker):
    texts = [IRRELEVANT] * 16 + [RELEVANT]
    scores = reranker.score(QUERY, texts)
    assert len(scores) == 17
    assert scores[16] == pytest.approx(reranker.score(QUERY, [RELEVANT])[0], abs=1e-3)


def test_empty_input_returns_no_scores(reranker):
    assert reranker.score(QUERY, []) == []
