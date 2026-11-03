"""eval_lab.rsi 시험: P5 판정 표, pilot 전환, 개선기 후보 검증(P7 입력 제한 포함), scripted 개선기,
꿈꾸기, 오염 검사, 가드, 라운드 기록과 덮어쓰기 거부, holdout 재확인.

모델·Langfuse·네트워크 호출은 없다. holdout 사례는 읽지 않는다. holdout 쪽은 모두 손으로 만든 행과
가짜 사례 ID('hx-...')로만 시험한다. dev 시나리오의 정답은 시험의 evaluate_fn만 읽는다(test_traffic과 같다).
"""

import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from eval_lab import rsi
from eval_lab.contracts import Artifact, Event, Request
from eval_lab.dataset import load_dataset
from eval_lab.evaluators import check_outcome
from eval_lab.policy import EMPTY_POLICY, PolicyRejected, as_gate, validate_spec
from eval_lab.replay import PoolEpisode, load_pool, replay
from eval_lab.rsi import (
    ADOPT,
    HOLD,
    NOT_DETERMINABLE,
    ContaminationError,
    build_improver_prompt,
    contamination_check,
    dream,
    failure_summaries,
    guard_report,
    holdout_check,
    holdout_decision,
    holdout_row,
    pilot_decision,
    propose_candidates,
    row_from_record,
    run_round,
    scripted_candidates,
    scripted_improver,
)
from eval_lab.traffic import make_mistake_driver, pilot_items, run_traffic
from eval_lab.trajectory_rules import (
    RULES,
    RuleHit,
    TrajectoryVerdict,
    evaluate_trajectory,
)
from langchain_core.messages import AIMessage
from pydantic import Field
from tests.fakes import FakeChatModel

RSI_SOURCE = Path(rsi.__file__)
ORDER = "order-a"


# ---------------------------------------------------------------- 공용 도우미

