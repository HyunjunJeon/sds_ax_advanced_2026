"""예산, 근거 등록, 범위 고정 도구."""
import json
from datetime import date

import pytest
from rag_lab.corpus import Document, Scope, load_cases, load_corpus
from rag_lab.evaluation import evaluate_retrieval, load_gold, recall_by_type
from rag_lab.evidence import Budget, BudgetExceeded, RetrievalContext, assess_sufficiency, make_search_tools
from rag_lab.retrieval import Retriever

ALPHA_NOW = Scope(entity="알파", as_of=date(2026, 9, 8))


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever(load_corpus())


@pytest.mark.parametrize("kind, limit", [("tool", "max_tool_calls"), ("model", "max_model_calls"),
                                         ("search", "max_searches"), ("read", "max_reads")])
def test_budget_raises_on_call_past_limit(kind, limit):
    budget = Budget(**{limit: 2})
    budget.consume(kind)
    budget.consume(kind)
    with pytest.raises(BudgetExceeded):
        budget.consume(kind)
    assert budget.report()["counts"][kind] == 2


def test_budget_zero_limit_blocks_first_call_and_other_kinds_only_record():
    budget = Budget(max_model_calls=0)
    with pytest.raises(BudgetExceeded):
        budget.consume("model")
    budget.consume("tool_denied", name="write_file")
    assert budget.report()["events"][-1]["name"] == "write_file"
    assert "tool_denied" not in budget.report()["counts"]


def test_budget_raises_when_time_is_up():
    budget = Budget(max_seconds=0)
    with pytest.raises(BudgetExceeded):
        budget.remaining()
    with pytest.raises(BudgetExceeded):
        budget.consume("note")


def test_search_budget_stops_second_search(retriever):
    context = RetrievalContext(retriever, ALPHA_NOW, Budget(max_searches=1))
    context.search("서비스 크레딧")
    with pytest.raises(BudgetExceeded):
        context.search("서비스 크레딧")


def test_search_registers_exact_source_quotes_only_in_scope(retriever):
    context = RetrievalContext(retriever, ALPHA_NOW)
    result = context.search("서비스 크레딧 비율 신청 기한")
    assert result["status"] == "found" and context.search_count == 1
    for item in result["evidence"]:
        assert item["evidence_id"] in context.evidence
        assert item["quote"] in retriever.documents[item["doc_id"]].text
        assert retriever.documents[item["doc_id"]].applies(ALPHA_NOW)
    assert result["scope"] == {"entity": "알파", "as_of": "2026-09-08", "domain": None}


def test_related_docs_point_to_family_in_scope_without_body(retriever):
    """같은 family의 만료본(sla-a-v1)과 초안(sla-a-draft)은 힌트에도 나오지 않는다."""
    result = RetrievalContext(retriever, ALPHA_NOW).search("가용률 구간별 서비스 크레딧 비율", limit=1)
    assert result["evidence"][0]["doc_id"] == "sla-a-amendment"
    assert result["related_docs"] == ["sla-a-v2"]


@pytest.mark.parametrize("query, limit", [("", 6), ("   ", 6), ("가" * 1501, 6), ("기한", 0), ("기한", 11)])
def test_search_returns_status_for_bad_input_without_spending(retriever, query, limit):
    context = RetrievalContext(retriever, ALPHA_NOW)
    assert context.search(query, limit)["status"] == "invalid_input"
    assert context.search_count == 0 and context.budget.report()["counts"] == {}


def test_read_more_refuses_out_of_scope_documents(retriever):
    context = RetrievalContext(retriever, ALPHA_NOW)
    for doc_id in ("sla-b", "sla-a-v1", "sla-a-draft", "없는문서"):
        assert context.read_more(doc_id)["status"] == "out_of_scope"
    assert context.evidence == {}


def test_read_more_returns_requested_lines(retriever):
    context = RetrievalContext(retriever, ALPHA_NOW)
    item = context.read_more("sla-a-amendment", start_line=6, line_count=1)["evidence"]
    assert item["quote"] == "서비스 크레딧 신청 기한은 장애 발생 다음 달 20일까지로 한다."
    assert (item["start_line"], item["end_line"]) == (6, 6)
    assert item["evidence_id"] in context.evidence


