"""온라인 평가: trace 선정, root observation에서 Artifact 복원, 일괄 채점, 점수 붙이기, 사람 검수 대기열.

운영 trace에는 정답이 없다(DESIGN 8절). 그래서 이 모듈의 채점은 정답 없이 되는 것만 쓴다.
- 궤적 규칙(`trajectory_rules.evaluate_trajectory`): 치명·경고 위반 수, 차단 시도 수, 판정 상태 5종.
- 의미 판정(`judges.judge_semantics`, reference=None): Jev 먼저, 불확실하면 Judge.

흐름은 이렇다.

    records(또는 Langfuse root observation) -> select_traces -> 채점 -> push_scores -> enqueue_for_review

Langfuse v4부터 trace 입출력은 root observation에서 온다. Episode가 끝날 때 root observation output에
JSON 요약을 넣어 두므로(`episodes.episode_summary`), 평가기는 그 요약만으로 Artifact를 다시 만든다.
요약이 비었거나 잘렸으면 Artifact를 지어내지 않고 `NO_EVIDENCE` 또는 `INCOMPLETE`로 남긴다.

이 모듈은 직접 네트워크를 쓰지 않는다. Langfuse 클라이언트는 호출하는 쪽이 넘긴다.
"""
from __future__ import annotations

import json
import math
import random
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langfuse import Evaluation, EvaluatorInputs
from langfuse.api import ConfigCategory, ScoreConfigDataType
from langfuse.api.annotation_queues.types import AnnotationQueueObjectType
from langfuse.api.evaluation_commons.types import (
    EvaluationRuleBooleanFilterOperator,
    EvaluationRuleFilter_Boolean,
    EvaluationRuleFilter_StringOptions,
    EvaluationRuleOptionsFilterOperator,
)
from langfuse.api.evaluation_rules.types import EvaluationRuleEvaluatorAssignmentInput

from eval_lab.contracts import Artifact
from eval_lab.decisions import DecisionBackend
from eval_lab.episodes import SUMMARY_SCHEMA, artifact_from_summary, episode_summary
from eval_lab.judges import judge_semantics
from eval_lab.trajectory_rules import evaluate_trajectory, run_rules

# Episode의 root observation 이름. episodes.execute_episode가 이 이름으로 root를 연다.
ROOT_OBSERVATION_NAME = "episode"

# 신호 기반 선정의 우선순위. 앞쪽일수록 먼저 뽑는다.
SIGNAL_PRIORITY = ("tool_error", "model_error", "escalated", "latency", "cost", "rule")

# 지연·비용 상위로 보는 비율. 기록의 10%(올림, 최소 1건)를 상위로 본다.
TOP_FRACTION = 0.1

# artifact_from_summary가 읽는 요약 필드. 하나라도 없으면 요약이 잘렸거나 다른 형식으로 본다.
SUMMARY_FIELDS = ("artifact_id", "scenario_id", "release", "trial", "status", "error_type", "request",
                  "last_request", "turns", "events", "gate_events", "initial_state", "final_state",
                  "response", "usage", "episode_id", "elapsed_seconds")

# 이 모듈이 만드는 점수 이름. 모니터링과 노트북이 같은 이름으로 읽는다.
TRAJECTORY_SCORE_NAMES = ("trajectory_status", "fatal_count", "warn_count", "blocked_attempts")


# ---------------------------------------------------------------- 1. 표본 선정

@dataclass(frozen=True)
class Selection:
    """선정된 기록 하나. record_index는 입력 records 목록의 위치, reason은 뽑힌 이유(한국어)다."""

    record_index: int
    trace_id: str | None
    reason: str


def request_shape(record: dict) -> tuple[bool, str, str]:
    """기록의 요청 모양을 (주문 번호 유무, 문형, 가족 ID)로 돌려준다. 새로움 전략과 Golden 모양 비교에 쓴다."""
    artifact: Artifact = record["artifact"]
    first_request = artifact.initial_request or artifact.request
    has_order_id = first_request.order_id is not None
    return (has_order_id, record["style"], record["family_id"])


def _make_selection(records: list[dict], index: int, reason: str) -> Selection:
    """records[index]로 Selection을 만든다. trace_id가 없는 기록(Langfuse 없이 돌린 것)은 None으로 둔다."""
    return Selection(record_index=index, trace_id=records[index].get("trace_id"), reason=reason)


