"""빠른 답변과 게이트 검증 턴. 모델은 대본이고 Retriever, 검증기, Agent 조립은 실제 코드다."""
import json
import re
from datetime import date

import pytest
from fakes import ScriptedChatModel, ScriptedDecider, ScriptExhausted, rag_script, tool_call
from langchain_core.messages import AIMessage, BaseMessage
from rag_lab.corpus import Scope, load_corpus
from rag_lab.decisions import DecisionError
from rag_lab.evidence import Budget, BudgetExceeded
from rag_lab.phases import ask_two_phase
from rag_lab.retrieval import Retriever
from rag_lab.settings import ROOT

QUESTION = "알파 서비스 크레딧 신청 기한은 언제인가요?"
OTHER_QUESTION = "알파 SLA 표의 서비스 크레딧 비율 중 최댓값은 무엇인가요?"
ALPHA_NOW = Scope(entity="알파", as_of=date(2026, 9, 8))
ALPHA_JULY = Scope(entity="알파", as_of=date(2026, 7, 15))
FOREIGN_ID = "E-000000000000"
FAST_TEXT = "빠른 답변 문장입니다."
VERIFIED_TEXT = "검증 턴이 고친 문장입니다."
UNREAD_SKILL_ERROR = "grounded-qa/SKILL.md 전체 본문을 read_file로 읽어야 합니다."


def answer_step(*, text: str = FAST_TEXT, cite: str | None = None, skill: str = "grounded-qa",
                headings: tuple[str, ...] = ("결론", "설명"), citations: int = 1):
    """받은 메시지에 나온 앞쪽 근거 ID를 인용하는 답변 단계. 근거 ID는 내용 해시라 대본에 미리 쓸 수 없다."""
    def reply(messages: list[BaseMessage]) -> AIMessage:
        found = list(dict.fromkeys(re.findall(r"E-[0-9a-f]{12}", "\n".join(m.text for m in messages))))
        item = {"text": text, "evidence_ids": [cite] if cite else found[:citations]}
        return AIMessage(content=json.dumps({
            "skill": skill, "status": "answered",
            "sections": [{"heading": heading, "items": [item]} for heading in headings],
        }, ensure_ascii=False))

    return reply


FAST = answer_step()
INVALID_FAST = answer_step(headings=("결론",))


def verification_steps(answer_text: str = VERIFIED_TEXT) -> list:
    return rag_script(skill="grounded-qa", query="서비스 크레딧 신청 기한", answer_text=answer_text)


class BrokenReranker:
    def score(self, query: str, texts: list[str]) -> list[float]:
        raise RuntimeError("재순위 모델 고장")


class RecordingReranker:
    """재순위 기준 질의를 모두 적어 둔다. 재순위 모델은 외부 경계라 가짜로 둔다."""
    def __init__(self):
        self.queries: list[str] = []

    def score(self, query: str, texts: list[str]) -> list[float]:
        self.queries.append(query)
        return [0.0] * len(texts)


class SpyRetriever(Retriever):
    """실제 Retriever로 검색하면서 받은 질의를 적어 둔다."""
    def __init__(self, documents):
        super().__init__(documents)
        self.ranked: list[str] = []

    def rank(self, query, scope, limit=6):
        self.ranked.append(query)
        return super().rank(query, scope, limit)


def decomposition(*queries: str) -> AIMessage:
    return AIMessage(content=json.dumps({"queries": list(queries)}, ensure_ascii=False))


def search_events(record: dict) -> list[str]:
    return [event["query"] for event in record["trace"]["events"] if event["event"] == "search"]


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever(load_corpus())


@pytest.fixture
def run(retriever, skills_dir):
    """ask_two_phase를 부르고 (기록, 모델)을 돌려준다. 저장된 기록 파일은 시험 뒤에 지운다."""
    records = []

    def call(steps, *, using=None, decider=None, question=QUESTION, scope=ALPHA_NOW, **kwargs):
        model = ScriptedChatModel(steps=steps)
        record = ask_two_phase(question, retriever=using or retriever, scope=scope, model=model,
                               decider=decider or ScriptedDecider(), skills_dir=skills_dir, **kwargs)
        records.append(record)
        return record, model

    yield call
    for record in records:
        (ROOT / "outputs" / "runs" / f"{record['run_id']}.json").unlink(missing_ok=True)


