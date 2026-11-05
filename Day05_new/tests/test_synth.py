"""합성 7일 배경 운영 기록(eval_lab.synth)을 확인한다. 모델·네트워크·키를 쓰지 않는다.

기록은 실습 폴더와 같은 조건으로 만든다: 이어서 처리 요청은 실습 폴더의 ops.resume_item으로,
그 fixture(fx-ops-resume)는 use_cc/ops_fixtures.json에서 읽어 dev fixture에 더한다(setup_sandbox.py와 같은 병합).
합성 수치는 LLM 성능이 아니다. 이 시험은 구조와 결정성, 고정된 모니터링 규칙에 대한 이야기의 모양만 본다.
"""

import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path
from statistics import median
from types import SimpleNamespace

import pytest
from eval_lab import synth
from eval_lab.agent import MAX_MODEL_CALLS, PROMPTS
from eval_lab.contracts import Response
from eval_lab.dataset import load_fixtures
from eval_lab.episodes import artifact_from_summary, execute_episode
from eval_lab.monitoring import evaluate_alerts, local_metrics
from eval_lab.online import select_traces
from eval_lab.settings import Settings
from eval_lab.trajectory_rules import evaluate_trajectory
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

DAY05_ROOT = Path(__file__).resolve().parents[1]
SANDBOX = DAY05_ROOT / "use_cc" / "sandbox"
if str(SANDBOX) not in sys.path:
    sys.path.insert(0, str(SANDBOX))

# 실습 폴더 모듈이라 sys.path에 실습 폴더를 넣은 뒤에 읽는다.
import ops

SEOUL = timezone(timedelta(hours=9))
ANCHOR = datetime(2026, 11, 5, 12, 0, tzinfo=SEOUL)
SEED = 7
# 기준일(2026-11-05) 0시 KST와 그 7일 전 0시 KST. 이야기는 이 사이에만 있어야 한다.
WEEK_END = datetime(2026, 11, 5, 0, 0, tzinfo=SEOUL)
WEEK_START = datetime(2026, 10, 29, 0, 0, tzinfo=SEOUL)


def merged_fixtures() -> dict:
    """dev fixture에 운영 사례 fixture를 더한다. 실습 폴더의 data/fixtures.json과 같은 내용이다."""
    extra = json.loads((DAY05_ROOT / "use_cc" / "ops_fixtures.json").read_text(encoding="utf-8"))
    return {**load_fixtures(), **extra}


def default_plans(seed: int = SEED):
    return synth.plan_episodes(synth.DEFAULT_STORY, seed=seed, anchor=ANCHOR, resume_factory=ops.resume_item)


@pytest.fixture(scope="module")
def plans():
    return default_plans()


# ---------------------------------------------------------------- 계획

def test_same_seed_and_anchor_give_the_same_plans_and_another_seed_differs(plans):
    assert default_plans() == plans
    assert default_plans(seed=8) != plans


def test_story_has_forty_episodes_on_each_of_seven_days(plans):
    per_day = Counter(plan.story_day for plan in plans)
    assert per_day == {day: 40 for day in range(1, 8)}
    assert [plan.index for plan in plans] == list(range(280))
    assert len({plan.item.item_id for plan in plans}) == 280


def test_start_times_lie_in_the_week_before_the_anchor_date(plans):
    # 1일차는 2026-10-29, 7일차는 2026-11-04(KST)다. 시작 시각은 모두 기준일 0시 KST 전이다.
    for plan in plans:
        assert WEEK_START <= plan.start_time < WEEK_END
        local = plan.start_time.astimezone(SEOUL)
        assert local.date().isoformat() == plan.date
        assert local.date() == (WEEK_START + timedelta(days=plan.story_day - 1)).date()
        assert 8 <= local.hour <= 22
    assert [plan.start_time for plan in plans] == sorted(plan.start_time for plan in plans)


def test_resume_requests_are_exact_counts_and_surge_on_day_seven(plans):
    resume = Counter(plan.story_day for plan in plans if plan.item.family_id == synth.RESUME_FAMILY)
    assert resume == {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2, 7: 16}


