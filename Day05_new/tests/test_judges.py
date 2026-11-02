"""Code -> Jev -> Judge 연쇄와 DeepEval 연결 시험. 모델·네트워크 호출은 모두 가짜다."""
from typing import Any

import pytest
from deepeval.metrics import StepEfficiencyMetric, ToolPermissionMetric
from deepeval.models.base_model import DeepEvalBaseLLM
from eval_lab.contracts import Artifact, Event, Expected, Request, Response
from eval_lab.decisions import DecisionError
from eval_lab.judges import (
    JEV_QUESTIONS,
    T_HI,
    T_LO,
    DeepEvalAnthropic,
    JudgeUsage,
    build_state,
    judge_semantics,
    run_agent_metrics,
    to_deepeval_case,
)
from langchain_core.messages import AIMessage
from pydantic import BaseModel
from tests.fakes import FakeChatModel, FakeDecider

QUESTION_NAMES = ["message_consistent", "next_step_clear", "clarify_when_needed"]
PASS_JSON = '{"verdict": "PASS", "reason": "기록과 일치합니다."}'
FAIL_JSON = '{"verdict": "FAIL", "reason": "기록에 없는 환불을 말했습니다."}'


def make_artifact(*, with_refund: bool = False, message: str = "취소 접수가 끝났습니다.") -> Artifact:
    """합성 Artifact. 서비스 사건은 조회(+선택적으로 환불)다."""
    request = Request(message="주문 O-1 취소해 주세요", order_id="O-1", request_id="r1")
    events = [Event(event_id="e1", step=1, tool="get_order", args={"order_id": "O-1"},
                    result={"status": "ok", "order": {"status": "paid"}}, start_ns=1, end_ns=2)]
    if with_refund:
        events.append(Event(event_id="e2", step=2, tool="refund_payment", args={"order_id": "O-1", "amount": 18900},
                            result={"status": "ok"}, start_ns=3, end_ns=4))
    state = {"subject_id": "O-1", "orders": {"O-1": {"status": "paid", "sku": "S1"}},
             "payments": {"O-1": {"refunded_cents": 0}}, "inventory": {"S1": 5}, "tickets": []}
    return Artifact(
        artifact_id="a1", scenario_id="s1", release="t", trial=1, request=request, execution_status="completed",
        initial_state=state, final_state=state, events=events,
        response=Response(kind="escalated", message=message, order_id="O-1", refund_cents=None),
        elapsed_seconds=0.1,
    )


def judge_that_says(*texts: str) -> FakeChatModel:
    return FakeChatModel.scripted([AIMessage(content=text) for text in texts])


class CountingJudge(FakeChatModel):
    """invoke 횟수를 센다."""

    calls: int = 0

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        return super().invoke(*args, **kwargs)


def counting_judge(*texts: str) -> CountingJudge:
    return CountingJudge(messages=iter([AIMessage(content=t) for t in texts]))


# ---------------------------------------------------------------- 연쇄

def test_jev_questions_are_three_noul():
    assert [q.name for q in JEV_QUESTIONS] == QUESTION_NAMES
    assert all(q.true and q.false and q.instructions for q in JEV_QUESTIONS)
    assert (T_LO, T_HI) == (0.2, 0.8)


def test_cascade_keeps_confident_and_escalates_mid_band_and_refused():
    decider = FakeDecider({"message_consistent": 0.95, "next_step_clear": 0.5})  # clarify는 refused
    judge = counting_judge(PASS_JSON, FAIL_JSON)
    usage = JudgeUsage()
    results = judge_semantics(make_artifact(), decider=decider, judge_model=judge, usage=usage)
    by_name = {r.name: r for r in results}

    assert len(decider.calls) == 1  # 질문 세 개를 한 번에
    assert judge.calls == 2
    assert by_name["message_consistent"].stage == "jev" and by_name["message_consistent"].passed is True
    assert by_name["message_consistent"].escalated is False
    assert by_name["next_step_clear"].stage == "judge" and by_name["next_step_clear"].passed is True
    assert by_name["next_step_clear"].probability == 0.5 and by_name["next_step_clear"].escalated
    assert by_name["clarify_when_needed"].stage == "judge" and by_name["clarify_when_needed"].passed is False
    assert (usage.jev_calls, usage.judge_calls, usage.escalated) == (1, 2, 2)
    assert usage.escalation_rate == pytest.approx(2 / 3)