def statement_texts(answer: dict) -> set[str]:
    return {item["text"] for section in answer["sections"] for item in section["items"]}


def phase_names(record: dict) -> list[str]:
    return [phase["name"] for phase in record["phases"]]


def gate_entry(record: dict, name: str) -> dict:
    return next(entry for entry in record["gates"] if entry["gate"] == name)


def gate_names(record: dict) -> list[str]:
    return [entry["gate"] for entry in record["gates"]]


def first_cited(record: dict, field: str = "answer") -> list[str]:
    return record[field]["sections"][0]["items"][0]["evidence_ids"]


def test_gate_below_threshold_skips_verification(run):
    record, model = run([FAST], decider=ScriptedDecider(follow_up=0.49))
    assert record["status"] == "answered" and record["validation"] == "passed" and record["errors"] == []
    assert record["verification"] == "skipped"
    assert len(model.calls) == 1 and record["trace"]["counts"]["model"] == 1
    entry = gate_entry(record, "follow_up")
    assert (entry["probability"], entry["threshold"], entry["decision"], entry["fallback"]) == (0.49, 0.5, False, None)
    assert (entry["backend"], entry["model"]) == ("fake-backend", "fake-model")
    assert record["markdown"].startswith("## 결론") and FAST_TEXT in record["markdown"]
    assert phase_names(record) == ["decompose", "prefetch", "fast", "citations", "gate"]
    assert (ROOT / "outputs" / "runs" / f"{record['run_id']}.json").is_file()


def test_fast_phase_uses_native_format_and_binds_no_tools(run):
    _, model = run([FAST])
    assert model.bound_tool_names == []
    assert model.structured_methods == ["json_schema"]


def test_gate_at_exactly_threshold_verifies(run):
    record, model = run([FAST, *verification_steps()], decider=ScriptedDecider(follow_up=0.5))
    assert record["verification"] == "ran" and record["status"] == "answered"
    assert len(model.calls) == 5
    assert phase_names(record) == ["decompose", "prefetch", "fast", "citations", "gate", "verification"]


@pytest.mark.parametrize("reply", [DecisionError("fake-backend: HTTP 500"), None], ids=["decision-error", "refusal"])
def test_unusable_follow_up_gate_verifies_and_leaves_a_diagnostic(run, reply):
    record, _ = run([FAST, *verification_steps()], decider=ScriptedDecider(follow_up=reply))
    assert record["verification"] == "ran" and record["status"] == "answered"
    assert gate_entry(record, "follow_up")["fallback"] == "follow-up-check-fallback"
    assert [d.split(":")[0] for d in record["diagnostics"]] == ["follow-up-check-fallback"]


@pytest.mark.parametrize("reply", [DecisionError("fake-backend: HTTP 500"), None], ids=["decision-error", "refusal"])
def test_unusable_decomposition_gate_searches_the_question_only(run, reply):
    record, model = run([FAST], decider=ScriptedDecider(decompose=reply))
    assert record["status"] == "answered" and record["queries"] == [QUESTION] and len(model.calls) == 1
    assert [d.split(":")[0] for d in record["diagnostics"]] == ["query-decomposition-fallback"]


@pytest.mark.parametrize("reply", [DecisionError("fake-backend: HTTP 500"), None], ids=["decision-error", "refusal"])
def test_unusable_citation_gate_keeps_the_citations(run, reply):
    record, _ = run([FAST], decider=ScriptedDecider(citation=reply))
    assert record["status"] == "answered" and record["citations_removed"] == [] and len(first_cited(record)) == 1
    assert [d.split(":")[0] for d in record["diagnostics"]] == ["citation-relevance-fallback"]


def test_a_clean_run_has_no_diagnostics(run):
    record, _ = run([FAST])
    assert record["diagnostics"] == [] and record["citations_removed"] == []