def test_payment_incident_window_is_day_five_from_14_to_16_kst(plans):
    incident = [plan for plan in plans if plan.incident]
    assert incident, "5일차 장애 창 안의 요청이 하나도 없습니다."
    for plan in incident:
        local = plan.start_time.astimezone(SEOUL)
        assert plan.story_day == 5 and 14 <= local.hour < 16


def test_canary_runs_agent_v2_partly_before_13_and_fully_after(plans):
    day6 = [plan for plan in plans if plan.story_day == 6]
    before = [plan.version for plan in day6 if plan.start_time.astimezone(SEOUL).hour < 13]
    after = [plan.version for plan in day6 if plan.start_time.astimezone(SEOUL).hour >= 13]
    assert set(after) == {"agent-v2"}
    assert set(before) == {"agent-v1", "agent-v2"}
    assert {plan.version for plan in plans if plan.story_day != 6} == {"agent-v1"}


def test_anchor_moves_dates_but_not_the_story(plans):
    later = synth.plan_episodes(synth.DEFAULT_STORY, seed=SEED, anchor=ANCHOR + timedelta(days=3),
                                resume_factory=ops.resume_item)
    assert [p.item for p in later] == [p.item for p in plans]
    assert [p.start_time - q.start_time for p, q in zip(later, plans)] == [timedelta(days=3)] * 280


def test_plan_never_contains_holdout_families_or_fixtures(plans):
    assert not [p for p in plans if p.item.family_id.startswith("incident-hv-")]
    assert not [p for p in plans if p.item.fixture_id.startswith("fx-hv-")]


@pytest.mark.parametrize(("family", "reason"), [("incident-hv-timeout-after", "holdout 가족"),
                                                ("incident-made-up", "dev 가족도")])
def test_holdout_or_unknown_family_is_refused(family, reason):
    story = replace(synth.DEFAULT_STORY, incident_mix={**synth.DEFAULT_STORY.incident_mix, family: 5})
    with pytest.raises(ValueError, match=f"{reason}.*{family}"):
        synth.plan_episodes(story, seed=SEED, anchor=ANCHOR, resume_factory=ops.resume_item)


def test_resume_share_without_resume_factory_is_refused():
    with pytest.raises(ValueError, match="resume_factory"):
        synth.plan_episodes(synth.DEFAULT_STORY, seed=SEED, anchor=ANCHOR)


def test_naive_anchor_is_refused():
    with pytest.raises(ValueError, match="시간대"):
        # 시간대 없는 anchor를 거절하는지 보는 시험이라 일부러 naive datetime을 만든다.
        naive = datetime(2026, 11, 5, 12, 0)  # noqa: DTZ001 - 거절 대상 입력을 일부러 만든다.
        synth.plan_episodes(synth.DEFAULT_STORY, seed=SEED, anchor=naive, resume_factory=ops.resume_item)


# ---------------------------------------------------------------- 시뮬레이션과 옷 입히기

@pytest.fixture(scope="module")
def simulated(plans):
    return synth.simulate(plans, fixtures=merged_fixtures())


@pytest.fixture(scope="module")
def dressed(simulated):
    return synth.dress(simulated, environment="synth_ops")


def span_type(span) -> str:
    return span.attributes["langfuse.observation.type"]


def test_simulation_needs_the_resume_fixture(plans):
    resume_plan = next(plan for plan in plans if plan.item.family_id == synth.RESUME_FAMILY)
    with pytest.raises(ValueError, match="fx-ops-resume"):
        synth.simulate([resume_plan], fixtures=load_fixtures())


def test_simulation_keeps_injected_mistakes_from_the_driver(simulated):
    injected = Counter(name for episode in simulated for name in episode.injected_mistakes)
    # 확률이 0이 아닌 실수는 280건 중 적어도 한 번은 시도된다(seed 7 기준).
    assert set(injected) >= {"skip_final_check", "write_before_approval"}
    assert all(episode.artifact.model_calls == 0 for episode in simulated)


