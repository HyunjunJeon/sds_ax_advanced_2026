"""모의 운영 트래픽(eval_lab.traffic)을 확인한다. 모델·네트워크 호출은 없다.

traffic 항목은 정답 명세를 담지 않는다. 이 시험만 dev 시나리오의 정답을 읽어
실수가 실제로 일어났고 평가기가 잡는지 대조한다.
"""

import json
from collections import Counter
from pathlib import Path

import pytest
from eval_lab import traffic
from eval_lab.contracts import GateDecision
from eval_lab.dataset import load_dataset
from eval_lab.evaluators import check_policy, check_recovery, check_response
from eval_lab.traffic import (
    DAY_MIX,
    MISTAKES,
    SHIFTED_FAMILIES,
    STYLES,
    make_mistake_driver,
    make_traffic,
    pilot_items,
    record_from_artifact,
    round_items,
    run_traffic,
)
from test_agent_episodes import memory_langfuse

TRAFFIC_SOURCE = Path(traffic.__file__)


# ---------------------------------------------------------------- 도우미

def expected_by_family() -> dict:
    """가족 ID -> 정답 명세. 항목 자체에는 없으므로 시험만 따로 읽는다."""
    return {card.metadata.family_id: card.expected_output for card in load_dataset(split="dev")}


def item_for(family_suffix: str, *, style: str = "정중"):
    """round_items(1)에서 가족과 문형이 맞는 항목 하나를 찾는다."""
    return next(i for i in round_items(1)
                if i.family_id == f"incident-{family_suffix}" and i.style == style)


def run_forced(mistake: str, family_suffix: str, *, gate=None):
    """실수 하나를 확률 1.0으로 강제해 항목 하나를 실행하고 기록을 돌려준다."""
    driver = make_mistake_driver({mistake: 1.0}, seed=0)
    record = run_traffic([item_for(family_suffix)], driver=driver, gate=gate)[0]
    return record, expected_by_family()[f"incident-{family_suffix}"]


def tools(artifact) -> list[str]:
    return [event.tool for event in artifact.events]


# ---------------------------------------------------------------- 항목과 분포

def test_make_traffic_is_deterministic_for_a_seed():
    first = make_traffic(1, 40, seed=7)
    second = make_traffic(1, 40, seed=7)
    other_seed = make_traffic(1, 40, seed=8)
    assert first == second
    assert first != other_seed
    assert len({item.item_id for item in first}) == 40


def test_make_traffic_rejects_unknown_day():
    with pytest.raises(ValueError):
        make_traffic(3, 5, seed=0)


def test_day_mix_weights_are_documented_and_day2_is_shifted():
    # 두 날짜 모두 가중치의 합이 100이고 dev 가족 9종을 빠짐없이 다룬다.
    dev_families = {card.metadata.family_id for card in load_dataset(split="dev")}
    for mix in DAY_MIX.values():
        assert sum(mix.values()) == 100
        assert set(mix) == dev_families
    # 1일차는 정상이 가장 많고, 2일차는 선언한 네 가족 각각이 1일차보다 늘어난다.
    assert max(DAY_MIX[1], key=DAY_MIX[1].get) == "incident-normal"
    for family in SHIFTED_FAMILIES:
        assert DAY_MIX[2][family] > DAY_MIX[1][family]
    assert DAY_MIX[2]["incident-normal"] < DAY_MIX[1]["incident-normal"]


def test_day2_traffic_differs_from_day1_as_declared():
    day1 = Counter(item.family_id for item in make_traffic(1, 600, seed=3))
    day2 = Counter(item.family_id for item in make_traffic(2, 600, seed=3))
    shifted_day1 = sum(day1[f] for f in SHIFTED_FAMILIES)
    shifted_day2 = sum(day2[f] for f in SHIFTED_FAMILIES)
    assert shifted_day2 > 2 * shifted_day1
    assert day1["incident-normal"] > day2["incident-normal"]
    assert day1.most_common(1)[0][0] == "incident-normal"


def test_pilot_items_has_nine_distinct_fixtures_in_polite_style():
    items = pilot_items()
    assert len(items) == 9
    assert len({item.fixture_id for item in items}) == 9
    assert {item.style for item in items} == {"정중"}
    dev_fixtures = {card.fixture_id for card in load_dataset(split="dev")}
    assert {item.fixture_id for item in items} == dev_fixtures
    # 사전 점검 9건은 1라운드의 일부다. 따로 만든 다른 항목이 아니다.
    assert items == round_items(1)[:9]


def test_round_items_cover_nine_fixtures_by_three_styles():
    items = round_items(1)
    assert len(items) == 27
    assert Counter(item.style for item in items) == {style: 9 for style in STYLES}
    assert len({(item.fixture_id, item.style) for item in items}) == 27
    assert len({item.item_id for item in items}) == 27
    assert len({item.item_id for item in round_items(2)} & {item.item_id for item in items}) == 0


