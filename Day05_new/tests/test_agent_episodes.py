"""에이전트·Episode·실행 기록(eval_lab.agent, episodes, runs)의 이식 동등성과 새 계약을 확인한다.

모델은 tests/fakes.py의 FakeChatModel, Langfuse는 실제 SDK에 메모리 exporter를 붙여 쓴다.
네트워크 호출은 없다(conftest가 IP 연결을 막는다). Day05/business_lab은 읽기 전용 기준으로만 불러온다.
"""

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from eval_lab import evidence, runs
from eval_lab.agent import COMMON_PROMPT, PROMPTS, call_tool
from eval_lab.contracts import GateDecision, Verdict, verdict
from eval_lab.counterexamples import verify_learner_check
from eval_lab.dataset import fingerprint, load_dataset, load_fixtures
from eval_lab.environment import WRITE_TOOLS, OrderEnvironment
from eval_lab.episodes import artifact_from_summary, episode_summary, execute_episode
from eval_lab.evaluators import evaluate
from fakes import FakeChatModel
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import Field

REPO_ROOT = Path(__file__).resolve().parents[2]
DAY05_ROOT = REPO_ROOT / "Day05"

# 정상 취소 한 번에 에이전트가 부르는 도구 순서 (COMMON_PROMPT의 처리 순서)
NORMAL_TOOL_ORDER = ["get_order", "check_cancel_policy", "begin_cancellation", "get_payment",
                     "refund_payment", "release_stock", "complete_cancellation", "get_order"]
ALL_TOOL_NAMES = ["get_order", "check_cancel_policy", "begin_cancellation", "get_payment", "refund_payment",
                  "release_stock", "complete_cancellation", "create_ticket"]


# ---------------------------------------------------------------- 공용 도우미

def dev_card(scenario_id: str):
    """dev 분할에서 시나리오 하나를 찾는다."""
    return next(card for card in load_dataset(split="dev") if card.metadata.scenario_id == scenario_id)


def run_card(card, *, mode: str = "scripted", release: str = "baseline", **options):
    """시나리오 카드 하나를 execute_episode로 실행한다. options는 execute_episode에 그대로 넘긴다."""
    fixture = load_fixtures()[card.fixture_id]
    return execute_episode(card.input, fixture, followups=card.followups, max_turns=card.max_turns,
                           scenario_id=card.metadata.scenario_id, release=release, trial=1, mode=mode,
                           prompt=PROMPTS[release], **options)


def tool_trace(artifact) -> list[tuple]:
    """Artifact의 서비스 호출을 (도구, 인자, 결과) 목록으로 줄인다. ID와 시각은 실행마다 달라 뺀다."""
    return [(event.tool, event.args, event.result) for event in artifact.events]


def tool_call_message(index: int, name: str, **args) -> AIMessage:
    """가짜 모델이 돌려줄 도구 호출 메시지 하나. 호출 ID는 call-<index>다."""
    call = {"name": name, "args": args, "id": f"call-{index}", "type": "tool_call"}
    return AIMessage(content="", tool_calls=[call])


def normal_cancellation_script(fixture: dict) -> list[AIMessage]:
    """fixture 값을 읽어, 정상 취소 8단계와 구조화 응답(Response 도구)을 차례로 부르는 대본을 만든다."""
    order_id = fixture["subject_id"]
    order = next(row for row in fixture["orders"] if row["id"] == order_id)
    payment = next(row for row in fixture["payments"] if row["order_id"] == order_id)
    remaining = payment["captured_cents"] - payment["refunded_cents"]
    return [
        tool_call_message(1, "get_order", order_id=order_id),
        tool_call_message(2, "check_cancel_policy", order_id=order_id),
        tool_call_message(3, "begin_cancellation", order_id=order_id, expected_version=order["version"]),
        tool_call_message(4, "get_payment", order_id=order_id),
        tool_call_message(5, "refund_payment", order_id=order_id, amount_cents=remaining,
                          idempotency_key=f"refund:{order_id}"),
        tool_call_message(6, "release_stock", order_id=order_id, idempotency_key=f"stock:{order_id}"),
        tool_call_message(7, "complete_cancellation", order_id=order_id),
        tool_call_message(8, "get_order", order_id=order_id),
        tool_call_message(9, "Response", kind="completed", message="주문 취소와 환불을 확인했습니다.",
                          order_id=order_id, refund_cents=remaining),
    ]