def test_cascade_low_probability_fails_without_judge():
    decider = FakeDecider({name: 0.05 for name in QUESTION_NAMES})
    judge = counting_judge()
    results = judge_semantics(make_artifact(), decider=decider, judge_model=judge)
    assert [r.passed for r in results] == [False, False, False]
    assert judge.calls == 0


def test_cascade_band_edges_escalate():
    decider = FakeDecider({"message_consistent": T_LO, "next_step_clear": T_HI, "clarify_when_needed": 0.81})
    judge = counting_judge(PASS_JSON, PASS_JSON)
    results = judge_semantics(make_artifact(), decider=decider, judge_model=judge)
    assert [r.stage for r in results] == ["judge", "judge", "jev"]
    assert judge.calls == 2


def test_jev_only_never_calls_judge():
    decider = FakeDecider({"message_consistent": 0.9, "next_step_clear": 0.5})
    judge = counting_judge()
    results = judge_semantics(make_artifact(), decider=decider, judge_model=judge, mode="jev_only")
    assert judge.calls == 0
    assert [r.passed for r in results] == [True, None, None]
    assert all(r.stage == "jev" and not r.escalated for r in results)


def test_judge_only_never_calls_decider():
    decider = FakeDecider({name: 0.9 for name in QUESTION_NAMES})
    judge = counting_judge(PASS_JSON, FAIL_JSON, PASS_JSON)
    usage = JudgeUsage()
    results = judge_semantics(make_artifact(), decider=decider, judge_model=judge, mode="judge_only", usage=usage)
    assert decider.calls == []
    assert [r.passed for r in results] == [True, False, True]
    assert all(r.stage == "judge" for r in results)
    assert (usage.jev_calls, usage.judge_calls, usage.escalated) == (0, 3, 0)


def test_unparsable_judge_output_is_none_never_pass():
    decider = FakeDecider({})  # 전부 refused
    judge = judge_that_says("잘 모르겠습니다", '{"verdict": "MAYBE"}', "{깨진 json")
    results = judge_semantics(make_artifact(), decider=decider, judge_model=judge)
    assert [r.passed for r in results] == [None, None, None]
    assert all(r.reason == "판정 파싱 실패" for r in results)


def test_judge_output_inside_code_fence_and_list_content_parses():
    decider = FakeDecider({})
    fenced = "```json\n" + PASS_JSON + "\n```"
    blocks = [AIMessage(content=fenced), AIMessage(content=[{"type": "text", "text": FAIL_JSON}]), AIMessage(content=PASS_JSON)]
    results = judge_semantics(make_artifact(), decider=decider, judge_model=FakeChatModel.scripted(blocks))
    assert [r.passed for r in results] == [True, False, True]


def test_decision_error_escalates_everything_and_records_kind():
    decider = FakeDecider(error=DecisionError("typesafe: HTTP 500"))
    judge = counting_judge(PASS_JSON, PASS_JSON, PASS_JSON)
    results = judge_semantics(make_artifact(), decider=decider, judge_model=judge)
    assert judge.calls == 3
    assert all(r.stage == "judge" and r.escalated and r.jev_error == "typesafe: HTTP 500" for r in results)


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        judge_semantics(make_artifact(), decider=FakeDecider(), judge_model=judge_that_says(), mode="vote")  # type: ignore[arg-type]


# ---------------------------------------------------------------- 상태 문장

def test_build_state_without_reference_has_no_reference_text():
    state = build_state(make_artifact(with_refund=True))
    assert "주문 O-1 취소해 주세요" in state
    assert "refund_payment" in state and "e2" in state
    assert "kind: escalated" in state
    assert "기대 답변" not in state and "필수 내용" not in state


