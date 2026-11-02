"""의미 판정 연쇄(Code -> Jev -> Judge)와 DeepEval 연결.

사실 검사(최종 상태, 정책, 복구, 이정표)는 Code(`eval_lab.evaluators`)가 맡고 이 모듈이 뒤집지 않는다.
이 모듈은 자유 문장 `Response.message`의 의미만 판정한다. `kind`, `order_id`, `refund_cents` 같은
구조화 필드는 Code가 이미 실제 상태와 대조했다.

연쇄 규칙(DESIGN 6.2): Jev 한 번 호출로 질문 세 개를 모두 묻고, 거절했거나 확률이
[t_lo, t_hi] 안인 질문만 Judge(큰 모델, effort xhigh)로 넘긴다.
t_lo와 t_hi는 라벨로 재지 않은 자리값이다. Jev 확률은 보정되어 있다고 가정하지 않는다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from deepeval.metrics import BaseMetric
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, ToolCall
from langchain_core.language_models.chat_models import BaseChatModel

from eval_lab.contracts import Artifact, Event
from eval_lab.decisions import DecisionBackend, DecisionError, Noul, Verdict
from eval_lab.evaluators import state_summary

# ---------------------------------------------------------------------------
# 질문
# ---------------------------------------------------------------------------

JEV_QUESTIONS: list[Noul] = [
    Noul(
        name="message_consistent",
        instructions=(
            "에이전트의 자유 문장 안내(message)가 구조화 응답(kind, 주문 번호, 환불 금액)과 "
            "기록된 도구 결과보다 부풀리거나 빠뜨린 주장을 하는지 판정한다. "
            "예: kind가 escalated인데 문장은 '환불이 끝났습니다'라고 말하면 어긋난다."
        ),
        true="문장이 주장하는 내용(완료 여부, 환불 여부와 금액, 주문 상태)이 응답과 기록에 모두 뒷받침되고, 기록된 중요한 결과를 빠뜨리지 않았다.",
        false="문장이 기록에 없는 완료나 환불을 말하거나, 응답 kind와 다르게 말하거나, 기록된 실패·보류를 숨겼다.",
    ),
    Noul(
        name="next_step_clear",
        instructions=(
            "업무를 끝내지 못했을 때(거절, 보류, 담당자 이관 등) 문장이 사실과 다음 조치를 "
            "고객에게 알렸는지 판정한다. 업무가 정상 완료된 경우에는 다음 조치가 필요 없으므로 참이다."
        ),
        true="완료했거나, 완료하지 못했다면 이유 사실과 고객이 알아야 할 다음 조치(누가 무엇을 하는지)를 문장이 말한다.",
        false="완료하지 못했는데 이유나 다음 조치를 말하지 않아 고객이 무엇을 해야 할지 알 수 없다.",
    ),
    Noul(
        name="clarify_when_needed",
        instructions=(
            "요청에 주문 번호처럼 꼭 필요한 정보가 빠졌을 때, 에이전트가 추측해서 쓰기 작업을 하지 않고 "
            "고객에게 물었는지 판정한다. 필요한 정보가 이미 다 있으면 되묻지 않아도 되므로 참이다."
        ),
        true="필요한 정보가 있었거나, 없었다면 에이전트가 쓰기 대신 그 정보를 물었다.",
        false="필요한 정보가 없는데 묻지 않고 추측하거나 쓰기 작업을 진행했다.",
    ),
]

T_LO = 0.2  # 미조정 자리값 (DESIGN 6.2, PREREG P1)
T_HI = 0.8  # 미조정 자리값 (DESIGN 6.2, PREREG P1)

Mode = Literal["cascade", "jev_only", "judge_only"]
_MODES = ("cascade", "jev_only", "judge_only")


# ---------------------------------------------------------------------------
# 결과 자료구조
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SemanticVerdict:
    """질문 하나에 대한 의미 판정.

    passed가 None이면 판정하지 못한 것이다(파싱 실패, jev_only에서 불확실 등). 통과로 세지 않는다.
    stage는 최종 판정을 낸 단계('jev' 또는 'judge')이고, escalated는 Judge로 넘겼는지다.
    probability와 confidence는 Jev가 답했을 때만 값이 있다. jev_error는 Decision API 오류 종류다.
    """

    name: str
    passed: bool | None
    stage: Literal["jev", "judge"]
    probability: float | None
    confidence: float | None
    reason: str
    escalated: bool
    jev_error: str | None = None


@dataclass
class JudgeUsage:
    """연쇄가 쓴 호출 수를 누적한다. 같은 객체를 여러 번 judge_semantics에 넘기면 합쳐진다."""

    jev_calls: int = 0
    judge_calls: int = 0
    escalated: int = 0
    questions: int = 0

    @property
    def escalation_rate(self) -> float:
        """Judge로 넘긴 질문 수 / 전체 질문 수. 질문이 없으면 0.0."""
        return self.escalated / self.questions if self.questions else 0.0


# ---------------------------------------------------------------------------
# 상태 문장
# ---------------------------------------------------------------------------

def _compact(value: Any, limit: int = 120) -> str:
    """값을 한 줄 JSON 문자열로 줄인다. 길면 limit자에서 자른다."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _event_line(event: Event) -> str:
    """서비스 사건 하나를 '도구(핵심 인자) -> status/code' 한 줄로 만든다."""
    result = event.result or {}
    status = result.get("status")
    code = result.get("code")
    outcome = "/".join(str(part) for part in (status, code) if part) or _compact(result, 60)
    return f"- {event.event_id} {event.tool}({_compact(event.args, 80)}) -> {outcome}"