def block_begin_cancellation(prefix_events, tool: str, args: dict) -> GateDecision:
    """시험용 게이트: begin_cancellation만 막고 나머지는 통과시킨다."""
    if tool == "begin_cancellation":
        return GateDecision(action="block", rule_id="test-block-begin", reason="시험용 차단")
    return GateDecision(action="allow")


class RecordingFakeChatModel(FakeChatModel):
    """모델이 받은 메시지 목록을 호출마다 남기는 가짜. 막힌 도구 결과가 모델에 닿았는지 확인한다."""

    seen: list[list] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


# ---------------------------------------------------------------- (a) 원본과의 동등성

@pytest.fixture
def old_lab(monkeypatch):
    """Day05/business_lab을 읽기 전용으로 불러온다.

    business_lab/__init__.py는 .env를 읽어 환경 변수에 올린다. 시험은 키를 만지지 않으므로
    dotenv.load_dotenv를 빈 함수로 바꾼 상태에서 import하고, 끝나면 모듈 캐시를 지운다.
    """
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.syspath_prepend(str(DAY05_ROOT))
    for name in [n for n in sys.modules if n == "business_lab" or n.startswith("business_lab.")]:
        monkeypatch.delitem(sys.modules, name)
    import business_lab.agents as old_agents
    import business_lab.dataset as old_dataset
    import business_lab.episodes as old_episodes
    import business_lab.evaluators as old_evaluators

    yield SimpleNamespace(agents=old_agents, dataset=old_dataset, episodes=old_episodes,
                          evaluators=old_evaluators)
    for name in [n for n in sys.modules if n == "business_lab" or n.startswith("business_lab.")]:
        sys.modules.pop(name, None)


@pytest.mark.parametrize("release", ["baseline", "candidate"])
def test_scripted_episodes_match_original(old_lab, release):
    """dev 9개 시나리오에서 이식본과 원본의 scripted Episode가 같은 판정·호출·응답·최종 상태를 낸다."""
    new_cards = {card.metadata.scenario_id: card for card in load_dataset(split="dev")}
    old_cards = {card.metadata.scenario_id: card for card in old_lab.dataset.load_dataset(split="dev")}
    assert len(new_cards) == 9
    assert new_cards.keys() == old_cards.keys()
    old_fixtures = old_lab.dataset.load_fixtures()

    for scenario_id in sorted(new_cards):
        new_card, old_card = new_cards[scenario_id], old_cards[scenario_id]
        new_artifact = run_card(new_card, release=release)
        old_artifact = old_lab.episodes.execute_episode(
            old_card.input, old_fixtures[old_card.fixture_id], followups=old_card.followups,
            max_turns=old_card.max_turns, scenario_id=scenario_id, release=release, trial=1,
            mode="scripted", prompt=old_lab.agents.PROMPTS[release])

        new_verdicts = [(v.name, v.passed) for v in evaluate(new_artifact, new_card.expected_output.model_dump())]
        old_verdicts = [(v.name, v.passed)
                        for v in old_lab.evaluators.evaluate(old_artifact, old_card.expected_output.model_dump())]
        assert new_verdicts == old_verdicts, scenario_id
        # 판정보다 강한 비교: 서비스 호출, 응답, 최종 상태, 사용량까지 같아야 한다.
        assert tool_trace(new_artifact) == tool_trace(old_artifact), scenario_id
        assert new_artifact.response.model_dump() == old_artifact.response.model_dump(), scenario_id
        assert new_artifact.final_state == old_artifact.final_state, scenario_id
        assert new_artifact.execution_status == old_artifact.execution_status == "completed", scenario_id
        assert (new_artifact.model_calls, new_artifact.cost_usd) == (old_artifact.model_calls, old_artifact.cost_usd)
        assert new_artifact.gate_events == []


def test_equivalence_comparison_can_see_a_difference():
    """음성 대조: 위 비교가 차이를 실제로 잡는지 확인한다. 환불 TIMEOUT 처리는 release마다 다르다."""
    differing = []
    for card in load_dataset(split="dev"):
        baseline = run_card(card, release="baseline")
        candidate = run_card(card, release="candidate")
        if tool_trace(baseline) != tool_trace(candidate):
            differing.append(card.metadata.scenario_id)
    assert differing, "baseline과 candidate가 모든 시나리오에서 같으면 비교가 차이를 못 보는 것이다."


