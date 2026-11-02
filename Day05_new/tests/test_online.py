"""온라인 평가(eval_lab.online) 시험. 기록은 scripted 모의 트래픽이고 Langfuse·모델은 모두 가짜다."""
import json
from types import SimpleNamespace

import pytest
from eval_lab.episodes import episode_summary
from eval_lab.online import (
    Selection,
    artifact_from_root_observation,
    batch_evaluate,
    create_root_rule,
    enqueue_for_review,
    evaluate_records_locally,
    observation_mapper,
    online_evaluators,
    push_scores,
    request_shape,
    root_filter,
    select_traces,
)
from eval_lab.traffic import make_mistake_driver, round_items, run_traffic
from langchain_core.messages import AIMessage
from tests.fakes import FakeChatModel, FakeDecider

QUESTION_NAMES = ["message_consistent", "next_step_clear", "clarify_when_needed"]
SURE_PASS = {name: 0.95 for name in QUESTION_NAMES}  # 확신 구간이라 Judge를 부르지 않는다.


# ---------------------------------------------------------------- 도우미

def item_for(family_suffix: str, *, style: str = "정중"):
    """round_items(1)에서 가족과 문형이 맞는 항목 하나."""
    return next(i for i in round_items(1) if i.family_id == f"incident-{family_suffix}" and i.style == style)


def with_trace_ids(records: list[dict]) -> list[dict]:
    """scripted 기록에는 trace_id가 없으므로 시험용 ID를 붙인 사본을 만든다."""
    return [{**record, "trace_id": f"{index:032x}"} for index, record in enumerate(records)]


@pytest.fixture(scope="module")
def clean_records() -> list[dict]:
    """실수 없이 돌린 27개 항목(문형 3 x 가족 9)."""
    return with_trace_ids(run_traffic(round_items(1)))


@pytest.fixture(scope="module")
def mistake_record() -> dict:
    """정상 주문에서 승인 없이 쓰기를 강제로 일으킨 기록 하나."""
    driver = make_mistake_driver({"write_before_approval": 1.0}, seed=0)
    return run_traffic([item_for("normal")], driver=driver)[0]


@pytest.fixture(scope="module")
def mixed_records(clean_records, mistake_record) -> list[dict]:
    """깨끗한 기록 27건 뒤에 실수 기록 한 건을 붙인 것. 실수 기록의 위치는 마지막(27)이다."""
    return with_trace_ids([*clean_records, mistake_record])


def sure_pass_evaluators():
    """Jev가 확신하는 가짜. Judge 모델은 불리면 오류가 나도록 비워 둔다."""
    return online_evaluators(decider=FakeDecider(SURE_PASS), judge_model=FakeChatModel.scripted([]))


def scores_by_name(evaluations) -> dict:
    return {evaluation.name: evaluation for evaluation in evaluations}


# ---------------------------------------------------------------- 가짜 Langfuse 클라이언트

class FakeAnnotationQueues:
    def __init__(self):
        self.queues: list[SimpleNamespace] = []
        self.items: list[tuple[str, str, str]] = []

    def list_queues(self, *, page=None, limit=None):
        return SimpleNamespace(data=list(self.queues), meta=SimpleNamespace(total_items=len(self.queues)))

    def create_queue(self, *, name, score_config_ids, description=None):
        queue = SimpleNamespace(id=f"q{len(self.queues) + 1}", name=name)
        self.queues.append(queue)
        return queue

    def create_queue_item(self, queue_id, *, object_id, object_type):
        self.items.append((queue_id, object_id, str(object_type)))


class FakeEvaluationRules:
    def __init__(self):
        self.created: list[dict] = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(id="rule-1")


class FakeLangfuse:
    """run_batched_evaluation, create_score, api.annotation_queues, api.evaluation_rules를 흉내 낸다.

    run_batched_evaluation은 가진 observation에 mapper와 평가기를 진짜로 돌리고 점수를 create_score로 남긴다.
    """

    def __init__(self, observations=()):
        self.observations = list(observations)
        self.batch_calls: list[dict] = []
        self.scores: list[dict] = []
        self.api = SimpleNamespace(annotation_queues=FakeAnnotationQueues(), evaluation_rules=FakeEvaluationRules())

    def run_batched_evaluation(self, **kwargs):
        self.batch_calls.append(kwargs)
        for observation in self.observations[: kwargs["max_items"]]:
            inputs = kwargs["mapper"](item=observation)
            for evaluator in kwargs["evaluators"]:
                result = evaluator(input=inputs.input, output=inputs.output,
                                   expected_output=inputs.expected_output, metadata=inputs.metadata)
                for evaluation in result:
                    self.create_score(trace_id=observation.trace_id, observation_id=observation.id,
                                      name=evaluation.name, value=evaluation.value,
                                      data_type=evaluation.data_type, comment=evaluation.comment)
        return SimpleNamespace(completed=True)

    def create_score(self, **kwargs):
        self.scores.append(kwargs)


