"""평가자 자체의 평가(eval_lab.meta_eval)를 시험한다. 모델·네트워크 호출은 없다.

- 결함 주입: 치명 규칙마다 scripted dev 기록 전부에서 그 규칙이 잡는다(재현율 1.0).
- 무해한 변형: 치명 hit을 새로 만들지 않는다.
- wilson_interval: 알려진 값, n == 0, 경계.
- 입력 Artifact는 바뀌지 않고 사건 ID는 유일하다.
"""

import pytest
from eval_lab.agent import PROMPTS
from eval_lab.dataset import load_dataset, load_fixtures
from eval_lab.episodes import execute_episode
from eval_lab.meta_eval import (
    FATAL_RULE_IDS,
    benign_variants,
    inject_defect,
    measure,
    wilson_interval,
)
from eval_lab.trajectory_rules import RULES, run_rules

SEED = 7


@pytest.fixture(scope="module")
def dev_artifacts():
    """dev 시나리오 전부를 scripted 드라이버로 한 번씩 실행한다. 모델 호출 0회."""
    fixtures = load_fixtures()
    artifacts = {}
    for card in load_dataset(split="dev"):
        artifacts[card.metadata.scenario_id] = execute_episode(
            card.input, fixtures[card.fixture_id], followups=card.followups, max_turns=card.max_turns,
            scenario_id=card.metadata.scenario_id, release="baseline", trial=1, mode="scripted",
            prompt=PROMPTS["baseline"])
    return artifacts


def fatal_ids(artifact):
    """치명 hit을 낸 규칙 ID 집합."""
    return {hit.rule_id for hit in run_rules(artifact) if hit.severity == "fatal"}


# ---------------------------------------------------------------- wilson_interval

def test_wilson_interval_known_value():
    low, high = wilson_interval(9, 10)
    assert (round(low, 3), round(high, 3)) == (0.596, 0.982)


def test_wilson_interval_without_samples_is_none():
    assert wilson_interval(0, 0) is None


def test_wilson_interval_stays_inside_unit_range():
    for k, n in ((0, 5), (5, 5), (1, 1), (0, 1)):
        low, high = wilson_interval(k, n)
        assert 0.0 <= low <= k / n <= high <= 1.0


def test_wilson_interval_rejects_impossible_counts():
    with pytest.raises(ValueError):
        wilson_interval(3, 2)
    with pytest.raises(ValueError):
        wilson_interval(-1, 2)


# ---------------------------------------------------------------- 결함 주입

def test_fatal_rule_ids_follow_the_rules_table():
    assert FATAL_RULE_IDS == tuple(rule_id for rule_id, severity, _ in RULES if severity == "fatal")
    assert len(FATAL_RULE_IDS) == 6


def test_clean_dev_artifacts_have_no_fatal_hits(dev_artifacts):
    assert len(dev_artifacts) == 9
    for scenario_id, artifact in dev_artifacts.items():
        assert fatal_ids(artifact) == set(), scenario_id


@pytest.mark.parametrize("rule_id", FATAL_RULE_IDS)
def test_injection_is_detected_on_every_dev_artifact(dev_artifacts, rule_id):
    for scenario_id, artifact in dev_artifacts.items():
        defective = inject_defect(artifact, rule_id, seed=SEED)
        assert rule_id in fatal_ids(defective), f"{rule_id} / {scenario_id}"


@pytest.mark.parametrize("rule_id", FATAL_RULE_IDS)
def test_injection_does_not_mutate_input_and_keeps_ids_unique(dev_artifacts, rule_id):
    for scenario_id, artifact in dev_artifacts.items():
        before = artifact.model_dump()
        defective = inject_defect(artifact, rule_id, seed=SEED)
        assert artifact.model_dump() == before, f"{rule_id} / {scenario_id}"
        assert defective is not artifact
        ids = [event.event_id for event in defective.events]
        assert len(ids) == len(set(ids)), f"{rule_id} / {scenario_id}"
        assert [event.step for event in defective.events] == list(range(1, len(ids) + 1))
        assert defective.artifact_id != artifact.artifact_id


@pytest.mark.parametrize("rule_id", FATAL_RULE_IDS)
def test_injection_is_deterministic_per_seed(dev_artifacts, rule_id):
    artifact = dev_artifacts["normal"]
    first = inject_defect(artifact, rule_id, seed=SEED)
    second = inject_defect(artifact, rule_id, seed=SEED)
    assert first.model_dump() == second.model_dump()


def test_injection_on_normal_flow_triggers_only_the_target_rule(dev_artifacts):
    # 정상 취소 흐름은 결함을 심을 자리가 모두 있으므로 규칙 하나만 울리는지 가장 깨끗하게 볼 수 있다.
    artifact = dev_artifacts["normal"]
    for rule_id in FATAL_RULE_IDS:
        assert fatal_ids(inject_defect(artifact, rule_id, seed=SEED)) == {rule_id}, rule_id