# ---------------------------------------------------------------- (b) 가짜 모델로 live Episode

def test_fake_live_episode_cancels_order_and_counts_model_calls():
    """가짜 모델이 정상 취소 대본을 따르면 주문이 취소되고 모델 호출 9회가 집계된다. 비용은 미확인(None)이다."""
    card = dev_card("normal")
    assert card.fixture_id == "fx-normal"
    fixture = load_fixtures()[card.fixture_id]
    model = FakeChatModel.scripted(normal_cancellation_script(fixture))

    artifact = run_card(card, mode="live", model=model)

    assert artifact.execution_status == "completed", artifact.error_type
    assert artifact.final_state["orders"][fixture["subject_id"]]["status"] == "cancelled"
    assert artifact.model_calls == 9  # 도구 호출 8회 + 구조화 응답 1회
    assert artifact.cost_usd is None  # Anthropic 응답에 비용 필드가 없으므로 0이 아니라 미확인
    assert artifact.input_tokens is None  # 가짜 모델은 usage_metadata가 없어 토큰도 미확인
    assert [event.tool for event in artifact.events] == NORMAL_TOOL_ORDER
    assert [event.call_id for event in artifact.events] == [f"call-{i}" for i in range(1, 9)]
    assert model.bound_tools[0] == [*ALL_TOOL_NAMES, "Response"]
    assert artifact.response.kind == "completed"
    statuses = {v.name: v.status for v in evaluate(artifact, card.expected_output.model_dump())}
    assert set(statuses.values()) == {"PASS"}, statuses


# ---------------------------------------------------------------- (c) 하네스 게이트

def test_call_tool_contract():
    """call_tool: 게이트 없음 = env.call, allow는 실행, block/ask는 실행하지 않고 막힌 결과를 돌려준다."""
    fixture = load_fixtures()["fx-normal"]
    order_id = fixture["subject_id"]
    env = OrderEnvironment(fixture)
    seen_prefixes = []

    def recording_gate(prefix_events, tool, args):
        seen_prefixes.append([event.tool for event in prefix_events])
        prefix_events.clear()  # 게이트가 받은 목록을 지워도 원본 기록은 그대로여야 한다.
        actions = {"get_order": "allow", "get_payment": "ask", "check_cancel_policy": "block"}
        return GateDecision(action=actions[tool], rule_id=None if tool == "get_order" else f"rule-{tool}")

    # 게이트 없음: 기록이 하나 생기고 gate_events는 비어 있다.
    assert call_tool(env, "get_order", {"order_id": order_id})["status"] == "ok"
    assert len(env.events) == 1 and env.gate_events == []

    # allow: 서비스에 닿는다.
    assert call_tool(env, "get_order", {"order_id": order_id}, gate=recording_gate)["status"] == "ok"
    # ask: 서비스에 닿지 않고 NEEDS_CONFIRMATION을 돌려준다.
    asked = call_tool(env, "get_payment", {"order_id": order_id}, gate=recording_gate)
    assert asked == {"status": "blocked", "code": "NEEDS_CONFIRMATION", "rule_id": "rule-get_payment", "reason": ""}
    # block: 서비스에 닿지 않고 POLICY_BLOCKED를 돌려준다.
    blocked = call_tool(env, "check_cancel_policy", {"order_id": order_id}, gate=recording_gate)
    assert blocked["code"] == "POLICY_BLOCKED"

    assert [event.tool for event in env.events] == ["get_order", "get_order"]
    assert [g.decision.action for g in env.gate_events] == ["allow", "ask", "block"]
    assert seen_prefixes == [["get_order"], ["get_order", "get_order"], ["get_order", "get_order"]]

    # GateDecision이 아닌 값은 통과로 간주하지 않는다.
    with pytest.raises(TypeError):
        call_tool(env, "get_order", {"order_id": order_id}, gate=lambda *_: "allow")
    env.close()


def assert_order_untouched(artifact) -> None:
    """주문·결제·재고·환불·재고복원 기록이 처음과 같은지 확인한다(티켓은 이관 때문에 생길 수 있다)."""
    for table in ("orders", "payments", "inventory", "refunds", "releases"):
        assert artifact.final_state[table] == artifact.initial_state[table], table


