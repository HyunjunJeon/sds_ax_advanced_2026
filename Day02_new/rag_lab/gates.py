"""AutoRAG의 Decision API 게이트 세 개: 분해가 필요한가, 추가 확인이 필요한가, 인용이 무관한가.

질문 문장은 AutoRAG(0c39052)의 영어 원문을 그대로 옮겼다. 그쪽이 실제 Jev로 맞춘 문장이다. 문턱값은 코드 규칙이며
우리 라벨로 재서 정한 값이 아니다. 판단이 실패하면 AutoRAG의 규칙대로 분해하지 않고, 검증하고, 인용을 남긴다.

route 분기(organize, extra, config), 메모리 판단, 데이터 소스 검사는 옮기지 않았다. 이 과정은 문서만 검색하며
검색을 건너뛰는 분기를 두면 Scope를 우회한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from rag_lab.answer import AnswerPayload
from rag_lab.decisions import DecisionBackend, DecisionError, Judgment, Noul, Question
from rag_lab.evidence import Budget, Evidence

DECOMPOSE_THRESHOLD = 0.5
FOLLOWUP_THRESHOLD = 0.5
CITATION_RELEVANCE_FLOOR = 0.3  # 이 값 미만만 뺀다. 주제가 같으면 일부만 뒷받침해도 남긴다.
_MAX_CHUNK_CHARS = 1500  # 이보다 긴 글은 참/거짓 판단에 보탬이 없고 묶음만 키운다(AutoRAG 주석).
_NO_VERDICT = "모델이 거절했거나 쓸 수 있는 답을 주지 않았습니다."

_DECOMPOSE = Noul(
    "decompose",
    "Does answering this question need several separate search queries instead of one search for the question as written?",
    "It combines several sub-questions, compares items, or needs multiple independent facts confirmed, so one search would miss parts of it.",
    "A single search for the question as written would already find the answer.",
)
_FOLLOW_UP = Noul(
    "follow_up",
    "Is any part of the user's question left unanswered, uncertain, possibly inaccurate, or asking the user to clarify?",
    "Some part is missing, hedged, vague, contradictory, says it was not found or needs verification, or the answer asks the user to clarify.",
    "Every part of the question is answered with a concrete, specific, consistent fact (a name, date, number, or definite statement).",
)
_CITATION_STATE = "Each question asks whether one cited piece of evidence is relevant to the answer sentence that cites it or to what the user asked. Judge only that evidence. The user's messages are the whole conversation so far, oldest first; the latest one is the question being answered."
_CITATION_TRUE = "The evidence contains information on the same subject as the cited sentence or what the user asked; it may back only part of the claim."
_CITATION_FALSE = "The evidence has no information on the cited sentence's subject or what the user asked: a table of contents, navigation, header or footer, copyright or boilerplate, a generic introduction, or another topic."


@dataclass(frozen=True)
class GateResult:
    """게이트 한 번의 결과. decision은 분해·추가 확인이면 bool, 인용이면 뺄 근거 ID 목록이다.

    fallback은 판단 없이 기본값을 쓴 경우의 진단 코드이고 그때 reason이 그 이유다. model은 답을 받았을 때만 안다."""
    gate: str
    decision: bool | list[str]
    threshold: float
    backend: str
    model: str | None = None
    probability: float | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    reason: str = ""
    fallback: str | None = None


@dataclass(frozen=True)
class CitedChunk:
    """답변이 인용한 근거 하나와 그 근거를 인용한 문장들."""
    evidence_id: str
    text: str
    sentences: list[str]


class MeteredDecider:
    """judge 한 번마다 decision 예산을 쓴다. BudgetExceeded는 DecisionError가 아니라서 게이트의 기본값으로 숨지 않고 실행을 멈춘다."""
    def __init__(self, decider: DecisionBackend, budget: Budget) -> None:
        self.decider, self.budget, self.name = decider, budget, decider.name

    def judge(self, state: str, questions: list[Question]) -> Judgment:
        self.budget.consume("decision", questions=[question.name for question in questions])
        return self.decider.judge(state, questions)


def _quoted(text: str) -> str:
    """사용자 글과 근거를 JSON 문자열로 넣어 줄바꿈이나 가짜 머리글로 state 구조를 흉내 내지 못하게 한다."""
    return json.dumps(text, ensure_ascii=False)


def _ask(decider: DecisionBackend, state: str, noul: Noul, threshold: float, on_failure: bool, code: str) -> GateResult:
    """참/거짓 질문 하나를 묻는다. 확률이 문턱값 이상이면 참이다. 판단이 없으면 on_failure와 진단 코드를 돌려준다."""
    try:
        judgment = decider.judge(state, [noul])
    except DecisionError as error:
        return GateResult(noul.name, on_failure, threshold, decider.name, reason=str(error), fallback=code)
    probability = judgment.verdicts[noul.name].probability
    if probability is None:
        return GateResult(noul.name, on_failure, threshold, judgment.backend, judgment.model, reason=_NO_VERDICT, fallback=code)
    return GateResult(noul.name, probability >= threshold, threshold, judgment.backend, judgment.model, probability,
                      reason=f"P={probability:.2f}, 문턱값 {threshold} 이상이면 참")


def needs_decomposition(decider: DecisionBackend, question: str) -> GateResult:
    """검색 질의를 나눠야 하는가. 판단이 없으면 나누지 않고 원 질문 하나로 검색한다."""
    return _ask(decider, f"User question: {_quoted(question)}", _DECOMPOSE, DECOMPOSE_THRESHOLD, False, "query-decomposition-fallback")


def needs_follow_up(decider: DecisionBackend, question: str, answer_text: str) -> GateResult:
    """빠른 답변을 원문으로 다시 확인해야 하는가. 판단이 없으면 확인한다. 확인 없이 끝내는 쪽이 더 비싼 실수다."""
    state = f"User question: {_quoted(question)}\n\nFirst answer:\n{_quoted(answer_text)}"
    return _ask(decider, state, _FOLLOW_UP, FOLLOWUP_THRESHOLD, True, "follow-up-check-fallback")


def _citation_noul(index: int, chunk: CitedChunk) -> Noul:
    backed = "the answer"
    if chunk.sentences:
        backed = "the answer sentence it backs: " + " ".join(map(_quoted, chunk.sentences))
    text = chunk.text.strip()
    bounded = text if len(text) <= _MAX_CHUNK_CHARS else text[:_MAX_CHUNK_CHARS - 1] + "…"
    instructions = f"Is the evidence below relevant to {backed} or to what the user asked?\nEvidence: {_quoted(bounded)}"
    return Noul(f"citation_{index}", instructions, _CITATION_TRUE, _CITATION_FALSE)


def irrelevant_citations(decider: DecisionBackend, question: str, cited: list[CitedChunk]) -> GateResult:
    """인용한 근거마다 질문 하나를 한 번의 judge로 묻고 뺄 ID를 돌려준다.

    답하지 않은 근거는 남긴다. 어느 근거에도 답이 없으면 모두 남기고 진단 코드를 적는다."""
    judged = [chunk for chunk in cited if chunk.text.strip()]
    gate, code = "citation_relevance", "citation-relevance-fallback"
    if not judged:
        return GateResult(gate, [], CITATION_RELEVANCE_FLOOR, decider.name, reason="판단할 인용이 없습니다.")
    nouls = [_citation_noul(index, chunk) for index, chunk in enumerate(judged)]
    state = f"{_CITATION_STATE}\nUser messages, oldest first:\n1. {_quoted(question)}"
    try:
        judgment = decider.judge(state, nouls)
    except DecisionError as error:
        return GateResult(gate, [], CITATION_RELEVANCE_FLOOR, decider.name, reason=str(error), fallback=code)
    answers = ((chunk.evidence_id, judgment.verdicts[noul.name].probability) for chunk, noul in zip(judged, nouls, strict=True))
    probabilities = {evidence_id: probability for evidence_id, probability in answers if probability is not None}
    if not probabilities:
        return GateResult(gate, [], CITATION_RELEVANCE_FLOOR, judgment.backend, judgment.model, reason=_NO_VERDICT, fallback=code)
    rejected = [evidence_id for evidence_id, probability in probabilities.items() if probability < CITATION_RELEVANCE_FLOOR]
    unanswered = len(judged) - len(probabilities)
    return GateResult(gate, rejected, CITATION_RELEVANCE_FLOOR, judgment.backend, judgment.model, probabilities=probabilities,
                      reason=f"문턱값 {CITATION_RELEVANCE_FLOOR} 미만을 뺍니다. 답이 없어 남긴 인용 {unanswered}개.")


def answer_text(answer: AnswerPayload) -> str:
    """추가 확인 게이트가 읽는 답변 글. 빠진 것과 상충하는 것도 답변의 일부다."""
    return "\n".join([line for section in answer.sections for line in (section.heading, *(item.text for item in section.items))]
                     + answer.missing + answer.conflicts)


def cited_chunks(answer: AnswerPayload, evidence: dict[str, Evidence]) -> list[CitedChunk]:
    """답변이 인용한 근거와 인용 문장을 모은다. 이번 턴에 없는 ID는 validate_answer가 막으므로 묻지 않는다."""
    sentences: dict[str, list[str]] = {}
    for item in (item for section in answer.sections for item in section.items):
        for reference in item.evidence_ids:
            if reference in evidence:
                sentences.setdefault(reference, []).append(item.text)
    return [CitedChunk(reference, evidence[reference].quote, texts) for reference, texts in sentences.items()]


def strip_citations(answer: AnswerPayload, rejected: list[str]) -> AnswerPayload:
    """뺄 ID를 문장에서 지운 사본을 돌려준다. 대입은 Statement의 min_length를 다시 검사하지 않아 빈 문장이 남을 수 있다."""
    stripped = answer.model_copy(deep=True)
    for item in (item for section in stripped.sections for item in section.items):
        item.evidence_ids = [reference for reference in item.evidence_ids if reference not in rejected]
    return stripped
