"""모니터링 지표·경보·Metrics API 질의(eval_lab.monitoring)를 확인한다. 모델·네트워크 호출은 없다."""

import json
from types import SimpleNamespace

import pytest
from eval_lab import monitoring
from eval_lab.monitoring import (
    ALERT_RULES,
    compare_remote_local,
    evaluate_alerts,
    fetch_metrics,
    local_metrics,
    metrics_query,
    otel_names,
    total_variation_distance,
)
from eval_lab.traffic import make_mistake_driver, make_traffic, run_traffic
from opentelemetry.semconv._incubating.attributes import gen_ai_attributes as semconv

# ---------------------------------------------------------------- 도우미

def day_records(day: int, n: int = 60, *, seed: int, mistakes: dict | None = None) -> list[dict]:
    """scripted 트래픽 기록. mistakes를 주면 그 실수를 섞은 드라이버로 돌린다."""
    driver = make_mistake_driver(mistakes, seed=seed) if mistakes else None
    return run_traffic(make_traffic(day, n, seed=seed), driver=driver)


@pytest.fixture(scope="module")
def two_days() -> dict:
    """1일차(정상)와 2일차(분포가 바뀌고 실수를 강제)를 한 번만 만든다."""
    day1 = day_records(1, seed=1)
    day2 = day_records(2, seed=2, mistakes={"write_before_approval": 0.5, "claim_without_record": 0.3})
    return local_metrics(day1 + day2, group_by="day")


# ---------------------------------------------------------------- 경보

def test_day_two_raises_fatal_and_input_mix_alerts(two_days):
    alerts = evaluate_alerts(two_days[2], two_days[1])
    rules = {alert.rule for alert in alerts}
    assert {"fatal-rate", "input-mix-shift"} <= rules
    by_rule = {alert.rule: alert for alert in alerts}
    assert by_rule["fatal-rate"].value > 0
    assert by_rule["input-mix-shift"].value > monitoring.INPUT_MIX_TVD_LIMIT


def test_identical_groups_raise_no_alert(two_days):
    assert two_days[1]["fatal_rate"] == 0.0
    assert evaluate_alerts(two_days[1], two_days[1]) == []


def test_alert_rules_are_fixed_constants():
    ids = {rule.rule_id for rule in ALERT_RULES}
    assert ids == {"fatal-rate", "evaluation-completeness", "latency-p95", "input-mix-shift"}
    assert (monitoring.FATAL_RATE_LIMIT, monitoring.COMPLETENESS_MIN) == (0.0, 0.9)
    assert (monitoring.LATENCY_P95_RATIO, monitoring.INPUT_MIX_TVD_LIMIT) == (1.5, 0.3)
    with pytest.raises(AttributeError):
        ALERT_RULES[0].threshold = 1.0


def test_latency_and_completeness_alerts_use_their_thresholds():
    baseline = {"latency_p95": 100.0, "evaluation_completeness": 1.0, "fatal_rate": 0.0}
    ok = {"latency_p95": 150.0, "evaluation_completeness": 0.9, "fatal_rate": 0.0}
    assert evaluate_alerts(ok, baseline) == []
    bad = {"latency_p95": 151.0, "evaluation_completeness": 0.89, "fatal_rate": 0.0}
    assert {a.rule for a in evaluate_alerts(bad, baseline)} == {"latency-p95", "evaluation-completeness"}
    # 계산하지 못한 값(None)은 경보를 만들지 않는다.
    assert evaluate_alerts({"latency_p95": None, "fatal_rate": None}, baseline) == []


def test_total_variation_distance_bounds():
    assert total_variation_distance({"a": 1.0}, {"a": 1.0}) == 0.0
    assert total_variation_distance({"a": 1.0}, {"b": 1.0}) == 1.0


# ---------------------------------------------------------------- 지표

def test_cost_per_success_is_none_when_a_cost_is_unknown():
    records = day_records(1, 12, seed=4)
    known = local_metrics(records)[1]
    assert known["cost_per_success"] == 0.0  # scripted는 비용 0.0으로 알려져 있다.
    records[3]["cost_usd"] = None
    assert local_metrics(records)[1]["cost_per_success"] is None


def test_completeness_counts_incomplete_separately():
    records = day_records(1, 20, seed=5)
    records[0]["execution_status"] = "execution_error"  # 끝나지 못한 Episode
    metrics = local_metrics(records)[1]
    assert metrics["status_counts"]["INCOMPLETE"] == 1
    assert metrics["incomplete_share"] == pytest.approx(1 / 20)
    judged = metrics["status_counts"]["PASS"] + metrics["status_counts"]["FAIL"]
    assert metrics["evaluation_completeness"] == pytest.approx(judged / 20)
    shares = (metrics["evaluation_completeness"] + metrics["incomplete_share"]
              + metrics["provisional_share"] + metrics["no_evidence_share"])
    assert shares == pytest.approx(1.0)