def observation_of(record: dict, observation_id: str) -> SimpleNamespace:
    """기록의 Artifact를 root observation 모양(ObservationsView 흉내)으로 바꾼다."""
    return SimpleNamespace(id=observation_id, trace_id=record["trace_id"], input={}, parent_observation_id=None,
                           output=episode_summary(record["artifact"]), version="baseline", environment="day05_new")


# ---------------------------------------------------------------- 선정 전략

@pytest.mark.parametrize("strategy", ["random", "stratified", "signal"])
def test_strategies_are_deterministic_and_return_k_with_reasons(mixed_records, strategy):
    first = select_traces(mixed_records, strategy, 5, seed=3)
    second = select_traces(mixed_records, strategy, 5, seed=3)
    assert first == second
    assert len(first) == 5
    assert len({selection.record_index for selection in first}) == 5
    assert all(isinstance(s, Selection) and s.reason for s in first)
    assert all(s.trace_id == mixed_records[s.record_index]["trace_id"] for s in first)


def test_random_changes_with_seed(mixed_records):
    assert select_traces(mixed_records, "random", 8, seed=1) != select_traces(mixed_records, "random", 8, seed=2)


def test_stratified_covers_every_family_before_repeating(mixed_records):
    picked = select_traces(mixed_records, "stratified", 9, seed=0)
    families = {mixed_records[s.record_index]["family_id"] for s in picked}
    assert len(families) == 9


def test_signal_ranks_the_mistake_record_first(mixed_records):
    # 승인 전 쓰기는 서비스가 막지 않으므로 도구 오류가 아니라 규칙 위반 신호다.
    # 같은 라운드의 깨끗한 기록에도 도구 오류(타임아웃·결제 장애)가 있어 그쪽이 앞선다.
    # 그래서 도구 오류 신호가 전혀 없는 기록 집합으로 좁혀 순위를 본다.
    no_tool_error = [r for r in mixed_records if not any(e.result.get("status") in {"error", "denied"}
                                                        for e in r["artifact"].events)]
    mistake_index = next(i for i, r in enumerate(no_tool_error) if r["injected_mistakes"])
    picked = select_traces(no_tool_error, "signal", 3, seed=0)
    assert picked[0].record_index == mistake_index
    assert "규칙 위반" in picked[0].reason


def test_signal_prefers_tool_error_over_rule_hit(mixed_records):
    picked = select_traces(mixed_records, "signal", 1, seed=0)
    artifact = mixed_records[picked[0].record_index]["artifact"]
    assert any(e.result.get("status") in {"error", "denied"} for e in artifact.events)
    assert "도구 오류" in picked[0].reason


def test_signal_returns_fewer_when_no_signal(clean_records):
    normal = [r for r in clean_records if r["family_id"] == "incident-normal" and r["style"] == "정중"]
    normal = [{**r, "latency_ms": 0.0} for r in normal]
    picked = select_traces(normal, "signal", 5, seed=0)
    assert picked == []


def test_novelty_needs_golden_shapes(mixed_records):
    with pytest.raises(ValueError):
        select_traces(mixed_records, "novelty", 3, seed=0)


def test_novelty_skips_known_shapes(mixed_records):
    shapes = {request_shape(r) for r in mixed_records}
    known = {shape for shape in shapes if shape[1] == "정중"}
    picked = select_traces(mixed_records, "novelty", 6, seed=0, golden_shapes=known)
    assert len(picked) == 6
    assert all(request_shape(mixed_records[s.record_index]) not in known for s in picked)
    assert select_traces(mixed_records, "novelty", 6, seed=0, golden_shapes=shapes) == []


def test_unknown_strategy_is_rejected(mixed_records):
    with pytest.raises(ValueError):
        select_traces(mixed_records, "best-effort", 3, seed=0)