def test_same_seed_gives_identical_ids_times_and_summaries(dressed):
    again = synth.dress(synth.simulate(default_plans(), fixtures=merged_fixtures()), environment="synth_ops")
    assert [e.trace_id for e in again] == [e.trace_id for e in dressed]
    assert [e.spans for e in again] == [e.spans for e in dressed]
    assert [e.artifact for e in again] == [e.artifact for e in dressed]


def test_environment_changes_ids_but_not_times(dressed):
    other = synth.dress([episode for episode in synth.simulate(default_plans()[:3], fixtures=merged_fixtures())],
                        environment="synth_ops_b")
    for mine, theirs in zip(dressed[:3], other):
        assert mine.trace_id != theirs.trace_id
        assert [s.span_id for s in mine.spans] != [s.span_id for s in theirs.spans]
        assert [(s.start_ms, s.end_ms) for s in mine.spans] == [(s.start_ms, s.end_ms) for s in theirs.spans]


def test_every_episode_stays_inside_its_story_day(dressed):
    for episode in dressed:
        root = episode.spans[0]
        day_start = WEEK_START + timedelta(days=episode.plan.story_day - 1)
        assert root.parent_id is None and root.name == "episode"
        assert day_start.timestamp() * 1000 <= root.start_ms < root.end_ms < (day_start + timedelta(days=1)).timestamp() * 1000
        assert root.start_ms == int(episode.plan.start_time.timestamp() * 1000)


def test_children_lie_strictly_inside_parents_and_siblings_follow_event_steps(dressed):
    for episode in dressed:
        by_id = {span.span_id: span for span in episode.spans}
        assert len(by_id) == len(episode.spans)
        children: dict[str, list] = {}
        for span in episode.spans[1:]:
            parent = by_id[span.parent_id]
            assert parent.start_ms < span.start_ms and span.end_ms < parent.end_ms
            assert span.start_ms < span.end_ms
            children.setdefault(span.parent_id, []).append(span)
        for siblings in children.values():
            ordered = sorted(siblings, key=lambda span: span.start_ms)
            starts = [span.start_ms for span in ordered]
            assert len(set(starts)) == len(starts)
            # 형제는 겹치지 않는다: 다음 형제는 앞 형제가 끝난 뒤에 시작한다.
            assert all(a.end_ms < b.start_ms for a, b in pairwise(ordered))
        # 도구 span의 시간 순서가 서비스 Event의 step 순서와 같다.
        step_by_tool_span = {event.parent_observation_id: event.step for event in episode.artifact.events}
        tool_spans = sorted((s for s in episode.spans if span_type(s) == "tool"), key=lambda s: s.start_ms)
        assert [step_by_tool_span[s.span_id] for s in tool_spans] == sorted(step_by_tool_span.values())


def test_root_summary_rebuilds_the_dressed_artifact(dressed):
    for episode in dressed:
        root = episode.spans[0]
        summary = json.loads(root.attributes["langfuse.observation.output"])
        rebuilt = artifact_from_summary(summary)
        assert rebuilt == episode.artifact.model_copy(update={"model_events": []})


def test_dressing_keeps_trajectory_verdicts(simulated, dressed):
    for raw, episode in zip(simulated, dressed):
        before = evaluate_trajectory(raw.artifact)
        after = evaluate_trajectory(episode.artifact)
        assert after.status == before.status
        assert [hit.rule_id for hit in after.fatal] == [hit.rule_id for hit in before.fatal]
        assert [hit.rule_id for hit in after.warn] == [hit.rule_id for hit in before.warn]
    statuses = Counter(evaluate_trajectory(e.artifact).status for e in dressed)
    assert statuses["FAIL"] > 0 and statuses["PASS"] > 0