def test_gate_blocks_begin_cancellation_in_scripted_episode():
    """scripted: 게이트가 begin_cancellation을 막으면 주문은 그대로이고 막힌 호출은 서비스 기록에 없다."""
    artifact = run_card(dev_card("normal"), gate=block_begin_cancellation)

    assert artifact.execution_status == "completed", artifact.error_type
    assert_order_untouched(artifact)
    blocks = [g for g in artifact.gate_events if g.decision.action == "block"]
    assert len(blocks) == 1
    assert blocks[0].tool == "begin_cancellation" and blocks[0].decision.rule_id == "test-block-begin"
    assert "begin_cancellation" not in [event.tool for event in artifact.events]
    # 서비스에 닿은 호출은 모두 allow 결정을 거쳤다.
    allowed = [g for g in artifact.gate_events if g.decision.action == "allow"]
    assert [g.tool for g in allowed] == [event.tool for event in artifact.events]
    assert artifact.response.kind == "escalated"


def test_gate_blocks_begin_cancellation_in_fake_live_episode():
    """live: 막힌 결과가 모델에 도구 결과로 돌아가고, 서비스에는 닿지 않는다."""
    card = dev_card("normal")
    fixture = load_fixtures()[card.fixture_id]
    order_id = fixture["subject_id"]
    script = normal_cancellation_script(fixture)[:3] + [
        tool_call_message(4, "create_ticket", order_id=order_id, reason="정책 차단으로 취소 시작 불가"),
        tool_call_message(5, "Response", kind="escalated", message="취소를 시작하지 못해 담당자에게 넘겼습니다.",
                          order_id=order_id),
    ]
    model = RecordingFakeChatModel.scripted(script)

    artifact = run_card(card, mode="live", model=model, gate=block_begin_cancellation)

    assert artifact.execution_status == "completed", artifact.error_type
    assert_order_untouched(artifact)
    assert [g.decision.action for g in artifact.gate_events].count("block") == 1
    assert [event.tool for event in artifact.events] == ["get_order", "check_cancel_policy", "create_ticket"]
    # 네 번째 모델 호출이 받은 메시지 안에 call-3의 막힌 결과가 있다.
    tool_messages = [m for m in model.seen[3] if isinstance(m, ToolMessage) and m.tool_call_id == "call-3"]
    assert len(tool_messages) == 1
    assert "POLICY_BLOCKED" in tool_messages[0].content and "test-block-begin" in tool_messages[0].content


def test_custom_scripted_driver_with_gate_is_refused():
    """직접 만든 드라이버와 gate를 함께 주면 게이트가 조용히 무시되지 않도록 ValueError를 낸다."""
    card = dev_card("normal")
    with pytest.raises(ValueError):
        run_card(card, gate=block_begin_cancellation, scripted_driver=lambda request, env, release: None)


def test_custom_scripted_driver_replaces_default():
    """scripted_driver를 주면 기본 run_scripted 대신 그 드라이버가 턴을 처리한다."""
    from eval_lab.contracts import Response

    def ask_for_confirmation(request, env, release):
        call_tool(env, "get_order", {"order_id": request.order_id})
        return Response(kind="escalated", message="확인 필요", order_id=request.order_id), {}

    artifact = run_card(dev_card("normal"), scripted_driver=ask_for_confirmation)
    assert [event.tool for event in artifact.events] == ["get_order"]
    assert artifact.response.message == "확인 필요"


# ---------------------------------------------------------------- (d) Langfuse root observation

@contextmanager
def memory_langfuse():
    """실제 Langfuse SDK를 네트워크 없이 쓴다. (client, exporter)를 주고, 내보낸 span은 메모리 exporter에 모인다.

    Langfuse는 public_key마다 자원을 하나만 만들어 재사용한다(싱글턴). 앞 시험의 exporter가
    남지 않도록 만들기 전과 끝난 뒤에 비운다. TracerProvider는 전역을 건드리지 않게 따로 만든다.
    test_traffic.py도 이 함수를 불러 쓴다.
    """
    from langfuse import Langfuse
    from langfuse._client.resource_manager import LangfuseResourceManager
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    LangfuseResourceManager.reset()
    exporter = InMemorySpanExporter()
    client = Langfuse(public_key="pk-lf-test", secret_key="sk-lf-test", base_url="http://127.0.0.1:9",
                      span_exporter=exporter, tracer_provider=TracerProvider())
    try:
        yield client, exporter
    finally:
        client.shutdown()
        LangfuseResourceManager.reset()