def test_ask_two_phase_requires_a_decider(retriever):
    with pytest.raises(TypeError, match="decider"):
        ask_two_phase(QUESTION, retriever=retriever, scope=ALPHA_NOW, model=ScriptedChatModel(steps=[]))


def test_decision_calls_spend_their_own_budget_not_the_model_budget(run):
    decider = ScriptedDecider()
    record, _ = run([FAST], decider=decider)
    assert record["trace"]["counts"]["decision"] == len(decider.calls) == 3
    assert record["trace"]["counts"]["model"] == 1


def test_default_budget_allows_six_decision_calls():
    budget = Budget()
    for _ in range(6):
        budget.consume("decision")
    with pytest.raises(BudgetExceeded, match="decision 호출 한도"):
        budget.consume("decision")


@pytest.mark.parametrize("limit, calls", [(0, 0), (1, 1), (2, 2)])
def test_exhausted_decision_budget_stops_before_the_call_instead_of_falling_back(run, limit, calls):
    decider = ScriptedDecider()
    record, _ = run([FAST], decider=decider, budget=Budget(max_decision_calls=limit))
    assert record["status"] == "error" and record["answer"] is None and len(decider.calls) == calls
    assert record["errors"][0].startswith("BudgetExceeded") and "decision 호출 한도" in record["errors"][0]
    assert record["diagnostics"] == []


# ---- 인용 관련성 ----

def test_rejected_citation_is_removed_and_the_rest_of_the_statement_stands(run):
    decider = ScriptedDecider(citation=[0.1, 0.9])
    record, _ = run([answer_step(citations=2)], decider=decider)
    assert record["status"] == "answered" and record["verification"] == "skipped"
    kept = first_cited(record)
    removed = record["citations_removed"]
    assert len(kept) == 1 and len(removed) == 1 and removed[0]["evidence_id"] != kept[0]
    assert removed[0]["probability"] == 0.1 and removed[0]["doc_id"]
    assert removed[0]["evidence_id"] not in record["markdown"] and kept[0] in record["markdown"]


def test_citation_at_exactly_the_floor_stays(run):
    record, _ = run([answer_step(citations=2)], decider=ScriptedDecider(citation=0.3))
    assert len(first_cited(record)) == 2 and record["citations_removed"] == []


def test_statement_left_with_no_citation_fails_validation_and_goes_to_verification(run):
    """게이트가 끝내도 좋다고 해도 인용 없는 문장은 그대로 나가지 않는다."""
    decider = ScriptedDecider(citation=[0.1, 0.9], follow_up=0.01)
    record, model = run([FAST, *verification_steps()], decider=decider)
    assert record["verification"] == "ran" and record["status"] == "answered"
    assert first_cited(record, "fast_answer") == [] and len(record["citations_removed"]) == 1
    fast_errors = next(phase["errors"] for phase in record["phases"] if phase["name"] == "fast")
    assert fast_errors == [f"인용이 남지 않은 문장: {FAST_TEXT}"] * 2
    assert f"인용이 남지 않은 문장: {FAST_TEXT}" in model.calls[1][-1].text
    assert statement_texts(record["answer"]) == {VERIFIED_TEXT}


def test_statement_left_with_no_citation_is_an_error_under_verify_never(run):
    record, _ = run([FAST], verify="never", decider=ScriptedDecider(citation=0.1))
    assert record["status"] == "error" and record["answer"] is None and record["markdown"] == ""
    assert f"인용이 남지 않은 문장: {FAST_TEXT}" in record["errors"]


def test_verified_answer_is_checked_for_citation_relevance_too(run):
    decider = ScriptedDecider(follow_up=0.9, citation=[0.9, 0.1, 0.9])
    steps = [FAST, *verification_steps()[:2], answer_step(text=VERIFIED_TEXT, citations=2)]
    record, _ = run(steps, decider=decider)
    assert record["status"] == "answered" and len(first_cited(record)) == 1
    assert len(record["citations_removed"]) == 1
    assert gate_names(record) == ["decompose", "citation_relevance", "follow_up", "citation_relevance"]