def test_build_state_with_reference_appends_frozen_answer():
    expected = Expected(final_state={"order_status": "paid"}, forbidden_tools=[], response_kind="escalated",
                        max_refund_attempts=0, reference_answer="담당자가 확인합니다.", required_facts=["담당자"])
    state = build_state(make_artifact(), reference=expected)
    assert "기대 답변: 담당자가 확인합니다." in state
    assert "필수 내용: 담당자" in state


# ---------------------------------------------------------------- DeepEval

def test_to_deepeval_case_maps_events_to_tool_calls():
    case = to_deepeval_case(make_artifact(with_refund=True))
    assert case.input == "주문 O-1 취소해 주세요"
    assert case.actual_output == "취소 접수가 끝났습니다."
    assert [t.name for t in case.tools_called] == ["get_order", "refund_payment"]
    assert case.tools_called[1].input_parameters == {"order_id": "O-1", "amount": 18900}


def test_tool_permission_fails_deterministically_on_refund_call():
    metric = ToolPermissionMetric(denied_tools=["refund_payment"])
    (bad,) = run_agent_metrics(make_artifact(with_refund=True), [metric])
    assert bad["status"] == "measured" and bad["score"] == 0.5 and bad["success"] is False
    (good,) = run_agent_metrics(make_artifact(with_refund=False), [ToolPermissionMetric(denied_tools=["refund_payment"])])
    assert good["score"] == 1.0 and good["success"] is True


class ScriptedEvalLLM(DeepEvalBaseLLM):
    """schema에 맞는 고정 인스턴스를 돌려주는 가짜 평가 모델."""

    def __init__(self) -> None:
        super().__init__("fake-eval")

    def load_model(self) -> str:
        return "fake"

    def generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> Any:
        if schema is None:
            return "{}"
        fields = schema.model_fields
        if "task" in fields:
            return schema(task="주문 O-1 취소")
        return schema(score=0.8, reason="불필요한 호출이 없습니다.")

    async def a_generate(self, prompt: str, schema: Any = None, **kwargs: Any) -> Any:
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return "fake-eval"


def test_trace_dict_probe_step_efficiency_scores_or_reports_unsupported():
    metric = StepEfficiencyMetric(model=ScriptedEvalLLM(), async_mode=False)
    assert metric.requires_trace is True
    (result,) = run_agent_metrics(make_artifact(with_refund=True), [metric])
    assert result["metric"] == "StepEfficiencyMetric"
    if result["status"] == "measured":
        assert result["score"] == pytest.approx(0.8)
    else:
        assert result == {"metric": "StepEfficiencyMetric", "status": "unsupported", "reason": "DeepEval tracing 필요"}


def test_trace_dict_is_set_for_trace_metrics_only():
    seen: list[Any] = []

    class Probe(ToolPermissionMetric):
        requires_trace = True

        def measure(self, test_case, *args, **kwargs):
            seen.append(test_case._trace_dict)
            return super().measure(test_case, *args, **kwargs)

    run_agent_metrics(make_artifact(with_refund=True), [Probe(denied_tools=["x"])])
    trace = seen[0]
    assert trace["type"] == "agent" and [c["name"] for c in trace["children"]] == ["get_order", "refund_payment"]
    assert trace["children"][0]["type"] == "tool"


def test_deepeval_anthropic_parses_schema_and_text():
    class Verdict(BaseModel):
        score: float
        reason: str

    model = DeepEvalAnthropic(FakeChatModel.scripted([
        AIMessage(content='```json\n{"score": 0.7, "reason": "좋음"}\n```'),
        AIMessage(content="그냥 문장"),
    ]), model_name="claude-sonnet-5-5")
    parsed = model.generate("평가해", schema=Verdict)
    assert parsed == Verdict(score=0.7, reason="좋음")
    assert model.generate("말해") == "그냥 문장"
    assert model.get_model_name() == "claude-sonnet-5-5"


def test_deepeval_anthropic_async_generate():
    import asyncio

    class Verdict(BaseModel):
        score: float

    model = DeepEvalAnthropic(FakeChatModel.scripted([AIMessage(content='{"score": 1}')]))
    assert asyncio.run(model.a_generate("x", schema=Verdict)) == Verdict(score=1.0)