@pytest.fixture
def langfuse_memory():
    """memory_langfuse를 시험 하나 동안 연다."""
    with memory_langfuse() as opened:
        yield opened


def ancestors(span, by_id: dict) -> list[int]:
    """span의 조상 span ID를 가까운 것부터 모은다."""
    found = []
    parent = span.parent
    while parent is not None:
        found.append(parent.span_id)
        parent_span = by_id.get(parent.span_id)
        parent = parent_span.parent if parent_span is not None else None
    return found


def assert_one_root_per_episode(spans, artifact, *, mode: str, environment_tag: str, tags: list[str]) -> None:
    """Episode 하나가 root observation 하나와 그 아래 span들로만 기록됐는지 확인한다."""
    # 1단계: 이 Episode의 span(session.id = episode_id)을 고르고 root가 하나인지 본다.
    episode_spans = [s for s in spans if s.attributes.get("session.id") == artifact.episode_id]
    roots = [s for s in episode_spans if s.parent is None]
    assert len(roots) == 1
    root = roots[0]
    assert root.name == "episode"
    assert root.attributes["langfuse.observation.type"] == "agent"

    # 2단계: 모든 span이 같은 trace이고, 그 trace의 모든 span이 이 Episode의 것이다.
    trace_id = root.context.trace_id
    assert {s.context.trace_id for s in episode_spans} == {trace_id}
    same_trace = [s for s in spans if s.context.trace_id == trace_id]
    assert len(same_trace) == len(episode_spans)
    assert {turn.trace_id for turn in artifact.turns} == {format(trace_id, "032x")}

    # 3단계: service.* span은 서비스 Event 수만큼 있고 모두 root의 자손이다.
    by_id = {s.context.span_id: s for s in same_trace}
    service_spans = [s for s in same_trace if s.name.startswith("service.")]
    assert len(service_spans) == len(artifact.events)
    for span in service_spans:
        assert root.context.span_id in ancestors(span, by_id), span.name

    # 4단계: Episode 단위 속성이 root에 붙었다.
    attributes = root.attributes
    assert attributes["langfuse.version"] == artifact.release
    assert attributes["langfuse.environment"] == environment_tag
    assert list(attributes["langfuse.trace.tags"]) == tags
    assert attributes["langfuse.trace.metadata.scenario_id"] == artifact.scenario_id
    assert attributes["langfuse.trace.metadata.trial"] == str(artifact.trial)
    assert attributes["langfuse.trace.metadata.mode"] == mode

    # 5단계: root 입력은 첫 요청, 출력은 Artifact 요약이며 요약만으로 Artifact를 다시 만들 수 있다.
    assert json.loads(attributes["langfuse.observation.input"]) == artifact.initial_request.model_dump(mode="json")
    output = json.loads(attributes["langfuse.observation.output"])
    assert output["response"] == artifact.response.model_dump(mode="json")
    assert output["status"] == artifact.execution_status == "completed"
    assert output == episode_summary(artifact)
    rebuilt = artifact_from_summary(output)
    assert rebuilt.model_dump(exclude={"model_events"}) == artifact.model_dump(exclude={"model_events"})


def test_each_episode_is_one_root_observation(langfuse_memory):
    """scripted Episode와 가짜 모델 live Episode가 각각 root observation 하나로 기록된다."""
    client, exporter = langfuse_memory
    card = dev_card("normal")
    fixture = load_fixtures()[card.fixture_id]
    labels = {"environment_tag": "day05-test", "tags": ["offline-test"]}

    scripted = run_card(card, langfuse=client, **labels)
    live = run_card(card, mode="live", model=FakeChatModel.scripted(normal_cancellation_script(fixture)),
                    langfuse=client, **labels)
    client.flush()
    spans = exporter.get_finished_spans()

    assert_one_root_per_episode(spans, scripted, mode="scripted", **labels)
    assert_one_root_per_episode(spans, live, mode="live", **labels)
    # 두 Episode는 서로 다른 trace이고, 어느 Episode에도 속하지 않는 span은 없다.
    assert scripted.turns[0].trace_id != live.turns[0].trace_id
    assert {s.attributes.get("session.id") for s in spans} == {scripted.episode_id, live.episode_id}
    # live trace에는 LangChain 콜백이 남긴 모델 호출 기록도 같은 trace 안에 있다.
    live_names = {s.name for s in spans if s.attributes.get("session.id") == live.episode_id}
    assert "LangGraph" in live_names