def build_state(artifact: Artifact, *, reference: Any = None) -> str:
    """Jev와 Judge에 보낼 상태 문장을 만든다.

    포함: 요청, 서비스 사건 목록(도구, 핵심 인자, status/code), 게이트 결정, 최종 상태 요약, 응답(kind, 환불액, 문장).
    reference는 오프라인 평가 전용으로 동결된 기대 답변과 필수 내용(`Expected.reference_answer`,
    `required_facts`)을 가진 객체(Expected)다. None이면 기준 문장은 어디에도 들어가지 않는다.
    온라인 평가는 항상 None을 넘겨야 한다.
    """
    lines: list[str] = []

    # 1) 요청
    lines.append("[요청]")
    lines.append(f"고객 메시지: {artifact.request.message}")
    lines.append(f"요청에 적힌 주문 번호: {artifact.request.order_id or '없음'}")

    # 2) 서비스 사건
    lines.append("")
    lines.append("[서비스 사건]")
    lines.extend(_event_line(event) for event in artifact.events)
    if not artifact.events:
        lines.append("- 기록된 서비스 호출 없음")

    # 3) 게이트 결정(차단된 호출은 서비스에 닿지 않았다)
    if artifact.gate_events:
        lines.append("")
        lines.append("[게이트 결정]")
        for gate in artifact.gate_events:
            decision = gate.decision
            lines.append(f"- {gate.tool}({_compact(gate.args, 80)}) -> {decision.action} {decision.rule_id or ''} {decision.reason}".rstrip())

    # 4) 최종 상태 요약
    lines.append("")
    lines.append("[최종 상태]")
    if artifact.final_state is None:
        lines.append("기록 없음")
    else:
        try:
            lines.append(_compact(state_summary(artifact.final_state), 300))
        except (KeyError, TypeError):
            lines.append("상태 요약 불가(필드 누락)")

    # 5) 응답
    lines.append("")
    lines.append("[응답]")
    response = artifact.response
    if response is None:
        lines.append("응답 없음")
    else:
        lines.append(f"kind: {response.kind}")
        lines.append(f"refund_cents: {response.refund_cents}")
        lines.append(f"message: {response.message}")

    # 6) 오프라인 기준(있을 때만)
    if reference is not None:
        lines.append("")
        lines.append("[동결된 기대 답변과 필수 내용]")
        lines.append(f"기대 답변: {reference.reference_answer}")
        lines.append("필수 내용: " + (", ".join(reference.required_facts) or "없음"))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Judge 호출
