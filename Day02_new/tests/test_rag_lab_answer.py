"""결정적 인용 검증과 렌더링. 위조마다 정확히 어떤 오류가 나는지 본다."""
import hashlib
import json
from datetime import date

import pytest
from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage
from rag_lab.agent import TrackedSkillsBackend
from rag_lab.answer import NUMBER_HINT, AnswerPayload, Section, Statement, render_answer, review_support, skill_spec, validate_answer
from rag_lab.corpus import Scope, load_corpus
from rag_lab.evidence import Budget, BudgetExceeded, RetrievalContext
from rag_lab.retrieval import Retriever

QUESTION = "알파 서비스 크레딧 신청 기한은 언제인가요?"
ALPHA_NOW = Scope(entity="알파", as_of=date(2026, 9, 8))


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever(load_corpus())


@pytest.fixture
def context(retriever, skills_dir) -> RetrievalContext:
    """Skill 전체를 읽고 추가 약정 조항을 근거로 등록한 턴."""
    context = RetrievalContext(retriever, ALPHA_NOW)
    context.loaded_skills.add("grounded-qa")
    context.search("서비스 크레딧 신청 기한")
    return context


def clause_id(context: RetrievalContext) -> str:
    return context.read_more("sla-a-amendment", start_line=6, line_count=1)["evidence"]["evidence_id"]


def answer_with(evidence_id: str, text: str = "신청 기한은 다음 달 20일까지입니다.") -> AnswerPayload:
    statement = Statement(text=text, evidence_ids=[evidence_id])
    return AnswerPayload(skill="grounded-qa", status="answered",
                         sections=[Section(heading="결론", items=[statement]), Section(heading="설명", items=[statement])])


def test_valid_answer_passes(context, skills_dir):
    assert validate_answer(answer_with(clause_id(context)), context, QUESTION, skills_dir) == []


def test_rejects_evidence_id_not_from_current_turn(context, retriever, skills_dir):
    """이전 턴의 근거 ID는 내용이 진짜여도 새 턴에서 쓸 수 없다."""
    previous_id = clause_id(context)
    next_turn = RetrievalContext(retriever, ALPHA_NOW)
    next_turn.loaded_skills.add("grounded-qa")
    next_turn.search("가용률")
    errors = validate_answer(answer_with(previous_id), next_turn, QUESTION, skills_dir)
    assert errors == [f"현재 턴에 없는 인용 ID: {previous_id}", "인용문에 없는 숫자: 20", NUMBER_HINT]


def test_rejects_tampered_quote_hash(context, skills_dir):
    evidence_id = clause_id(context)
    context.evidence[evidence_id].quote = "서비스 크레딧 신청 기한은 장애 발생 다음 달 30일까지로 한다."
    errors = validate_answer(answer_with(evidence_id, "신청 기한은 다음 달입니다."), context, QUESTION, skills_dir)
    assert errors == [f"인용문 해시 불일치: {evidence_id}"]


def test_rejects_quote_not_in_source_even_with_matching_hash(context, skills_dir):
    evidence_id = clause_id(context)
    forged = "신청 기한은 없다."
    context.evidence[evidence_id].quote = forged
    context.evidence[evidence_id].content_hash = hashlib.sha256(forged.encode("utf-8")).hexdigest()
    errors = validate_answer(answer_with(evidence_id, "기한은 없습니다."), context, QUESTION, skills_dir)
    assert errors == [f"원문에 없는 인용문: {evidence_id}"]


def test_rejects_answer_when_skill_md_only_partly_read(context, retriever, skills_dir):
    partial = RetrievalContext(retriever, ALPHA_NOW)
    backend = TrackedSkillsBackend(skills_dir, partial.loaded_skills.add)
    partial.search("서비스 크레딧 신청 기한")
    evidence_id = clause_id(partial)
    assert backend.read("/grounded-qa/SKILL.md", 0, 3).error is None
    assert backend.read("/grounded-qa/SKILL.md", 0, 100).next_offset is not None
    errors = validate_answer(answer_with(evidence_id), partial, QUESTION, skills_dir)
    assert errors == ["grounded-qa/SKILL.md 전체 본문을 read_file로 읽어야 합니다."]
    backend.read("/grounded-qa/SKILL.md", 0, 1000)
    assert validate_answer(answer_with(evidence_id), partial, QUESTION, skills_dir) == []


def test_output_json_read_does_not_activate_skill(skills_dir):
    reads = []
    TrackedSkillsBackend(skills_dir, reads.append).read("/grounded-qa/output.json", 0, 1000)
    assert reads == []