def _round_robin(groups: dict[Any, list[int]], k: int) -> list[tuple[Any, int]]:
    """층 키 순서대로 한 건씩 돌아가며 k건을 고른다. (층 키, 기록 위치) 쌍을 돌려준다."""
    keys = sorted(groups)
    queues = {key: list(groups[key]) for key in keys}
    picked: list[tuple[Any, int]] = []
    while len(picked) < k and any(queues.values()):
        for key in keys:
            if queues[key] and len(picked) < k:
                picked.append((key, queues[key].pop(0)))
    return picked


def _tool_error_events(artifact: Artifact) -> list[str]:
    """서비스가 error 또는 denied로 답한 사건의 도구 이름. 정상 거절(allowed=False)은 ok 응답이라 세지 않는다."""
    return [event.tool for event in artifact.events if event.result.get("status") in {"error", "denied"}]


def _top_threshold(values: list[float | None]) -> float | None:
    """상위 TOP_FRACTION(올림, 최소 1건)에 드는 경계값. 0 이하와 None은 제외한다. 값이 없으면 None."""
    positives = sorted((v for v in values if v is not None and v > 0), reverse=True)
    if not positives:
        return None
    top_count = max(1, math.ceil(len(values) * TOP_FRACTION))
    return positives[min(top_count, len(positives)) - 1]


def _signals_of(record: dict, latency_cut: float | None, cost_cut: float | None) -> list[tuple[str, str]]:
    """기록 하나가 가진 신호를 SIGNAL_PRIORITY 순서로 (신호 이름, 설명) 목록으로 돌려준다."""
    artifact: Artifact = record["artifact"]
    found: list[tuple[str, str]] = []

    # 1) 도구 오류 결과
    tool_errors = _tool_error_events(artifact)
    if tool_errors:
        found.append(("tool_error", f"도구 오류 결과 {len(tool_errors)}건({', '.join(sorted(set(tool_errors)))})"))

    # 2) 모델 오류 또는 실행 오류
    if artifact.execution_status != "completed" or artifact.error_type:
        found.append(("model_error", f"실행 상태 {artifact.execution_status}, 오류 {artifact.error_type}"))

    # 3) 에스컬레이션 응답
    if artifact.response is not None and artifact.response.kind == "escalated":
        found.append(("escalated", "응답 유형 escalated"))

    # 4) 지연 상위, 5) 비용 상위
    latency = record.get("latency_ms")
    if latency_cut is not None and latency is not None and latency >= latency_cut:
        found.append(("latency", f"지연 상위({latency:.0f}ms)"))
    cost = record.get("cost_usd")
    if cost_cut is not None and cost is not None and cost >= cost_cut:
        found.append(("cost", f"비용 상위(${cost:.4f})"))

    # 6) 궤적 규칙 위반. 경고뿐 아니라 치명도 여기에 모은다(치명이면 설명에 따로 적는다).
    hits = run_rules(artifact)
    if hits:
        fatal_count = sum(1 for hit in hits if hit.severity == "fatal")
        rule_ids = sorted({hit.rule_id for hit in hits})
        found.append(("rule", f"규칙 위반 {len(hits)}건(치명 {fatal_count}): {', '.join(rule_ids)}"))
    return found


