"""코퍼스, 조각, BM25, RRF, 범위 필터."""
from datetime import date

import pytest
from fakes import HashEmbeddings
from rag_lab.corpus import Chunk, Document, Scope, count_cut_tables, fixed_chunks, load_cases, load_corpus, section_chunks
from rag_lab.retrieval import (BM25Index, DenseIndex, Retriever, content_terms, corroborate, fuse_scores, rrf, tokenize)

ALPHA_NOW = Scope(entity="알파", as_of=date(2026, 9, 8))


def chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id, chunk_id, "", text, 0, len(text), 1, 1)


@pytest.fixture(scope="module")
def documents() -> dict[str, Document]:
    return load_corpus()


@pytest.fixture(scope="module")
def retriever(documents) -> Retriever:
    return Retriever(documents)


def test_tokenize_strips_korean_particles():
    assert "기한" in tokenize("신청 기한은")
    assert "기한은" not in tokenize("신청 기한은")


def test_korean_bm25_finds_document_through_attached_particle(documents):
    index = BM25Index([c for doc in documents.values() for c in section_chunks(doc)])
    top_chunk, top_score = index.search("현금영수증을 제출하나요", limit=1)[0]
    assert top_chunk.startswith("travel#")
    assert top_score > 0
    whitespace = BM25Index([c for doc in documents.values() for c in section_chunks(doc)], tokenizer=str.split)
    assert whitespace.search("현금영수증을", limit=1) == []


def test_bm25_keeps_candidate_when_term_appears_in_every_chunk():
    """BM25Okapi라면 IDF가 음수가 되어 후보가 사라지는 경우다."""
    index = BM25Index([chunk("a", "크레딧 신청"), chunk("b", "크레딧 비율"), chunk("c", "크레딧 한도")], tokenizer=str.split)
    assert {chunk_id for chunk_id, _ in index.search("크레딧")} == {"a", "b", "c"}


def test_bm25_allowed_ids_limit_candidates_and_empty_set_returns_nothing():
    index = BM25Index([chunk("a", "크레딧"), chunk("b", "크레딧")], tokenizer=str.split)
    assert [chunk_id for chunk_id, _ in index.search("크레딧", allowed_ids={"b"})] == ["b"]
    assert index.search("크레딧", allowed_ids=set()) == []


def test_rrf_sums_reciprocal_ranks():
    assert rrf([["a", "b", "c"], ["b", "c"]]) == ["b", "c", "a"]


def test_rrf_weight_changes_winner_and_ties_break_by_key():
    assert rrf([["a", "b"], ["b", "a"]]) == ["a", "b"]
    assert rrf([["a", "b"], ["b", "a"]], weights=[1.0, 2.0]) == ["b", "a"]


def test_rrf_counts_duplicate_once_and_rejects_bad_arguments():
    assert rrf([["a", "a", "b"], ["b", "c"]])[0] == "b"
    with pytest.raises(ValueError):
        rrf([["a"]], weights=[1.0, 2.0])
    with pytest.raises(ValueError):
        rrf([["a"]], constant=0)


def test_scope_excludes_other_entity_expired_and_draft(retriever):
    query = "알파 베타 서비스 크레딧 비율 신청 기한 초안"
    unscoped = {retriever.chunks[c].doc_id for c in retriever.rank(query, None, limit=32)}
    scoped = {retriever.chunks[c].doc_id for c in retriever.rank(query, ALPHA_NOW, limit=32)}
    assert {"sla-b", "sla-a-v1", "sla-a-draft"} <= unscoped
    assert not {"sla-b", "sla-a-v1", "sla-a-draft"} & scoped
    assert "sla-a-v2" in scoped


def test_valid_until_day_itself_is_excluded(documents):
    last_day = Scope("알파", date(2026, 6, 30))
    boundary = Scope("알파", date(2026, 7, 1))
    assert documents["sla-a-v1"].applies(last_day) and not documents["sla-a-v2"].applies(last_day)
    assert documents["sla-a-v2"].applies(boundary) and not documents["sla-a-v1"].applies(boundary)


def test_domain_filter_and_common_entity(documents):
    assert documents["travel"].applies(Scope("알파", date(2026, 9, 8), domain="인사"))
    assert not documents["travel"].applies(Scope("알파", date(2026, 9, 8), domain="계약"))


def test_section_chunks_keep_original_text_positions_and_tables(documents):
    chunks = [c for doc in documents.values() for c in section_chunks(doc)]
    assert len(chunks) == 32
    for c in chunks:
        doc = documents[c.doc_id]
        assert doc.text[c.start:c.end] == c.text
        assert doc.text.split("\n")[c.start_line - 1] == c.text.split("\n")[0]
    assert count_cut_tables(documents["sla-a-v2"], section_chunks(documents["sla-a-v2"])) == 0


