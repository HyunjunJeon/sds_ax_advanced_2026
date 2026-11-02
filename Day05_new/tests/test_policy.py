"""eval_lab.policy 시험: 규칙 네 가지의 차단·허용, 형식 거부, 빈 정책, Episode 연동, 지나치게 엄격한 정책의 반례.

모델 호출과 네트워크는 없다. holdout 시나리오는 읽지 않고 dev 시나리오와 fx-normal fixture만 쓴다.
"""

import json
from copy import deepcopy

import pytest
from eval_lab.agent import call_tool
from eval_lab.contracts import Event, Response
from eval_lab.dataset import load_dataset, load_fixtures
from eval_lab.episodes import execute_episode
from eval_lab.policy import (
    EMPTY_POLICY,
    PolicyRejected,
    PolicySpec,
    as_gate,
    decide,
    describe,
    validate_spec,
)

ORDER = "order-a"
OTHER = "order-b"


# ---------------------------------------------------------------- 공용 도우미

def ev(step: int, tool: str, result: dict | None = None, order: str | None = ORDER, **args) -> Event:
    """손으로 만든 서비스 Event. order가 None이면 order_id 인자를 넣지 않는다."""
    call_args = ({"order_id": order} if order is not None else {}) | args
    return Event(event_id=f"e{step}", step=step, tool=tool, args=call_args,
                 result=result if result is not None else {"status": "ok"},
                 start_ns=step, end_ns=step + 1)


def spec_of(*rules: dict) -> PolicySpec:
    """규칙 dict들로 정책을 만든다. 검증을 거치므로 형식 오류는 여기서 드러난다."""
    return validate_spec({"version": "t1", "rules": list(rules)})


def decide_for(spec: PolicySpec, prefix: list[Event], tool: str, order: str = ORDER):
    return decide(spec, prefix, tool, {"order_id": order})


# ---------------------------------------------------------------- 규칙별 차단·허용

def test_require_before():
    spec = spec_of({"kind": "require_before", "tool": "refund_payment", "requires_tool": "begin_cancellation"})
    # 선행 호출이 없으면 막고, rule_id 형식을 지킨다.
    blocked = decide_for(spec, [], "refund_payment")
    assert blocked.action == "block"
    assert blocked.rule_id == "require_before:refund_payment<-begin_cancellation"
    # 선행 호출이 실패했으면 성공이 아니므로 막는다.
    failed = [ev(1, "begin_cancellation", {"status": "error", "code": "VERSION_CONFLICT"})]
    assert decide_for(spec, failed, "refund_payment").action == "block"
    # 다른 주문의 성공은 same_order=True에서 인정하지 않는다.
    assert decide_for(spec, [ev(1, "begin_cancellation", order=OTHER)], "refund_payment").action == "block"
    # 같은 주문의 성공이 있으면 통과한다.
    assert decide_for(spec, [ev(1, "begin_cancellation")], "refund_payment").action == "allow"
    # 규칙과 무관한 도구는 통과한다.
    assert decide_for(spec, [], "get_order").action == "allow"


def test_require_before_any_order_and_ask():
    spec = spec_of({"kind": "require_before", "tool": "refund_payment", "requires_tool": "get_payment",
                    "same_order": False, "action": "ask"})
    assert decide_for(spec, [], "refund_payment").action == "ask"
    assert decide_for(spec, [ev(1, "get_payment", order=OTHER)], "refund_payment").action == "allow"


@pytest.mark.parametrize("seen, on_code", [
    ({"status": "denied", "code": "FORBIDDEN"}, "denied"),
    ({"status": "denied", "code": "FORBIDDEN"}, "FORBIDDEN"),
    ({"status": "ok", "order": {"status": "shipped"}}, "shipped"),
])
def test_block_after(seen, on_code):
    spec = spec_of({"kind": "block_after", "on_code": on_code, "tools": ["begin_cancellation", "refund_payment"]})
    prefix = [ev(1, "get_order", seen)]
    blocked = decide_for(spec, prefix, "refund_payment")
    assert blocked.action == "block"
    assert blocked.rule_id == f"block_after:{on_code}->refund_payment"
    # 목록에 없는 도구(조회)는 계속 허용한다.
    assert decide_for(spec, prefix, "get_payment").action == "allow"
    # 다른 주문의 관측은 이 주문을 막지 않는다.
    assert decide_for(spec, prefix, "refund_payment", order=OTHER).action == "allow"
    # 관측 전에는 허용한다.
    assert decide_for(spec, [], "refund_payment").action == "allow"