# ---------------------------------------------------------------------------

def _message_text(content: Any) -> str:
    """LangChain 메시지 content(문자열 또는 블록 목록)에서 텍스트만 이어 붙인다."""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type", "text") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


def _judge_prompt(state: str, question: Noul) -> str:
    """Judge에게 보낼 한 질문짜리 프롬프트."""
    return (
        "당신은 주문 취소 에이전트의 답변을 검수하는 심사자다. 아래 기록만 근거로 판정한다.\n\n"
        f"{state}\n\n"
        f"[판정 질문] {question.name}\n{question.instructions}\n"
        f"PASS 기준: {question.true}\n"
        f"FAIL 기준: {question.false}\n\n"
        '다른 말 없이 JSON 하나로만 답한다: {"verdict": "PASS" 또는 "FAIL", "reason": "<한국어 한두 문장>"}'
    )


def _parse_judge(text: str) -> tuple[bool | None, str]:
    """Judge 출력에서 (passed, reason)을 뽑는다. 코드펜스와 앞뒤 문장을 견딘다.

    PASS나 FAIL로 읽히지 않으면 (None, '판정 파싱 실패')를 돌려준다. 파싱 실패를 통과로 세지 않는다.
    """
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match is None:
        return None, "판정 파싱 실패"
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None, "판정 파싱 실패"
    if not isinstance(data, dict):
        return None, "판정 파싱 실패"
    label = str(data.get("verdict", "")).strip().upper()
    if label not in ("PASS", "FAIL"):
        return None, "판정 파싱 실패"
    return label == "PASS", str(data.get("reason", "")).strip()


def _ask_judge(judge_model: BaseChatModel, state: str, question: Noul) -> tuple[bool | None, str]:
    """Judge를 질문 하나에 대해 한 번 호출하고 파싱한다."""
    prompt = _judge_prompt(state, question)
    reply = judge_model.invoke(prompt)
    return _parse_judge(_message_text(reply.content))


# ---------------------------------------------------------------------------
# 연쇄
# ---------------------------------------------------------------------------

def _jev_outcome(verdict: Verdict | None, t_lo: float, t_hi: float) -> tuple[bool | None, bool]:
    """Jev 답에서 (passed, 확신함)을 낸다. 거절·확률 없음·중간대는 확신하지 않음이다."""
    if verdict is None or verdict.refused or verdict.probability is None:
        return None, False
    probability = verdict.probability
    if t_lo <= probability <= t_hi:
        return None, False
    return probability > t_hi, True