def test_title_only_piece_attaches_to_next_section(documents):
    first = section_chunks(documents["sla-a-amendment"])[0]
    assert first.text.startswith("# 알파 SLA 개별 추가 약정")
    assert first.heading == "서명과 적용"


def test_fixed_chunks_can_cut_a_table_section_chunks_do_not(documents):
    doc = documents["sla-a-v2"]
    assert count_cut_tables(doc, fixed_chunks(doc, size=250, overlap=50)) == 1


def test_fixed_chunks_cover_text_and_reject_bad_overlap(documents):
    doc = documents["travel"]
    pieces = fixed_chunks(doc, size=100, overlap=20)
    assert pieces[0].text == doc.text[:100] and pieces[1].start == 80 and pieces[-1].end == len(doc.text)
    with pytest.raises(ValueError):
        fixed_chunks(doc, size=100, overlap=100)


def test_dense_index_ranks_the_matching_chunk_first(documents):
    index = DenseIndex(section_chunks(documents["travel"]), HashEmbeddings())
    assert index.search("숙박비 한도", limit=1)[0][0] == "travel#1"


def test_dense_scope_filter_and_missing_embeddings_error(documents):
    dense = Retriever(documents, embeddings=HashEmbeddings(), mode="dense")
    docs = {dense.chunks[c].doc_id for c in dense.rank("크레딧 비율", ALPHA_NOW, limit=32)}
    assert "sla-b" not in docs
    for mode in ("dense", "hybrid"):
        with pytest.raises(ValueError):
            Retriever(documents, mode=mode)
    with pytest.raises(ValueError):
        Retriever(documents, mode="없는방식")


def test_hybrid_ranks_with_scope(documents):
    hybrid = Retriever(documents, embeddings=HashEmbeddings(), mode="hybrid")
    ranked = hybrid.rank("숙박비 한도", ALPHA_NOW, limit=3)
    assert len(ranked) == 3 and ranked[0].startswith("travel#")


def test_fusion_ranks_with_scope_and_never_returns_out_of_scope_chunk(documents):
    fusion = Retriever(documents, embeddings=HashEmbeddings(), mode="fusion")
    ranked = fusion.rank("크레딧 비율", ALPHA_NOW, limit=len(fusion.chunks))
    assert ranked and "sla-b" not in {fusion.chunks[c].doc_id for c in ranked}
    assert fusion.rank("숙박비 한도", ALPHA_NOW, limit=3)[0].startswith("travel#")


def test_fusion_needs_embeddings(documents):
    with pytest.raises(ValueError):
        Retriever(documents, mode="fusion")


def test_fuse_scores_combines_normalised_scores():
    # a: 밀집 최고(1.0), BM25 0 -> 0.7 / b: 밀집 최저(0), BM25 최고(1.0) -> 0.3 / c: 밀집 0.5 -> 0.35
    assert fuse_scores([("a", 0.9), ("b", 0.1), ("c", 0.5)], [("b", 4.0)]) == ["a", "c", "b"]


def test_fuse_scores_dense_weight_changes_winner():
    dense, sparse = [("a", 1.0), ("b", 0.0)], [("b", 2.0)]
    assert fuse_scores(dense, sparse, dense_weight=0.7) == ["a", "b"]
    assert fuse_scores(dense, sparse, dense_weight=0.3) == ["b", "a"]


def test_fuse_scores_degenerate_inputs():
    assert fuse_scores([("b", 0.5), ("a", 0.5)], []) == ["a", "b"]  # 밀집 점수가 모두 같아도 0으로 나누지 않는다
    assert fuse_scores([], [("x", 2.0), ("y", 1.0)]) == ["x", "y"]
    assert fuse_scores([("a", 0.2), ("b", 0.8)], []) == ["b", "a"]
    assert fuse_scores([], []) == []


def test_fuse_scores_ties_break_by_key():
    assert fuse_scores([("z", 1.0), ("a", 1.0), ("m", 0.0)], []) == ["a", "z", "m"]


def test_content_terms_keeps_unique_nouns_in_order():
    assert content_terms("크레딧 크레딧 비율은") == ["크레딧", "비율"]


def test_cases_file_carries_no_answers():
    case = load_cases()[0]
    assert "expected_docs" not in case and "facts" not in case


