"""시나리오, 관측 기록, 판정의 경계. 이 모듈은 외부 호출을 하지 않는다."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Request(Contract):
    """사용자 입력. 인증된 고객 ID는 도구 환경에 주입하며 모델이 바꿀 수 없다."""

    message: str = Field(min_length=1)
    order_id: str | None
    request_id: str = Field(min_length=1)


class Expected(Contract):
    """평가자 전용 업무 명세. final_state가 비면 자동 통과시키지 않는다."""

    final_state: dict[str, Any] = Field(min_length=1)
    forbidden_tools: list[str]
    response_kind: Literal["completed", "refused", "clarification", "escalated"]
    max_refund_attempts: int = Field(ge=0, le=2)
    required_milestones: list[Literal["authorized", "refund_verified", "stock_restored", "cancel_verified"]] = Field(default_factory=list)
    reference_answer: str = ""  # 01b에서 정리하고 02에서 검수한 마지막 턴의 기대 답변.
    required_facts: list[str] = Field(default_factory=list)  # 답변의 필수 내용. Judge·사람 검수 전용.


class Metadata(Contract):
    scenario_id: str
    family_id: str
    slice: str
    split: Literal["dev", "holdout"]
    source: str
    policy_version: str
    review_status: Literal["approved", "pending", "rejected"]
    reviewer: str
    review_reason: str
    source_trace_id: str | None = None
    source_artifact_id: str | None = None
    sanitization_record: str | None = None


class Followup(Contract):
    """미리 정한 사용자 후속 입력. 평가 정답은 이 객체에 넣지 않는다."""

    when_response: Literal["clarification"] = "clarification"
    request: Request


class Scenario(Contract):
    input: Request
    fixture_id: str
    expected_output: Expected
    metadata: Metadata
    followups: list[Followup] = Field(default_factory=list)
    max_turns: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def valid_episode(self):
        if len(self.followups) + 1 > self.max_turns:
            raise ValueError("후속 입력 수가 최대 턴을 넘습니다.")
        if any(f.request.request_id != self.input.request_id for f in self.followups):
            raise ValueError("동일 Episode의 요청 ID는 유지해야 합니다.")
        return self


class Response(Contract):
    """에이전트의 보고. 실제 업무 상태를 검증하는 근거로 대신 사용하지 않는다."""

    kind: Literal["completed", "refused", "clarification", "escalated"]
    message: str = Field(min_length=1)
    order_id: str | None
    refund_cents: int | None = Field(default=None, ge=0)


class Event(Contract):
    event_id: str
    step: int
    tool: str
    args: dict[str, Any]
    result: dict[str, Any]
    start_ns: int
    end_ns: int
    observation_id: str | None = None
    parent_observation_id: str | None = None
    call_id: str | None = None
    turn_index: int = 1


class TurnRecord(Contract):
    turn_index: int
    request: Request
    response: Response | None
    event_ids: list[str]
    initial_state: dict[str, Any]
    final_state: dict[str, Any]
    trace_id: str | None = None


class GateDecision(Contract):
    """하네스 게이트의 결정. 도구 호출이 업무 환경에 닿기 전에 내린다.

    action은 allow(통과), block(차단), ask(사람에게 확인) 중 하나다.
    rule_id는 결정을 내린 규칙의 ID이고, 규칙과 무관한 allow는 None이다.
    """

    action: Literal["allow", "block", "ask"]
    rule_id: str | None = None
    reason: str = ""


class GateEvent(Contract):
    """게이트가 도구 호출 하나에 내린 결정 기록.

    차단된 호출은 서비스에 닿지 않으므로 서비스 Event가 아니다.
    Event는 서비스가 실제로 받은 호출만 담고, 차단·확인 요청은 이 기록에만 남는다.
    이 기록은 에이전트 계층이 채우며 업무 환경은 채우지 않는다.
    """

    event_id: str
    turn_index: int
    tool: str
    args: dict[str, Any]
    decision: GateDecision


class Artifact(Contract):
    """하네스가 수집한 근거. 상태는 도구 환경에서 읽고, 답변과 독립 보관한다."""

    artifact_id: str
    scenario_id: str
    release: str
    trial: int
    request: Request
    execution_status: Literal["completed", "execution_error", "infra_error"]
    initial_state: dict[str, Any]
    final_state: dict[str, Any] | None
    events: list[Event]
    response: Response | None
    error_type: str | None = None
    elapsed_seconds: float
    model_calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    initial_request: Request | None = None
    turns: list[TurnRecord] = Field(default_factory=list)
    model_events: list[dict[str, Any]] = Field(default_factory=list)
    episode_id: str | None = None
    gate_events: list[GateEvent] = Field(default_factory=list)  # 게이트 결정 기록. 없으면 빈 목록.
    # 고객의 답을 기다리며 멈춘 Episode인가. 실행기가 최대 턴에서 멈췄는데, 마지막 응답 유형과
    # when_response가 같은 후속 입력이 아직 쓰이지 않고 남아 있을 때만 True다.
    # 추가 질문이 마지막 답이고 남은 후속 입력이 없으면 끝난 Episode이므로 False다.
    # 기본값 False 덕분에 이 필드가 생기기 전의 Artifact와 요약도 그대로 읽힌다.
    awaiting_user: bool = False


class Verdict(Contract):
    name: str
    status: Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "EVALUATOR_ERROR"]
    passed: bool | None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_status(self):
        required = {"PASS": True, "FAIL": False}.get(self.status)
        if self.passed is not required:
            raise ValueError("판정 상태와 passed가 일치하지 않습니다.")
        return self


def verdict(name: str, passed: bool, reason: str, events: list[Event] = ()) -> Verdict:
    return Verdict(name=name, status="PASS" if passed else "FAIL", passed=passed,
                   reason=reason, evidence_ids=[event.event_id for event in events])