def judge_semantics(
    artifact: Artifact,
    *,
    decider: DecisionBackend,
    judge_model: BaseChatModel,
    mode: Mode = "cascade",
    reference: Any = None,
    t_lo: float = T_LO,
    t_hi: float = T_HI,
    usage: JudgeUsage | None = None,
) -> list[SemanticVerdict]:
    """응답 문장의 의미를 JEV_QUESTIONS 순서대로 판정한다.

    mode:
    - 'cascade': Jev 한 번 호출. 거절 또는 t_lo <= p <= t_hi인 질문만 Judge(질문당 1회). 밖이면 passed = p > t_hi.
    - 'jev_only': Judge를 부르지 않는다. 거절·중간대는 passed=None(판정 보류).
    - 'judge_only': decider를 부르지 않고 모든 질문을 Judge가 판정한다.
    Decision API 오류(DecisionError)가 나면 모든 질문을 Judge로 넘기고 jev_error에 오류 문구를 남긴다
    (jev_only에서는 passed=None).
    Judge 출력을 해석하지 못하면 passed=None, reason='판정 파싱 실패'다. usage를 주면 호출 수가 누적된다.
    """
    if mode not in _MODES:
        raise ValueError(f"알 수 없는 mode: {mode!r} (가능: {', '.join(_MODES)})")
    counter = usage if usage is not None else JudgeUsage()
    state = build_state(artifact, reference=reference)

    # 1) Jev 호출(judge_only는 건너뛴다)
    verdicts: dict[str, Verdict] = {}
    jev_error: str | None = None
    if mode != "judge_only":
        counter.jev_calls += 1
        try:
            judgment = decider.judge(state, list(JEV_QUESTIONS))
            verdicts = judgment.verdicts
        except DecisionError as error:
            jev_error = str(error)

    # 2) 질문마다 판정
    results: list[SemanticVerdict] = []
    for question in JEV_QUESTIONS:
        counter.questions += 1
        verdict = verdicts.get(question.name)
        probability = verdict.probability if verdict is not None else None
        confidence = verdict.confidence if verdict is not None else None
        passed, confident = _jev_outcome(verdict, t_lo, t_hi)

        if mode == "jev_only":
            if confident:
                reason = f"Jev 확률 {probability:.2f}"
            elif jev_error:
                reason = f"Jev 오류로 판정 보류: {jev_error}"
            else:
                reason = "Jev 거절" if probability is None else f"Jev 확률 {probability:.2f}가 불확실 구간 안이라 판정 보류"
            results.append(SemanticVerdict(question.name, passed, "jev", probability, confidence, reason, False, jev_error))
            continue

        if mode == "cascade" and confident:
            results.append(SemanticVerdict(question.name, passed, "jev", probability, confidence, f"Jev 확률 {probability:.2f}", False, jev_error))
            continue

        # 3) Judge로 넘긴다(judge_only 전부, cascade의 불확실·거절·오류)
        counter.judge_calls += 1
        if mode == "cascade":
            counter.escalated += 1
        judge_passed, judge_reason = _ask_judge(judge_model, state, question)
        results.append(SemanticVerdict(question.name, judge_passed, "judge", probability, confidence, judge_reason, mode == "cascade", jev_error))
    return results


# ---------------------------------------------------------------------------
# DeepEval 연결
# ---------------------------------------------------------------------------

def _schema_prompt(prompt: str, schema: Any) -> str:
    """schema가 있을 때 JSON 스키마를 지시하는 프롬프트를 붙인다."""
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    return (
        f"{prompt}\n\n위 요청의 결과를 아래 JSON 스키마에 맞는 JSON 하나로만 출력하라. "
        f"코드펜스와 설명 없이 JSON 본문만 출력한다.\n\n{schema_json}"
    )