@pytest.mark.parametrize("kwargs", [{"start_line": 0}, {"line_count": 0}, {"line_count": 121}])
def test_read_more_rejects_bad_ranges(retriever, kwargs):
    assert RetrievalContext(retriever, ALPHA_NOW).read_more("sla-a-v2", **kwargs)["status"] == "invalid_input"


def test_read_past_end_is_not_evidence(retriever):
    assert RetrievalContext(retriever, ALPHA_NOW).read_more("sla-a-v2", start_line=9999)["status"] == "no_evidence"


def test_context_budget_excludes_evidence_and_records_event(retriever):
    context = RetrievalContext(retriever, ALPHA_NOW, Budget(max_context_bytes=10))
    assert context.read_more("sla-a-v2")["status"] == "context_budget"
    assert context.search("서비스 크레딧")["status"] == "context_budget"
    assert context.evidence == {}
    assert context.budget.report()["events"][-1]["event"] == "context_excluded"


class ChunkOrderReranker:
    """재순위 뒤의 순서가 BM25 순서와 반드시 달라지도록 입력 순서를 뒤집는 점수를 준다."""
    def score(self, query: str, texts: list[str]) -> list[float]:
        return [float(position) for position in range(len(texts))]


class RaisingReranker:
    def score(self, query: str, texts: list[str]) -> list[float]:
        raise RuntimeError("모델을 읽지 못했습니다")


def test_search_with_reranker_returns_its_order(retriever):
    query = "서비스 크레딧 비율 신청 기한"
    allowed_ids = retriever.rank(query, ALPHA_NOW, limit=50)
    expected = allowed_ids[::-1][:3]
    result = RetrievalContext(retriever, ALPHA_NOW, reranker=ChunkOrderReranker()).search(query, limit=3)
    assert [(e["doc_id"], e["quote"]) for e in result["evidence"]] == [
        (retriever.chunks[c].doc_id, retriever.chunks[c].text) for c in expected]


def test_search_with_raising_reranker_still_returns_evidence_and_traces_the_warning(retriever):
    query = "서비스 크레딧 비율 신청 기한"
    plain = RetrievalContext(retriever, ALPHA_NOW).search(query, limit=3)
    context = RetrievalContext(retriever, ALPHA_NOW, reranker=RaisingReranker())
    result = context.search(query, limit=3)
    assert result == plain
    warnings = [e["warning"] for e in context.budget.report()["events"] if e["event"] == "retrieval_warning"]
    assert warnings == ["rerank-failed: RuntimeError"]


def test_search_with_reranker_keeps_the_context_budget_report(retriever):
    context = RetrievalContext(retriever, ALPHA_NOW, Budget(max_context_bytes=10), reranker=ChunkOrderReranker())
    assert context.search("서비스 크레딧")["status"] == "context_budget"
    assert context.evidence == {}
    assert context.budget.report()["events"][-1]["event"] == "context_excluded"


SMALL_A, BIG, SMALL_B = "크레딧 작은 조각 가", "크레딧 큰 조각 " + "나" * 400, "크레딧 작은 조각 다"
RANK_ORDER = [SMALL_A, BIG, SMALL_B]


class FixedOrderReranker:
    """주어진 원문 순서대로 점수를 준다. 시험이 순위를 직접 정해 자르기만 본다."""
    def __init__(self, order: list[str]):
        self.order = order

    def score(self, query: str, texts: list[str]) -> list[float]:
        return [-float(self.order.index(text)) if text in self.order else -99.0 for text in texts]


def sized_document(doc_id: str, text: str) -> Document:
    return Document(doc_id=doc_id, title=doc_id, source=f"{doc_id}.md", domain="sla", entity="알파", version="v1",
                    valid_from=date(2026, 1, 1), valid_until=None, status="approved", owner="담당자", family=None, text=text)


@pytest.fixture(scope="module")
def sized_retriever() -> Retriever:
    return Retriever({d.doc_id: d for d in (sized_document("small-a", SMALL_A), sized_document("big", BIG),
                                            sized_document("small-b", SMALL_B))})


def excluded_docs(context: RetrievalContext) -> list[str]:
    return [e["doc_id"] for e in context.budget.report()["events"] if e["event"] == "context_excluded"]