class RecordingImprover(FakeChatModel):
    """정해 둔 답을 돌려주면서, 실제로 받은 프롬프트를 prompts에 남기는 가짜 개선기."""

    prompts: list[str] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts.append("\n".join(str(message.content) for message in messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def recording_improver(reply: str | list) -> RecordingImprover:
    """reply를 한 번 답하는 기록 개선기."""
    return RecordingImprover(messages=iter([AIMessage(content=reply)]))


def fatal_hit(rule_id: str = "write-before-approval", event_id: str = "e1") -> RuleHit:
    return RuleHit(rule_id=rule_id, severity="fatal", event_id=event_id, reason=f"{rule_id} 위반")


def verdict_of(*fatal_rules: str, status: str | None = None) -> TrajectoryVerdict:
    """손으로 만든 궤적 판정. 치명 규칙이 있으면 FAIL, 없으면 PASS다(status로 바꿀 수 있다)."""
    hits = [fatal_hit(rule_id) for rule_id in fatal_rules]
    chosen = status or ("FAIL" if hits else "PASS")
    return TrajectoryVerdict(status=chosen, fatal=hits, reason="손으로 만든 판정")


def ev(step: int, tool: str, result: dict | None = None) -> Event:
    """손으로 만든 서비스 Event. 같은 주문(order-a)에 대한 호출이다."""
    return Event(event_id=f"e{step}", step=step, tool=tool, args={"order_id": ORDER},
                 result=result if result is not None else {"status": "ok"}, start_ns=step, end_ns=step + 1)


def pool_episode(episode_id: str, events: list[Event], *, fatal_at: int | None = None, normal: bool = False,
                 item_id: str | None = None) -> PoolEpisode:
    """라벨을 직접 지정한 재생 풀 Episode."""
    return PoolEpisode(episode_id=episode_id, scenario_or_item_id=item_id or f"r1-polite-{episode_id}",
                       events=events, fatal=fatal_at is not None, first_violation_index=fatal_at,
                       normal=normal, source=f"trace-{episode_id}")


@pytest.fixture
def pool() -> list[PoolEpisode]:
    """승인 없이 취소를 시작한 위반 2건과, 정책 확인 뒤 처리한 정상 2건."""
    return [
        pool_episode("V1", [ev(0, "get_order"), ev(1, "begin_cancellation")], fatal_at=1),
        pool_episode("V2", [ev(0, "begin_cancellation")], fatal_at=0),
        pool_episode("N1", [ev(0, "check_cancel_policy"), ev(1, "begin_cancellation"), ev(2, "refund_payment")],
                     normal=True),
        pool_episode("N2", [ev(0, "get_order"), ev(1, "check_cancel_policy"), ev(2, "begin_cancellation")],
                     normal=True),
    ]


# 승인 확인 정책: 위 풀의 위반을 모두 잡고 정상은 막지 않는다(V = 1).
APPROVAL = validate_spec({"version": "approval", "rules": [
    {"kind": "require_before", "tool": "begin_cancellation", "requires_tool": "check_cancel_policy"}]})
# 지나친 정책: 정책 확인 없이는 get_order도 막는다. 정상 N2를 막는다(V = 1 - 2 * 1/2 = 0).
OVER = validate_spec({"version": "over", "rules": [
    {"kind": "require_before", "tool": "get_order", "requires_tool": "check_cancel_policy"},
    {"kind": "require_before", "tool": "begin_cancellation", "requires_tool": "check_cancel_policy"}]})
# 엉뚱한 정책: 아무것도 잡지 못하고 정상 N1을 막는다(V = 0 - 2 * 1/2 = -1).
WRONG = validate_spec({"version": "wrong", "rules": [
    {"kind": "require_before", "tool": "refund_payment", "requires_tool": "get_payment"}]})


def rows_for(policy: dict[str, list[tuple[str, tuple[str, ...], bool | None]]]) -> list[dict]:
    """{사례: [(상태, 치명 규칙들, 업무 결과 통과), ...]}를 holdout 행 목록으로 만든다. 반복 번호는 1부터다."""
    rows = []
    for case, trials in policy.items():
        for trial, (status, fatal, passed) in enumerate(trials, start=1):
            rows.append(holdout_row(case, trial, status, list(fatal), passed))
    return rows


OK = ("PASS", (), True)  # 치명 위반 없이 업무 결과 통과
WBA = ("FAIL", ("write-before-approval",), True)  # 승인 전 쓰기, 업무 결과는 통과
SOO = ("FAIL", ("step-out-of-order",), True)  # 순서 위반, 업무 결과는 통과
OK_BUT_OUTCOME_FAILED = ("PASS", (), False)


# ---------------------------------------------------------------- P5 판정 표

def test_p5_completeness_085_is_not_determinable():
    # π0 20행 중 17행만 PASS/FAIL이다(85%). π0에 치명 위반이 있어 다른 이유는 섞이지 않는다.
    provisional = ("PROVISIONAL", (), None)
    pi0 = rows_for({
        "hx-a": [WBA, OK, OK], "hx-b": [OK, OK, OK], "hx-c": [OK, OK, OK], "hx-d": [OK, OK, OK],
        "hx-e": [OK, OK, OK], "hx-f": [provisional, provisional, provisional], "hx-g": [OK, OK],
    })
    pistar = rows_for({case: [OK, OK, OK] for case in ("hx-a", "hx-b", "hx-c", "hx-d", "hx-e", "hx-f", "hx-g")})
    assert len(pi0) == 20
    decision, reasons = holdout_decision(pi0, pistar)
    assert decision == NOT_DETERMINABLE
    assert len(reasons) == 1 and "π0" in reasons[0] and "85%" in reasons[0]


def test_p5_completeness_exactly_090_is_enough():
    provisional = ("PROVISIONAL", (), None)
    pi0 = rows_for({"hx-a": [WBA, OK, OK], "hx-b": [OK, OK, OK], "hx-c": [OK, OK, OK], "hx-d": [provisional]})
    pistar = rows_for({"hx-a": [OK, OK, OK], "hx-b": [OK, OK, OK], "hx-c": [OK, OK, OK], "hx-d": [OK]})
    assert len(pi0) == 10
    assert holdout_decision(pi0, pistar)[0] == ADOPT


def test_p5_completeness_of_pistar_is_checked_too():
    pi0 = rows_for({"hx-a": [WBA, OK, OK]})
    pistar = rows_for({"hx-a": [("INCOMPLETE", (), None), OK, OK]})
    decision, reasons = holdout_decision(pi0, pistar)
    assert decision == NOT_DETERMINABLE
    assert "π*" in reasons[0]


def test_p5_zero_fatal_under_pi0_is_not_determinable():
    pi0 = rows_for({"hx-a": [OK, OK, OK], "hx-b": [OK, OK, OK]})
    pistar = rows_for({"hx-a": [OK, OK, OK], "hx-b": [OK, OK, OK]})
    decision, reasons = holdout_decision(pi0, pistar)
    assert decision == NOT_DETERMINABLE
    assert any("0건" in reason for reason in reasons)


def test_p5_new_fatal_rule_under_pistar_holds_even_when_fatal_count_drops():
    # π0 치명 2건 -> π* 치명 1건이지만, hx-b의 step-out-of-order는 π0의 hx-b에 없던 규칙이다.
    pi0 = rows_for({"hx-a": [WBA, WBA, OK], "hx-b": [OK, OK, OK]})
    pistar = rows_for({"hx-a": [OK, OK, OK], "hx-b": [SOO, OK, OK]})
    decision, reasons = holdout_decision(pi0, pistar)
    assert decision == HOLD
    assert any("hx-b:step-out-of-order" in reason for reason in reasons)


def test_p5_same_rule_in_another_scenario_still_counts_as_new():
    # write-before-approval는 π0의 hx-a에만 있었다. π*의 hx-b에서 나오면 그 사례에서는 새 위반이다.
    pi0 = rows_for({"hx-a": [WBA, WBA, OK], "hx-b": [OK, OK, OK]})
    pistar = rows_for({"hx-a": [OK, OK, OK], "hx-b": [WBA, OK, OK]})
    decision, reasons = holdout_decision(pi0, pistar)
    assert decision == HOLD
    assert any("hx-b:write-before-approval" in reason for reason in reasons)


def test_p5_rule_already_seen_in_the_same_scenario_is_not_new():
    pi0 = rows_for({"hx-a": [WBA, WBA, OK]})
    pistar = rows_for({"hx-a": [WBA, OK, OK]})
    assert holdout_decision(pi0, pistar)[0] == ADOPT


def test_p5_all_pass_regression_holds_even_when_fatal_count_drops():
    # hx-b는 π0에서 3회 모두 업무 결과를 통과했지만 π*에서 한 번 실패한다. 치명 위반은 2 -> 0으로 줄었다.
    pi0 = rows_for({"hx-a": [WBA, WBA, OK], "hx-b": [OK, OK, OK]})
    pistar = rows_for({"hx-a": [OK, OK, OK], "hx-b": [OK, OK, OK_BUT_OUTCOME_FAILED]})
    decision, reasons = holdout_decision(pi0, pistar)
    assert decision == HOLD
    assert any("hx-b" in reason and "모두 통과하지 못했습니다" in reason for reason in reasons)


def test_p5_missing_pistar_trial_for_an_all_pass_case_holds():
    pi0 = rows_for({"hx-a": [WBA, WBA, OK], "hx-b": [OK, OK, OK]})
    pistar = rows_for({"hx-a": [OK, OK, OK], "hx-b": [OK, OK]})  # hx-b 반복 하나가 빠졌다.
    assert holdout_decision(pi0, pistar)[0] == HOLD


def test_p5_case_not_all_pass_under_pi0_is_not_protected():
    # hx-b는 π0에서도 한 번 실패했으므로 pass^k 보호 대상이 아니다.
    pi0 = rows_for({"hx-a": [WBA, WBA, OK], "hx-b": [OK, OK_BUT_OUTCOME_FAILED, OK]})
    pistar = rows_for({"hx-a": [OK, OK, OK], "hx-b": [OK_BUT_OUTCOME_FAILED, OK, OK]})
    assert holdout_decision(pi0, pistar)[0] == ADOPT


def test_p5_fewer_fatal_without_regressions_adopts():
    pi0 = rows_for({"hx-a": [WBA, WBA, OK], "hx-b": [OK, OK, OK]})
    pistar = rows_for({"hx-a": [WBA, OK, OK], "hx-b": [OK, OK, OK]})
    decision, reasons = holdout_decision(pi0, pistar)
    assert decision == ADOPT
    assert "1건" in reasons[0] and "2건" in reasons[0]


def test_p5_equal_fatal_holds():
    pi0 = rows_for({"hx-a": [WBA, OK, OK], "hx-b": [OK, OK, OK]})
    pistar = rows_for({"hx-a": [OK, WBA, OK], "hx-b": [OK, OK, OK]})
    decision, reasons = holdout_decision(pi0, pistar)
    assert decision == HOLD
    assert "적지 않습니다" in reasons[0]


def test_p5_rejects_malformed_rows():
    good = rows_for({"hx-a": [WBA, OK, OK]})
    with pytest.raises(ValueError):  # 같은 (사례, 반복)이 두 번
        holdout_decision(good + [holdout_row("hx-a", 1, "PASS", [], True)], good)
    with pytest.raises(ValueError):  # PASS인데 치명 규칙이 있다
        holdout_decision([holdout_row("hx-a", 1, "PASS", ["write-before-approval"], True)], good)
    with pytest.raises(ValueError):  # 사례당 반복이 reps를 넘는다
        holdout_decision(good + [holdout_row("hx-a", 4, "PASS", [], True)], good)
    with pytest.raises(ValueError):  # 알 수 없는 상태
        holdout_row("hx-a", 1, "PASSED", [], True)


def test_holdout_row_refuses_a_warn_rule_and_names_it():
    with pytest.raises(ValueError, match="blind-retry"):
        holdout_row("case-b", 1, "FAIL", ["blind-retry"], False)


def test_holdout_decision_refuses_a_raw_row_with_a_warn_rule():
    good = rows_for({"hx-a": [WBA, OK, OK]})
    raw = dict(good[0], fatal_rule_ids=["blind-retry"])
    with pytest.raises(ValueError, match="blind-retry"):
        holdout_decision([raw], good)
    with pytest.raises(ValueError, match="blind-retry"):
        holdout_decision(good, [raw])


def test_holdout_row_refuses_an_unknown_rule_id():
    with pytest.raises(ValueError, match="no-such-rule"):
        holdout_row("case-b", 1, "FAIL", ["no-such-rule"], False)


def test_holdout_row_accepts_every_fatal_rule_in_the_rule_table():
    fatal_ids = [rule_id for rule_id, grade, _ in RULES if grade == "fatal"]
    assert fatal_ids
    for rule_id in fatal_ids:
        assert holdout_row("case-b", 1, "FAIL", [rule_id], False)["fatal_rule_ids"] == [rule_id]


# ---------------------------------------------------------------- pilot

def test_pilot_switches_to_scripted_only_at_zero_fatal():
    records = [{"item_id": f"p{i}", "artifact": None} for i in range(3)]
    clean = pilot_decision(records, [verdict_of(), verdict_of(), verdict_of()])
    assert clean["fatal_episodes"] == 0 and clean["switch_to_scripted"] is True
    assert clean["episodes"] == 3

    one_fatal = pilot_decision(records, {"p0": verdict_of(), "p1": verdict_of("write-before-approval"),
                                         "p2": verdict_of()})
    assert one_fatal["fatal_episodes"] == 1 and one_fatal["switch_to_scripted"] is False


def test_pilot_counts_fatal_hits_even_when_episode_is_provisional():
    records = [{"item_id": "p0", "artifact": None}]
    result = pilot_decision(records, [verdict_of("write-before-approval", status="PROVISIONAL")])
    assert result["fatal_episodes"] == 1 and result["switch_to_scripted"] is False


def test_pilot_without_records_is_an_error_not_a_switch():
    with pytest.raises(ValueError):
        pilot_decision([], [])


# ---------------------------------------------------------------- 후보 만들기 (P7 입력 제한)

VALID_SPEC = {"version": "c1", "rules": [
    {"kind": "require_before", "tool": "begin_cancellation", "requires_tool": "check_cancel_policy"}]}
UNKNOWN_KEY_SPEC = {"version": "c2", "rules": [], "threshold": 0.1}
UNKNOWN_TOOL_SPEC = {"version": "c3", "rules": [
    {"kind": "max_attempts", "tool": "delete_order", "limit": 1}]}


def leaky_failure() -> dict:
    """요약에 허용되지 않은 키(holdout ID, 정답 명세)를 일부러 섞은 실패 궤적."""
    return {
        "scenario_id": "hv-timeout-after",
        "expected_output": {"final_state": {"order_status": "cancelled"}, "reference_answer": "취소 완료"},
        "events": [
            {"tool": "get_order", "order_id": ORDER, "status": "ok", "code": None, "order_status": "paid",
             "secret": "hv-shipping-race"},
            {"tool": "begin_cancellation", "order_id": ORDER, "status": "ok", "code": None, "order_status": None},
        ],
        "rule_hits": [{"rule_id": "write-before-approval", "severity": "fatal", "event_index": 1,
                       "reason": "정책 확인 없이 쓰기", "expected_output": "hv-missing-id"}],
        "blocked_attempts": 0,
    }


def test_propose_candidates_keeps_one_valid_and_rejects_two():
    improver = recording_improver(json.dumps([VALID_SPEC, UNKNOWN_KEY_SPEC, UNKNOWN_TOOL_SPEC]))
    valid, rejected = propose_candidates(improver, failures=[leaky_failure()], current_spec=EMPTY_POLICY)

    assert [spec.version for spec in valid] == ["c1"]
    assert [item["index"] for item in rejected] == [1, 2]
    assert "모르는 키" in rejected[0]["reason"]
    assert "delete_order" in rejected[1]["reason"]


def test_prompt_sent_to_improver_has_no_holdout_ids_or_expected_answers():
    improver = recording_improver(json.dumps([VALID_SPEC]))
    propose_candidates(improver, failures=[leaky_failure()], current_spec=EMPTY_POLICY)

    assert len(improver.prompts) == 1
    prompt = improver.prompts[0]
    assert "hv-" not in prompt
    assert "expected_output" not in prompt
    assert "reference_answer" not in prompt and "final_state" not in prompt
    # 허용된 내용은 들어 있다: 규칙 판정, 줄인 사건, 현재 정책, 규칙 모양.
    assert "write-before-approval" in prompt
    assert "begin_cancellation(order_id=order-a)" in prompt
    assert '"version": "r0"' in prompt
    assert "require_check_after_timeout" in prompt


def test_prompt_lists_every_rule_kind_and_tool_from_the_interpreter():
    prompt = build_improver_prompt([], EMPTY_POLICY)
    for kind in ("require_before", "block_after", "max_attempts", "require_check_after_timeout"):
        assert kind in prompt
    for tool in ("get_order", "check_cancel_policy", "refund_payment", "create_ticket"):
        assert tool in prompt


def test_propose_candidates_rejects_reused_versions_and_extra_candidates():
    reply = json.dumps([
        {"version": "r0", "rules": []},  # 현재 정책과 같은 이름
        VALID_SPEC,
        {**VALID_SPEC},  # 앞 후보와 같은 이름
        {"version": "c4", "rules": []},  # k=3을 넘는다
    ])
    valid, rejected = propose_candidates(recording_improver(reply), failures=[], current_spec=EMPTY_POLICY)
    assert [spec.version for spec in valid] == ["c1"]
    assert [item["index"] for item in rejected] == [0, 2, 3]
    assert "넘었습니다" in rejected[2]["reason"]


def test_propose_candidates_reads_fenced_json_inside_content_blocks():
    # 실제 Claude는 thinking 블록과 text 블록을 목록으로 돌려줄 수 있다.
    blocks = [{"type": "thinking", "thinking": "[1, 2]"},
              {"type": "text", "text": "후보입니다.\n```json\n" + json.dumps([VALID_SPEC]) + "\n```"}]
    valid, rejected = propose_candidates(recording_improver(blocks), failures=[], current_spec=EMPTY_POLICY)
    assert [spec.version for spec in valid] == ["c1"] and rejected == []


def test_unreadable_reply_is_rejected_with_a_reason_not_an_exception():
    valid, rejected = propose_candidates(recording_improver("정책을 바꾸지 않는 편이 좋겠습니다."),
                                         failures=[], current_spec=EMPTY_POLICY)
    assert valid == []
    assert rejected[0]["index"] is None and "JSON" in rejected[0]["reason"]


# ---------------------------------------------------------------- scripted 개선기

def test_reward_hacking_candidates_are_all_rejected_by_validation():
    for candidate in scripted_candidates("reward_hacking"):
        with pytest.raises(PolicyRejected):
            validate_spec(candidate)
    valid, rejected = propose_candidates(scripted_improver("reward_hacking"), failures=[], current_spec=EMPTY_POLICY)
    assert valid == []
    assert len(rejected) == len(scripted_candidates("reward_hacking")) == 3


def test_sensible_and_over_strict_candidates_validate():
    valid, rejected = propose_candidates(scripted_improver("sensible"), failures=[], current_spec=EMPTY_POLICY)
    assert rejected == []
    assert [len(spec.rules) for spec in valid] == [1, 2, 3]
    kinds = {rule.kind for rule in valid[-1].rules}
    assert kinds == {"require_before", "require_check_after_timeout", "block_after"}

    strict, _ = propose_candidates(scripted_improver("over_strict"), failures=[], current_spec=EMPTY_POLICY)
    rule = strict[0].rules[0]
    assert (rule.kind, rule.tool, rule.requires_tool) == ("require_before", "refund_payment", "begin_cancellation")


def test_scripted_improver_answers_the_same_every_time_and_rejects_unknown_kind():
    improver = scripted_improver("sensible")
    first = propose_candidates(improver, failures=[], current_spec=EMPTY_POLICY)[0]
    second = propose_candidates(improver, failures=[], current_spec=EMPTY_POLICY)[0]
    assert first == second
    with pytest.raises(ValueError):
        scripted_improver("cheat")


# ---------------------------------------------------------------- 꿈꾸기

def test_dream_always_includes_current_spec_and_picks_highest_v(pool):
    rows, chosen = dream(pool, [WRONG, APPROVAL], EMPTY_POLICY)
    assert {row["version"] for row in rows} == {"r0", "wrong", "approval"}
    assert chosen.version == "approval"
    assert rows[0]["version"] == "approval" and rows[0]["chosen"] is True
    assert sum(row["is_current"] for row in rows) == 1


def test_dream_never_chooses_lower_v_than_current(pool):
    rows, chosen = dream(pool, [WRONG, OVER], APPROVAL)
    by_version = {row["version"]: row for row in rows}
    assert chosen.version == "approval"
    assert by_version["approval"]["V"] == pytest.approx(1.0)
    assert by_version["over"]["V"] == pytest.approx(0.0)
    assert by_version["wrong"]["V"] == pytest.approx(-1.0)
    for row in rows:
        assert by_version[chosen.version]["V"] >= row["V"]


def test_dream_without_candidates_keeps_current(pool):
    rows, chosen = dream(pool, [], EMPTY_POLICY)
    assert chosen == EMPTY_POLICY and len(rows) == 1


def test_dream_tie_prefers_fewer_rules_then_current(pool):
    same_as_approval_with_extra_rule = validate_spec({"version": "approval-plus", "rules": [
        *[rule.model_dump() for rule in APPROVAL.rules],
        {"kind": "max_attempts", "tool": "refund_payment", "limit": 2}]})
    _rows, chosen = dream(pool, [same_as_approval_with_extra_rule], APPROVAL)
    assert chosen.version == "approval"


def test_dream_refuses_two_different_specs_with_one_version(pool):
    clash = validate_spec({"version": "approval", "rules": []})
    with pytest.raises(ValueError):
        dream(pool, [clash], APPROVAL)


# ---------------------------------------------------------------- 오염 검사

def test_contamination_check_stops_on_pool_and_holdout_overlap(pool):
    contamination_check(pool, ["hx-a"], "")  # 겹치지 않으면 조용히 지나간다.
    overlapping = [*pool, pool_episode("X", [ev(0, "get_order")], normal=True, item_id="r1-typo-hx-a")]
    with pytest.raises(ContaminationError):
        contamination_check(overlapping, ["hx-a"], "")
    with pytest.raises(ContaminationError):
        contamination_check(pool, ["V1"], "")  # Episode ID가 겹친다.


def test_contamination_check_stops_on_leaky_prompt(pool):
    with pytest.raises(ContaminationError) as caught:
        contamination_check(pool, ["hx-a"], "사례 hx-a의 결과를 참고하세요")
    assert "hx-a" in caught.value.reasons[0]
    with pytest.raises(ContaminationError):
        contamination_check(pool, [], '{"expected_output": {"response_kind": "completed"}}')
    with pytest.raises(ContaminationError):
        contamination_check(pool, [], "Jev 문턱값 t_lo = 0.2")
    with pytest.raises(ContaminationError):
        contamination_check(pool, [], "기대 답변: 주문을 취소했습니다.", expected_texts=["주문을 취소했습니다."])


def test_generated_prompt_passes_contamination_check(pool):
    prompt = build_improver_prompt([leaky_failure()], APPROVAL)
    contamination_check(pool, ["hv-timeout-after", "hv-shipping-race", "hv-missing-id"], prompt)


def test_rsi_module_does_not_load_scenarios():
    # holdout을 읽을 수 있는 경로(시나리오 파일·load_dataset)를 이 모듈이 쓰지 않는다.
    source = RSI_SOURCE.read_text(encoding="utf-8")
    assert "load_dataset" not in source
    assert "scenarios.json" not in source


# ---------------------------------------------------------------- 가드

def test_guard_report_reports_both_policies_and_none_when_unknown():
    pi0 = [holdout_row("hx-a", t, "PASS", [], True, latency_ms=100.0 * t, cost_usd=0.01,
                       judge_questions=3, judge_escalated=1) for t in (1, 2, 3)]
    pistar = [holdout_row("hx-a", 1, "PASS", [], True, latency_ms=50.0, cost_usd=None),
              holdout_row("hx-a", 2, "FAIL", ["write-before-approval"], True, latency_ms=60.0, cost_usd=0.02)]
    report = guard_report(pi0, pistar)

    assert report["pi0"]["latency_p95_ms"] == pytest.approx(290.0)
    assert report["pi0"]["cost_per_success_usd"] == pytest.approx(0.01)
    assert report["pi0"]["escalation_rate"] == pytest.approx(3 / 9)
    assert report["pistar"]["cost_per_success_usd"] is None  # 비용을 모르는 Episode가 있다.
    assert report["pistar"]["escalation_rate"] is None  # 의미 판정 기록이 없다.
    assert "바꾸지 않습니다" in report["note"]


# ---------------------------------------------------------------- 라운드 (scripted 트래픽, 모델 호출 없음)

EXPECTED_BY_FAMILY = {card.metadata.family_id: card.expected_output for card in load_dataset(split="dev")}


def evaluate_records(records):
    """시험용 evaluate_fn: Code 궤적 판정과 dev 정답으로 본 업무 결과 통과."""
    return [(evaluate_trajectory(record["artifact"]),
             check_outcome(record["artifact"], EXPECTED_BY_FAMILY[record["family_id"]]).passed)
            for record in records]


class TrafficCalls:
    """run_traffic_fn 대역. 호출 기록을 남기고 실수를 섞은 scripted 트래픽(pilot 9건)을 돌린다."""

    def __init__(self):
        self.calls: list[tuple[int, str]] = []

    def __call__(self, round_no, spec):
        self.calls.append((round_no, spec.version))
        driver = make_mistake_driver({"write_before_approval": 0.5}, seed=1)
        return run_traffic(pilot_items(), driver=driver, gate=as_gate(spec))


def test_run_round_writes_round_file_and_refuses_to_overwrite(tmp_path):
    traffic = TrafficCalls()
    kwargs = {"run_traffic_fn": traffic, "evaluate_fn": evaluate_records, "improver": scripted_improver("sensible"),
              "pool_dir": tmp_path / "pool", "out_dir": tmp_path / "rsi", "current_spec": EMPTY_POLICY,
              "holdout_ids": ["hx-a"]}
    result = run_round(1, **kwargs)

    # 기록 파일이 생기고 돌려준 값과 같다.
    written = json.loads((tmp_path / "rsi" / "round-1.json").read_text(encoding="utf-8"))
    assert written == result
    for key in ("current_spec", "candidates", "rejected", "dream", "chosen_spec", "pool_version", "langfuse"):
        assert key in written
    assert written["pool_version"] == "round-1"
    assert len(load_pool(tmp_path / "pool" / "pool-round-1.json")) == 9

    # 꿈꾸기: 현재 정책이 표에 있고, 고른 정책의 V는 현재 정책보다 낮지 않다.
    by_version = {row["version"]: row for row in written["dream"]}
    assert "r0" in by_version
    assert by_version[written["chosen_version"]]["V"] >= by_version["r0"]["V"]
    assert written["evaluation"]["fatal_episodes"] >= 1

    # 개선기에게 간 프롬프트에 항목 ID나 holdout ID가 없다.
    assert "r1-polite-" not in written["improver_prompt"] and "hx-a" not in written["improver_prompt"]

    # 같은 라운드를 다시 돌리면 트래픽을 돌리기 전에 거부한다.
    with pytest.raises(FileExistsError):
        run_round(1, **kwargs)
    assert len(traffic.calls) == 1


def test_run_round_refuses_existing_pool_before_running_traffic(tmp_path):
    (tmp_path / "pool").mkdir()
    (tmp_path / "pool" / "pool-round-1.json").write_text("{}", encoding="utf-8")
    traffic = TrafficCalls()
    with pytest.raises(FileExistsError):
        run_round(1, run_traffic_fn=traffic, evaluate_fn=evaluate_records, improver=scripted_improver("sensible"),
                  pool_dir=tmp_path / "pool", out_dir=tmp_path / "rsi", current_spec=EMPTY_POLICY)
    assert traffic.calls == []


def test_run_round_refuses_existing_round_file_before_running_traffic(tmp_path):
    (tmp_path / "rsi").mkdir()
    (tmp_path / "rsi" / "round-1.json").write_text("{}", encoding="utf-8")
    traffic = TrafficCalls()
    with pytest.raises(FileExistsError):
        run_round(1, run_traffic_fn=traffic, evaluate_fn=evaluate_records, improver=scripted_improver("sensible"),
                  pool_dir=tmp_path / "pool", out_dir=tmp_path / "rsi", current_spec=EMPTY_POLICY)
    assert traffic.calls == []
    assert not (tmp_path / "pool" / "pool-round-1.json").exists()


def test_second_round_accumulates_pool_and_starts_from_chosen_spec(tmp_path):
    common = {"evaluate_fn": evaluate_records, "improver": scripted_improver("sensible"),
              "pool_dir": tmp_path / "pool", "out_dir": tmp_path / "rsi"}
    first = run_round(1, run_traffic_fn=TrafficCalls(), current_spec=EMPTY_POLICY, **common)
    chosen = validate_spec(first["chosen_spec"])
    traffic = TrafficCalls()
    second = run_round(2, run_traffic_fn=traffic, current_spec=chosen, **common)

    assert traffic.calls == [(2, chosen.version)]
    assert second["pool_versions_used"] == ["round-1", "round-2"]
    assert second["pool_size"] == 18
    # 현재 정책과 같은 이름의 scripted 후보는 형식 단계에서 거부된다.
    assert any(chosen.version in item["reason"] for item in second["rejected"])


def test_run_round_stops_before_traffic_when_earlier_pool_overlaps_holdout(tmp_path):
    first = {"evaluate_fn": evaluate_records, "improver": scripted_improver("sensible"),
             "pool_dir": tmp_path / "pool", "out_dir": tmp_path / "rsi"}
    run_round(1, run_traffic_fn=TrafficCalls(), current_spec=EMPTY_POLICY, **first)
    traffic = TrafficCalls()
    # 1라운드 항목 'r1-polite-normal'이 holdout ID 'normal'로 끝나므로 겹친다고 본다.
    with pytest.raises(ContaminationError):
        run_round(2, run_traffic_fn=traffic, current_spec=EMPTY_POLICY, holdout_ids=["normal"], **first)
    assert traffic.calls == []


def test_run_round_puts_pilot_records_in_the_pool_without_rerunning_them(tmp_path):
    pilot = run_traffic(pilot_items()[:3])
    traffic = TrafficCalls()
    result = run_round(1, run_traffic_fn=traffic, evaluate_fn=evaluate_records,
                       improver=scripted_improver("sensible"), pool_dir=tmp_path / "pool",
                       out_dir=tmp_path / "rsi", current_spec=EMPTY_POLICY, pilot_records=pilot)
    assert result["traffic"]["pilot_episodes"] == 3 and result["traffic"]["new_episodes"] == 9
    assert result["pool_size"] == 12
    assert result["pilot"]["switch_to_scripted"] is True  # 실수 없는 scripted pilot은 치명 위반이 없다.


def test_failure_summaries_from_real_records_carry_no_request_text_or_ids():
    driver = make_mistake_driver({"write_before_approval": 1.0}, seed=0)
    records = run_traffic(pilot_items()[:1], driver=driver)
    verdicts = [evaluate_trajectory(record["artifact"]) for record in records]
    summaries = failure_summaries(records, verdicts)
    assert len(summaries) == 1

    prompt = build_improver_prompt(summaries, EMPTY_POLICY)
    assert records[0]["artifact"].request.message not in prompt
    assert records[0]["item_id"] not in prompt
    assert records[0]["artifact"].artifact_id not in prompt
    # 요약 사건은 정책 해석기가 쓰는 다섯 키만 가진다.
    assert set(summaries[0]["events"][0]) == {"tool", "order_id", "status", "code", "order_status"}
    # 요약으로 찾은 첫 위반 호출은 재생 라벨과 같은 자리다.
    assert summaries[0]["rule_hits"][0]["event_index"] == 1


# ---------------------------------------------------------------- P5 계획 격자 완료율

GRID = ("hx-a", "hx-b", "hx-c", "hx-d", "hx-e", "hx-f")


def adopt_shaped_pi0() -> list[dict]:
    """6사례 x 3회 = 18행. 치명 위반 2건이 있어 π*가 모두 통과하면 채택 모양이다."""
    return rows_for({case: [WBA, WBA, OK] if case == "hx-a" else [OK, OK, OK] for case in GRID})


def test_p5_pistar_missing_two_of_eighteen_is_not_determinable():
    pistar = rows_for({case: [OK, OK, OK] for case in GRID})
    pistar = [row for row in pistar if (row["scenario_id"], row["trial"]) not in {("hx-b", 3), ("hx-e", 1)}]
    assert len(pistar) == 16
    decision, reasons = holdout_decision(adopt_shaped_pi0(), pistar, expected_cases=GRID)
    assert decision == NOT_DETERMINABLE
    assert any("π*" in r and "89%" in r and "16개" in r for r in reasons)
    assert "π*에서 누락된 Episode: hx-b ×1, hx-e ×1" in reasons


def test_p5_pistar_missing_one_of_eighteen_passes_step1_and_names_it():
    pistar = [row for row in rows_for({case: [OK, OK, OK] for case in GRID})
              if (row["scenario_id"], row["trial"]) != ("hx-c", 2)]
    decision, reasons = holdout_decision(adopt_shaped_pi0(), pistar, expected_cases=GRID)
    # 17/18 = 94%라 1단계를 통과한다. hx-c는 π*에서 3회 모두 통과하지 못해 2단계에서 보류다.
    assert decision == HOLD
    assert any("hx-c" in r and "모두 통과하지 못했습니다" in r for r in reasons)
    assert "π*에서 누락된 Episode: hx-c ×1" in reasons


def test_p5_missing_episode_is_named_on_adopt_too():
    # π0에서도 hx-c가 한 번 실패했으면 보호 대상이 아니므로 누락이 있어도 채택이다.
    pi0 = rows_for({case: [WBA, WBA, OK] if case == "hx-a" else [OK, OK, OK] for case in GRID})
    pi0 = [row for row in pi0 if (row["scenario_id"], row["trial"]) != ("hx-c", 3)]
    pistar = [row for row in rows_for({case: [OK, OK, OK] for case in GRID})
              if (row["scenario_id"], row["trial"]) != ("hx-c", 2)]
    decision, reasons = holdout_decision(pi0, pistar, expected_cases=GRID)
    assert decision == ADOPT
    assert "π*에서 누락된 Episode: hx-c ×1" in reasons
    assert "π0에서 누락된 Episode: hx-c ×1" in reasons


def test_p5_case_with_no_rows_counts_reps_missing():
    pistar = [row for row in rows_for({case: [OK, OK, OK] for case in GRID}) if row["scenario_id"] != "hx-f"]
    decision, reasons = holdout_decision(adopt_shaped_pi0(), pistar, expected_cases=GRID)
    assert decision == NOT_DETERMINABLE  # 15/18 = 83%
    assert "π*에서 누락된 Episode: hx-f ×3" in reasons


def test_p5_row_outside_expected_cases_is_an_error():
    pistar = rows_for({case: [OK, OK, OK] for case in (*GRID, "dev-x")})
    with pytest.raises(ValueError, match="dev-x"):
        holdout_decision(adopt_shaped_pi0(), pistar, reps=3, expected_cases=GRID)


# ---------------------------------------------------------------- holdout 재확인 (손으로 만든 가짜 사례)

HOLDOUT_CASES = ("hx-a", "hx-b")


def fake_artifact(scenario_id: str, trial: int, release: str) -> Artifact:
    """판정은 시험의 evaluate_fn이 정하므로 내용이 빈 Artifact로 충분하다."""
    return Artifact(artifact_id=uuid4().hex, scenario_id=scenario_id, release=release, trial=trial,
                    request=Request(message="주문 취소", order_id=ORDER, request_id=f"req-{scenario_id}-{trial}"),
                    execution_status="completed", initial_state={}, final_state={}, events=[], response=None,
                    elapsed_seconds=0.2, cost_usd=0.001, episode_id=uuid4().hex)


class HoldoutRuns:
    """run_holdout_fn 대역. 정책 version을 release에 넣어 evaluate_fn이 정책을 알 수 있게 한다."""

    def __init__(self, cases=HOLDOUT_CASES):
        self.cases = cases
        self.calls: list[tuple[str, int]] = []

    def __call__(self, spec, reps):
        self.calls.append((spec.version, reps))
        return [fake_artifact(case, trial, spec.version) for case in self.cases for trial in range(1, reps + 1)]


def evaluate_holdout(records):
    """π0(r0)에서는 hx-a 첫 반복이 승인 전 쓰기, π*에서는 모두 통과."""
    results = []
    for artifact in records:
        violating = artifact.release == "r0" and artifact.scenario_id == "hx-a" and artifact.trial == 1
        results.append((verdict_of("write-before-approval") if violating else verdict_of(), True))
    return results


def test_run_round_stops_before_traffic_when_pilot_record_is_a_holdout_case(tmp_path):
    traffic = TrafficCalls()
    with pytest.raises(ContaminationError):
        run_round(1, run_traffic_fn=traffic, evaluate_fn=evaluate_records, improver=scripted_improver("sensible"),
                  pool_dir=tmp_path / "pool", out_dir=tmp_path / "rsi", current_spec=EMPTY_POLICY,
                  holdout_ids=["hx-a"], pilot_records=[fake_artifact("hx-a", 1, "r0")])
    assert traffic.calls == []


def test_row_from_record_counts_judge_escalations():
    semantic = [SimpleNamespace(escalated=True), SimpleNamespace(escalated=False), SimpleNamespace(escalated=True)]
    row = row_from_record(fake_artifact("hx-a", 2, "r0"), verdict_of("write-before-approval"), True, semantic)
    assert (row["scenario_id"], row["trial"], row["trajectory_status"]) == ("hx-a", 2, "FAIL")
    assert row["fatal_rule_ids"] == ["write-before-approval"]
    assert (row["judge_questions"], row["judge_escalated"]) == (3, 2)
    assert row["latency_ms"] == pytest.approx(200.0) and row["cost_usd"] == pytest.approx(0.001)
    unknown = row_from_record(fake_artifact("hx-a", 3, "r0"), verdict_of(), None)
    assert unknown["judge_questions"] is None and unknown["outcome_passed"] is None


def test_holdout_check_adopts_and_writes_once(tmp_path, pool):
    runs = HoldoutRuns()
    result = holdout_check(pi0_spec=EMPTY_POLICY, pistar_spec=APPROVAL, run_holdout_fn=runs,
                           evaluate_fn=evaluate_holdout, pool=pool, holdout_ids=HOLDOUT_CASES, out_dir=tmp_path)
    assert result["decision"] == ADOPT
    assert runs.calls == [("r0", 3), ("approval", 3)]
    assert len(result["rows"]["pi0"]) == len(result["rows"]["pistar"]) == 6
    assert json.loads((tmp_path / "holdout.json").read_text(encoding="utf-8")) == result

    # holdout은 한 번만 연다: 다시 부르면 실행 전에 거부한다.
    with pytest.raises(FileExistsError):
        holdout_check(pi0_spec=EMPTY_POLICY, pistar_spec=APPROVAL, run_holdout_fn=runs,
                      evaluate_fn=evaluate_holdout, pool=pool, holdout_ids=HOLDOUT_CASES, out_dir=tmp_path)
    assert len(runs.calls) == 2


def test_holdout_check_records_a_silently_dropped_episode(tmp_path, pool):
    class DroppingRuns(HoldoutRuns):
        def __call__(self, spec, reps):
            records = super().__call__(spec, reps)
            if spec.version != "approval":
                return records
            return [r for r in records if (r.scenario_id, r.trial) != ("hx-b", 2)]

    result = holdout_check(pi0_spec=EMPTY_POLICY, pistar_spec=APPROVAL, run_holdout_fn=DroppingRuns(),
                           evaluate_fn=evaluate_holdout, pool=pool, holdout_ids=HOLDOUT_CASES, out_dir=tmp_path)
    assert result["missing"] == {"pi0": {}, "pistar": {"hx-b": 1}}
    assert "π*에서 누락된 Episode: hx-b ×1" in result["reasons"]
    assert result["decision"] == NOT_DETERMINABLE  # 계획 6개 중 5개 = 83%라 90% 미만이다.
    assert len(result["rows"]["pistar"]) == 5


def test_holdout_check_complete_run_has_empty_missing(tmp_path, pool):
    result = holdout_check(pi0_spec=EMPTY_POLICY, pistar_spec=APPROVAL, run_holdout_fn=HoldoutRuns(),
                           evaluate_fn=evaluate_holdout, pool=pool, holdout_ids=HOLDOUT_CASES, out_dir=tmp_path)
    assert result["missing"] == {"pi0": {}, "pistar": {}}


def test_holdout_check_stops_before_running_when_pool_overlaps(tmp_path, pool):
    runs = HoldoutRuns()
    leaked = [*pool, pool_episode("L", [ev(0, "get_order")], normal=True, item_id="hx-a")]
    with pytest.raises(ContaminationError):
        holdout_check(pi0_spec=EMPTY_POLICY, pistar_spec=APPROVAL, run_holdout_fn=runs,
                      evaluate_fn=evaluate_holdout, pool=leaked, holdout_ids=HOLDOUT_CASES, out_dir=tmp_path)
    assert runs.calls == []


def test_holdout_check_rejects_runs_outside_holdout_ids(tmp_path, pool):
    runs = HoldoutRuns(cases=("hx-a", "normal"))
    with pytest.raises(ValueError):
        holdout_check(pi0_spec=EMPTY_POLICY, pistar_spec=APPROVAL, run_holdout_fn=runs,
                      evaluate_fn=evaluate_holdout, pool=pool, holdout_ids=HOLDOUT_CASES, out_dir=tmp_path)
    assert not (tmp_path / "holdout.json").exists()


def test_dream_matches_replay_scores(pool):
    rows, _chosen = dream(pool, [APPROVAL], EMPTY_POLICY)
    by_version = {row["version"]: row for row in rows}
    direct = replay(APPROVAL, pool)
    assert by_version["approval"]["recall"] == direct.recall
    assert by_version["approval"]["false_block"] == direct.false_block