def test_events_point_at_service_spans_under_tool_spans(dressed):
    for episode in dressed:
        by_id = {span.span_id: span for span in episode.spans}
        for event in episode.artifact.events:
            service = by_id[event.observation_id]
            tool = by_id[event.parent_observation_id]
            assert (service.name, span_type(service)) == (f"service.{event.tool}", "span")
            assert (tool.name, span_type(tool)) == (event.tool, "tool")
            assert service.parent_id == tool.span_id
            assert (event.start_ns, event.end_ns) == (service.start_ms * 1_000_000, service.end_ms * 1_000_000)
        assert {turn.trace_id for turn in episode.artifact.turns} == {episode.trace_id}


def test_model_calls_per_episode_follow_the_calibration(dressed):
    calls = [episode.artifact.model_calls for episode in dressed]
    generations = [sum(1 for s in e.spans if span_type(s) == "generation") for e in dressed]
    assert calls == generations
    assert 3 <= median(calls) <= 8
    assert max(calls) <= MAX_MODEL_CALLS
    # 턴마다 마지막 model-call이 하나 있으므로 도구 호출이 없는 Episode도 1회는 부른다.
    assert min(calls) >= 1


def long_simulated_episodes(plan, copies: int) -> list:
    """서비스 호출 예산 한도(18개)까지 get_order만 부르는 Episode를 번호만 바꿔 copies개 만든다.

    도구 묶음이 무작위라도 모델 호출 수가 MAX_MODEL_CALLS를 넘지 않는지 보려는 긴 기록이다. 업무 결과는 시뮬레이터 값이다.
    """
    def lookups_only(request, env, release):
        for _ in range(18):
            env.call("get_order", order_id=request.order_id)
        return Response(kind="completed", message="조회만 했습니다.", order_id=request.order_id), {}

    fixture = merged_fixtures()[plan.item.fixture_id]
    artifact = execute_episode(plan.item.request, fixture, followups=[], max_turns=1, scenario_id=plan.item.item_id,
                               release="baseline", trial=1, mode="scripted", prompt=PROMPTS["baseline"],
                               scripted_driver=lookups_only)
    assert len(artifact.events) == 18
    return [synth.SimulatedEpisode(plan=replace(plan, index=index), artifact=artifact,
                                   actor_id=fixture["actor_id"], injected_mistakes=[]) for index in range(copies)]


def test_long_episodes_stay_within_the_model_call_budget(plans):
    normal_plan = next(plan for plan in plans if plan.item.family_id == "incident-normal")
    for episode in synth.dress(long_simulated_episodes(normal_plan, copies=40), environment="synth_ops"):
        generations = [s for s in episode.spans if span_type(s) == "generation"]
        tools = [s for s in episode.spans if span_type(s) == "tool"]
        assert len(generations) == episode.artifact.model_calls <= MAX_MODEL_CALLS
        assert len(tools) == 18


def test_generation_usage_and_cost_follow_the_price_constants(dressed):
    for episode in dressed:
        input_total = output_total = 0
        cost_total = 0.0
        for span in episode.spans:
            if span_type(span) != "generation":
                continue
            assert span.name == "model-call"
            assert span.attributes["langfuse.observation.model.name"] == "synthetic/deepseek-v4.1-flash-ultrafast"
            usage = json.loads(span.attributes["langfuse.observation.usage_details"])
            cost = json.loads(span.attributes["langfuse.observation.cost_details"])
            assert set(usage) == set(cost) == {"input", "output"}
            assert cost["input"] == pytest.approx(usage["input"] * 0.15 / 1_000_000)
            assert cost["output"] == pytest.approx(usage["output"] * 0.60 / 1_000_000)
            assert 130 <= usage["input"] <= 1567 and 41 <= usage["output"] <= 476
            assert "langfuse.observation.metadata.cache_read_tokens" in span.attributes
            input_total += usage["input"]
            output_total += usage["output"]
            cost_total += cost["input"] + cost["output"]
        assert (episode.artifact.input_tokens, episode.artifact.output_tokens) == (input_total, output_total)
        assert episode.artifact.cost_usd == pytest.approx(cost_total)