def test_record_release_writes_trace_id_per_row(langfuse_memory, tmp_path):
    """record_release(live, langfuse)는 행마다 그 Episode의 trace ID를 남긴다. root는 Episode가 끝나면 닫힌다."""
    client, exporter = langfuse_memory
    card = dev_card("normal")
    frozen = frozen_snapshot([card])
    model = FakeChatModel.scripted(normal_cancellation_script(load_fixtures()[card.fixture_id]))

    report = runs.record_release(frozen, release="baseline", prompt=COMMON_PROMPT, repeats=1, mode="live",
                                 out=tmp_path / "live.json", model=model, langfuse=client)

    row = report["rows"][0]
    assert report["status"] == "completed"
    assert row["trace_id"] is not None
    root_trace_ids = {format(s.context.trace_id, "032x") for s in exporter.get_finished_spans() if s.parent is None}
    assert root_trace_ids == {row["trace_id"]}
    assert report["config"]["agent_model"] == "FakeChatModel"
    assert report["config"]["gate"] is None


def test_version_label_reaches_langfuse_instead_of_release(langfuse_memory):
    """version을 주면 Langfuse version이 그 정책·Prompt 버전 이름이 된다. 주지 않으면 release다."""
    client, exporter = langfuse_memory
    card = dev_card("normal")

    labelled = run_card(card, langfuse=client, version="policy-r2")
    default = run_card(card, langfuse=client)
    client.flush()
    spans = exporter.get_finished_spans()

    def versions(artifact) -> set:
        """이 Episode(session.id = episode_id)의 span들이 단 Langfuse version 값."""
        return {s.attributes.get("langfuse.version") for s in spans
                if s.attributes.get("session.id") == artifact.episode_id}

    # root와 그 아래 모든 span이 같은 version을 단다. Artifact의 release는 그대로다.
    assert versions(labelled) == {"policy-r2"}
    assert versions(default) == {"baseline"}
    assert labelled.release == "baseline"


def test_summary_round_trip_keeps_awaiting_user():
    """awaiting_user는 root observation 요약에 실리고, 요약에서 다시 만든 Artifact에도 남는다."""
    waiting = run_card(dev_card("missing-id")).model_copy(update={"awaiting_user": True})
    summary = episode_summary(waiting)

    assert summary["awaiting_user"] is True
    assert artifact_from_summary(summary).awaiting_user is True
    assert artifact_from_summary(json.loads(json.dumps(summary))).awaiting_user is True


def test_summary_without_awaiting_user_rebuilds_as_finished():
    """awaiting_user가 생기기 전의 요약도 다시 만들 수 있고, 그 값은 False(끝난 Episode)다."""
    summary = episode_summary(run_card(dev_card("missing-id")).model_copy(update={"awaiting_user": True}))
    older = {key: value for key, value in summary.items() if key != "awaiting_user"}

    assert artifact_from_summary(older).awaiting_user is False


def test_scripted_runner_never_leaves_an_episode_awaiting_user():
    """execute_episode는 후속 입력 수 + 1 <= 최대 턴을 확인하므로, 추가 질문으로 끝난 Episode도 끝난 Episode다."""
    artifact = run_card(dev_card("missing-id"))

    assert artifact.response.kind == "clarification"
    assert artifact.awaiting_user is False


# ---------------------------------------------------------------- 실행 기록·채점·반례

def frozen_snapshot(cards) -> dict:
    """record_release가 읽는 동결 문서를 시험용으로 만든다(authoring.freeze의 결과와 같은 필드)."""
    fixtures = load_fixtures()
    dumped = [card.model_dump() for card in cards]
    snapshot = {"cards": dumped, "fixtures": {c["fixture_id"]: fixtures[c["fixture_id"]] for c in dumped}}
    return {"run_id": "test-frozen", "snapshot": snapshot, "snapshot_hash": fingerprint(snapshot)}