def siblings(source: str, count: int) -> tuple[dict[str, float], dict[str, str], dict[str, set[str]]]:
    """같은 출처의 점수 0 조각 count개."""
    names = [f"{source}{i}" for i in range(count)]
    return {n: 0.0 for n in names}, {n: source for n in names}, {n: {"dense"} for n in names}


def test_corroborate_without_corroboration_keeps_score_order_and_key_order():
    scores = {"b": 0.4, "a": 0.4, "c": 0.9}
    sources, methods = {k: k for k in scores}, {k: {"dense"} for k in scores}
    assert corroborate(scores, sources, methods) == ["c", "b", "a"]  # 동점은 입력 순서


def test_corroborate_bonus_matches_log_formula_for_sibling_chunks():
    # 형제 3개: 보강도 3, 가산 ln(4) * 0.15 = 0.20794 -> 0.5 + 0.20794 = 0.70794
    sib_scores, sib_sources, sib_methods = siblings("S", 3)
    sources = {"a": "S", "c": "T", **sib_sources}
    methods = {"a": {"dense"}, "c": {"dense"}, **sib_methods}
    assert corroborate({"a": 0.5, "c": 0.707, **sib_scores}, sources, methods)[0] == "a"
    assert corroborate({"a": 0.5, "c": 0.709, **sib_scores}, sources, methods)[0] == "c"


def test_corroborate_counts_methods_that_found_the_source():
    # 조각 하나뿐이어도 두 방법이 찾았으면 보강도 1: 0.5 + ln(2) * 0.15 = 0.60397
    sources = {"a": "S", "c": "T"}
    methods = {"a": {"dense", "bm25"}, "c": {"dense"}}
    assert corroborate({"c": 0.603, "a": 0.5}, sources, methods)[0] == "a"
    assert corroborate({"c": 0.605, "a": 0.5}, sources, methods)[0] == "c"


def test_corroborate_prefers_corroborated_document_over_equal_scored_one_off():
    sources = {"one": "T", "a": "S", "b": "S"}
    methods = {k: {"dense"} for k in sources}
    assert corroborate({"one": 0.5, "a": 0.5, "b": 0.1}, sources, methods)[:2] == ["a", "one"]


def test_corroborate_bonus_is_capped_at_point_three():
    # 형제 20개면 무제한 가산은 ln(21) * 0.15 = 0.457이지만 상한은 0.3: 0.5 + 0.3 = 0.8 < 0.85
    sib_scores, sib_sources, sib_methods = siblings("S", 20)
    sources = {"x": "S", "y": "T", **sib_sources}
    methods = {"x": {"dense"}, "y": {"dense"}, **sib_methods}
    assert corroborate({"x": 0.5, "y": 0.85, **sib_scores}, sources, methods)[:2] == ["y", "x"]


def test_corroborate_does_not_overturn_a_large_relevance_gap():
    sib_scores, sib_sources, sib_methods = siblings("S", 5)
    sources = {"weak": "S", "strong": "T", **sib_sources}
    methods = {"weak": {"dense", "bm25"}, "strong": {"dense"}, **sib_methods}
    assert corroborate({"weak": 0.2, "strong": 0.9, **sib_scores}, sources, methods)[0] == "strong"


def test_fusion_corroboration_off_equals_plain_fusion_order(documents):
    off = Retriever(documents, embeddings=HashEmbeddings(), mode="fusion", corroboration=False)
    for query in ("숙박비 한도", "크레딧 비율", "휴가 신청"):
        plain = fuse_scores(off.dense.search(query, len(off.chunks)), off.bm25.search(query, len(off.chunks)))
        assert off.rank(query, None, limit=len(off.chunks)) == plain[:len(off.chunks)]
        assert off.rank(query, None, limit=4) == plain[:4]


def test_fusion_corroboration_is_default_and_keeps_recall_depth(documents):
    on = Retriever(documents, embeddings=HashEmbeddings(), mode="fusion")
    off = Retriever(documents, embeddings=HashEmbeddings(), mode="fusion", corroboration=False)
    assert on.corroboration is True
    full = len(on.chunks)
    ranked = on.rank("크레딧 비율", ALPHA_NOW, limit=full)
    assert sorted(ranked) == sorted(off.rank("크레딧 비율", ALPHA_NOW, limit=full))


def test_fusion_corroboration_never_lets_out_of_scope_chunks_in(documents):
    on = Retriever(documents, embeddings=HashEmbeddings(), mode="fusion")
    allowed = {c.chunk_id for c in on.chunks.values() if documents[c.doc_id].applies(ALPHA_NOW)}
    ranked = on.rank("크레딧 비율", ALPHA_NOW, limit=len(on.chunks))
    assert set(ranked) == allowed and len(ranked) == len(allowed)