# ---------------------------------------------------------------- 로컬 기록과 고정된 모니터링 규칙

@pytest.fixture(scope="module")
def records(dressed):
    return synth.local_records(dressed)


def metrics_by_day(records) -> dict[int, dict]:
    """local_metrics(group_by='date')를 이야기 날짜 번호로 다시 묶는다."""
    by_date = local_metrics(records, group_by="date")
    day_of_date = {record["date"]: record["story_day"] for record in records}
    return {day_of_date[date]: metrics for date, metrics in by_date.items()}


def alert_rules(current: dict, baseline: dict) -> set[str]:
    return {alert.rule for alert in evaluate_alerts(current, baseline)}


def test_local_records_carry_time_version_and_root_latency(records, dressed):
    for record, episode in zip(records, dressed):
        root = episode.spans[0]
        assert record["latency_ms"] == root.end_ms - root.start_ms
        assert record["trace_id"] == episode.trace_id
        assert record["start_time"] == episode.plan.start_time.isoformat(timespec="milliseconds")
        assert (record["date"], record["story_day"], record["version"]) == (
            episode.plan.date, episode.plan.story_day, episode.plan.version)
        assert record["injected_mistakes"] == episode.injected_mistakes
        assert record["artifact"] is episode.artifact


def test_local_records_survive_a_jsonl_round_trip(records, tmp_path):
    path = tmp_path / "기록 폴더" / "synth_ops.jsonl"
    synth.write_local_records(path, records)
    loaded = synth.read_local_records(path)
    assert loaded == records
    # 다시 읽은 기록도 모니터링과 trace 선정 함수가 그대로 받는다.
    assert local_metrics(loaded, group_by="date") == local_metrics(records, group_by="date")
    assert len(select_traces(loaded, "stratified", 10, seed=SEED)) == 10


def test_payment_incident_day_raises_the_latency_alert(records):
    metrics = metrics_by_day(records)
    assert "latency-p95" in alert_rules(metrics[5], metrics[1])
    assert "latency-p95" not in alert_rules(metrics[2], metrics[1])


def test_resume_surge_day_raises_the_input_mix_alert(records):
    metrics = metrics_by_day(records)
    assert "input-mix-shift" in alert_rules(metrics[7], metrics[1])
    assert "input-mix-shift" not in alert_rules(metrics[2], metrics[1])


def test_canary_agent_v2_skips_the_final_check_more_often_on_day_six(records):
    day6 = [record for record in records if record["story_day"] == 6]
    by_version = local_metrics(day6, group_by="version")
    v1_rate = by_version["agent-v1"]["warn_rate"].get("skip-final-check", 0.0)
    v2_rate = by_version["agent-v2"]["warn_rate"].get("skip-final-check", 0.0)
    # 수강생이 볼 수 있는 차이여야 한다: agent-v2 Episode 열에 하나 이상(10%p 이상) 더 많다.
    assert v2_rate - v1_rate >= 0.10


# ---------------------------------------------------------------- OTLP 내보내기 (네트워크 없이 메모리 exporter로)

TRACE_ATTRIBUTE_KEYS = ("langfuse.environment", "langfuse.version", "session.id", "user.id", "langfuse.trace.tags",
                        "langfuse.trace.metadata.synthetic", "langfuse.trace.metadata.generator",
                        "langfuse.trace.metadata.story", "langfuse.trace.metadata.seed",
                        "langfuse.observation.metadata.synthetic")


@pytest.fixture(scope="module")
def exported(dressed):
    exporter = InMemorySpanExporter()
    counts = synth.export_otlp(dressed, settings=Settings(), environment="synth_ops", exporter=exporter)
    return counts, exporter.get_finished_spans()


def test_export_sends_every_span_once_and_reports_counts(exported, dressed):
    counts, spans = exported
    total = sum(len(episode.spans) for episode in dressed)
    assert counts == {"traces": 280, "observations": total, "exported": total, "failed": 0}
    assert len({(span.context.trace_id, span.context.span_id) for span in spans}) == total