def test_verified_statement_left_with_no_citation_is_retried_then_blocked(run):
    decider = ScriptedDecider(follow_up=0.9, citation=[0.9, 0.1, 0.1])
    steps = [FAST, *verification_steps()[:2], answer_step(text=VERIFIED_TEXT), answer_step(text=VERIFIED_TEXT)]
    record, model = run(steps, decider=decider)
    assert record["status"] == "error" and record["answer"] is None and record["markdown"] == ""
    assert f"인용이 남지 않은 문장: {VERIFIED_TEXT}" in record["errors"]
    assert any(m.text.startswith("검증 실패를 수정하세요: 인용이 남지 않은 문장") for m in model.calls[-1])
    assert statement_texts(record["fast_answer"]) == {FAST_TEXT}


def test_answer_that_skipped_verification_is_judged_once(run):
    decider = ScriptedDecider()
    record, _ = run([FAST], decider=decider)
    assert gate_names(record) == ["decompose", "citation_relevance", "follow_up"] and len(decider.calls) == 3


def test_foreign_citation_is_not_sent_to_the_decision_api(run):
    decider = ScriptedDecider(citation=0.0)
    record, _ = run([answer_step(cite=FOREIGN_ID)], verify="never", decider=decider)
    assert f"현재 턴에 없는 인용 ID: {FOREIGN_ID}" in record["errors"] and record["citations_removed"] == []
    assert FOREIGN_ID not in "".join(state for state, _ in decider.calls)


def test_follow_up_gate_reads_the_answer_text_including_what_is_missing(run):
    decider = ScriptedDecider()
    def insufficient(messages):
        reference = re.search(r"E-[0-9a-f]{12}", "\n".join(m.text for m in messages))[0]
        return AIMessage(content=json.dumps({"skill": "insufficient-evidence", "status": "insufficient", "missing": ["부족한 사항 하나"],
                                             "sections": [{"heading": "확인된 사실", "items": [{"text": "확인한 문장", "evidence_ids": [reference]}]}]}, ensure_ascii=False))
    run([insufficient], decider=decider)
    state = next(state for state, questions in decider.calls if questions[0].name == "follow_up")
    assert '"확인된 사실\\n확인한 문장\\n부족한 사항 하나"' in state


def test_invalid_fast_answer_verifies_even_under_auto_with_a_low_gate(run):
    record, model = run([INVALID_FAST, *verification_steps()], decider=ScriptedDecider(follow_up=0.01))
    assert record["verification"] == "ran" and record["status"] == "answered"
    assert gate_entry(record, "follow_up")["probability"] == 0.01
    fast_errors = next(phase["errors"] for phase in record["phases"] if phase["name"] == "fast")
    assert any("절 제목" in error for error in fast_errors)
    verification_message = model.calls[1][-1].text
    assert "절 제목" in verification_message and FAST_TEXT in verification_message


def test_unparsed_fast_reply_goes_to_verification(run):
    decider = ScriptedDecider(follow_up=0.01)
    record, _ = run([AIMessage(content="JSON이 아닌 답"), *verification_steps()], decider=decider)
    assert record["verification"] == "ran" and record["status"] == "answered"
    assert record["fast_answer"] is None
    assert gate_names(record) == ["decompose", "citation_relevance"]  # 읽지 못한 답은 물을 글이 없다. 인용 판단은 검증 턴의 답이다.


def test_verify_never_with_invalid_answer_is_an_error_with_no_answer(run):
    record, model = run([INVALID_FAST], verify="never")
    assert record["status"] == "error" and record["validation"] == "failed"
    assert record["markdown"] == "" and record["answer"] is None
    assert any("절 제목" in error for error in record["errors"])
    assert record["verification"] == "skipped" and len(model.calls) == 1


def test_verify_never_with_valid_answer_makes_no_gate_call(run):
    record, model = run([FAST], verify="never")
    assert record["status"] == "answered" and len(model.calls) == 1
    assert "follow_up" not in gate_names(record)


def test_verify_always_makes_no_gate_call(run):
    record, model = run([FAST, *verification_steps()], verify="always")
    assert record["verification"] == "ran" and record["status"] == "answered"
    assert len(model.calls) == 5 and "follow_up" not in gate_names(record)