def test_group_by_other_keys_and_input_mix():
    records = day_records(1, 40, seed=6)
    by_style = local_metrics(records, group_by="style")
    assert set(by_style) <= {"정중", "짧게", "오타"}
    assert sum(g["episode_count"] for g in by_style.values()) == 40
    mix = local_metrics(records)[1]["input_mix"]
    assert sum(mix["family_id"].values()) == pytest.approx(1.0)
    assert sum(mix["style"].values()) == pytest.approx(1.0)


def test_semantic_metrics_only_when_given():
    records = day_records(1, 6, seed=7)
    assert "semantic_fail_rate" not in local_metrics(records)[1]
    verdict = lambda passed, escalated: SimpleNamespace(passed=passed, escalated=escalated)
    semantic = {
        records[0]["item_id"]: [verdict(False, True), verdict(True, False)],
        records[1]["item_id"]: [verdict(None, True)],
    }
    metrics = local_metrics(records, semantic_results=semantic)[1]
    assert metrics["semantic_fail_rate"] == pytest.approx(1 / 2)  # 판정 못 한 것은 분모에서 뺀다
    assert metrics["escalation_rate"] == pytest.approx(2 / 3)


def test_tool_error_rate_counts_error_results(two_days):
    assert 0.0 < two_days[1]["tool_error_rate"] < 1.0


def test_precomputed_trajectory_results_are_used():
    records = day_records(1, 6, seed=8)
    fake = [SimpleNamespace(status="FAIL", fatal=[object()], warn=[]) for _ in records]
    metrics = local_metrics(records, trajectory_results=fake)[1]
    assert metrics["fatal_rate"] == 1.0
    with pytest.raises(ValueError):
        local_metrics(records, trajectory_results=fake[:-1])


# ---------------------------------------------------------------- Metrics API v2 질의

def test_metrics_query_uses_documented_keys_and_root_filter():
    query = metrics_query(view="observations", metrics=[("latency", "p95"), ("totalCost", "sum")],
                          dimensions=["name"], filters=None,
                          from_ts="2026-11-01T00:00:00Z", to_ts="2026-11-02T00:00:00Z")
    assert set(query) == {"view", "dimensions", "metrics", "filters", "fromTimestamp", "toTimestamp"}
    assert query["metrics"][0] == {"measure": "latency", "aggregation": "p95"}
    assert query["dimensions"] == [{"field": "name"}]
    assert query["filters"] == [{"column": "isRootObservation", "operator": "=", "value": True, "type": "boolean"}]
    json.dumps(query)  # client.api.metrics.metrics(query=json.dumps(...))에 넣을 수 있어야 한다.


def test_metrics_query_rejects_traces_view_and_bad_aggregation():
    common = {"dimensions": [], "filters": None, "from_ts": "a", "to_ts": "b"}
    with pytest.raises(ValueError, match="traces"):
        metrics_query(view="traces", metrics=[("count", "sum")], **common)
    with pytest.raises(ValueError):
        metrics_query(metrics=[("latency", "median")], **common)
    with pytest.raises(ValueError):
        metrics_query(metrics=[], **common)


def test_fetch_metrics_sends_json_string():
    seen = {}

    def metrics(*, query):
        seen["query"] = query
        return SimpleNamespace(data=[{"count_count": 3}])

    client = SimpleNamespace(api=SimpleNamespace(metrics=SimpleNamespace(metrics=metrics)))
    query = metrics_query(metrics=[("count", "count")], dimensions=None, filters=None, from_ts="a", to_ts="b")
    assert fetch_metrics(client, query) == [{"count_count": 3}]
    assert json.loads(seen["query"]) == query


def test_compare_remote_local_shows_differences_and_lag_note():
    table = compare_remote_local({"latency_p95": 120.0, "episode_count": 10}, {"latency_p95": 100.0, "fatal_rate": 0.0})
    rows = {row["metric"]: row for row in table["rows"]}
    assert rows["latency_p95"]["difference"] == pytest.approx(20.0)
    assert rows["episode_count"]["difference"] is None  # 한쪽이 없으면 0으로 읽지 않는다
    assert rows["fatal_rate"]["remote"] is None
    assert "비동기" in table["note"]


# ---------------------------------------------------------------- OTel 이름

def test_otel_names_equal_installed_constants():
    names = otel_names()
    assert names["operation_attribute"] == semconv.GEN_AI_OPERATION_NAME == "gen_ai.operation.name"
    assert names["operation"] == {"invoke_agent": "invoke_agent", "execute_tool": "execute_tool"}
    assert names["evaluation"] == {
        "name": semconv.GEN_AI_EVALUATION_NAME,
        "score_value": semconv.GEN_AI_EVALUATION_SCORE_VALUE,
        "score_label": semconv.GEN_AI_EVALUATION_SCORE_LABEL,
        "explanation": semconv.GEN_AI_EVALUATION_EXPLANATION,
    }
    assert all(value.startswith("gen_ai.evaluation.") for value in names["evaluation"].values())
    assert "semantic-conventions-genai" in names["note"]
    assert "확인" in names["note"]