def test_exported_spans_match_local_ids_parents_and_times(exported, dressed):
    _, spans = exported
    sent = {(format(s.context.trace_id, "032x"), format(s.context.span_id, "016x")): s for s in spans}
    for episode in dressed:
        for local in episode.spans:
            span = sent[(episode.trace_id, local.span_id)]
            parent = format(span.parent.span_id, "016x") if span.parent else None
            assert (span.name, parent) == (local.name, local.parent_id)
            assert (span.start_time, span.end_time) == (local.start_ms * 1_000_000, local.end_ms * 1_000_000)
            assert dict(span.attributes) == {k: tuple(v) if isinstance(v, list) else v
                                             for k, v in local.attributes.items()}


def test_every_exported_event_service_span_hangs_under_a_tool_span(exported, dressed):
    _, spans = exported
    by_id = {format(s.context.span_id, "016x"): s for s in spans}
    for episode in dressed:
        for event in episode.artifact.events:
            service = by_id[event.observation_id]
            tool = by_id[format(service.parent.span_id, "016x")]
            assert service.attributes["langfuse.observation.type"] == "span"
            assert tool.attributes["langfuse.observation.type"] == "tool"
            assert format(tool.context.span_id, "016x") == event.parent_observation_id


def test_every_exported_span_carries_trace_attributes_and_synthetic_marks(exported, dressed):
    _, spans = exported
    plan_of = {episode.trace_id: episode.plan for episode in dressed}
    for span in spans:
        plan = plan_of[format(span.context.trace_id, "032x")]
        assert all(key in span.attributes for key in TRACE_ATTRIBUTE_KEYS)
        assert span.attributes["langfuse.environment"] == "synth_ops"
        assert span.attributes["langfuse.version"] == plan.version
        assert span.attributes["langfuse.trace.metadata.synthetic"] == "true"
        tags = span.attributes["langfuse.trace.tags"]
        assert tags[:3] == ("synthetic", "day05-ops-week", f"day-{plan.story_day}")
        assert plan.item.family_id in tags


def test_failed_results_and_error_levels_are_marked(exported):
    _, spans = exported
    levels = Counter((s.attributes.get("langfuse.observation.level"), s.attributes.get("langfuse.observation.status_message"))
                     for s in spans if s.name.startswith("service."))
    assert levels[("ERROR", "TIMEOUT")] > 0
    assert levels[("WARNING", "FORBIDDEN")] > 0
    for span in spans:
        output = span.attributes.get("langfuse.observation.output")
        if span.name.startswith("service.") and json.loads(output).get("status") == "ok":
            assert "langfuse.observation.level" not in span.attributes


def test_root_input_keeps_korean_request_text(dressed):
    root = dressed[0].spans[0]
    request = json.loads(root.attributes["langfuse.observation.input"])
    assert request == dressed[0].plan.item.request.model_dump(mode="json")
    assert "\\u" not in root.attributes["langfuse.observation.input"]


def test_default_story_fits_the_observation_budget(dressed, exported):
    counts, _ = exported
    estimate = synth.estimate_observations(dressed)
    assert estimate["observations"] == counts["observations"] <= 7000
    assert estimate["traces"] == 280
    assert sum(estimate["by_type"].values()) == estimate["observations"]


class FailingExporter(InMemorySpanExporter):
    """수집기가 거절하는 상황(예: 401). 받은 묶음마다 실패를 돌려준다."""

    def export(self, spans):
        return SpanExportResult.FAILURE


def test_export_counts_spans_the_collector_refused(dressed):
    counts = synth.export_otlp(dressed[:2], settings=Settings(), environment="synth_ops", exporter=FailingExporter())
    total = len(dressed[0].spans) + len(dressed[1].spans)
    assert counts == {"traces": 2, "observations": total, "exported": 0, "failed": total}


def test_export_refuses_records_dressed_for_another_environment(dressed):
    with pytest.raises(ValueError, match="synth_ops"):
        synth.export_otlp(dressed[:1], settings=Settings(), environment="synth_ops_b", exporter=InMemorySpanExporter())