def test_max_attempts():
    spec = spec_of({"kind": "max_attempts", "tool": "refund_payment", "limit": 2})
    timeout = {"status": "error", "code": "TIMEOUT"}
    one = [ev(1, "refund_payment", timeout)]
    two = one + [ev(2, "refund_payment", timeout)]
    assert decide_for(spec, one, "refund_payment").action == "allow"
    blocked = decide_for(spec, two, "refund_payment")
    assert blocked.action == "block" and blocked.rule_id == "max_attempts:refund_payment<=2"
    # 다른 주문의 시도는 세지 않는다.
    assert decide_for(spec, two, "refund_payment", order=OTHER).action == "allow"


def test_require_check_after_timeout():
    spec = spec_of({"kind": "require_check_after_timeout", "tool": "refund_payment", "check_tool": "get_payment"})
    timeout = ev(1, "refund_payment", {"status": "error", "code": "TIMEOUT", "outcome": "unknown"})
    # TIMEOUT 전에는 허용, 직후 재호출은 차단.
    assert decide_for(spec, [], "refund_payment").action == "allow"
    blocked = decide_for(spec, [timeout], "refund_payment")
    assert blocked.action == "block"
    assert blocked.rule_id == "require_check_after_timeout:refund_payment<-get_payment"
    # 확인 도구가 TIMEOUT보다 앞에 있었던 것은 인정하지 않는다.
    assert decide_for(spec, [ev(0, "get_payment"), timeout], "refund_payment").action == "block"
    # TIMEOUT 뒤에 확인 도구를 부르면 다시 허용한다.
    assert decide_for(spec, [timeout, ev(2, "get_payment")], "refund_payment").action == "allow"


def test_first_matching_rule_wins():
    spec = spec_of(
        {"kind": "max_attempts", "tool": "refund_payment", "limit": 1, "action": "ask"},
        {"kind": "require_before", "tool": "refund_payment", "requires_tool": "begin_cancellation"},
    )
    decision = decide_for(spec, [ev(1, "refund_payment", {"status": "error", "code": "TIMEOUT"})], "refund_payment")
    assert decision.action == "ask" and decision.rule_id.startswith("max_attempts")


def test_describe_one_line_per_rule():
    spec = spec_of(
        {"kind": "require_before", "tool": "begin_cancellation", "requires_tool": "check_cancel_policy"},
        {"kind": "block_after", "on_code": "shipped", "tools": ["begin_cancellation"]},
        {"kind": "max_attempts", "tool": "refund_payment", "limit": 2, "action": "ask"},
        {"kind": "require_check_after_timeout", "tool": "refund_payment", "check_tool": "get_payment"},
    )
    lines = describe(spec).splitlines()
    assert len(lines) == 4
    assert "check_cancel_policy" in lines[0] and "shipped" in lines[1] and "확인 요청" in lines[2]
    assert "규칙 없음" in describe(EMPTY_POLICY)


# ---------------------------------------------------------------- 형식 거부

def test_validate_accepts_json_string_and_dict():
    obj = {"version": "r1", "rules": [{"kind": "max_attempts", "tool": "refund_payment", "limit": 2}]}
    assert validate_spec(obj) == validate_spec(json.dumps(obj))
    assert validate_spec(obj).rules[0].action == "block"