def test_move_and_swap_reuse_existing_events(dev_artifacts):
    artifact = dev_artifacts["normal"]
    original_ids = [event.event_id for event in artifact.events]

    moved = inject_defect(artifact, "write-before-approval", seed=SEED)
    assert moved.events[0].tool == "begin_cancellation"
    assert sorted(e.event_id for e in moved.events) == sorted(original_ids)

    swapped = inject_defect(artifact, "step-out-of-order", seed=SEED)
    tools = [event.tool for event in swapped.events]
    assert tools.index("release_stock") < tools.index("refund_payment")
    assert sorted(e.event_id for e in swapped.events) == sorted(original_ids)


def test_claim_injection_leaves_no_completion_record(dev_artifacts):
    defective = inject_defect(dev_artifacts["duplicate-request"], "claim-without-record", seed=SEED)
    assert defective.response.kind == "completed"
    assert all(event.tool != "complete_cancellation" for event in defective.events)
    assert all((event.result.get("order") or {}).get("status") != "cancelled" for event in defective.events)


def test_injection_rejects_warn_and_unknown_rules(dev_artifacts):
    artifact = dev_artifacts["normal"]
    with pytest.raises(ValueError):
        inject_defect(artifact, "blind-retry", seed=SEED)
    with pytest.raises(ValueError):
        inject_defect(artifact, "no-such-rule", seed=SEED)


# ---------------------------------------------------------------- 무해한 변형

def test_benign_variants_add_no_fatal_hits(dev_artifacts):
    total = 0
    for scenario_id, artifact in dev_artifacts.items():
        for variant in benign_variants(artifact, seed=SEED):
            total += 1
            assert fatal_ids(variant) == set(), f"{scenario_id} / {variant.artifact_id}"
    assert total > 0


def test_benign_variants_do_not_mutate_input_and_keep_ids_unique(dev_artifacts):
    for scenario_id, artifact in dev_artifacts.items():
        before = artifact.model_dump()
        for variant in benign_variants(artifact, seed=SEED):
            ids = [event.event_id for event in variant.events]
            assert len(ids) == len(set(ids)), scenario_id
        assert artifact.model_dump() == before, scenario_id


def test_benign_variants_keep_response_facts(dev_artifacts):
    artifact = dev_artifacts["normal"]
    variants = {variant.artifact_id.split("#")[-1]: variant for variant in benign_variants(artifact, seed=SEED)}
    assert {"benign-reorder-reads", "benign-extra-read", "benign-reword", "benign-combined"} <= set(variants)

    reworded = variants["benign-reword"].response
    assert reworded.message != artifact.response.message
    assert artifact.response.message in reworded.message
    assert (reworded.kind, reworded.order_id, reworded.refund_cents) == \
        (artifact.response.kind, artifact.response.order_id, artifact.response.refund_cents)

    extra = variants["benign-extra-read"]
    assert len(extra.events) == len(artifact.events) + 1
    reordered = variants["benign-reorder-reads"]
    assert [e.event_id for e in reordered.events] != [e.event_id for e in artifact.events]
    assert sorted(e.event_id for e in reordered.events) == sorted(e.event_id for e in artifact.events)


# ---------------------------------------------------------------- measure

def test_measure_recall_is_one_for_every_fatal_rule(dev_artifacts):
    report = measure(list(dev_artifacts.values()), seed=SEED)

    assert report.clean_count == 9
    assert [metric.rule_id for metric in report.per_rule] == list(FATAL_RULE_IDS)
    for metric in report.per_rule:
        assert metric.injected == 9, metric.rule_id
        assert metric.detected == 9, metric.rule_id
        assert metric.recall == 1.0
        assert metric.recall_interval == wilson_interval(9, 9)
    assert report.skipped_injections == {}


def test_measure_false_positive_rate_is_zero_with_interval(dev_artifacts):
    report = measure(list(dev_artifacts.values()), seed=SEED)

    assert report.benign_total > 0
    assert report.benign_with_fatal == 0
    assert report.false_positive_rate == 0.0
    assert report.false_positive_interval == wilson_interval(0, report.benign_total)


def test_measure_precision_counts_collateral_hits(dev_artifacts):
    report = measure(list(dev_artifacts.values()), seed=SEED)

    assert report.true_detections == 6 * 9
    assert report.all_detections >= report.true_detections
    assert report.precision == report.true_detections / report.all_detections
    assert report.precision_interval == wilson_interval(report.true_detections, report.all_detections)
    for metric in report.per_rule:
        assert metric.precision == metric.detected / (metric.detected + metric.false_detections)


def test_measure_skips_injection_when_clean_already_violates(dev_artifacts):
    already_bad = inject_defect(dev_artifacts["normal"], "write-before-approval", seed=SEED)
    report = measure([already_bad], seed=SEED)

    assert report.skipped_injections == {"write-before-approval": 1}
    metrics = {metric.rule_id: metric for metric in report.per_rule}
    assert metrics["write-before-approval"].injected == 0
    assert metrics["write-before-approval"].recall is None
    assert metrics["write-before-approval"].recall_interval is None


def test_measure_with_no_artifacts_reports_none_not_made_up_values():
    report = measure([], seed=SEED)

    assert report.clean_count == 0
    assert report.false_positive_rate is None and report.false_positive_interval is None
    assert report.precision is None and report.precision_interval is None
    assert all(metric.recall is None and metric.recall_interval is None for metric in report.per_rule)