def select_traces(records: list[dict], strategy: str, k: int, *, seed: int,
                  golden_shapes: set[tuple] | None = None) -> list[Selection]:
    """records에서 사람이 볼 trace k건을 전략대로 고른다. 같은 입력과 seed면 항상 같은 결과다.

    strategy:
    - 'random': seed 고정 무작위. 놓치는 것: 드문 문제. 전체의 2%만 문제라면 k건 중 평균 0.02k건만 잡힌다.
    - 'stratified': (family_id, day) 층마다 돌아가며 한 건씩. 놓치는 것: 층 안의 문제 발생률 차이.
      층은 우리가 아는 분류라서, 분류에 없는 새 유형은 층에 숨는다. 기록이 적은 층도 같은 몫을 받는다.
    - 'signal': 도구 오류, 모델 오류, escalated, 지연 상위, 비용 상위, 규칙 위반 순서의 우선순위.
      놓치는 것: 신호 없이 조용히 틀린 trace(예: 기록에 없는 말을 하는 문장). 신호가 없는 기록은
      뽑지 않으므로 k건보다 적게 돌려줄 수 있다. 전체 비율을 말할 근거로 쓰면 안 된다(편향된 표본).
    - 'novelty': 요청 모양(request_shape)이 golden_shapes에 없는 것. 층(모양)마다 돌아가며 한 건씩.
      놓치는 것: Golden에 있는 모양에서 생긴 회귀. golden_shapes가 필수이며 없으면 ValueError다.

    k가 후보보다 크면 후보 수만큼만 돌려준다. 각 Selection.reason에 뽑힌 이유가 있다.
    """
    if k < 0:
        raise ValueError("k는 0 이상이어야 합니다.")
    rng = random.Random(seed)

    # 1단계: 무작위. 위치를 seed로 섞어 앞에서 k건을 취한다.
    if strategy == "random":
        positions = rng.sample(range(len(records)), min(k, len(records)))
        return [_make_selection(records, index, f"무작위 추출(seed={seed})") for index in positions]

    # 2단계: 층화. 층 안의 순서를 seed로 섞고 층을 돌며 한 건씩 뽑는다.
    if strategy == "stratified":
        groups: dict[tuple[str, int], list[int]] = defaultdict(list)
        for index, record in enumerate(records):
            groups[(record["family_id"], record["day"])].append(index)
        for members in groups.values():
            rng.shuffle(members)
        picked = _round_robin(groups, k)
        return [_make_selection(records, index, f"층화: {family_id}, {day}일차 층에서 추출")
                for (family_id, day), index in picked]

    # 3단계: 신호 기반. 우선순위가 높은 신호부터, 같은 순위면 신호가 많은 것부터, 그래도 같으면 입력 순서.
    if strategy == "signal":
        latency_cut = _top_threshold([record.get("latency_ms") for record in records])
        cost_cut = _top_threshold([record.get("cost_usd") for record in records])
        ranked: list[tuple[int, int, int, list[tuple[str, str]]]] = []
        for index, record in enumerate(records):
            signals = _signals_of(record, latency_cut, cost_cut)
            if signals:
                top_priority = SIGNAL_PRIORITY.index(signals[0][0])
                ranked.append((top_priority, -len(signals), index, signals))
        ranked.sort(key=lambda row: row[:3])
        return [_make_selection(records, index, "신호: " + "; ".join(text for _, text in signals))
                for _, _, index, signals in ranked[:k]]

    # 4단계: 새로움. 요청 모양이 Golden에 없는 기록만 모양별로 돌려 뽑는다.
    if strategy == "novelty":
        if golden_shapes is None:
            raise ValueError("novelty 전략에는 golden_shapes가 필요합니다. 비교할 Golden이 없으면 새로움을 말할 수 없습니다.")
        shape_groups: dict[tuple, list[int]] = defaultdict(list)
        for index, record in enumerate(records):
            shape = request_shape(record)
            if shape not in golden_shapes:
                shape_groups[shape].append(index)
        for members in shape_groups.values():
            rng.shuffle(members)
        picked = _round_robin(shape_groups, k)
        return [_make_selection(records, index, f"새로운 요청 모양 {shape}: Golden에 없음")
                for shape, index in picked]

    raise ValueError(f"알 수 없는 전략입니다: {strategy!r} (random, stratified, signal, novelty)")


# ---------------------------------------------------------------- 2. root observation에서 Artifact 복원

def _read_field(source: Any, name: str) -> Any:
    """dict 또는 객체에서 필드를 읽는다. 없으면 None."""
    if isinstance(source, dict):
        return source.get(name)
    return getattr(source, name, None)


def _rebuild(observation: Any) -> tuple[Artifact | None, str, bool]:
    """(Artifact 또는 None, 이유, output이 비어 있었는지)를 돌려준다.

    observation은 Langfuse observation 객체·dict이거나 episode_summary가 만든 요약 dict(또는 그 JSON 문자열) 자체다.
    """
    # 1단계: 요약 본문을 꺼낸다. 요약 dict가 바로 오면 그대로 쓴다.
    if isinstance(observation, str) or (isinstance(observation, dict) and "schema" in observation):
        output = observation
    else:
        parent_id = _read_field(observation, "parent_observation_id")
        if parent_id is not None:
            return None, f"root observation이 아닙니다(부모 {parent_id}).", False
        output = _read_field(observation, "output")

    # 2단계: 비었으면 근거가 없는 것이다.
    if output is None or output == "" or output == {}:
        return None, "root observation output이 비어 있습니다.", True

    # 3단계: 문자열이면 JSON으로 읽는다. 잘린 문자열은 여기서 걸린다.
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            return None, "output이 JSON으로 읽히지 않습니다(잘렸을 수 있습니다).", False
    if not isinstance(output, dict):
        return None, f"output이 객체가 아닙니다({type(output).__name__}).", False

    # 4단계: 형식과 필드를 확인한다. 하나라도 없으면 지어내지 않는다.
    if output.get("schema") != SUMMARY_SCHEMA:
        return None, f"요약 형식이 다릅니다(schema={output.get('schema')!r}).", False
    missing = [name for name in SUMMARY_FIELDS if name not in output]
    if missing:
        return None, f"요약에 필드가 없습니다: {', '.join(missing)}", False

    # 5단계: 값 검증까지 통과해야 Artifact다.
    try:
        return artifact_from_summary(output), "", False
    except (KeyError, TypeError, ValueError) as error:
        return None, f"요약을 Artifact로 읽지 못했습니다({type(error).__name__}).", False