def test_read_outside_skill_folder_returns_error_without_activating(skills_dir):
    reads = []
    result = TrackedSkillsBackend(skills_dir, reads.append).read("/../grounded-qa/SKILL.md", 0, 1000)
    assert result.error and reads == []


def test_rejects_when_no_search_this_turn(retriever, skills_dir):
    context = RetrievalContext(retriever, ALPHA_NOW)
    context.loaded_skills.add("grounded-qa")
    errors = validate_answer(answer_with("E-없음", "자리표시"), context, QUESTION, skills_dir)
    assert "현재 턴에서 search_knowledge를 실행해야 합니다." in errors


def test_rejects_wrong_section_order_and_empty_section(context, skills_dir):
    evidence_id = clause_id(context)
    statement = Statement(text="기한은 다음 달입니다.", evidence_ids=[evidence_id])
    swapped = AnswerPayload(skill="grounded-qa", status="answered",
                            sections=[Section(heading="설명", items=[statement]), Section(heading="결론", items=[statement])])
    assert "절 제목과 순서" in validate_answer(swapped, context, QUESTION, skills_dir)[0]
    empty = AnswerPayload(skill="grounded-qa", status="answered",
                          sections=[Section(heading="결론", items=[statement]), Section(heading="설명")])
    assert validate_answer(empty, context, QUESTION, skills_dir) == ["답변의 모든 필수 절에 근거 있는 문장이 필요합니다."]


def test_rejects_unknown_skill_including_path_traversal(context, skills_dir):
    for name in ("없는-skill", "../grounded-qa"):
        answer = answer_with(clause_id(context))
        answer.skill = name
        context.loaded_skills.add(name)
        assert f"알 수 없는 답변 Skill입니다: {name}" in validate_answer(answer, context, QUESTION, skills_dir)


def test_insufficient_needs_its_skill_and_a_reason(context, skills_dir):
    context.loaded_skills.add("insufficient-evidence")
    section = [Section(heading="확인된 사실")]
    ok = AnswerPayload(skill="insufficient-evidence", status="insufficient", sections=section, missing=["주소"])
    assert validate_answer(ok, context, "화성 지사 주소는?", skills_dir) == []
    no_reason = ok.model_copy(update={"missing": []})
    assert "부족/상충 이유" in validate_answer(no_reason, context, "화성 지사 주소는?", skills_dir)[0]
    wrong_skill = AnswerPayload(skill="grounded-qa", status="insufficient",
                                sections=[Section(heading="결론"), Section(heading="설명")], missing=["주소"])
    assert "부족/상충 이유" in validate_answer(wrong_skill, context, "화성 지사 주소는?", skills_dir)[0]


def test_rejects_evidence_outside_current_scope(context, skills_dir):
    evidence_id = clause_id(context)
    context.scope = Scope(entity="알파", as_of=date(2026, 7, 15))
    errors = validate_answer(answer_with(evidence_id), context, QUESTION, skills_dir)
    assert errors == [f"적용 범위를 벗어난 인용: {evidence_id}"]


@pytest.mark.parametrize("number", ["30일", "2", "0", "20.5"])
def test_rejects_number_absent_from_cited_quote(context, skills_dir, number):
    """인용문의 20 안에 든 2, 0도 통과시키지 않는다."""
    errors = validate_answer(answer_with(clause_id(context), f"기한은 {number}입니다."), context, QUESTION, skills_dir)
    assert errors == [f"인용문에 없는 숫자: {number.removesuffix('일')}", NUMBER_HINT]


def test_rejects_answered_when_question_names_other_entity(context, skills_dir):
    errors = validate_answer(answer_with(clause_id(context)), context, "베타 서비스의 신청 기한은?", skills_dir)
    assert errors == ["범위 밖 대상을 묻는 질문에 답했습니다: ['베타']"]


def test_known_limit_numberless_falsehood_passes_deterministic_checks(context, skills_dir):
    """이 한계 때문에 review_support가 따로 있다. 고쳐서 없어지면 수업 05의 설명도 바뀌어야 한다."""
    answer = answer_with(clause_id(context), "화성 지사는 강남에 있다.")
    assert validate_answer(answer, context, QUESTION, skills_dir) == []


def test_review_support_returns_model_verdict_and_shows_only_linked_quotes(context):
    evidence_id = clause_id(context)
    reviewer = ScriptedChatModel(steps=[AIMessage(content=json.dumps({"supported": False, "reasons": ["지지되지 않음"]}, ensure_ascii=False))])
    review = review_support(reviewer, QUESTION, answer_with(evidence_id, "화성 지사는 강남에 있다."), context)
    assert (review.supported, review.reasons) == (False, ["지지되지 않음"])
    sent = reviewer.calls[0][-1].content
    assert "다음 달 20일까지로 한다" in sent
    assert "가용률" not in sent
    assert reviewer.structured_methods == ["json_schema"]