def bytes_of(sized_retriever: Retriever, *quotes: str) -> int:
    """근거를 예산 없이 등록해 그 JSON 크기를 잰다. 시험의 한도를 이 크기로 딱 맞춘다."""
    probe = RetrievalContext(sized_retriever, ALPHA_NOW, reranker=FixedOrderReranker(list(quotes)))
    found = probe.search("크레딧", limit=len(quotes))["evidence"]
    return len(json.dumps(found, ensure_ascii=False).encode("utf-8"))


@pytest.mark.parametrize("fetch", [lambda c: c.search("크레딧", limit=3), lambda c: c.prefetch("크레딧", [], top_n=3)],
                         ids=["search", "prefetch"])
def test_overflow_drops_every_lower_rank_even_a_small_one_that_would_fit(sized_retriever, fetch):
    """small-b는 small-a와 합쳐도 한도 안이다. 그래도 위 순위가 잘렸으니 등록하지 않는다."""
    limit = bytes_of(sized_retriever, SMALL_A, SMALL_B)
    context = RetrievalContext(sized_retriever, ALPHA_NOW, Budget(max_context_bytes=limit),
                               reranker=FixedOrderReranker(RANK_ORDER))
    result = fetch(context)
    assert [item["quote"] for item in result["evidence"]] == [SMALL_A]
    assert excluded_docs(context) == ["big", "small-b"]
    assert [item.quote for item in context.evidence.values()] == [SMALL_A]
    assert result["status"] == "found" and result["context_bytes"] <= limit


def test_context_limit_is_inclusive_at_the_exact_byte(sized_retriever):
    limit = bytes_of(sized_retriever, SMALL_A)
    reranker = FixedOrderReranker([SMALL_A])
    fits = RetrievalContext(sized_retriever, ALPHA_NOW, Budget(max_context_bytes=limit), reranker=reranker)
    result = fits.search("크레딧", limit=1)
    assert result["status"] == "found" and result["context_bytes"] == limit
    short = RetrievalContext(sized_retriever, ALPHA_NOW, Budget(max_context_bytes=limit - 1), reranker=reranker)
    assert short.search("크레딧", limit=1)["status"] == "context_budget"
    assert short.evidence == {} and short.search_count == 1


def test_context_trim_keeps_all_candidates_under_the_limit_in_rank_order(sized_retriever):
    limit = bytes_of(sized_retriever, *RANK_ORDER)
    context = RetrievalContext(sized_retriever, ALPHA_NOW, Budget(max_context_bytes=limit),
                               reranker=FixedOrderReranker(RANK_ORDER))
    assert [item["quote"] for item in context.search("크레딧", limit=3)["evidence"]] == RANK_ORDER
    assert excluded_docs(context) == []


def test_registered_evidence_stays_and_does_not_count_as_new(sized_retriever):
    limit = bytes_of(sized_retriever, SMALL_A, SMALL_B)
    context = RetrievalContext(sized_retriever, ALPHA_NOW, Budget(max_context_bytes=limit),
                               reranker=FixedOrderReranker([SMALL_A]))
    context.search("크레딧", limit=1)
    context.reranker = FixedOrderReranker([BIG, SMALL_A, SMALL_B])
    result = context.search("크레딧", limit=3)
    assert [item["quote"] for item in result["evidence"]] == [SMALL_A]
    assert excluded_docs(context) == ["big", "small-b"]
    context.reranker = FixedOrderReranker([SMALL_A])
    assert context.search("크레딧", limit=1)["status"] == "found"
    assert excluded_docs(context) == ["big", "small-b"]


def test_read_more_refuses_only_the_item_it_was_asked_for(sized_retriever):
    limit = bytes_of(sized_retriever, SMALL_A)
    context = RetrievalContext(sized_retriever, ALPHA_NOW, Budget(max_context_bytes=limit))
    assert context.read_more("big")["status"] == "context_budget"
    assert context.read_more("small-a")["status"] == "found"
    assert excluded_docs(context) == ["big"]


def test_prefetch_returns_the_shape_search_returns_and_spends_one_search(retriever):
    query = "서비스 크레딧 비율 신청 기한"
    context = RetrievalContext(retriever, ALPHA_NOW)
    assert context.prefetch(query, [], top_n=3) == RetrievalContext(retriever, ALPHA_NOW).search(query, limit=3)
    assert context.search_count == 1 and context.budget.report()["counts"] == {"search": 1}