def test_messages_are_rewritten_but_work_content_is_kept():
    originals = {card.metadata.family_id: card.input for card in load_dataset(split="dev")}
    for item in round_items(1):
        original = originals[item.family_id]
        assert item.request.order_id == original.order_id
        assert item.request.message != original.message
        assert item.request.request_id != original.request_id
    messages = {item.style: item.request.message for item in round_items(1)
                if item.family_id == "incident-normal"}
    assert len(set(messages.values())) == 3


def test_items_carry_no_expected_answer_text():
    # 모듈 소스가 평가 정답 필드 이름을 아예 쓰지 않는다.
    assert "expected_output" not in TRAFFIC_SOURCE.read_text()
    # 항목을 JSON으로 풀었을 때 정답 쪽 필드나 문장이 없다.
    cards = load_dataset(split="dev")
    forbidden_keys = {"final_state", "forbidden_tools", "response_kind", "reference_answer",
                      "required_facts", "required_milestones", "max_refund_attempts"}
    reference_texts = [card.expected_output.reference_answer for card in cards
                       if card.expected_output.reference_answer]
    for item in [*round_items(1), *make_traffic(2, 30, seed=1)]:
        dumped = item.model_dump_json()
        assert not forbidden_keys & set(json.loads(dumped))
        assert not any(key in dumped for key in forbidden_keys)
        assert not any(text in dumped for text in reference_texts)


# ---------------------------------------------------------------- 실수 주입

def test_mistake_names_are_the_five_declared():
    assert MISTAKES == ("write_before_approval", "blind_retry", "claim_without_record",
                        "write_out_of_scope", "skip_final_check")


def test_mistake_driver_rejects_bad_rates():
    with pytest.raises(ValueError):
        make_mistake_driver({"no_such_mistake": 1.0}, seed=0)
    with pytest.raises(ValueError):
        make_mistake_driver({"blind_retry": 1.5}, seed=0)


def test_write_before_approval_happens_and_policy_flags_it():
    record, expected = run_forced("write_before_approval", "normal")
    artifact = record["artifact"]
    order = tools(artifact)
    assert record["injected_mistakes"] == ["write_before_approval"]
    # 승인(check_cancel_policy) 전에 취소 시작 쓰기가 먼저 나갔다.
    assert order.index("begin_cancellation") < order.index("check_cancel_policy")
    verdict = check_policy(artifact, expected.model_copy(update={"forbidden_tools": []}))
    assert verdict.status == "FAIL"


def test_blind_retry_happens_and_recovery_flags_it():
    record, expected = run_forced("blind_retry", "timeout-before")
    artifact = record["artifact"]
    refunds = [i for i, tool in enumerate(tools(artifact)) if tool == "refund_payment"]
    assert record["injected_mistakes"] == ["blind_retry"]
    assert len(refunds) == 2
    # 첫 TIMEOUT 직후, 결제 조회 없이 바로 다시 환불했다.
    assert artifact.events[refunds[0]].result["code"] == "TIMEOUT"
    assert refunds[1] == refunds[0] + 1
    assert check_recovery(artifact, expected).status == "FAIL"


def test_claim_without_record_happens_and_response_check_flags_it():
    record, expected = run_forced("claim_without_record", "normal")
    artifact = record["artifact"]
    assert record["injected_mistakes"] == ["claim_without_record"]
    assert artifact.response.kind == "completed"
    # 취소를 완료한 기록이 없고, 실제 주문은 아직 취소 중이다.
    assert "complete_cancellation" not in tools(artifact)
    assert artifact.final_state["orders"]["order-a"]["status"] == "cancelling"
    assert check_response(artifact, expected).status == "FAIL"


def test_claim_without_record_replaces_the_ticket_when_work_fails():
    record, expected = run_forced("claim_without_record", "payment-down")
    artifact = record["artifact"]
    assert artifact.response.kind == "completed"
    assert "create_ticket" not in tools(artifact)
    assert check_response(artifact, expected).status == "FAIL"


def test_write_out_of_scope_happens_and_policy_flags_it():
    record, expected = run_forced("write_out_of_scope", "normal")
    artifact = record["artifact"]
    assert record["injected_mistakes"] == ["write_out_of_scope"]
    foreign = [e for e in artifact.events if e.tool == "begin_cancellation" and e.args["order_id"] == "order-b"]
    assert len(foreign) == 1
    # 서비스가 거절해 다른 고객의 주문은 그대로지만 시도는 기록에 남는다.
    assert foreign[0].result["code"] == "FORBIDDEN"
    assert artifact.final_state["orders"]["order-b"] == artifact.initial_state["orders"]["order-b"]
    verdict = check_policy(artifact, expected.model_copy(update={"forbidden_tools": []}))
    assert verdict.status == "FAIL"


def test_skip_final_check_happens_and_response_check_flags_it():
    record, expected = run_forced("skip_final_check", "normal")
    artifact = record["artifact"]
    assert record["injected_mistakes"] == ["skip_final_check"]
    assert tools(artifact)[-1] == "complete_cancellation"
    # 일은 끝났지만(상태는 cancelled) 최종 확인 조회가 없어 완료 주장에 근거가 모자란다.
    assert artifact.final_state["orders"]["order-a"]["status"] == "cancelled"
    assert check_response(artifact, expected).status == "FAIL"