# ---------------------------------------------------------------- root observation 복원

def test_artifact_round_trips_the_episode_summary(clean_records):
    original = clean_records[0]["artifact"]
    summary = episode_summary(original)
    for source in (summary, json.dumps(summary), SimpleNamespace(output=summary, parent_observation_id=None),
                   {"output": summary}):
        rebuilt, reason = artifact_from_root_observation(source)
        assert reason == ""
        assert rebuilt == original.model_copy(update={"model_events": []})


def test_truncated_summary_returns_none_with_reason(clean_records):
    summary = episode_summary(clean_records[0]["artifact"])
    cut_field = {key: value for key, value in summary.items() if key != "events"}
    artifact, reason = artifact_from_root_observation(cut_field)
    assert artifact is None and "events" in reason

    artifact, reason = artifact_from_root_observation(json.dumps(summary)[:200])
    assert artifact is None and "JSON" in reason


@pytest.mark.parametrize("observation", [None, SimpleNamespace(output=None, parent_observation_id=None),
                                         {"output": {}}, {"output": {"schema": "other"}},
                                         SimpleNamespace(output={"schema": "x"}, parent_observation_id="p1")])
def test_unusable_observations_return_none(observation):
    artifact, reason = artifact_from_root_observation(observation)
    assert artifact is None and reason


# ---------------------------------------------------------------- 평가기

def test_evaluators_count_fatal_for_a_mistake_and_zero_for_a_clean_record(clean_records, mistake_record):
    trajectory, semantic = sure_pass_evaluators()
    clean_normal = next(r for r in clean_records if r["family_id"] == "incident-normal")

    clean = scores_by_name(trajectory(input=None, output=episode_summary(clean_normal["artifact"])))
    assert clean["fatal_count"].value == 0
    assert clean["trajectory_status"].value == "PASS"
    assert set(clean) == {"trajectory_status", "fatal_count", "warn_count", "blocked_attempts"}

    bad = scores_by_name(trajectory(input=None, output=episode_summary(mistake_record["artifact"])))
    assert bad["fatal_count"].value > 0
    assert bad["trajectory_status"].value == "FAIL"
    assert "write-before-approval" in bad["fatal_count"].comment

    semantic_scores = scores_by_name(semantic(input=None, output=episode_summary(clean_normal["artifact"])))
    assert list(semantic_scores) == QUESTION_NAMES
    assert all(score.value == "PASS" for score in semantic_scores.values())


def test_missing_artifact_never_yields_pass(clean_records):
    trajectory, semantic = sure_pass_evaluators()
    summary = episode_summary(clean_records[0]["artifact"])
    truncated = {key: value for key, value in summary.items() if key != "gate_events"}

    empty = trajectory(input=None, output=None)
    assert [e.name for e in empty] == ["trajectory_status"]
    assert empty[0].value == "NO_EVIDENCE" and empty[0].comment

    cut = trajectory(input=None, output=truncated)
    assert [e.name for e in cut] == ["trajectory_status"]
    assert cut[0].value == "INCOMPLETE" and "gate_events" in cut[0].comment

    assert semantic(input=None, output=truncated) == []


def test_mid_band_question_goes_to_the_judge(clean_records):
    decider = FakeDecider({**SURE_PASS, "next_step_clear": 0.5})
    judge = FakeChatModel.scripted([AIMessage(content='{"verdict": "FAIL", "reason": "다음 조치가 없습니다."}')])
    _, semantic = online_evaluators(decider=decider, judge_model=judge)
    normal = next(r for r in clean_records if r["family_id"] == "incident-normal")
    scores = scores_by_name(semantic(input=None, output=episode_summary(normal["artifact"])))
    assert scores["next_step_clear"].value == "FAIL"
    assert scores["next_step_clear"].metadata["stage"] == "judge"
    assert scores["message_consistent"].metadata["stage"] == "jev"


# ---------------------------------------------------------------- 일괄 채점과 점수 붙이기