def artifact_from_root_observation(observation: Any) -> tuple[Artifact | None, str]:
    """root observation output(Episode 요약)에서 Artifact를 다시 만든다.

    성공하면 (Artifact, ""). output이 비었거나 잘렸거나 필드가 모자라거나 형식이 다르면
    (None, 이유)를 돌려준다. 빠진 값을 채워 가짜 Artifact를 만들지 않는다.
    model_events는 요약에 없으므로 빈 목록이다.
    """
    artifact, reason, _ = _rebuild(observation)
    return artifact, reason


# ---------------------------------------------------------------- 3. 온라인 평가기

def _missing_evidence_evaluation(reason: str, was_empty: bool) -> Evaluation:
    """Artifact를 못 만들었을 때의 trajectory_status. 비었으면 NO_EVIDENCE, 그 밖에는 INCOMPLETE. PASS는 없다."""
    status = "NO_EVIDENCE" if was_empty else "INCOMPLETE"
    return Evaluation(name="trajectory_status", value=status, data_type="CATEGORICAL", comment=reason)


def _rule_summary(hits: list) -> str:
    """위반 목록을 한 줄 설명으로 줄인다."""
    return "; ".join(f"{hit.rule_id}@{hit.event_id}" for hit in hits)


def _trajectory_evaluations(artifact: Artifact) -> list[Evaluation]:
    """궤적 규칙 판정을 점수 4개로 바꾼다."""
    verdict = evaluate_trajectory(artifact)
    return [
        Evaluation(name="trajectory_status", value=verdict.status, data_type="CATEGORICAL", comment=verdict.reason),
        Evaluation(name="fatal_count", value=len(verdict.fatal), data_type="NUMERIC",
                   comment=_rule_summary(verdict.fatal) or "치명 위반 없음"),
        Evaluation(name="warn_count", value=len(verdict.warn), data_type="NUMERIC",
                   comment=_rule_summary(verdict.warn) or "경고 없음"),
        Evaluation(name="blocked_attempts", value=verdict.blocked_attempts, data_type="NUMERIC",
                   comment="게이트가 차단하거나 확인을 요청한 시도 수"),
    ]


def online_evaluators(*, decider: DecisionBackend, judge_model: BaseChatModel,
                      mode: str = "cascade") -> list[Callable[..., Any]]:
    """`batch_evaluate`(SDK `run_batched_evaluation`과 같은 EvaluatorFunction 형식)에 넘길 평가기 2개를 만든다.

    1. 궤적 평가기: trajectory_status, fatal_count, warn_count, blocked_attempts.
       Artifact를 못 만들면 trajectory_status만 NO_EVIDENCE 또는 INCOMPLETE로 낸다(개수 점수는 내지 않는다.
       모르는 값을 0으로 쓰지 않기 위해서다).
    2. 의미 평가기: JEV_QUESTIONS 질문마다 PASS / FAIL / UNDECIDED 점수 하나.
       정답이 없는 운영이라 reference=None이다. Artifact가 없거나 응답이 없으면 아무 점수도 내지 않는다.
       Judge를 부르는 것은 이 평가기뿐이다.
    """

    def trajectory_evaluator(*, input: Any, output: Any, expected_output: Any = None,
                             metadata: dict | None = None, **kwargs: Any) -> list[Evaluation]:
        """궤적 규칙 평가기. 입력은 mapper가 넘긴 root observation output(Episode 요약)이다."""
        artifact, reason, was_empty = _rebuild(output)
        if artifact is None:
            return [_missing_evidence_evaluation(reason, was_empty)]
        return _trajectory_evaluations(artifact)

    def semantic_evaluator(*, input: Any, output: Any, expected_output: Any = None,
                           metadata: dict | None = None, **kwargs: Any) -> list[Evaluation]:
        """의미 평가기. Code가 이미 본 구조화 필드가 아니라 자유 문장의 의미만 판정한다."""
        artifact, _, _ = _rebuild(output)
        if artifact is None or artifact.response is None:
            return []
        verdicts = judge_semantics(artifact, decider=decider, judge_model=judge_model, mode=mode, reference=None)
        evaluations = []
        for verdict in verdicts:
            value = "UNDECIDED" if verdict.passed is None else ("PASS" if verdict.passed else "FAIL")
            evaluations.append(Evaluation(
                name=verdict.name, value=value, data_type="CATEGORICAL", comment=verdict.reason,
                metadata={"stage": verdict.stage, "escalated": verdict.escalated,
                          "probability": verdict.probability, "confidence": verdict.confidence}))
        return evaluations

    return [trajectory_evaluator, semantic_evaluator]