def test_rate_zero_never_injects_and_same_seed_picks_same_mistakes():
    item = item_for("normal")
    clean = run_traffic([item], driver=make_mistake_driver({m: 0.0 for m in MISTAKES}, seed=1))[0]
    assert clean["injected_mistakes"] == []
    assert check_policy(clean["artifact"], expected_by_family()[item.family_id]).status == "PASS"

    rates = {m: 0.5 for m in MISTAKES}
    items = round_items(1)
    first = run_traffic(items, driver=make_mistake_driver(rates, seed=11))
    second = run_traffic(items, driver=make_mistake_driver(rates, seed=11))
    assert [r["injected_mistakes"] for r in first] == [r["injected_mistakes"] for r in second]
    assert any(r["injected_mistakes"] for r in first)


def test_gate_blocks_an_injected_write_before_it_reaches_the_service():
    def block_begin(prefix_events, tool, args):
        if tool == "begin_cancellation" and not any(e.tool == "check_cancel_policy" for e in prefix_events):
            return GateDecision(action="block", rule_id="require-policy", reason="정책 확인 전 쓰기")
        return GateDecision(action="allow")

    record, expected = run_forced("write_before_approval", "normal", gate=block_begin)
    artifact = record["artifact"]
    # 막힌 호출은 서비스 Event가 아니라 게이트 기록에만 남는다. 이후 정상 흐름은 끝까지 간다.
    assert any(g.decision.action == "block" for g in artifact.gate_events)
    order = tools(artifact)
    assert order.index("check_cancel_policy") < order.index("begin_cancellation")
    assert record["injected_mistakes"] == ["write_before_approval"]
    assert check_policy(artifact, expected.model_copy(update={"forbidden_tools": []})).status == "PASS"


# ---------------------------------------------------------------- 실행과 기록

def test_scripted_pilot_without_mistakes_passes_policy_for_every_artifact():
    expected = expected_by_family()
    records = run_traffic(pilot_items())
    assert len(records) == 9
    for record in records:
        assert record["artifact"].execution_status == "completed"
        assert check_policy(record["artifact"], expected[record["family_id"]]).status == "PASS"
        assert record["injected_mistakes"] == []


def test_scripted_pilot_with_empty_mistake_driver_passes_policy_too():
    expected = expected_by_family()
    records = run_traffic(pilot_items(), driver=make_mistake_driver({}, seed=0), release="candidate")
    for record in records:
        assert check_policy(record["artifact"], expected[record["family_id"]]).status == "PASS"


def test_records_carry_item_fields_and_known_zero_cost_for_scripted():
    records = run_traffic(pilot_items()[:2])
    expected_keys = {"artifact", "item_id", "day", "style", "family_id", "fixture_id", "latency_ms",
                     "model_calls", "input_tokens", "output_tokens", "cost_usd", "trace_id",
                     "execution_status", "injected_mistakes"}
    for record in records:
        assert set(record) == expected_keys
        assert record["model_calls"] == 0
        assert record["cost_usd"] == 0.0  # 모델 호출이 없다는 것을 아는 0
        assert record["latency_ms"] >= 0
        assert record["trace_id"] is None  # Langfuse를 쓰지 않았다
        assert record["artifact"].scenario_id == record["item_id"]


def test_run_traffic_forwards_the_version_label_to_langfuse():
    """run_traffic(version=...)은 Episode마다 그 버전 이름을 Langfuse version으로 단다. 기록의 release는 그대로다."""
    items = pilot_items()[:2]
    with memory_langfuse() as (client, exporter):
        records = run_traffic(items, langfuse=client, version="policy-r3")
        client.flush()
        roots = [s for s in exporter.get_finished_spans() if s.parent is None]

    assert [root.attributes["langfuse.version"] for root in roots] == ["policy-r3"] * len(items)
    assert {record["artifact"].release for record in records} == {"baseline"}


def test_unknown_cost_stays_none_in_record():
    item = pilot_items()[0]
    artifact = run_traffic([item])[0]["artifact"]
    unknown = artifact.model_copy(update={"cost_usd": None, "input_tokens": None, "output_tokens": None,
                                          "model_calls": 3})
    record = record_from_artifact(item, unknown)
    assert record["cost_usd"] is None
    assert record["input_tokens"] is None
    assert record["model_calls"] == 3


def test_live_mode_requires_model_and_rejects_driver():
    with pytest.raises(ValueError):
        run_traffic(pilot_items()[:1], mode="live")
    with pytest.raises(ValueError):
        run_traffic(pilot_items()[:1], mode="live", model=object(),
                    driver=make_mistake_driver({}, seed=0))
    with pytest.raises(ValueError):
        run_traffic(pilot_items()[:1], mode="batch")
    with pytest.raises(ValueError):
        run_traffic(pilot_items()[:1], release="unknown")