def test_unknown_verify_mode_raises_before_any_call(retriever):
    model = ScriptedChatModel(steps=[])
    with pytest.raises(ValueError, match="sometimes"):
        ask_two_phase(QUESTION, retriever=retriever, scope=ALPHA_NOW, model=model, decider=ScriptedDecider(), verify="sometimes")
    assert model.calls == []


def test_verification_correction_replaces_the_fast_answer(run):
    record, _ = run([FAST, *verification_steps()], decider=ScriptedDecider(follow_up=0.9))
    assert statement_texts(record["answer"]) == {VERIFIED_TEXT}
    assert statement_texts(record["fast_answer"]) == {FAST_TEXT}
    assert VERIFIED_TEXT in record["markdown"] and FAST_TEXT not in record["markdown"]


def test_verification_message_tells_the_model_not_to_mention_the_fast_answer_or_the_check(run):
    """프롬프트가 행동을 보장하지는 않는다. 이 시험은 지시가 메시지에 실려 가는지만 본다. 실제 누출은 실측으로 본다."""
    _, model = run([FAST, *verification_steps()], verify="always")
    verify_message = next(m.text for m in model.calls[-1] if QUESTION in m.text and "evidence" in m.text)
    assert re.search(r"최종 답변은 .*읽", verify_message)
    assert re.search(r"빠른 답변.*확인.*언급하지 마세요", verify_message)


def test_fast_answer_is_not_the_answer_when_it_passes_but_verification_fails(run):
    steps = [FAST, *verification_steps()[:2], answer_step(cite=FOREIGN_ID), answer_step(cite=FOREIGN_ID)]
    record, _ = run(steps, decider=ScriptedDecider(follow_up=0.9))
    assert record["status"] == "error" and record["answer"] is None and record["markdown"] == ""
    assert statement_texts(record["fast_answer"]) == {FAST_TEXT}


def test_foreign_citation_is_rejected_in_the_fast_phase(run):
    record, _ = run([answer_step(cite=FOREIGN_ID)], verify="never")
    assert record["status"] == "error"
    assert f"현재 턴에 없는 인용 ID: {FOREIGN_ID}" in record["errors"]


def test_foreign_citation_is_rejected_in_the_verification_phase(run):
    steps = [FAST, *verification_steps()[:2], answer_step(cite=FOREIGN_ID), answer_step(cite=FOREIGN_ID)]
    record, _ = run(steps, verify="always")
    assert record["status"] == "error" and record["validation"] == "failed"
    assert f"현재 턴에 없는 인용 ID: {FOREIGN_ID}" in record["errors"]


def test_verification_can_cite_prefetched_evidence_without_searching_again(run):
    steps = [FAST, *verification_steps()[:2], answer_step(text=VERIFIED_TEXT)]
    record, _ = run(steps, verify="always")
    assert record["status"] == "answered" and record["trace"]["counts"]["search"] == 1


def test_verification_retries_once_with_the_errors_in_its_messages(run):
    good = verification_steps()
    steps = [FAST, *good[:2], answer_step(cite=FOREIGN_ID), *good[2:]]
    record, model = run(steps, verify="always")
    assert record["status"] == "answered"
    assert any(message.text.startswith(f"검증 실패를 수정하세요: 현재 턴에 없는 인용 ID: {FOREIGN_ID}") for message in model.calls[-1])
    assert any(event["event"] == "validation_retry" for event in record["trace"]["events"])


def test_fast_system_block_holds_the_whole_skill_body_and_records_the_read(run):
    record, model = run([FAST])
    assert "절차 149" in model.calls[0][0].text  # 시험용 Skill 본문의 마지막 줄. read_file 기본 limit 100을 넘는 위치다.
    assert record["loaded_skills"] == ["grounded-qa", "insufficient-evidence"]
    reads = [event["skill"] for event in record["trace"]["events"] if event["event"] == "skill_read"]
    assert reads == ["grounded-qa", "insufficient-evidence"]