# ---------------------------------------------------------------- 4. 일괄 채점

def root_filter(environment: str) -> str:
    """환경이 environment이고 이름이 root observation(episode)인 observation만 고르는 필터 JSON.

    형식은 Langfuse 관측 목록 API의 필터 배열(type, column, operator, value)이다.
    각 조건은 AND로 묶인다. environment는 Langfuse 환경 형식(소문자·숫자·-·_)이어야 한다.
    """
    conditions = [
        {"type": "string", "column": "environment", "operator": "=", "value": environment},
        {"type": "string", "column": "name", "operator": "=", "value": ROOT_OBSERVATION_NAME},
    ]
    return json.dumps(conditions)


def observation_mapper(*, item: Any, **kwargs: Any) -> EvaluatorInputs:
    """observation 하나를 평가기 입력으로 바꾼다. output이 Episode 요약이다. 정답은 없다(expected_output=None)."""
    return EvaluatorInputs(
        input=_read_field(item, "input"),
        output=_read_field(item, "output"),
        expected_output=None,
        metadata={
            "observation_id": _read_field(item, "id"),
            "trace_id": _read_field(item, "trace_id"),
            "parent_observation_id": _read_field(item, "parent_observation_id"),
            "release": _read_field(item, "version"),
            "environment": _read_field(item, "environment"),
        },
    )


# Langfuse v2 관측 API에서 읽을 칸. 기본 응답에는 input/output이 없어 io를 함께 요청한다.
# v2는 input/output을 언제나 JSON 문자열로 준다(parseIoAsJson은 2026-11-05 서버가 400으로 거절). _rebuild가 문자열을 읽는다.
V2_OBSERVATION_FIELDS = "core,basic,io"
_V2_PAGE_LIMIT = 50


@dataclass
class BatchResult:
    """batch_evaluate의 결과. 칸 이름은 Langfuse SDK의 BatchEvaluationResult와 같게 두었다(노트북이 이 이름으로 읽는다)."""

    total_items_fetched: int = 0
    total_items_processed: int = 0
    total_items_failed: int = 0
    total_scores_created: int = 0
    total_evaluations_failed: int = 0
    completed: bool = False
    has_more_items: bool = False
    resume_token: str | None = None
    duration_seconds: float = 0.0
    failed_item_ids: list[str] = field(default_factory=list)
    error_summary: dict[str, int] = field(default_factory=dict)
    item_evaluations: dict[str, list[Evaluation]] = field(default_factory=dict)


def _score_kwargs(item: Any, evaluation: Evaluation) -> dict:
    """평가 하나를 그 observation에 붙이는 create_score 인자. SDK의 observation 범위 점수와 같은 칸이다."""
    return {
        "observation_id": _read_field(item, "id"),
        "trace_id": _read_field(item, "trace_id"),
        "name": evaluation.name,
        "value": evaluation.value,
        "comment": evaluation.comment,
        "metadata": evaluation.metadata or {},
        "data_type": evaluation.data_type,
        "config_id": evaluation.config_id,
    }


def count_observations(client: Any, filter_json: str, *, cap: int = 10_000) -> int:
    """filter_json에 걸리는 observation 수를 v2 관측 API로 센다. v2에는 전체 개수 칸이 없어 쪽을 넘기며 센다.

    cap에서 멈춘다(그 이상이면 cap을 돌려준다). 집계 지연 때문에 방금 기록한 것은 아직 안 세일 수 있다.
    """
    counted, cursor = 0, None
    while counted < cap:
        response = client.api.observations.get_many(fields="core", limit=min(100, cap - counted), cursor=cursor,
                                                    filter=filter_json)
        counted += len(response.data)
        cursor = getattr(response.meta, "cursor", None) or None
        if not response.data or cursor is None:
            break
    return counted


