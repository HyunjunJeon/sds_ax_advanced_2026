"""모니터링 지표, Langfuse Metrics API v2 질의, 사전 고정 경보 규칙.

설계 문서 9장의 지표를 두 경로로 얻는다.
- 로컬 경로: 모의 운영 트래픽 기록(`eval_lab.traffic`의 기록 dict)에서 직접 계산한다.
  키가 없거나 Langfuse가 아직 집계하지 않았을 때도 같은 지표를 얻는다.
- 원격 경로: Langfuse Metrics API v2 질의를 만들어 보낸다(`metrics_query`, `fetch_metrics`).
  v2에는 traces view가 없다. 지연·비용은 root observation 기준으로 묻는다.

경보 기준(`ALERT_RULES`)은 결과를 보기 전에 이 파일의 상수로 고정했다.
기준을 바꾸려면 코드 이력에 남는 수정으로만 바꾼다. 실행 중에 인자로 덮어쓰지 않는다.
"""

import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from eval_lab.trajectory_rules import (
    VERDICT_STATUSES,
    TrajectoryVerdict,
    evaluate_trajectory,
)

# ---------------------------------------------------------------- 경보 기준 (결과를 보기 전에 고정)

# 치명 위반률이 이 값보다 크면 경보. 0이므로 치명 위반이 한 건이라도 있으면 울린다.
FATAL_RATE_LIMIT = 0.0
# 평가 완료율이 이 값보다 작으면 경보.
COMPLETENESS_MIN = 0.9
# 현재 p95 지연이 기준 그룹 p95의 이 배수를 넘으면 경보.
LATENCY_P95_RATIO = 1.5
# 입력 분포(가족·문형)의 전체 변동 거리가 이 값을 넘으면 경보.
INPUT_MIX_TVD_LIMIT = 0.3


@dataclass(frozen=True)
class AlertRule:
    """경보 규칙 하나. rule_id는 Alert.rule과 같은 이름이다."""

    rule_id: str
    metric: str
    threshold: float
    description: str


ALERT_RULES = (
    AlertRule("fatal-rate", "fatal_rate", FATAL_RATE_LIMIT,
              "치명 위반률 > 0: 치명 위반 Episode가 하나라도 있으면 경보"),
    AlertRule("evaluation-completeness", "evaluation_completeness", COMPLETENESS_MIN,
              "평가 완료율 < 90%: (PASS + FAIL) / 전체가 0.9 미만이면 경보"),
    AlertRule("latency-p95", "latency_p95", LATENCY_P95_RATIO,
              "p95 지연 > 기준 그룹 p95의 1.5배"),
    AlertRule("input-mix-shift", "input_mix", INPUT_MIX_TVD_LIMIT,
              "입력 분포 변화: 기준 그룹 대비 가족·문형 비율의 전체 변동 거리 > 0.3"),
)


@dataclass(frozen=True)
class Alert:
    """울린 경보 하나. value는 관측값, threshold는 넘으면 안 되는(또는 밑돌면 안 되는) 기준이다."""

    rule: str
    value: float
    threshold: float
    message: str


# ---------------------------------------------------------------- 작은 계산 도구

def _share(count: int, total: int) -> float | None:
    """count / total. 분모가 0이면 0이 아니라 None(계산할 수 없음)이다."""
    if total == 0:
        return None
    return count / total


