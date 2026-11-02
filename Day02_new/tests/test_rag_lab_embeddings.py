"""실제 로컬 임베딩 모델의 계약. 처음 실행하면 모델 파일을 내려받지만 API 비용은 없다."""
import math

import pytest
from rag_lab.embeddings import LocalE5Embeddings
from rag_lab.settings import Settings, make_embeddings

SHORT = "서비스 크레딧 신청"
LONG = "서비스 크레딧 신청 기한은 장애가 발생한 달의 다음 달 말일까지이며 요청 ID와 관측 기록을 첨부해야 한다. " * 3


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


@pytest.fixture(scope="module")
def embeddings() -> LocalE5Embeddings:
    return make_embeddings(Settings(api_key=""))


def test_vector_has_model_dimension_and_unit_length(embeddings):
    vector = embeddings.embed_query(SHORT)
    assert len(vector) == 384
    assert math.sqrt(dot(vector, vector)) == pytest.approx(1.0)


def test_query_and_passage_use_different_prefixes(embeddings):
    assert embeddings.embed_query(SHORT) != embeddings.embed_documents([SHORT])[0]


def test_related_passage_scores_above_unrelated_one(embeddings):
    query = embeddings.embed_query("서비스 크레딧은 언제까지 신청하나요?")
    related, unrelated = embeddings.embed_documents(["서비스 크레딧 신청 기한은 다음 달 20일이다.", "출장 숙박비 한도는 1박 15만 원이다."])
    assert dot(query, related) > dot(query, unrelated)


def test_padding_does_not_change_a_vector(embeddings):
    """평균 풀링이 패딩을 빼지 않으면 같은 문장이 긴 문장과 함께일 때 값이 달라진다."""
    alone = embeddings.embed_documents([SHORT])[0]
    with_long = embeddings.embed_documents([SHORT, LONG])[0]
    assert dot(alone, with_long) == pytest.approx(1.0, abs=1e-4)


def test_batches_keep_input_order_and_count(embeddings):
    texts = [f"문장 {i}" for i in range(17)]
    vectors = embeddings.embed_documents(texts)
    assert len(vectors) == 17
    assert dot(vectors[16], embeddings.embed_documents(["문장 16"])[0]) == pytest.approx(1.0, abs=1e-4)


def test_empty_input_returns_no_vectors(embeddings):
    assert embeddings.embed_documents([]) == []