def wait_for_observations(client: Any, filter_json: str, *, expected: int, timeout_s: float = 180.0,
                          interval_s: float = 10.0) -> tuple[int, float]:
    """filter_json에 걸리는 observation이 expected건이 될 때까지 기다린다. (센 수, 기다린 초)를 돌려준다.

    Langfuse의 집계는 비동기라 방금 기록한 trace가 바로 읽히지 않는다(2026-11-05 1회 관찰: 기록 직후 0건, 몇 분 뒤 전부).
    timeout_s가 지나면 그때까지 센 수를 그대로 돌려준다. 모자란 수를 채우거나 숨기지 않는다.
    """
    started = time.monotonic()
    counted = count_observations(client, filter_json, cap=max(expected, 1))
    while counted < expected and time.monotonic() - started < timeout_s:
        time.sleep(interval_s)
        counted = count_observations(client, filter_json, cap=max(expected, 1))
    return counted, round(time.monotonic() - started, 1)


def batch_evaluate(client: Any, *, evaluators: list[Callable[..., Any]], environment: str,
                   max_items: int, resume_from: str | None = None, filter_json: str | None = None) -> BatchResult:
    """Langfuse에 쌓인 root observation(Episode)을 읽어 평가기를 돌리고, 점수를 그 observation에 붙인다.

    계약은 SDK의 `run_batched_evaluation(scope="observations")`과 같다: observation_mapper → 평가기 → create_score.
    그 함수를 부르지 않고 직접 도는 이유: 설치된 SDK(langfuse 4.15.1)의 run_batched_evaluation은 v1 관측 API
    (GET /api/public/observations)로 항목을 읽는데, Langfuse Cloud가 이 API를 2026-11-16에 없앤다
    (2026-11-05 jp.cloud.langfuse.com 응답의 Sunset 헤더와 본문 _deprecation.sunsetAt). 대체는 v2 관측 API다.

    - 읽는 곳: GET /api/public/v2/observations, fields=core,basic,io. 필터는 filter_json이 없으면 root_filter(environment)다.
      filter_json은 같은 형식의 조건 배열이다(예: root_filter에 traceId "any of" 조건을 더한 것).
    - max_items로 한 번에 채점할 양(=비용)을 제한한다. 다 읽기 전에 멈추면 resume_token(v2 cursor)이 남고,
      그 값을 resume_from에 넘겨 이어 간다.
    - 평가기 하나가 예외를 내도 배치는 계속하고 total_evaluations_failed와 error_summary에 센다.
      mapper가 실패한 항목은 total_items_failed와 failed_item_ids에 남긴다. 실패를 지우지 않는다.
    - 집계 지연: 방금 기록한 trace는 아직 읽히지 않을 수 있다. total_items_fetched가 0이면 1~2분 뒤 다시 부른다.
    """
    if max_items < 1:
        raise ValueError("max_items는 1 이상이어야 합니다.")
    effective_filter = filter_json if filter_json is not None else root_filter(environment)
    started = time.monotonic()
    result = BatchResult()
    errors: Counter = Counter()
    cursor = resume_from
    next_cursor: str | None = None

    while result.total_items_fetched < max_items:
        # 1단계: 한 쪽을 읽는다. 남은 양보다 많이 읽지 않으므로 쪽 중간에서 멈추는 일이 없다.
        limit = min(_V2_PAGE_LIMIT, max_items - result.total_items_fetched)
        response = client.api.observations.get_many(fields=V2_OBSERVATION_FIELDS, limit=limit, cursor=cursor,
                                                    filter=effective_filter)
        items = list(response.data)
        next_cursor = getattr(response.meta, "cursor", None) or None

        for item in items:
            result.total_items_fetched += 1
            item_id = str(_read_field(item, "id"))
            # 2단계: 평가기 입력을 만든다. 여기서 실패하면 그 항목은 채점하지 못한 것으로 남긴다.
            try:
                inputs = observation_mapper(item=item)
            except Exception as error:  # noqa: BLE001 - 어떤 실패든 항목 단위로 남기고 배치를 계속한다
                result.total_items_failed += 1
                result.failed_item_ids.append(item_id)
                errors[type(error).__name__] += 1
                continue
            # 3단계: 평가기마다 돌리고, 낸 평가를 그 observation에 점수로 붙인다.
            evaluations: list[Evaluation] = []
            for evaluator in evaluators:
                try:
                    produced = list(evaluator(input=inputs.input, output=inputs.output,
                                              expected_output=inputs.expected_output, metadata=inputs.metadata))
                except Exception as error:  # noqa: BLE001 - SDK와 같게 평가기 실패는 세고 계속한다
                    result.total_evaluations_failed += 1
                    errors[type(error).__name__] += 1
                    continue
                for evaluation in produced:
                    client.create_score(**_score_kwargs(item, evaluation))
                    result.total_scores_created += 1
                evaluations.extend(produced)
            result.item_evaluations[item_id] = evaluations
            result.total_items_processed += 1

        # 4단계: 다음 쪽이 없으면 끝이다.
        if not items or next_cursor is None:
            next_cursor = None
            break
        cursor = next_cursor

    result.has_more_items = next_cursor is not None
    result.resume_token = next_cursor
    result.completed = next_cursor is None
    result.error_summary = dict(errors)
    result.duration_seconds = round(time.monotonic() - started, 3)
    flush = getattr(client, "flush", None)
    if flush is not None:
        flush()
    return result