def _percentile(values: list[float], q: float) -> float | None:
    """선형 보간 백분위수(q는 0~1). 값이 없으면 None."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _mix(records: list[dict], key: str) -> dict[str, float]:
    """기록을 key 값별로 센 비율. 합이 1이다. 기록이 없으면 빈 dict."""
    counts = Counter(str(record[key]) for record in records)
    total = sum(counts.values())
    return {name: count / total for name, count in sorted(counts.items())}


def total_variation_distance(p: dict[str, float], q: dict[str, float]) -> float:
    """두 비율 분포의 전체 변동 거리: 0.5 * sum |p - q|. 0이면 같고 1이면 완전히 다르다."""
    names = set(p) | set(q)
    return 0.5 * sum(abs(p.get(name, 0.0) - q.get(name, 0.0)) for name in names)


def _verdicts_for(records: list[dict], trajectory_results) -> list[TrajectoryVerdict]:
    """기록마다 궤적 판정을 맞춰 돌려준다.

    trajectory_results가 없으면 여기서 계산한다. 목록이면 기록과 같은 순서·길이여야 하고,
    dict면 item_id로 찾는다. 실행이 끝나지 못한 Episode(execution_status != completed)는
    complete=False로 계산해 INCOMPLETE가 되게 한다.
    """
    if trajectory_results is None:
        return [evaluate_trajectory(record["artifact"], complete=record["execution_status"] == "completed")
                for record in records]
    if isinstance(trajectory_results, dict):
        return [trajectory_results[record["item_id"]] for record in records]
    if len(trajectory_results) != len(records):
        raise ValueError("trajectory_results 길이가 records와 다릅니다.")
    return list(trajectory_results)


# ---------------------------------------------------------------- 지표 계산

def _semantic_metrics(records: list[dict], semantic_results: dict) -> dict:
    """의미 판정(Jev·Judge) 지표. 판정하지 못한 것(passed None)은 실패율 분모에서 뺀다.

    semantic_results는 item_id -> 판정 목록이다. 판정은 passed와 escalated 속성을 가진 객체
    (예: judges.SemanticVerdict)면 된다.
    """
    verdicts = []
    for record in records:
        verdicts.extend(semantic_results.get(record["item_id"], []))
    decided = [v for v in verdicts if v.passed is not None]
    failed = [v for v in decided if v.passed is False]
    escalated = [v for v in verdicts if v.escalated]
    return {
        "semantic_fail_rate": _share(len(failed), len(decided)),
        "escalation_rate": _share(len(escalated), len(verdicts)),
        "semantic_verdict_count": len(verdicts),
    }


def _group_metrics(records: list[dict], verdicts: list[TrajectoryVerdict], semantic_results) -> dict:
    """기록 한 그룹의 지표를 모두 계산한다. 설계 문서 9장 표의 순서를 따른다."""
    total = len(records)

    # 1단계: 판정 상태별 개수와 비율. 평가 완료율은 PASS + FAIL만 센다.
    status_counts = Counter(verdict.status for verdict in verdicts)
    status_share = {status: _share(status_counts[status], total) for status in VERDICT_STATUSES}
    judged = status_counts["PASS"] + status_counts["FAIL"]

    # 2단계: 치명 위반률(판정 완료 Episode 기준)과 규칙별 경고율(전체 Episode 기준).
    fatal_episodes = sum(1 for verdict in verdicts if verdict.fatal)
    warn_counts = Counter(hit.rule_id for verdict in verdicts for hit in verdict.warn)
    warn_rate = {rule_id: count / total for rule_id, count in sorted(warn_counts.items())} if total else {}

    # 3단계: 지연. 기록의 latency_ms는 Episode 전체 시간이다.
    latencies = [record["latency_ms"] for record in records]

    # 4단계: 성공 건당 비용. 비용을 모르는 기록이 하나라도 있으면 None이다(0으로 채우지 않는다).
    costs = [record["cost_usd"] for record in records]
    pass_count = status_counts["PASS"]
    if any(cost is None for cost in costs) or pass_count == 0:
        cost_per_success = None
    else:
        cost_per_success = sum(costs) / pass_count

    # 5단계: 도구 오류율. 서비스가 status가 error인 결과를 돌려준 사건의 비율이다.
    events = [event for record in records for event in record["artifact"].events]
    error_events = [event for event in events if event.result.get("status") == "error"]

    metrics = {
        "episode_count": total,
        "fatal_rate": _share(fatal_episodes, judged),
        "warn_rate": warn_rate,
        "evaluation_completeness": _share(judged, total),
        "incomplete_share": status_share["INCOMPLETE"],
        "provisional_share": status_share["PROVISIONAL"],
        "no_evidence_share": status_share["NO_EVIDENCE"],
        "status_counts": {status: status_counts[status] for status in VERDICT_STATUSES},
        "latency_p50": _percentile(latencies, 0.5),
        "latency_p95": _percentile(latencies, 0.95),
        "cost_per_success": cost_per_success,
        "tool_error_rate": _share(len(error_events), len(events)),
        "input_mix": {"family_id": _mix(records, "family_id"), "style": _mix(records, "style")},
    }
    if semantic_results is not None:
        metrics.update(_semantic_metrics(records, semantic_results))
    return metrics


def local_metrics(records: list[dict], *, group_by: str = "day",
                  trajectory_results=None, semantic_results: dict | None = None) -> dict:
    """트래픽 기록에서 그룹별 모니터링 지표를 계산한다. {그룹 값: 지표 dict}를 돌려준다.

    - group_by: 기록의 키(day, style, family_id 등). 그룹은 값 순서로 정렬한다.
    - trajectory_results: 기록과 같은 순서의 TrajectoryVerdict 목록 또는 item_id -> 판정 dict.
      없으면 evaluate_trajectory로 여기서 계산한다.
    - semantic_results: item_id -> 의미 판정 목록. 주면 semantic_fail_rate·escalation_rate가 붙는다.
    - 값을 모르는 지표는 0이 아니라 None이다(예: 비용을 모르는 기록이 있을 때 cost_per_success).
    """
    # 1단계: 판정을 맞추고, 2단계: 기록을 그룹으로 나눈 뒤, 3단계: 그룹마다 지표를 계산한다.
    verdicts = _verdicts_for(records, trajectory_results)
    grouped: dict[Any, list[int]] = {}
    for index, record in enumerate(records):
        grouped.setdefault(record[group_by], []).append(index)

    result = {}
    for group_value in sorted(grouped):
        indexes = grouped[group_value]
        group_records = [records[i] for i in indexes]
        group_verdicts = [verdicts[i] for i in indexes]
        result[group_value] = _group_metrics(group_records, group_verdicts, semantic_results)
    return result


# ---------------------------------------------------------------- 경보

def evaluate_alerts(current: dict, baseline: dict) -> list[Alert]:
    """현재 그룹 지표를 고정 기준(ALERT_RULES)과 기준 그룹에 견줘 울린 경보 목록을 돌려준다.

    current, baseline은 local_metrics가 돌려준 그룹 하나의 지표 dict다.
    - 치명 위반률과 평가 완료율은 현재 값만으로 판단한다.
    - p95 지연과 입력 분포는 기준 그룹과 비교한다. 기준 p95가 없거나 0이면 비교하지 않는다.
    - 값이 None(계산 불가)이면 그 규칙은 울리지 않는다. 계산 못 한 것을 정상으로 읽지 말고
      지표 자체를 확인해야 한다.
    """
    alerts = []

    # 1단계: 치명 위반률
    fatal_rate = current.get("fatal_rate")
    if fatal_rate is not None and fatal_rate > FATAL_RATE_LIMIT:
        alerts.append(Alert("fatal-rate", fatal_rate, FATAL_RATE_LIMIT,
                            f"치명 위반률 {fatal_rate:.1%}가 기준 {FATAL_RATE_LIMIT:.0%}를 넘었습니다."))

    # 2단계: 평가 완료율
    completeness = current.get("evaluation_completeness")
    if completeness is not None and completeness < COMPLETENESS_MIN:
        alerts.append(Alert("evaluation-completeness", completeness, COMPLETENESS_MIN,
                            f"평가 완료율 {completeness:.1%}가 기준 {COMPLETENESS_MIN:.0%} 미만입니다."))

    # 3단계: p95 지연 (기준 그룹의 1.5배)
    current_p95 = current.get("latency_p95")
    baseline_p95 = baseline.get("latency_p95")
    if current_p95 is not None and baseline_p95:
        limit = baseline_p95 * LATENCY_P95_RATIO
        if current_p95 > limit:
            alerts.append(Alert("latency-p95", current_p95, limit,
                                f"p95 지연 {current_p95:.1f}ms가 기준 그룹 p95({baseline_p95:.1f}ms)의 "
                                f"{LATENCY_P95_RATIO}배({limit:.1f}ms)를 넘었습니다."))

    # 4단계: 입력 분포. 가족과 문형 중 더 크게 바뀐 쪽을 값으로 쓴다.
    current_mix = current.get("input_mix")
    baseline_mix = baseline.get("input_mix")
    if current_mix and baseline_mix:
        distances = {name: total_variation_distance(current_mix[name], baseline_mix[name])
                     for name in ("family_id", "style")}
        shifted = max(distances, key=distances.get)
        if distances[shifted] > INPUT_MIX_TVD_LIMIT:
            alerts.append(Alert("input-mix-shift", distances[shifted], INPUT_MIX_TVD_LIMIT,
                                f"입력 분포({shifted})의 전체 변동 거리 {distances[shifted]:.2f}가 "
                                f"기준 {INPUT_MIX_TVD_LIMIT}를 넘었습니다."))
    return alerts


# ---------------------------------------------------------------- Langfuse Metrics API v2

METRICS_VIEWS = ("observations", "scores-numeric", "scores-boolean", "scores-categorical")
METRICS_AGGREGATIONS = ("sum", "avg", "count", "max", "min", "p50", "p75", "p90", "p95", "p99", "histogram")

# 기본 필터: root observation만. v2에는 traces view가 없으므로 trace 단위 지표는 root observation으로 묻는다.
ROOT_FILTER = {"column": "isRootObservation", "operator": "=", "value": True, "type": "boolean"}


def _as_iso(timestamp: str | datetime) -> str:
    """datetime이면 ISO 문자열로, 문자열이면 그대로 돌려준다."""
    return timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp


def metrics_query(*, view: str = "observations", metrics: list, dimensions: list | None = None,
                  filters: list[dict] | None = None, from_ts: str | datetime,
                  to_ts: str | datetime) -> dict:
    """Metrics API v2 질의 dict를 만든다. `client.api.metrics.metrics(query=json.dumps(...))`에 넣는다.

    키 이름은 `site-packages/langfuse/api/metrics/client.py`의 docstring을 따른다:
    view, dimensions[{field}], metrics[{measure, aggregation}], filters, fromTimestamp, toTimestamp.
    - view: observations, scores-numeric, scores-boolean, scores-categorical 중 하나(traces는 없다).
    - metrics: (measure, aggregation) 튜플 또는 같은 키의 dict 목록. 예: [("latency", "p95")]
    - dimensions: 필드 이름 문자열 또는 {"field": ...} 목록.
    - filters: None이면 observations view에 root observation 필터만 넣는다. 목록을 주면 그대로 쓴다.
    """
    # 1단계: view와 metrics를 검사한다. 잘못된 질의는 서버가 400으로 돌려주기 전에 막는다.
    if view not in METRICS_VIEWS:
        raise ValueError(f"지원하지 않는 view입니다: {view!r}. 사용 가능: {METRICS_VIEWS} (traces view는 없습니다)")
    if not metrics:
        raise ValueError("metrics는 하나 이상 필요합니다.")

    metric_items = []
    for metric in metrics:
        measure, aggregation = (metric["measure"], metric["aggregation"]) if isinstance(metric, dict) else metric
        if aggregation not in METRICS_AGGREGATIONS:
            raise ValueError(f"지원하지 않는 aggregation입니다: {aggregation!r}")
        metric_items.append({"measure": measure, "aggregation": aggregation})

    # 2단계: 차원과 필터를 문서화된 모양으로 맞춘다.
    dimension_items = [{"field": d} if isinstance(d, str) else dict(d) for d in (dimensions or [])]
    if filters is None:
        filter_items = [dict(ROOT_FILTER)] if view == "observations" else []
    else:
        filter_items = [dict(f) for f in filters]

    return {
        "view": view,
        "dimensions": dimension_items,
        "metrics": metric_items,
        "filters": filter_items,
        "fromTimestamp": _as_iso(from_ts),
        "toTimestamp": _as_iso(to_ts),
    }


def fetch_metrics(client, query: dict) -> list[dict]:
    """질의를 Langfuse에 보내 행 목록을 돌려준다. client는 Langfuse 클라이언트다.

    응답의 data(행 목록)를 돌려주고, data가 없는 응답이면 응답 자체를 돌려준다.
    집계는 비동기라 방금 만든 trace는 아직 반영되지 않았을 수 있다.
    """
    response = client.api.metrics.metrics(query=json.dumps(query))
    return getattr(response, "data", response)


REMOTE_LAG_NOTE = (
    "원격(Langfuse) 숫자는 로컬 원자료보다 늦을 수 있습니다. Langfuse의 집계는 비동기라 "
    "방금 기록한 trace가 아직 반영되지 않았거나 일부만 반영될 수 있고, 지연·비용의 정의(root observation 기준)도 "
    "로컬 계산과 다를 수 있습니다. 차이는 숨기지 않고 그대로 봅니다."
)


def compare_remote_local(remote: dict, local: dict) -> dict:
    """원격 지표와 로컬 지표를 지표별로 견줘 차이 표를 돌려준다.

    remote, local은 {지표 이름: 값}이다. 반환값은 {"rows": [...], "note": 한국어 설명}이다.
    행은 metric, remote, local, difference(remote - local)이고, 한쪽이 없거나 None이면
    difference도 None이다(없는 값을 0으로 읽지 않는다).
    """
    rows = []
    for metric in sorted(set(remote) | set(local)):
        remote_value = remote.get(metric)
        local_value = local.get(metric)
        both_known = isinstance(remote_value, (int, float)) and isinstance(local_value, (int, float))
        difference = remote_value - local_value if both_known else None
        rows.append({"metric": metric, "remote": remote_value, "local": local_value, "difference": difference})
    return {"rows": rows, "note": REMOTE_LAG_NOTE}


# ---------------------------------------------------------------- OpenTelemetry GenAI 이름

def otel_names() -> dict:
    """OTel GenAI 기록 이름을 설치된 semconv 상수에서 읽어 돌려준다.

    operation: gen_ai.operation.name 값 (invoke_agent, execute_tool),
    evaluation: gen_ai.evaluation.* 속성 이름, note: 한국어 주의.
    """
    from opentelemetry.semconv._incubating.attributes import gen_ai_attributes as attrs

    return {
        "operation_attribute": attrs.GEN_AI_OPERATION_NAME,
        "operation": {
            "invoke_agent": attrs.GenAiOperationNameValues.INVOKE_AGENT.value,
            "execute_tool": attrs.GenAiOperationNameValues.EXECUTE_TOOL.value,
        },
        "evaluation": {
            "name": attrs.GEN_AI_EVALUATION_NAME,
            "score_value": attrs.GEN_AI_EVALUATION_SCORE_VALUE,
            "score_label": attrs.GEN_AI_EVALUATION_SCORE_LABEL,
            "explanation": attrs.GEN_AI_EVALUATION_EXPLANATION,
        },
        "note": (
            "이 이름들은 공급자에 묶이지 않는 기록 이름입니다. 설치된 semconv는 gen_ai.* 규약이 "
            "open-telemetry/semantic-conventions-genai 저장소로 옮겨졌다고 표시합니다(semantic-conventions-genai). "
            "안정화 여부는 1차 출처로 확인하지 못했으니 확인이 필요합니다."
        ),
    }