@pytest.mark.parametrize("bad", [
    {"version": "r1", "rules": [], "threshold": 0.5},                                   # 명세 최상위의 모르는 키
    {"version": "r1", "rules": [{"kind": "max_attempts", "tool": "refund_payment", "limit": 2, "budget": 9}]},
    {"version": "r1", "rules": [{"kind": "max_attempts", "tool": "refund_payment", "limit": 2,
                                 "dataset": "gold.jsonl", "path": "/tmp/x"}]},           # 평가 쪽 키
    {"version": "r1", "rules": [{"kind": "max_attempts", "tool": "drop_database", "limit": 2}]},   # 모르는 도구
    {"version": "r1", "rules": [{"kind": "block_after", "on_code": "x", "tools": ["nope"]}]},
    {"version": "r1", "rules": [{"kind": "set_threshold", "name": "t_lo", "value": 0.0}]},        # 모르는 규칙 종류
    {"version": "r1", "rules": [{"tool": "refund_payment", "limit": 2}]},                          # kind 없음
    {"version": "r1", "rules": [{"kind": "max_attempts", "tool": "refund_payment", "limit": 0}]},
    {"version": "r1", "rules": [{"kind": "max_attempts", "tool": "refund_payment", "limit": 2, "action": "allow"}]},
    {"version": "", "rules": []},
    {"rules": []},
    [],
    "{깨진 json",
])
def test_validate_rejects(bad):
    with pytest.raises(PolicyRejected) as caught:
        validate_spec(bad)
    assert caught.value.reason  # 한국어 이유가 비어 있지 않다.


def test_rejection_reason_names_the_problem():
    with pytest.raises(PolicyRejected, match="규칙 종류"):
        validate_spec({"version": "r1", "rules": [{"kind": "set_threshold", "value": 0}]})
    with pytest.raises(PolicyRejected, match="알 수 없는 도구"):
        validate_spec({"version": "r1", "rules": [{"kind": "max_attempts", "tool": "x", "limit": 1}]})
    with pytest.raises(PolicyRejected, match="모르는 키"):
        validate_spec({"version": "r1", "rules": [], "thresholds": {}})


# ---------------------------------------------------------------- 빈 정책

def test_empty_policy_allows_everything():
    prefix = [ev(1, "refund_payment", {"status": "error", "code": "TIMEOUT"}), ev(2, "get_order", {"status": "denied"})]
    for tool in ("get_order", "check_cancel_policy", "get_payment", "create_ticket", "begin_cancellation",
                 "refund_payment", "release_stock", "complete_cancellation"):
        decision = decide(EMPTY_POLICY, prefix, tool, {"order_id": ORDER})
        assert decision.action == "allow" and decision.rule_id is None


# ---------------------------------------------------------------- 게이트 연동

def run_dev_normal(gate=None):
    """dev 시나리오(fx-normal)를 scripted로 한 번 실행한다."""
    card = next(c for c in load_dataset(split="dev") if c.fixture_id == "fx-normal")
    return execute_episode(card.input, load_fixtures()["fx-normal"], followups=card.followups,
                           max_turns=card.max_turns, scenario_id=card.metadata.scenario_id,
                           release="baseline", trial=1, mode="scripted", prompt="", gate=gate)


def test_sensible_policy_still_completes_normal_scenario():
    spec = spec_of({"kind": "require_before", "tool": "begin_cancellation", "requires_tool": "check_cancel_policy"})
    artifact = run_dev_normal(as_gate(spec))
    assert artifact.execution_status == "completed"
    assert artifact.response.kind == "completed"
    assert artifact.final_state["orders"][ORDER]["status"] == "cancelled"
    assert artifact.gate_events and all(g.decision.action == "allow" for g in artifact.gate_events)