def fast_request(run, question: str, scope: Scope) -> tuple[BaseMessage, BaseMessage]:
    """빠른 단계 요청의 (system, user) 메시지. 분해와 검증을 꺼서 모델 호출은 빠른 답변 하나다."""
    _, model = run([FAST], question=question, scope=scope, decompose=False, verify="never")
    system, user = model.calls[0]
    return system, user


def test_fast_system_block_is_byte_identical_across_questions_and_scopes(run):
    """앞부분이 한 바이트라도 다르면 캐시를 읽지 못한다. 범위와 질문은 실행마다 달라지는 값이다."""
    first, _ = fast_request(run, QUESTION, ALPHA_NOW)
    second, _ = fast_request(run, OTHER_QUESTION, ALPHA_JULY)
    assert first.content == second.content


def test_fast_system_block_ends_with_an_ephemeral_breakpoint(run):
    system, _ = fast_request(run, QUESTION, ALPHA_NOW)
    assert system.content[-1]["cache_control"] == {"type": "ephemeral"}


def test_fast_user_message_carries_question_scope_and_evidence_outside_the_system_block(run):
    system, user = fast_request(run, QUESTION, ALPHA_NOW)
    material = json.loads(user.text)
    assert material["question"] == QUESTION
    assert (material["scope"]["entity"], material["scope"]["as_of"]) == ("알파", "2026-09-08")
    assert material["evidence"] and "skills" not in material
    for leaked in (QUESTION, "2026-09-08", "알파", material["evidence"][0]["evidence_id"], material["evidence"][0]["quote"]):
        assert leaked not in system.text


def test_fast_system_block_lists_skills_in_name_order(run):
    system, _ = fast_request(run, QUESTION, ALPHA_NOW)
    assert system.text.index('"name": "grounded-qa"') < system.text.index('"name": "insufficient-evidence"')


def test_fast_answer_naming_a_skill_that_was_not_loaded_is_rejected(run):
    record, _ = run([answer_step(skill="comparison")], verify="never")
    assert record["status"] == "error"
    assert "comparison/SKILL.md 전체 본문을 read_file로 읽어야 합니다." in record["errors"]


def test_folder_without_output_json_is_not_loaded_for_the_fast_phase(run, skills_dir):
    folder = skills_dir / "no-output"
    folder.mkdir()
    (folder / "SKILL.md").write_text("---\nname: no-output\ndescription: 설명\n---\n", encoding="utf-8")
    record, _ = run([FAST], verify="never")
    assert "no-output" not in record["loaded_skills"]


def test_verification_must_read_the_skill_itself(run):
    """빠른 단계에서 읽은 기록을 넘겨주면 검증 턴은 Skill을 보지 않고도 검증을 통과한다."""
    steps = [FAST, answer_step(text=VERIFIED_TEXT), answer_step(text=VERIFIED_TEXT)]
    record, _ = run(steps, verify="always")
    assert record["status"] == "error" and UNREAD_SKILL_ERROR in record["errors"]


def test_raising_reranker_leaves_a_warning_and_still_answers(run):
    record, _ = run([FAST], reranker=BrokenReranker())
    assert record["status"] == "answered"
    assert record["retrieval_warnings"] == ["rerank-failed: RuntimeError"]


def test_no_warnings_without_a_reranker(run):
    record, _ = run([FAST])
    assert record["retrieval_warnings"] == []


@pytest.mark.parametrize("budget, failed_phase, message", [
    (Budget(max_searches=0), "prefetch", "search 호출 한도"),
    (Budget(max_model_calls=0), "fast", "model 호출 한도"),
    (Budget(max_model_calls=1), "verification", "model 호출 한도"),
    (Budget(max_model_calls=2), "verification", "model 호출 한도"),
    (Budget(max_decision_calls=0), "decompose", "decision 호출 한도"),
    (Budget(max_decision_calls=1), "citations", "decision 호출 한도"),
    (Budget(max_decision_calls=2), "gate", "decision 호출 한도"),
    (Budget(max_decision_calls=3), "verification", "decision 호출 한도"),
])
def test_budget_exhaustion_in_any_phase_is_an_error_with_no_answer(run, budget, failed_phase, message):
    record, _ = run([FAST, *verification_steps()], budget=budget, decider=ScriptedDecider(follow_up=0.9))
    assert record["status"] == "error" and record["answer"] is None and record["markdown"] == ""
    assert record["errors"][0].startswith("BudgetExceeded") and message in record["errors"][0]
    assert record["phases"][-1]["name"] == failed_phase and record["phases"][-1]["errors"] == record["errors"]