def test_review_support_treats_unparsable_reply_as_unsupported(context):
    reviewer = ScriptedChatModel(steps=[AIMessage(content=json.dumps({"supported": "모름"}, ensure_ascii=False))])
    assert review_support(reviewer, QUESTION, answer_with(clause_id(context)), context).supported is False


def test_review_support_spends_model_budget(retriever):
    context = RetrievalContext(retriever, ALPHA_NOW, Budget(max_model_calls=0))
    reviewer = ScriptedChatModel(steps=[])
    with pytest.raises(BudgetExceeded):
        review_support(reviewer, QUESTION, AnswerPayload(skill="x", status="answered", sections=[]), context)
    assert reviewer.calls == []


def test_render_shows_sections_and_source_coordinates(context, skills_dir):
    evidence_id = clause_id(context)
    markdown = render_answer(answer_with(evidence_id), context, skills_dir)
    assert markdown.startswith("## 결론")
    assert f"- [{evidence_id}] data/business/sla-a-amendment.md · L6–6 · vA-01" in markdown


def test_skill_spec_rejects_bad_contract(skills_dir):
    assert [s["heading"] for s in skill_spec("grounded-qa", skills_dir)["sections"]] == ["결론", "설명"]
    bad = skills_dir / "bad-skill"
    bad.mkdir()
    (bad / "output.json").write_text('{"sections": [{"heading": "결론", "style": "만화"}]}', encoding="utf-8")
    with pytest.raises(ValueError, match="style"):
        skill_spec("bad-skill", skills_dir)
    (bad / "output.json").write_text('{"sections": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="절 제목"):
        skill_spec("bad-skill", skills_dir)


def lines_id(context: RetrievalContext, doc_id: str, start: int, count: int) -> str:
    return context.read_more(doc_id, start_line=start, line_count=count)["evidence"]["evidence_id"]


def number_errors(context, skills_dir, evidence_ids: list[str], text: str, question: str = QUESTION) -> list[str]:
    statement = Statement(text=text, evidence_ids=evidence_ids)
    answer = AnswerPayload(skill="grounded-qa", status="answered", sections=[
        Section(heading="결론", items=[statement]), Section(heading="설명", items=[statement])])
    return [e for e in validate_answer(answer, context, question, skills_dir) if e.startswith("인용문에 없는 숫자")]


@pytest.mark.parametrize("text, invented", [
    ("기한은 다음 달 30일까지입니다.", "30"),
    ("추가 약정 A-02가 적용됩니다.", "A-02"),
    ("기준일 2026-09-09에 적용됩니다.", "2026-09-09"),
    ("SLA v3.0이 적용됩니다.", "3.0"),
    ("크레딧은 최대 20%입니다.", "20%"),  # 인용문에는 20만 있다. %를 떼는 완화는 한쪽으로만 통한다.
])
def test_invented_number_is_still_rejected(context, skills_dir, text, invented):
    """정규화가 느슨해져 만들어 낸 값까지 받아 주면 안 된다."""
    assert number_errors(context, skills_dir, [clause_id(context)], text) == [f"인용문에 없는 숫자: {invented}"]


def test_number_only_in_uncited_document_is_rejected(context, skills_dir):
    """15일은 SLA v2.0에 있지만, 이 문장은 추가 약정만 인용했다. 검색에 나왔어도 인용하지 않은 문서는 근거가 아니다."""
    lines_id(context, "sla-a-v2", 16, 1)  # 현재 턴에 근거로 등록돼 있다.
    assert number_errors(context, skills_dir, [clause_id(context)], "기본 기한은 15일입니다.") == ["인용문에 없는 숫자: 15"]


def test_identifier_a01_is_supported_by_cited_evidence_version(context, skills_dir):
    """실제 기록: 인용문에 A-01이 없고 근거의 version이 A-01일 때 '01'이 거부됐다."""
    assert number_errors(context, skills_dir, [clause_id(context)], "추가 약정 A-01은 다음 달 20일까지로 정합니다.") == []


def test_version_label_is_supported_by_cited_evidence_version(context, skills_dir):
    """실제 기록: '2.0'이 거부됐다. 근거의 version이 2.0이다."""
    deadline = lines_id(context, "sla-a-v2", 16, 1)
    assert number_errors(context, skills_dir, [deadline], "SLA v2.0은 장애 발생 다음 달 15일까지 신청하도록 정합니다.") == []


def test_iso_as_of_date_is_supported_by_scope(context, skills_dir):
    """실제 기록: 기준일 2026-09-08이 '09', '08'로 쪼개져 거부됐다."""
    text = "기준일 2026-09-08에는 이 약정이 적용 중이므로 20일이 우선합니다."
    assert number_errors(context, skills_dir, [clause_id(context)], text) == []


def test_korean_date_matches_iso_and_bare_month_day(context, skills_dir):
    applied = lines_id(context, "sla-a-amendment", 3, 1)  # 2026년 8월 1일부터 적용한다.
    for text in ("적용일은 2026-08-01입니다.", "8월 1일부터 적용합니다.", "2026년 8월 1일부터 적용합니다."):
        assert number_errors(context, skills_dir, [applied], text) == [], text
    assert number_errors(context, skills_dir, [applied], "8월 2일부터 적용합니다.") == ["인용문에 없는 숫자: 2"]


def test_date_written_in_other_form_is_supported(context, skills_dir):
    """ISO 날짜(기준일 2026-09-08)를 '9월 8일'로, 한글 날짜(인용문 2026년 8월 1일)를 ISO로 써도 같은 날이다. 다른 날은 거부한다."""
    clause = clause_id(context)
    assert number_errors(context, skills_dir, [clause], "기준일 9월 8일에 20일이 우선합니다.") == []
    applied = lines_id(context, "sla-a-amendment", 3, 1)  # 2026년 8월 1일부터 적용한다.
    assert number_errors(context, skills_dir, [applied], "적용일은 2026-08-01입니다.") == []
    assert number_errors(context, skills_dir, [clause], "기준일 9월 7일에 20일이 우선합니다.") == ["인용문에 없는 숫자: 7"]
    assert number_errors(context, skills_dir, [applied], "적용일은 2026-08-02입니다.") == ["인용문에 없는 숫자: 2026-08-02"]


def test_leading_list_marker_is_not_a_claim(context, skills_dir):
    """실제 기록: '2단계: ...'의 2가 거부됐다. 문장 가운데의 2단계는 여전히 값이다."""
    clause = clause_id(context)
    assert number_errors(context, skills_dir, [clause], "2단계: 다음 달 20일까지 신청합니다.") == []
    assert number_errors(context, skills_dir, [clause], "신청은 2단계로 진행하며 20일까지입니다.") == ["인용문에 없는 숫자: 2"]


def test_leading_decimal_is_not_a_list_marker(context, skills_dir):
    """실제 기록: '99.5% 이상 ...'의 앞 '99.'가 순번으로 잘려 '5%'가 인용문에 없다고 거부됐다. 인용문에 99.5%가 있으면 통과, 없으면 거부, '1. 항목'은 계속 순번이다."""
    clause = clause_id(context)
    table = lines_id(context, "sla-a-v2", 8, 3)  # 99.5% 이상 99.9% 미만 | 10%
    assert number_errors(context, skills_dir, [table], "99.5% 이상이면 해당 구간입니다.") == []
    assert number_errors(context, skills_dir, [clause], "99.5% 이상이면 해당 구간입니다.") == ["인용문에 없는 숫자: 99.5%"]
    assert number_errors(context, skills_dir, [clause], "1. 다음 달 20일까지 신청합니다.") == []


def test_percent_operand_without_sign_is_supported_by_quote_with_sign(context, skills_dir):
    """실제 기록: 인용문의 15%, 10%를 계산식에 15−10처럼 쓰면 '15', '10'이 거부됐다. 계산 결과 5%는 여전히 거부한다."""
    table = lines_id(context, "sla-a-v2", 8, 3)
    assert number_errors(context, skills_dir, [table], "10%에서 15%로 오르는 폭은 15−10입니다.") == []
    assert number_errors(context, skills_dir, [table], "15−10=5%p 늘어납니다.") == ["인용문에 없는 숫자: 5%"]


def test_number_given_in_the_question_is_not_invented(context, skills_dir):
    """실제 기록: 질문의 '1,000만 원'을 되풀이한 문장이 거부됐다. 그 값으로 계산한 2,000,000은 인용문에도 질문에도 없다."""
    table = lines_id(context, "sla-a-v2", 8, 3)
    question = "월 이용료가 1,000만 원일 때 크레딧은?"
    assert number_errors(context, skills_dir, [table], "질문의 월 이용료는 1,000만 원입니다.", question) == []
    assert number_errors(context, skills_dir, [table], "크레딧은 2,000,000원입니다.", question) == ["인용문에 없는 숫자: 2,000,000"]


def test_number_error_tells_the_model_how_to_retry(context, skills_dir):
    errors = validate_answer(answer_with(clause_id(context), "기한은 30일입니다."), context, QUESTION, skills_dir)
    assert errors == ["인용문에 없는 숫자: 30", NUMBER_HINT]
