"""AutoRAG 후보 흐름. 재순위 모델만 가짜이고 Retriever와 범위 필터는 실제 코드다."""
from datetime import date

import pytest
from fakes import ScriptedChatModel, rag_script
from langchain_core.messages import AIMessage
from rag_lab.agent import ask
from rag_lab.corpus import Document, Scope, load_corpus
from rag_lab.pipeline import decompose_question, fit_context, interleave, retrieve
from rag_lab.retrieval import Retriever
from rag_lab.settings import ROOT

ALPHA_NOW = Scope(entity="알파", as_of=date(2026, 9, 8))
QUESTION = "환불 기한"
SUB_QUERY = "배송 지연"
DECOMPOSE_PROMPT_FOR_QUESTION = (
    "Split the user question below into search queries for a retrieval system.\n\nRules:\n"
    "- Return at most 5 queries; use fewer when fewer cover the question.\n"
    "- Each query is short, self-contained, and targets one fact or sub-question. "
    "Resolve pronouns and keep names, dates, and identifiers.\n"
    "- Together the queries must cover everything needed to answer the question.\n"
    "- Keep the question's language.\n"
    '- Reply with JSON only, no prose: {"queries": ["...", "..."]}\n\n'
    "User question: 알파 {기한}은?")


def make_doc(doc_id: str, text: str, entity: str = "알파") -> Document:
    return Document(doc_id=doc_id, title=doc_id, source=f"{doc_id}.md", domain="업무", entity=entity, version="1",
                    valid_from=date(2026, 1, 1), valid_until=None, status="approved", owner="담당자", family=None,
                    text=text)


def make_retriever(*documents: Document) -> Retriever:
    return Retriever({doc.doc_id: doc for doc in documents})


REFUND = [make_doc(f"refund-{n}", f"# 환불\n환불 기한 안내 {n}") for n in range(3)]
DELIVERY = [make_doc(f"delivery-{n}", f"# 배송\n배송 지연 안내 {n}") for n in range(3)]


class RecordingReranker:
    """받은 질의와 조각을 남긴다. 조각 본문의 끝 번호가 클수록 높은 점수를 준다."""
    def __init__(self):
        self.queries: list[str] = []
        self.texts: list[str] = []

    def score(self, query: str, texts: list[str]) -> list[float]:
        self.queries.append(query)
        self.texts = texts
        return [float(text.rsplit(" ", 1)[-1]) for text in texts]


class RaisingReranker:
    def score(self, query: str, texts: list[str]) -> list[float]:
        raise RuntimeError("sk-ant-secret-value")


class ShortReranker:
    def score(self, query: str, texts: list[str]) -> list[float]:
        return [1.0]


def test_original_question_is_searched_first_even_when_not_listed():
    run = retrieve(QUESTION, retriever=make_retriever(*REFUND, *DELIVERY), scope=ALPHA_NOW, queries=[SUB_QUERY])
    assert run.queries == [QUESTION, SUB_QUERY]
    assert run.chunk_ids[0].startswith("refund-") and run.chunk_ids[1].startswith("delivery-")


def test_repeated_original_is_searched_once_and_default_is_original_only():
    retriever = make_retriever(*REFUND)
    assert retrieve(QUESTION, retriever=retriever, scope=ALPHA_NOW).queries == [QUESTION]
    assert retrieve(QUESTION, retriever=retriever, scope=ALPHA_NOW, queries=[QUESTION]).queries == [QUESTION]


def test_rerank_scores_against_original_question_with_sub_queries():
    reranker = RecordingReranker()
    retrieve(QUESTION, retriever=make_retriever(*REFUND, *DELIVERY), scope=ALPHA_NOW, reranker=reranker,
             queries=[SUB_QUERY, "배송 안내"])
    assert reranker.queries == [QUESTION]


def test_sub_query_candidates_reach_the_reranker():
    reranker = RecordingReranker()
    retrieve(QUESTION, retriever=make_retriever(*REFUND, *DELIVERY), scope=ALPHA_NOW, reranker=reranker,
             queries=[SUB_QUERY])
    assert sum("배송" in text for text in reranker.texts) == 3


def test_pool_limits_each_query_and_is_cut_before_scoring():
    retriever = make_retriever(*REFUND, *DELIVERY)
    each_query = retrieve(QUESTION, retriever=retriever, scope=ALPHA_NOW, queries=[SUB_QUERY], pool=1)
    assert each_query.candidates == 2 and len(each_query.chunk_ids) == 1
    reranker = RecordingReranker()
    cut = retrieve(QUESTION, retriever=retriever, scope=ALPHA_NOW, reranker=reranker, queries=[SUB_QUERY], pool=2)
    assert cut.candidates == 4 and len(reranker.texts) == 2


def test_rerank_order_is_returned_and_cut_to_top_n():
    run = retrieve(QUESTION, retriever=make_retriever(*REFUND), scope=ALPHA_NOW, reranker=RecordingReranker(), top_n=2)
    assert run.chunk_ids == ["refund-2#0", "refund-1#0"]
    assert run.candidates == 3 and run.warnings == []


def test_equal_scores_keep_interleaved_order():
    class SameScore:
        def score(self, query: str, texts: list[str]) -> list[float]:
            return [0.0] * len(texts)

    retriever = make_retriever(*REFUND)
    plain = retrieve(QUESTION, retriever=retriever, scope=ALPHA_NOW)
    assert retrieve(QUESTION, retriever=retriever, scope=ALPHA_NOW, reranker=SameScore()).chunk_ids == plain.chunk_ids