def test_decide_sees_only_the_prefix():
    """게이트가 받은 prefix의 길이는 그 시점에 서비스에 닿은 호출 수와 같고, 뒤 사건은 결정에 영향이 없다."""
    spec = spec_of({"kind": "max_attempts", "tool": "get_order", "limit": 5})
    inner = as_gate(spec)
    seen = []

    def spy(prefix_events, tool, args):
        seen.append((len(prefix_events), tool))
        return inner(prefix_events, tool, args)

    artifact = run_dev_normal(spy)
    # 모두 허용되었으므로 i번째 호출의 prefix 길이는 i다.
    assert [n for n, _ in seen] == list(range(len(seen)))
    assert len(artifact.events) == len(seen)

    # 같은 사건열을 앞부분만 주면 뒤의 위반이 보이지 않는다.
    timeout = {"status": "error", "code": "TIMEOUT"}
    events = [ev(1, "get_order"), ev(2, "refund_payment", timeout), ev(3, "refund_payment", timeout)]
    cap = spec_of({"kind": "max_attempts", "tool": "refund_payment", "limit": 2})
    assert decide_for(cap, events[:2], "refund_payment").action == "allow"
    assert decide_for(cap, events, "refund_payment").action == "block"
    # decide는 받은 목록을 바꾸지 않는다.
    snapshot = deepcopy(events)
    decide_for(cap, events, "refund_payment")
    assert events == snapshot


# ---------------------------------------------------------------- 교육용 반례: 지나치게 엄격한 정책

def resume_fixture() -> dict:
    """fx-normal을 복사해 order-a를 '취소 중, 결제 캡처됨, 환불 전'(이어서 처리할 주문)으로 만든다."""
    fixture = deepcopy(load_fixtures()["fx-normal"])
    order = next(o for o in fixture["orders"] if o["id"] == ORDER)
    order["status"] = "cancelling"
    order["version"] = 2
    return fixture


def resume_driver(gate):
    """이어서 처리하는 올바른 경로. 이미 cancelling이므로 begin_cancellation을 다시 부르지 않는다."""

    def driver(request, env, release):
        oid = request.order_id

        def call(tool, **args):
            return call_tool(env, tool, args, gate=gate)

        def stop(reason):
            call("create_ticket", order_id=oid, reason=reason)
            return Response(kind="escalated", message="취소 처리가 끝나지 않아 담당자에게 접수했습니다.",
                            order_id=oid), {}

        # 1단계: 주문과 정책을 확인하고, 남은 결제액을 읽는다.
        call("get_order", order_id=oid)
        call("check_cancel_policy", order_id=oid)
        payment = call("get_payment", order_id=oid)["payment"]
        remaining = payment["captured_cents"] - payment["refunded_cents"]
        # 2단계: 환불, 재고 복원, 완료. 어느 단계든 ok가 아니면 이관한다.
        if call("refund_payment", order_id=oid, amount_cents=remaining,
                idempotency_key=f"refund:{request.request_id}")["status"] != "ok":
            return stop("환불 실패")
        if call("release_stock", order_id=oid, idempotency_key=f"stock:{oid}")["status"] != "ok":
            return stop("재고 복원 실패")
        if call("complete_cancellation", order_id=oid)["status"] != "ok":
            return stop("완료 실패")
        return Response(kind="completed", message="이어서 취소를 완료했습니다.", order_id=oid), {}

    return driver


def run_resume(spec: PolicySpec):
    card = next(c for c in load_dataset(split="dev") if c.fixture_id == "fx-normal")
    return execute_episode(card.input, resume_fixture(), followups=[], max_turns=1,
                           scenario_id="resume-synthetic", release="baseline", trial=1, mode="scripted",
                           prompt="", scripted_driver=resume_driver(as_gate(spec)))


def test_overstrict_policy_blocks_the_correct_resume_path():
    strict = spec_of({"kind": "require_before", "tool": "refund_payment", "requires_tool": "begin_cancellation"})

    # 빈 정책: 이어서 처리하는 경로가 끝까지 간다.
    free = run_resume(EMPTY_POLICY)
    assert free.response.kind == "completed"
    assert free.final_state["orders"][ORDER]["status"] == "cancelled"

    # 엄격한 정책: 올바른 경로의 환불이 막혀 주문이 완료되지 않는다.
    held = run_resume(strict)
    blocked = [g for g in held.gate_events if g.decision.action == "block"]
    assert [g.tool for g in blocked] == ["refund_payment"]
    assert blocked[0].decision.rule_id == "require_before:refund_payment<-begin_cancellation"
    assert held.response.kind == "escalated"
    assert held.final_state["orders"][ORDER]["status"] == "cancelling"
    assert held.final_state["payments"][ORDER]["refunded_cents"] == 0