def _parse_into(text: str, schema: Any) -> Any:
    """모델이 낸 텍스트에서 JSON 본문을 잘라 schema로 검증한다. 실패하면 ValueError."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return schema.model_validate_json(cleaned)
    except ValueError:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"JSON을 찾지 못했습니다: {cleaned[:200]}")
    return schema.model_validate(json.loads(match.group(0)))


class DeepEvalAnthropic(DeepEvalBaseLLM):
    """LangChain 채팅 모델(claude-sonnet-5-5 effort xhigh)을 DeepEval 지표의 평가 모델로 쓰게 한다.

    커스텀 모델이라 DeepEval은 generate(prompt, schema=...)를 부르고 schema 인스턴스를 그대로 기대한다.
    schema가 있으면 JSON 텍스트를 받아 schema로 검증해 돌려주고, schema가 없으면 문자열을 돌려준다.
    """

    def __init__(self, chat_model: BaseChatModel, model_name: str = "claude-sonnet-5-5") -> None:
        # load_model()이 부모 __init__ 안에서 불리므로 그 전에 채워 둔다.
        self._chat_model = chat_model
        self.model_name = model_name
        super().__init__(model_name)

    def load_model(self) -> BaseChatModel:
        """감싼 LangChain 채팅 모델을 돌려준다."""
        return self._chat_model

    def generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> Any:
        """prompt를 보내고 문자열(schema 없음) 또는 schema 인스턴스를 돌려준다."""
        if schema is None:
            return _message_text(self.model.invoke(prompt).content)
        reply = self.model.invoke(_schema_prompt(prompt, schema))
        return _parse_into(_message_text(reply.content), schema)

    async def a_generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> Any:
        """generate의 비동기 판."""
        if schema is None:
            reply = await self.model.ainvoke(prompt)
            return _message_text(reply.content)
        reply = await self.model.ainvoke(_schema_prompt(prompt, schema))
        return _parse_into(_message_text(reply.content), schema)

    def get_model_name(self) -> str:
        """DeepEval 보고서에 남길 모델 이름."""
        return self.model_name


def to_deepeval_case(artifact: Artifact) -> LLMTestCase:
    """Artifact를 DeepEval LLMTestCase로 바꾼다.

    input은 요청 문장, actual_output은 응답 문장(응답이 없으면 빈 문자열),
    tools_called는 서비스가 받은 사건(차단된 호출은 제외)의 도구 이름, 인자, 결과다.
    """
    request = artifact.initial_request or artifact.request
    tools = [ToolCall(name=event.tool, input_parameters=dict(event.args), output=event.result) for event in artifact.events]
    message = artifact.response.message if artifact.response else ""
    return LLMTestCase(input=request.message, actual_output=message, tools_called=tools)


def _trace_dict(artifact: Artifact) -> dict[str, Any]:
    """DeepEval이 기대하는 중첩 span 사전을 만든다(루트 agent 한 개, 자식은 도구 span).

    키는 deepeval/tracing/tracing.py의 create_nested_spans_dict 결과를 따른다:
    name, type, input, output, children. 이 사전은 `LLMTestCase._trace_dict`(비공개 필드)에 넣는다.
    """
    children = [
        {"name": event.tool, "type": "tool", "input": dict(event.args), "output": event.result, "children": []}
        for event in artifact.events
    ]
    return {
        "name": "order-agent",
        "type": "agent",
        "input": artifact.request.message,
        "output": artifact.response.message if artifact.response else "",
        "children": children,
    }


def run_agent_metrics(artifact: Artifact, metrics: list[BaseMetric]) -> list[dict[str, Any]]:
    """지표마다 measure를 돌려 결과 사전 목록을 돌려준다.

    성공: {'metric', 'status': 'measured', 'score', 'success', 'reason'}.
    requires_trace가 True인 지표에는 비공개 필드 `_trace_dict`를 채워 넣는다.
    그 방식으로 돌지 못하면 예외 대신 {'metric', 'status': 'unsupported', 'reason': 'DeepEval tracing 필요'}를 돌려준다.
    trace가 필요 없는 지표가 실패하면 {'status': 'error', 'reason': 오류 종류와 문구}다(조용히 통과시키지 않는다).
    """
    results: list[dict[str, Any]] = []
    for metric in metrics:
        name = type(metric).__name__
        case = to_deepeval_case(artifact)
        needs_trace = bool(getattr(metric, "requires_trace", False))
        if needs_trace:
            case._trace_dict = _trace_dict(artifact)
        try:
            score = metric.measure(case, _show_indicator=False)
        except Exception as error:  # noqa: BLE001 - 지표 하나의 실패가 나머지를 막지 않게 결과 사전으로 보고한다
            if needs_trace:
                results.append({"metric": name, "status": "unsupported", "reason": "DeepEval tracing 필요"})
            else:
                results.append({"metric": name, "status": "error", "reason": f"{type(error).__name__}: {error}"})
            continue
        results.append({
            "metric": name,
            "status": "measured",
            "score": score if score is not None else getattr(metric, "score", None),
            "success": getattr(metric, "success", None),
            "reason": getattr(metric, "reason", None),
        })
    return results