def test_budget_exhaustion_in_decompose_call_stops_before_the_model(run):
    record, model = run([], decider=ScriptedDecider(decompose=0.9), budget=Budget(max_model_calls=0))
    assert record["status"] == "error" and record["errors"][0].startswith("BudgetExceeded")
    assert model.calls == [] and phase_names(record) == ["decompose"]


def test_runtime_failure_is_recorded_not_raised(run):
    record, _ = run([])
    assert record["status"] == "error" and record["errors"][0].startswith(ScriptExhausted.__name__)
    assert (ROOT / "outputs" / "runs" / f"{record['run_id']}.json").is_file()


def test_decompose_off_makes_no_gate_and_no_decomposition_call(run):
    decider = ScriptedDecider(decompose=0.9)
    record, model = run([FAST], decompose=False, decider=decider)
    assert record["queries"] == [QUESTION] and len(model.calls) == 1
    assert "decompose" not in gate_names(record) and phase_names(record)[0] == "prefetch"
    assert not any("Split the user question" in message.text for call in model.calls for message in call)


def test_decomposition_is_on_by_default(run):
    sub_query = "서비스 크레딧 신청 기한"
    record, _ = run([decomposition(sub_query), FAST], decider=ScriptedDecider(decompose=0.9))
    assert record["queries"] == [QUESTION, sub_query]


def test_decompose_gate_at_threshold_decomposes(run):
    sub_query = "서비스 크레딧 신청 기한"
    record, model = run([decomposition(sub_query), FAST], decider=ScriptedDecider(decompose=0.5))
    assert record["queries"] == [QUESTION, sub_query]
    assert record["trace"]["counts"]["search"] == 1 and len(model.calls) == 2
    assert phase_names(record) == ["decompose", "prefetch", "fast", "citations", "gate"]


def test_decomposed_prefetch_reranks_only_against_the_original_question(run):
    """분해한 질의는 후보를 넓힐 뿐이다. 하위 질의별로 재순위하면 측정에서 나빠진 구조로 돌아간다."""
    subs = ["서비스 크레딧 신청 기한", "서비스 크레딧 비율"]
    spy, reranker = SpyRetriever(load_corpus()), RecordingReranker()
    record, _ = run([decomposition(*subs), FAST], decider=ScriptedDecider(decompose=0.9), using=spy, reranker=reranker)
    assert record["status"] == "answered"
    assert reranker.queries == [QUESTION]
    assert spy.ranked == [QUESTION, *subs]
    assert search_events(record) == [QUESTION] and record["trace"]["counts"]["search"] == 1
    assert record["queries"] == [QUESTION, *subs]


def test_decomposed_prefetch_merges_queries_without_a_reranker(run):
    subs = ["서비스 크레딧 신청 기한", "서비스 크레딧 비율"]
    spy = SpyRetriever(load_corpus())
    record, _ = run([decomposition(*subs), FAST], decider=ScriptedDecider(decompose=0.9), using=spy)
    assert spy.ranked == [QUESTION, *subs] and search_events(record) == [QUESTION]


@pytest.mark.parametrize("returned, expected", [
    ((QUESTION,), [QUESTION]),
    ((QUESTION, "서비스 크레딧 비율"), [QUESTION, "서비스 크레딧 비율"]),
    (("서비스 크레딧 비율", QUESTION), [QUESTION, "서비스 크레딧 비율"]),
])
def test_decomposition_returning_the_question_itself_is_deduplicated(run, returned, expected):
    spy = SpyRetriever(load_corpus())
    record, _ = run([decomposition(*returned), FAST], decider=ScriptedDecider(decompose=0.9), using=spy)
    assert record["queries"] == expected and spy.ranked == expected