# ---------------------------------------------------------------- 5. 키 없는 경로

def evaluate_records_locally(records: list[dict], *, decider: DecisionBackend, judge_model: BaseChatModel,
                             mode: str = "cascade") -> list[dict]:
    """로컬 기록에 온라인 평가기를 똑같이 돌린다(Langfuse 키가 없는 경로).

    기록의 Artifact를 episode_summary로 바꿔 평가기에 넣으므로 Langfuse 경로와 같은 코드 길을 지난다.
    점수 한 건이 dict 한 줄이다: record_index, item_id, trace_id, observation_id, name, value,
    data_type, comment, metadata. push_scores에 그대로 넘길 수 있다.
    """
    evaluators = online_evaluators(decider=decider, judge_model=judge_model, mode=mode)
    rows: list[dict] = []
    for index, record in enumerate(records):
        summary = episode_summary(record["artifact"])
        for evaluator in evaluators:
            for evaluation in evaluator(input=None, output=summary, expected_output=None, metadata=None):
                rows.append({
                    "record_index": index,
                    "item_id": record.get("item_id"),
                    "trace_id": record.get("trace_id"),
                    "observation_id": record.get("observation_id"),
                    "name": evaluation.name,
                    "value": evaluation.value,
                    "data_type": evaluation.data_type,
                    "comment": evaluation.comment,
                    "metadata": evaluation.metadata,
                })
    return rows


# ---------------------------------------------------------------- 6. 점수 붙이기와 사람 검수

def push_scores(client: Any, scores: list[dict]) -> dict:
    """점수 dict 목록을 `client.create_score`로 Langfuse에 붙인다. observation_id가 있으면 그 observation에 붙는다.

    trace_id가 없는 점수(Langfuse 없이 돌린 기록)는 붙일 곳이 없어 건너뛴다.
    돌려주는 값은 {"pushed": 붙인 수, "skipped": 건너뛴 수}다. 건너뛴 수를 숨기지 않는다.
    """
    pushed = 0
    skipped = 0
    for score in scores:
        if not score.get("trace_id"):
            skipped += 1
            continue
        client.create_score(
            trace_id=score["trace_id"],
            observation_id=score.get("observation_id"),
            name=score["name"],
            value=score["value"],
            data_type=score["data_type"],
            comment=score.get("comment"),
            metadata=score.get("metadata"),
        )
        pushed += 1
    flush = getattr(client, "flush", None)
    if flush is not None:
        flush()
    return {"pushed": pushed, "skipped": skipped}


def _find_queue_id(client: Any, queue_name: str) -> str | None:
    """이름이 queue_name인 annotation queue의 ID. 없으면 None. 쪽수를 넘기며 끝까지 찾는다."""
    page, limit = 1, 50
    while True:
        response = client.api.annotation_queues.list_queues(page=page, limit=limit)
        for queue in response.data:
            if queue.name == queue_name:
                return queue.id
        if not response.data or page * limit >= response.meta.total_items:
            return None
        page += 1