def test_batch_evaluate_passes_observation_scope_and_root_filter():
    client = FakeLangfuse()
    token = object()
    batch_evaluate(client, evaluators=sure_pass_evaluators(), environment="day05_new", max_items=7, resume_from=token)
    call = client.batch_calls[0]
    assert call["scope"] == "observations"
    assert call["max_items"] == 7 and call["resume_from"] is token
    assert call["mapper"] is observation_mapper
    conditions = json.loads(call["filter"])
    assert {"type": "string", "column": "environment", "operator": "=", "value": "day05_new"} in conditions
    assert {"type": "string", "column": "name", "operator": "=", "value": "episode"} in conditions
    assert call["filter"] == root_filter("day05_new")

    batch_evaluate(client, evaluators=[], environment="x", max_items=1, filter_json="[]")
    assert client.batch_calls[1]["filter"] == "[]"
    with pytest.raises(ValueError):
        batch_evaluate(client, evaluators=[], environment="x", max_items=0)


def test_batch_run_scores_land_on_the_observation(clean_records, mistake_record):
    records = with_trace_ids([clean_records[0], mistake_record])
    client = FakeLangfuse([observation_of(r, f"obs-{i}") for i, r in enumerate(records)])
    batch_evaluate(client, evaluators=sure_pass_evaluators(), environment="day05_new", max_items=10)

    fatal = {s["observation_id"]: s["value"] for s in client.scores if s["name"] == "fatal_count"}
    assert fatal["obs-0"] == 0 and fatal["obs-1"] > 0
    assert {s["trace_id"] for s in client.scores} == {records[0]["trace_id"], records[1]["trace_id"]}


def test_local_scores_match_the_langfuse_path(clean_records, mistake_record):
    records = with_trace_ids([clean_records[0], mistake_record])
    rows = evaluate_records_locally(records, decider=FakeDecider(SURE_PASS), judge_model=FakeChatModel.scripted([]))
    local = {(row["record_index"], row["name"]): row["value"] for row in rows}

    client = FakeLangfuse([observation_of(r, f"obs-{i}") for i, r in enumerate(records)])
    batch_evaluate(client, evaluators=sure_pass_evaluators(), environment="day05_new", max_items=10)
    remote = {(int(s["observation_id"].split("-")[1]), s["name"]): s["value"] for s in client.scores}

    assert local == remote
    assert local[(1, "fatal_count")] > 0 and local[(0, "fatal_count")] == 0


def test_push_scores_attaches_observation_id_and_skips_missing_trace(clean_records):
    records = with_trace_ids(clean_records[:1])
    records[0]["observation_id"] = "obs-9"
    rows = evaluate_records_locally(records, decider=FakeDecider(SURE_PASS), judge_model=FakeChatModel.scripted([]))
    rows.append({"trace_id": None, "observation_id": None, "name": "orphan", "value": 1, "data_type": "NUMERIC"})

    client = FakeLangfuse()
    result = push_scores(client, rows)
    assert result == {"pushed": len(rows) - 1, "skipped": 1}
    assert {s["observation_id"] for s in client.scores} == {"obs-9"}
    first = client.scores[0]
    assert first["trace_id"] == records[0]["trace_id"]
    assert first["name"] == "trajectory_status" and first["data_type"] == "CATEGORICAL"


# ---------------------------------------------------------------- 검수 대기열과 Rule

def test_enqueue_creates_queue_once_and_skips_missing_trace():
    client = FakeLangfuse()
    selections = [Selection(0, "t0", "a"), Selection(1, None, "b"), Selection(2, "t2", "c")]

    first = enqueue_for_review(client, "day05-review", selections)
    assert first == {"queue_id": "q1", "enqueued": 2, "skipped": 1}
    second = enqueue_for_review(client, "day05-review", selections[:1])
    assert second["queue_id"] == "q1"
    assert len(client.api.annotation_queues.queues) == 1
    assert [(item[1], item[2]) for item in client.api.annotation_queues.items] == \
        [("t0", "TRACE"), ("t2", "TRACE"), ("t0", "TRACE")]


def test_create_root_rule_is_a_draft_by_default():
    client = FakeLangfuse()
    create_root_rule(client, evaluator_id="ev-1", environment="day05_new", sampling=0.25)
    request = client.api.evaluation_rules.created[0]
    assert request["enabled"] is False
    assert request["sampling"] == 0.25
    assert request["evaluator_assignments"][0].evaluator_id == "ev-1"
    columns = {f.column: f.value for f in request["filter"]}
    assert columns == {"environment": ["day05_new"], "isRootObservation": True}
    with pytest.raises(ValueError):
        create_root_rule(client, evaluator_id="ev-1", environment="day05_new", sampling=0)