def test_verification_search_ranks_against_the_query_the_agent_asked(run):
    """검증 턴의 검색은 Agent가 직접 낸 질의이므로 그 질의가 기준이다."""
    reranker = RecordingReranker()
    record, _ = run([FAST, *verification_steps()], verify="always", reranker=reranker)
    assert record["status"] == "answered"
    assert reranker.queries == [QUESTION, "서비스 크레딧 신청 기한"]


def test_prefetch_is_one_search_however_many_queries_there_are(run):
    subs = [f"하위 질의 {n}" for n in range(5)]
    record, _ = run([decomposition(*subs), FAST], decider=ScriptedDecider(decompose=0.9), verify="never", budget=Budget(max_searches=1))
    assert record["queries"] == [QUESTION, *subs]
    assert record["status"] == "answered" and record["trace"]["counts"]["search"] == 1


def test_decompose_gate_below_threshold_searches_the_question_only(run):
    spy = SpyRetriever(load_corpus())
    record, model = run([FAST], decider=ScriptedDecider(decompose=0.49), using=spy)
    assert record["queries"] == [QUESTION] and len(model.calls) == 1 and spy.ranked == [QUESTION]


def test_decomposed_queries_all_search_and_leave_the_budget_for_verification(run):
    """기본 예산은 검색 3회다. 질의 수와 상관없이 미리 검색은 1회이므로 자르지 않는다."""
    subs = [f"하위 질의 {n}" for n in range(5)]
    record, _ = run([decomposition(*subs), FAST, *verification_steps()], decider=ScriptedDecider(decompose=0.9, follow_up=0.9))
    assert record["queries"] == [QUESTION, *subs]
    assert record["retrieval_warnings"] == []
    assert record["status"] == "answered" and record["trace"]["counts"]["search"] == 2


def supported(value: bool, *reasons: str) -> ScriptedChatModel:
    return ScriptedChatModel(steps=[AIMessage(content=json.dumps({"supported": value, "reasons": list(reasons)}))])


def test_reviewer_pass_in_verification_is_recorded(run):
    record, _ = run([FAST, *verification_steps()], verify="always", reviewer=supported(True))
    assert record["status"] == "answered" and record["support_review"] == "passed"


def test_reviewer_failure_in_verification_retries_then_blocks(run):
    steps = [FAST, *verification_steps(), verification_steps()[-1]]
    reviewer = ScriptedChatModel(steps=[AIMessage(content=json.dumps({"supported": False, "reasons": ["지지 안 됨"]}))] * 2)
    record, _ = run(steps, verify="always", reviewer=reviewer)
    assert record["status"] == "error" and record["answer"] is None
    assert record["support_review"] == "failed" and record["errors"] == ["지지 안 됨"]
    assert len(reviewer.calls) == 2


def test_reviewer_also_guards_an_answer_the_gate_would_release(run):
    record, _ = run([FAST, *verification_steps()], reviewer=ScriptedChatModel(steps=[
        AIMessage(content=json.dumps({"supported": False, "reasons": ["지지 안 됨"]})),
        AIMessage(content=json.dumps({"supported": True})),
    ]))
    assert record["verification"] == "ran" and record["status"] == "answered"
    assert statement_texts(record["answer"]) == {VERIFIED_TEXT}


def test_reviewer_failure_under_verify_never_blocks_the_answer(run):
    record, _ = run([FAST], verify="never", reviewer=supported(False, "지지 안 됨"))
    assert record["status"] == "error" and record["markdown"] == "" and record["answer"] is None
    assert record["validation"] == "passed" and record["support_review"] == "failed"


def test_skipped_verification_without_reviewer_says_review_was_skipped(run):
    record, _ = run([FAST])
    assert record["support_review"] == "skipped"


def test_denied_tool_is_refused_during_verification(run, skills_dir):
    steps = [FAST, tool_call("write_file", {"file_path": "/만든파일.md", "content": "x"}), *verification_steps()]
    record, _ = run(steps, verify="always")
    assert [e["name"] for e in record["trace"]["events"] if e["event"] == "tool_denied"] == ["write_file"]
    assert not (skills_dir / "만든파일.md").exists()