# 사람 검수 대기열에 붙이는 점수 설정. Langfuse는 대기열을 만들 때 점수 설정이 1개 이상 있어야 한다.
# 2026-11-05 jp.cloud.langfuse.com(v4.75.0)이 빈 scoreConfigIds를 400 "Too small: expected array to have >=1 items"로
# 거절했다(05 노트북이 미확인으로 남긴 항목). 검수자는 Langfuse 화면에서 이 점수(PASS/FAIL)를 고른다.
REVIEW_SCORE_CONFIG_NAME = "human_verdict"
REVIEW_SCORE_CATEGORIES = (("PASS", 1.0), ("FAIL", 0.0))
REVIEW_SCORE_DESCRIPTION = "사람 검수: 이 Episode의 처리가 정책 문서와 기록에 맞는가(PASS) 아닌가(FAIL)"


def ensure_review_score_config(client: Any) -> str:
    """사람 검수용 범주형 점수 설정(human_verdict: PASS/FAIL)의 ID. 보관되지 않은 같은 이름이 있으면 그것을, 없으면 만든다."""
    # 1단계: 쪽수를 넘기며 같은 이름을 찾는다. 보관(archived)된 설정은 쓰지 않는다.
    page, limit = 1, 50
    while True:
        response = client.api.score_configs.get(page=page, limit=limit)
        for config in response.data:
            if config.name == REVIEW_SCORE_CONFIG_NAME and not getattr(config, "is_archived", False):
                return config.id
        if not response.data or page * limit >= response.meta.total_items:
            break
        page += 1
    # 2단계: 없으면 만든다.
    created = client.api.score_configs.create(
        name=REVIEW_SCORE_CONFIG_NAME, data_type=ScoreConfigDataType.CATEGORICAL,
        categories=[ConfigCategory(label=label, value=value) for label, value in REVIEW_SCORE_CATEGORIES],
        description=REVIEW_SCORE_DESCRIPTION)
    return created.id


def enqueue_for_review(client: Any, queue_name: str, selections: list[Selection]) -> dict:
    """선정된 trace를 사람 검수 annotation queue에 넣는다. 대기열이 없으면 만든다.

    - trace_id가 없는 선정은 넣을 수 없어 건너뛴다.
    - 새 대기열에는 점수 설정 human_verdict(PASS/FAIL) 하나를 붙인다(ensure_review_score_config).
      Langfuse는 점수 설정이 없는 대기열을 거절한다.
    돌려주는 값은 {"queue_id", "enqueued", "skipped"}다.
    """
    queue_id = _find_queue_id(client, queue_name)
    if queue_id is None:
        created = client.api.annotation_queues.create_queue(
            name=queue_name, score_config_ids=[ensure_review_score_config(client)],
            description="Day05_new 온라인 평가에서 선정한 trace 검수")
        queue_id = created.id

    enqueued = 0
    skipped = 0
    for selection in selections:
        if not selection.trace_id:
            skipped += 1
            continue
        client.api.annotation_queues.create_queue_item(
            queue_id, object_id=selection.trace_id, object_type=AnnotationQueueObjectType.TRACE)
        enqueued += 1
    return {"queue_id": queue_id, "enqueued": enqueued, "skipped": skipped}


def create_root_rule(client: Any, *, evaluator_id: str, environment: str, sampling: float,
                     enabled: bool = False) -> Any:
    """서버 쪽 평가 Rule을 만든다(선택 경로). 환경이 environment인 root observation을 sampling 비율로 평가한다.

    주의: evaluator_id가 서버 쪽 LLM Judge라면 Langfuse에 LLM Connection이 있어야 하고, 그 연결에는
    수강생 본인의 모델 키가 들어간다. 키가 없으면 Rule이 평가를 만들지 못한다. 그래서 이 함수는
    enabled=False(초안)가 기본이다. 비용을 이해한 뒤 enabled=True로 켠다.
    sampling은 0 초과 1 이하의 비율이다. 생략(전부 평가)하는 길은 일부러 열지 않았다.
    """
    if not 0 < sampling <= 1:
        raise ValueError("sampling은 0 초과 1 이하여야 합니다.")
    filters = [
        EvaluationRuleFilter_StringOptions(
            column="environment", operator=EvaluationRuleOptionsFilterOperator.ANY_OF, value=[environment]),
        EvaluationRuleFilter_Boolean(
            column="isRootObservation", operator=EvaluationRuleBooleanFilterOperator.EQUALS, value=True),
    ]
    return client.api.evaluation_rules.create(
        name=f"day05-root-{environment}",
        enabled=enabled,
        evaluator_assignments=[EvaluationRuleEvaluatorAssignmentInput(evaluator_id=evaluator_id)],
        sampling=sampling,
        filter=filters,
    )