def test_export_ignores_an_active_outer_span(dressed):
    # 적재 도구가 다른 계측(예: Langfuse SDK span) 안에서 불려도 root는 부모 없이 나가야 한다.
    outer = TracerProvider(shutdown_on_exit=False).get_tracer("outer")
    exporter = InMemorySpanExporter()
    with outer.start_as_current_span("outer"):
        synth.export_otlp(dressed[:1], settings=Settings(), environment="synth_ops", exporter=exporter)
    roots = [span for span in exporter.get_finished_spans() if span.name == "episode"]
    assert len(roots) == 1 and roots[0].parent is None

def test_otlp_target_uses_basic_auth_and_ingestion_version_header():
    settings = Settings(langfuse_public_key="pk-lf-test", langfuse_secret_key="sk-lf-test",
                        langfuse_host="https://jp.cloud.langfuse.com/")
    endpoint, headers = synth.otlp_target(settings)
    assert endpoint == "https://jp.cloud.langfuse.com/api/public/otel/v1/traces"
    # base64("pk-lf-test:sk-lf-test")
    assert headers == {"Authorization": "Basic cGstbGYtdGVzdDpzay1sZi10ZXN0", "x-langfuse-ingestion-version": "4"}
    default_endpoint, _ = synth.otlp_target(Settings(langfuse_public_key="pk", langfuse_secret_key="sk"))
    assert default_endpoint == "https://cloud.langfuse.com/api/public/otel/v1/traces"


def test_otlp_target_names_missing_keys_without_values():
    with pytest.raises(RuntimeError, match="LANGFUSE_SECRET_KEY") as caught:
        synth.otlp_target(Settings(langfuse_public_key="pk-lf-visible"))
    assert "pk-lf-visible" not in str(caught.value)


@pytest.mark.parametrize("name", ["synth_ops", "a", "synth-ops-2", "x" * 40])
def test_valid_environment_names_pass(name):
    assert synth.validate_environment(name) == name


@pytest.mark.parametrize("name", ["", "Synth_ops", "synth ops", "합성", "langfuse-ops", "x" * 41, "synth.ops"])
def test_invalid_environment_names_are_refused(name):
    with pytest.raises(ValueError):
        synth.validate_environment(name)


# ---------------------------------------------------------------- 이미 적재된 root 확인 (가짜 Langfuse 클라이언트)

class FakeObservations:
    """Langfuse v2 관측 API의 get_many만 흉내 낸다. environment 필터에 맞는 root만 쪽으로 나눠 돌려준다."""

    def __init__(self, roots_by_environment: dict[str, int]):
        self.roots_by_environment = roots_by_environment
        self.filters: list[list[dict]] = []

    def get_many(self, *, fields, limit, cursor, filter):
        conditions = json.loads(filter)
        self.filters.append(conditions)
        environment = next(c["value"] for c in conditions if c["column"] == "environment")
        start = int(cursor or 0)
        stop = min(start + limit, self.roots_by_environment.get(environment, 0))
        data = [SimpleNamespace(id=f"root-{n}") for n in range(start, stop)]
        more = stop < self.roots_by_environment.get(environment, 0)
        return SimpleNamespace(data=data, meta=SimpleNamespace(cursor=str(stop) if more else None))


def fake_client(roots_by_environment: dict[str, int]):
    return SimpleNamespace(api=SimpleNamespace(observations=FakeObservations(roots_by_environment)))


def test_existing_roots_in_the_environment_are_counted():
    client = fake_client({"synth_ops": 130, "day05_new": 9})
    assert synth.existing_root_count(client, "synth_ops") == 130
    conditions = client.api.observations.filters[0]
    assert {"type": "string", "column": "name", "operator": "=", "value": "episode"} in conditions


def test_empty_environment_has_no_existing_roots():
    assert synth.existing_root_count(fake_client({"day05_new": 9}), "synth_ops") == 0