def test_prefetch_accepts_top_n_above_the_search_tool_limit():
    many = Retriever({f"doc-{n}": sized_document(f"doc-{n}", f"크레딧 조각 {n}") for n in range(30)})
    context = RetrievalContext(many, ALPHA_NOW)
    assert context.search("크레딧", limit=11)["status"] == "invalid_input"
    assert len(context.prefetch("크레딧", [], top_n=11)["evidence"]) == 11
    assert len(RetrievalContext(many, ALPHA_NOW).prefetch("크레딧", [])["evidence"]) == 25


@pytest.mark.parametrize("question", ["", "   ", "가" * 1501])
def test_prefetch_returns_status_for_bad_question_without_spending(retriever, question):
    context = RetrievalContext(retriever, ALPHA_NOW)
    assert context.prefetch(question, ["서비스 크레딧"])["status"] == "invalid_input"
    assert context.search_count == 0 and context.budget.report()["counts"] == {}


def test_prefetch_without_reranker_merges_the_queries(sized_retriever):
    """원 질문에 맞는 조각이 없어도 하위 질의의 후보가 같은 한 번의 검색으로 합쳐진다."""
    context = RetrievalContext(sized_retriever, ALPHA_NOW)
    result = context.prefetch("화성", ["크레딧"])
    assert result["status"] == "found" and {item["quote"] for item in result["evidence"]} == set(RANK_ORDER)
    assert context.budget.report()["counts"] == {"search": 1}


def test_prefetch_with_raising_reranker_keeps_merged_order_and_traces_the_warning(sized_retriever):
    plain = RetrievalContext(sized_retriever, ALPHA_NOW).prefetch("화성", ["크레딧"])
    context = RetrievalContext(sized_retriever, ALPHA_NOW, reranker=RaisingReranker())
    assert context.prefetch("화성", ["크레딧"]) == plain
    warnings = [e["warning"] for e in context.budget.report()["events"] if e["event"] == "retrieval_warning"]
    assert warnings == ["rerank-failed: RuntimeError"]


def test_tools_give_model_no_scope_arguments(retriever):
    search_tool, read_tool = make_search_tools(RetrievalContext(retriever, ALPHA_NOW))
    assert search_tool.name == "search_knowledge" and read_tool.name == "read_evidence"
    assert set(search_tool.args) == {"query", "limit"}
    assert set(read_tool.args) == {"doc_id", "start_line", "line_count"}


def test_sufficiency_is_a_signal_mars_low_beta_flagged(retriever):
    known = {d.entity for d in retriever.documents.values()}
    def assess(case_id):
        case = next(c for c in load_cases() if c["id"] == case_id)
        quotes = [retriever.chunks[c].text for c in retriever.rank(case["question"], ALPHA_NOW, 6)]
        return assess_sufficiency(case["question"], quotes, ALPHA_NOW, known)
    mars, beta = assess("unknown-mars-branch"), assess("scope-trap-beta-ratio")
    assert mars.low_coverage and "화성" in mars.missing_terms and mars.out_of_scope_terms == []
    assert not beta.low_coverage and beta.out_of_scope_terms == ["베타"]
    assert assess_sufficiency("은 는", [], ALPHA_NOW, known).coverage == 0.0


def test_evaluation_separates_missing_from_wrong_documents(retriever):
    cases, gold = load_cases(), load_gold()
    unscoped = evaluate_retrieval(retriever, cases, gold, k=2, use_scope=False)
    scoped = evaluate_retrieval(retriever, cases, gold, k=2)
    assert sum(len(row["out_of_scope_docs"]) for row in unscoped) > 0
    assert sum(len(row["out_of_scope_docs"]) for row in scoped) == 0
    assert len(scoped) == len(cases)
    summary = {row["type"]: row for row in recall_by_type(scoped)}
    assert summary["unknown"]["recall"] is None and summary["unknown"]["cases"] == 1
    assert summary["versioned"]["recall"] == 1.0
    assert {row["type"]: row["recall"] for row in recall_by_type(unscoped)}["versioned"] == 0.5


def test_evaluation_uses_custom_rank_and_k_one_caps_two_document_recall(retriever):
    case = next(c for c in load_cases() if c["id"] == "simple-deadline-current")
    row = evaluate_retrieval(retriever, [case], load_gold(), k=1, rank=lambda q, s: ["sla-a-v2#1"])[0]
    assert row["retrieved_docs"] == ["sla-a-v2"]
    assert row["missing_docs"] == ["sla-a-amendment"] and row["recall"] == 0.5