def test_scripted_record_grade_compare_round_trip(tmp_path):
    """scripted 원자료를 저장·검증·채점·비교하고 근거 문서를 만든다. 모델·Judge 호출은 없다."""
    frozen = frozen_snapshot(load_dataset(split="dev"))
    paths = {release: tmp_path / f"{release}.json" for release in ("baseline", "candidate")}
    for release, path in paths.items():
        runs.record_release(frozen, release=release, prompt=PROMPTS[release], repeats=1, mode="scripted", out=path)

    raws = {release: runs.read_recording(path) for release, path in paths.items()}
    for raw in raws.values():
        assert raw["status"] == "completed" and len(raw["rows"]) == 9
        assert all(row["trace_id"] is None for row in raw["rows"])
        assert raw["config"]["agent_model"] is None and raw["config"]["gate"] is None
        assert set(raw["config"]["code_hashes"]) == set(runs.EXECUTION_FILES)

    scored = {release: runs.grade_recording(raw) for release, raw in raws.items()}
    names = {v["name"] for row in scored["baseline"]["rows"] for v in row["verdicts"]}
    assert "episode" in names and "response_semantics" not in names  # scripted는 Judge 판정 칸이 없다.

    comparison = runs.compare_scored(scored["baseline"], scored["candidate"])
    assert sum(comparison["comparison"]["all_repeat_transitions"].values()) == 9
    assert comparison["gates"] == {"baseline": None, "candidate": None}

    evidence_path = evidence.inspect_recording(raws["baseline"], tmp_path / "evidence", tmp_path / "plan.json")
    assert evidence_path.exists()


def test_tampered_recording_is_rejected(tmp_path):
    """저장 후 원자료를 고치면 read_recording이 거부한다."""
    path = tmp_path / "base.json"
    runs.record_release(frozen_snapshot([dev_card("normal")]), release="baseline", prompt=COMMON_PROMPT,
                        repeats=1, mode="scripted", out=path)
    data = json.loads(path.read_text())
    data["rows"][0]["artifact"]["response"]["kind"] = "refused"
    path.write_text(json.dumps(data, ensure_ascii=False))
    with pytest.raises(ValueError):
        runs.read_recording(path)


def test_live_record_requires_model(tmp_path):
    """live 실행에 모델이 없으면 기본 모델을 몰래 만들지 않고 멈춘다."""
    with pytest.raises(ValueError):
        runs.record_release(frozen_snapshot([dev_card("normal")]), release="baseline", prompt=COMMON_PROMPT,
                            repeats=1, mode="live", out=tmp_path / "live.json")


def test_live_recording_without_judge_marks_semantics_insufficient(tmp_path):
    """live 원자료를 Judge 없이 채점하면 response_semantics는 INSUFFICIENT_EVIDENCE다."""
    card = dev_card("normal")
    model = FakeChatModel.scripted(normal_cancellation_script(load_fixtures()[card.fixture_id]))
    path = tmp_path / "live.json"
    runs.record_release(frozen_snapshot([card]), release="baseline", prompt=COMMON_PROMPT, repeats=1,
                        mode="live", out=path, model=model)
    scored = runs.grade_recording(runs.read_recording(path))
    semantics = [v for v in scored["rows"][0]["verdicts"] if v["name"] == "response_semantics"]
    assert [v["status"] for v in semantics] == ["INSUFFICIENT_EVIDENCE"]


def test_counterexamples_accept_a_correct_learner_check():
    """반례 검사(verify_learner_check)가 이식한 Episode 위에서 올바른 수강생 검사를 통과시킨다."""

    def no_write_before_target(artifact) -> Verdict:
        if not artifact.turns:
            return Verdict(name="learner_check", status="INSUFFICIENT_EVIDENCE", passed=None, reason="턴 기록 없음")
        unknown_target_ids = {eid for turn in artifact.turns if turn.request.order_id is None for eid in turn.event_ids}
        writes = [e for e in artifact.events if e.tool in WRITE_TOOLS and e.event_id in unknown_target_ids]
        return verdict("learner_check", not writes, "대상 확인 전 쓰기 시도 없음" if not writes else "대상 확인 전 쓰기", writes)

    verify_learner_check(no_write_before_target)