@pytest.mark.parametrize("reranker, warning", [(RaisingReranker(), "rerank-failed: RuntimeError"),
                                               (ShortReranker(), "rerank-failed: ValueError")])
def test_rerank_failure_keeps_order_and_warns_with_type_name_only(reranker, warning):
    retriever = make_retriever(*REFUND, *DELIVERY)
    plain = retrieve(QUESTION, retriever=retriever, scope=ALPHA_NOW, queries=[SUB_QUERY], top_n=4)
    run = retrieve(QUESTION, retriever=retriever, scope=ALPHA_NOW, reranker=reranker, queries=[SUB_QUERY], top_n=4)
    assert run.chunk_ids == plain.chunk_ids and len(run.chunk_ids) == 4
    assert run.warnings == [warning]


def test_no_reranker_means_no_warning():
    assert retrieve(QUESTION, retriever=make_retriever(*REFUND), scope=ALPHA_NOW).warnings == []


def test_out_of_scope_document_never_reaches_the_reranker():
    other = make_doc("refund-beta", "# 환불\n환불 기한 비밀 9", entity="베타")
    reranker = RecordingReranker()
    run = retrieve(QUESTION, retriever=make_retriever(*REFUND, other), scope=ALPHA_NOW, reranker=reranker)
    assert len(reranker.texts) == 3 and not any("비밀" in text for text in reranker.texts)
    assert "refund-beta#0" not in run.chunk_ids


@pytest.mark.parametrize("rankings, expected", [
    ([["a", "b", "c"], ["d", "e"]], ["a", "d", "b", "e", "c"]),
    ([["a", "b"], ["a", "c"], ["b", "d"]], ["a", "b", "c", "d"]),
    ([[], ["a"]], ["a"]),
    ([], []),
])
def test_interleave_is_round_robin_and_first_occurrence_wins(rankings, expected):
    assert interleave(rankings) == expected


def decompose(reply: str, question: str = QUESTION) -> list[str]:
    return decompose_question(ScriptedChatModel(steps=[AIMessage(content=reply)]), question)


def test_decomposition_sends_the_autorag_prompt_verbatim():
    model = ScriptedChatModel(steps=[AIMessage(content='{"queries": ["기한"]}')])
    decompose_question(model, "알파 {기한}은?")
    assert model.calls[0][-1].text == DECOMPOSE_PROMPT_FOR_QUESTION


@pytest.mark.parametrize("reply", ["쿼리를 드릴 수 없습니다", "", "{깨진 JSON", "[1, 2]", '{"queries": "하나"}',
                                   '{"queries": [1, 2]}', '{"other": []}', '{"queries": []}', '{"queries": ["  "]}'])
def test_decomposition_falls_back_to_the_question_when_reply_cannot_be_used(reply):
    assert decompose(reply) == [QUESTION]


def test_decomposition_caps_at_five_unique_non_empty_queries():
    reply = '{"queries": ["가", "가", " ", "나", " 다 ", "라", "마", "바", "사"]}'
    assert decompose(reply) == ["가", "나", "다", "라", "마"]


def test_decomposition_reads_fenced_json():
    assert decompose('```json\n{"queries": ["가", "나"]}\n```') == ["가", "나"]


@pytest.mark.parametrize("max_bytes, kept, dropped", [
    (100, ["aaaa", "bbb", "cc"], []),
    (9, ["aaaa", "bbb", "cc"], []),
    (8, ["aaaa", "bbb"], ["cc"]),
    (4, ["aaaa"], ["bbb", "cc"]),
    (3, [], ["aaaa", "bbb", "cc"]),
    (0, [], ["aaaa", "bbb", "cc"]),
])
def test_fit_context_drops_lowest_ranks_first_and_keeps_order(max_bytes, kept, dropped):
    assert fit_context(["aaaa", "bbb", "cc"], max_bytes, len) == (kept, dropped)


def test_fit_context_does_not_skip_past_a_large_item_to_keep_a_lower_rank():
    assert fit_context(["aa", "bbbbbb", "c"], 3, len) == (["aa"], ["bbbbbb", "c"])


def test_fit_context_leaves_its_input_untouched_and_accepts_empty():
    items = ["aa", "bb"]
    fit_context(items, 2, len)
    assert items == ["aa", "bb"]
    assert fit_context([], 0, len) == ([], [])


def test_ask_passes_the_reranker_and_a_failure_lands_in_the_trace(skills_dir):
    record = ask("알파 서비스 크레딧 신청 기한은 언제인가요?", retriever=Retriever(load_corpus()), scope=ALPHA_NOW,
                 model=ScriptedChatModel(steps=rag_script(skill="grounded-qa", query="서비스 크레딧 신청 기한")),
                 skills_dir=skills_dir, max_attempts=1, reranker=RaisingReranker())
    (ROOT / "outputs" / "runs" / f"{record['run_id']}.json").unlink(missing_ok=True)
    assert record["evidence"]
    warnings = [e["warning"] for e in record["trace"]["events"] if e["event"] == "retrieval_warning"]
    assert warnings == ["rerank-failed: RuntimeError"]
