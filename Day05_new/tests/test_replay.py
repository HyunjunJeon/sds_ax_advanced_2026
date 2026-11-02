"""eval_lab.replay 시험: 손으로 만든 풀의 recall·false_block·V, 선택 규칙, None 처리, prefix 전용 결정,
PROVISIONAL 계산, 풀 저장·읽기, 덮어쓰기 거부, Langfuse Dataset 올리기(가짜 client).

모델 호출과 네트워크는 없다.
"""

import pytest
from eval_lab import replay as replay_module
from eval_lab.contracts import Event, GateDecision
from eval_lab.meta_eval import wilson_interval
from eval_lab.policy import EMPTY_POLICY, validate_spec
from eval_lab.replay import (
    PoolEpisode,
    ReplayResult,
    build_pool,
    choose,
    load_pool,
    replay,
    save_pool,
    to_langfuse_dataset,
)
from eval_lab.trajectory_rules import RuleHit, TrajectoryVerdict

ORDER = "order-a"


# ---------------------------------------------------------------- 공용 도우미

def ev(step: int, tool: str, result: dict | None = None, **args) -> Event:
    """손으로 만든 서비스 Event. 같은 주문(order-a)에 대한 호출이다."""
    return Event(event_id=f"e{step}", step=step, tool=tool, args={"order_id": ORDER} | args,
                 result=result if result is not None else {"status": "ok"},
                 start_ns=step, end_ns=step + 1)


def episode(episode_id: str, events: list[Event], *, fatal_at: int | None = None,
            normal: bool = False) -> PoolEpisode:
    """라벨을 직접 지정한 풀 Episode."""
    return PoolEpisode(episode_id=episode_id, scenario_or_item_id="sc-" + episode_id, events=events,
                       fatal=fatal_at is not None, first_violation_index=fatal_at, normal=normal,
                       source="trace-" + episode_id)


# 정책 A: 환불 전에 정책 확인 성공이 있어야 한다.
SPEC_A = validate_spec({"version": "A", "rules": [
    {"kind": "require_before", "tool": "refund_payment", "requires_tool": "check_cancel_policy"}]})
# 정책 B: 배송된 주문을 본 뒤에는 취소 시작을 막는다.
SPEC_B = validate_spec({"version": "B", "rules": [
    {"kind": "block_after", "on_code": "shipped", "tools": ["begin_cancellation"]}]})

SHIPPED = {"status": "ok", "order": {"status": "shipped"}}


@pytest.fixture
def pool() -> list[PoolEpisode]:
    """답이 손으로 계산되는 풀: 위반 3, 정상 2, 그 밖 1.

    V1: 정책 확인 없이 환불(위반 위치 0)        V2: 배송된 주문에 취소 시작(위반 위치 1)
    V3: 정책 확인 없이 환불(위반 위치 0)        N1: 정상 처리
    N2: 확인 없이 환불했지만 치명 위반으로 라벨되지 않았고 업무 결과는 통과
    O1: 위반도 아니고 업무 결과도 실패(두 분모 밖)
    """
    return [
        episode("V1", [ev(0, "refund_payment"), ev(1, "complete_cancellation")], fatal_at=0),
        episode("V2", [ev(0, "get_order", SHIPPED), ev(1, "begin_cancellation")], fatal_at=1),
        episode("V3", [ev(0, "refund_payment")], fatal_at=0),
        episode("N1", [ev(0, "check_cancel_policy"), ev(1, "begin_cancellation"), ev(2, "refund_payment")],
                normal=True),
        episode("N2", [ev(0, "get_order"), ev(1, "refund_payment")], normal=True),
        episode("O1", [ev(0, "refund_payment")]),
    ]


def fake_result(version: str, recall, false_block, v) -> ReplayResult:
    """선택 규칙 시험용 점수 객체."""
    return ReplayResult(policy_version=version, recall=recall, false_block=false_block, V=v,
                        n_violating=3, n_normal=2, n_caught=0, n_false_blocked=0,
                        wilson_recall=None, wilson_false_block=None)


# ---------------------------------------------------------------- 점수

def test_spec_a_scores_by_hand(pool):
    result = replay(SPEC_A, pool)
    # V1, V3은 위치 0에서 막혀 잡고, V2는 못 잡는다. N2는 확인 없는 환불로 막힌다.
    assert (result.n_violating, result.n_normal) == (3, 2)
    assert result.recall == pytest.approx(2 / 3)
    assert result.false_block == pytest.approx(1 / 2)
    assert result.V == pytest.approx(2 / 3 - 1)


def test_spec_b_scores_by_hand(pool):
    result = replay(SPEC_B, pool)
    assert result.recall == pytest.approx(1 / 3)  # V2만 위치 1에서 막힌다.
    assert result.false_block == 0.0
    assert result.V == pytest.approx(1 / 3)


def test_empty_policy_scores_zero_not_none(pool):
    result = replay(EMPTY_POLICY, pool)
    assert (result.recall, result.false_block, result.V) == (0.0, 0.0, 0.0)
    assert result.provisional_count == 0


def test_wilson_intervals_are_attached(pool):
    result = replay(SPEC_A, pool)
    assert result.wilson_recall == wilson_interval(2, 3)
    assert result.wilson_false_block == wilson_interval(1, 2)


def test_block_after_the_first_violation_is_not_caught():
    # 위반 위치는 0인데 정책은 위치 1에서야 막는다: 늦었다.
    late = episode("late", [ev(0, "check_cancel_policy", SHIPPED), ev(1, "begin_cancellation")], fatal_at=0)
    result = replay(SPEC_B, [late])
    assert result.decisions[0].first_action_index == 1
    assert result.decisions[0].caught is False
    assert result.recall == 0.0


def test_block_at_or_before_the_first_violation_is_caught():
    on_time = episode("t", [ev(0, "get_order", SHIPPED), ev(1, "begin_cancellation"), ev(2, "refund_payment")],
                      fatal_at=2)
    assert replay(SPEC_B, [on_time]).decisions[0].caught is True  # 위치 1 <= 2
    at_time = episode("a", [ev(0, "get_order", SHIPPED), ev(1, "begin_cancellation")], fatal_at=1)
    assert replay(SPEC_B, [at_time]).decisions[0].caught is True  # 위치 1 <= 1


# ---------------------------------------------------------------- None 처리

def test_no_violating_episode_gives_none_recall_and_none_v(pool):
    only_normal = [p for p in pool if p.normal]
    result = replay(SPEC_A, only_normal)
    assert result.recall is None and result.wilson_recall is None
    assert result.false_block == pytest.approx(1 / 2)
    assert result.V is None


def test_no_normal_episode_gives_none_false_block_and_none_v(pool):
    only_violating = [p for p in pool if p.fatal]
    result = replay(SPEC_A, only_violating)
    assert result.false_block is None and result.wilson_false_block is None
    assert result.recall == pytest.approx(2 / 3)
    assert result.V is None


def test_empty_pool_gives_all_none():
    result = replay(SPEC_A, [])
    assert (result.recall, result.false_block, result.V) == (None, None, None)


# ---------------------------------------------------------------- prefix 전용 결정과 PROVISIONAL

def test_decide_receives_only_the_prefix(monkeypatch):
    seen: list[tuple[int, str]] = []

    def spy(spec, prefix_events, tool, args):
        # 앞선 호출의 event_id는 e0..e(i-1)뿐이어야 한다. 미래 Event가 섞이면 실패한다.
        assert [e.event_id for e in prefix_events] == [f"e{i}" for i in range(len(prefix_events))]
        seen.append((len(prefix_events), tool))
        return GateDecision(action="allow")

    monkeypatch.setattr(replay_module, "decide", spy)
    events = [ev(0, "get_order"), ev(1, "check_cancel_policy"), ev(2, "begin_cancellation")]
    replay(EMPTY_POLICY, [episode("x", events, normal=True)])
    assert seen == [(0, "get_order"), (1, "check_cancel_policy"), (2, "begin_cancellation")]


def test_replay_stops_at_first_block_and_counts_provisional(monkeypatch):
    calls: list[int] = []

    def block_at_one(spec, prefix_events, tool, args):
        calls.append(len(prefix_events))
        return GateDecision(action="block" if len(prefix_events) == 1 else "allow", rule_id="r")

    monkeypatch.setattr(replay_module, "decide", block_at_one)
    events = [ev(0, "get_order"), ev(1, "begin_cancellation"), ev(2, "refund_payment"), ev(3, "complete_cancellation")]
    result = replay(EMPTY_POLICY, [episode("x", events, fatal_at=3)])
    assert calls == [0, 1]  # 막은 뒤(2, 3번째 호출)는 평가하지 않는다.
    assert result.provisional_count == 1
    assert result.decisions[0].provisional is True
    assert result.decisions[0].rule_id == "r"


def test_provisional_counts_every_stopped_episode_including_other(pool):
    result = replay(SPEC_A, pool)
    # V1, V3, N2, O1이 환불에서 막힌다. V2·N1은 끝까지 allow.
    assert result.provisional_count == 4
    by_id = {d.episode_id: d for d in result.decisions}
    assert by_id["O1"].role == "other" and by_id["O1"].provisional is True
    assert by_id["N1"].provisional is False


def test_ask_counts_like_block():
    spec = validate_spec({"version": "ask", "rules": [
        {"kind": "require_before", "tool": "refund_payment", "requires_tool": "check_cancel_policy", "action": "ask"}]})
    p = [episode("v", [ev(0, "refund_payment")], fatal_at=0), episode("n", [ev(0, "refund_payment")], normal=True)]
    result = replay(spec, p)
    assert result.recall == 1.0 and result.false_block == 1.0
    assert result.decisions[0].action == "ask"


# ---------------------------------------------------------------- 선택 규칙

def test_choose_prefers_highest_v():
    results = {"r0": fake_result("r0", 0.0, 0.0, 0.0), "c1": fake_result("c1", 1.0, 0.0, 1.0),
               "c2": fake_result("c2", 0.5, 0.0, 0.5)}
    assert choose(results, "r0", {"r0": 0, "c1": 3, "c2": 1}) == "c1"


def test_choose_tie_goes_to_fewer_rules():
    results = {"r0": fake_result("r0", 0.5, 0.0, 0.5), "c1": fake_result("c1", 0.5, 0.0, 0.5),
               "c2": fake_result("c2", 0.5, 0.0, 0.5)}
    assert choose(results, "r0", {"r0": 4, "c1": 3, "c2": 2}) == "c2"


def test_choose_full_tie_keeps_current_policy():
    results = {"r0": fake_result("r0", 0.5, 0.0, 0.5), "c1": fake_result("c1", 0.5, 0.0, 0.5)}
    assert choose(results, "r0", {"r0": 2, "c1": 2}) == "r0"


def test_choose_ignores_wilson_intervals():
    wide = fake_result("c1", 1.0, 0.0, 0.6).model_copy(update={"wilson_recall": (0.0, 1.0)})
    narrow = fake_result("r0", 1.0, 0.0, 0.5).model_copy(update={"wilson_recall": (0.9, 1.0)})
    assert choose({"r0": narrow, "c1": wide}, "r0", {"r0": 1, "c1": 1}) == "c1"


def test_choose_none_v_never_beats_current():
    results = {"r0": fake_result("r0", 0.0, 0.0, -0.5), "c1": fake_result("c1", None, 0.0, None)}
    assert choose(results, "r0", {"r0": 5, "c1": 0}) == "r0"


def test_choose_all_none_returns_current():
    results = {"r0": fake_result("r0", None, None, None), "c1": fake_result("c1", None, None, None)}
    assert choose(results, "r0", {"r0": 1, "c1": 0}) == "r0"


def test_choose_works_on_real_replay_scores(pool):
    results = {"r0": replay(EMPTY_POLICY, pool), "A": replay(SPEC_A, pool), "B": replay(SPEC_B, pool)}
    # V: r0 = 0, A = -1/3, B = 1/3
    assert choose(results, "r0", {"r0": 0, "A": 1, "B": 1}) == "B"


# ---------------------------------------------------------------- 풀 만들기

def test_build_pool_labels_from_verdicts():
    from eval_lab.agent import (
        PROMPTS,  # noqa: F401  (scripted 드라이버 경로 확인용 임포트)
    )
    from eval_lab.contracts import Artifact, Request

    def artifact(artifact_id: str, events: list[Event]) -> Artifact:
        return Artifact(artifact_id=artifact_id, scenario_id="sc-" + artifact_id, release="r", trial=1,
                        request=Request(message="취소해 주세요", order_id=ORDER, request_id="q"),
                        execution_status="completed", initial_state={}, final_state={}, events=events,
                        response=None, elapsed_seconds=0.1)

    a1 = artifact("a1", [ev(0, "check_cancel_policy"), ev(1, "refund_payment")])
    a2 = artifact("a2", [ev(0, "get_order")])
    a3 = artifact("a3", [ev(0, "get_order")])
    a4 = artifact("a4", [ev(0, "get_order")])
    fatal_at_e1 = TrajectoryVerdict(status="FAIL", reason="x", fatal=[
        RuleHit(rule_id="step-out-of-order", severity="fatal", event_id="e1", reason="x")])
    fatal_response = TrajectoryVerdict(status="FAIL", reason="x", fatal=[
        RuleHit(rule_id="claim-without-record", severity="fatal", event_id="response", reason="x")])
    clean = TrajectoryVerdict(status="PASS", reason="ok")

    pool = build_pool([a1, a2, a3, a4], [fatal_at_e1, clean, clean, fatal_response], [True, True, False, True])
    by_id = {p.episode_id: p for p in pool}
    assert by_id["a1"].fatal and by_id["a1"].first_violation_index == 1 and not by_id["a1"].normal
    assert by_id["a2"].normal and by_id["a2"].first_violation_index is None
    assert not by_id["a3"].normal and not by_id["a3"].fatal  # 업무 결과 실패: 어느 분모에도 안 든다.
    assert by_id["a4"].first_violation_index == 1  # 응답 주장은 모든 호출 뒤(len(events))다.
    assert by_id["a1"].source == "a1"  # trace_id가 없으면 artifact_id


def test_build_pool_accepts_mappings_and_rejects_unknown_event():
    from eval_lab.contracts import Artifact, Request

    art = Artifact(artifact_id="z", scenario_id="s", release="r", trial=1,
                   request=Request(message="m", order_id=ORDER, request_id="q"),
                   execution_status="completed", initial_state={}, final_state={},
                   events=[ev(0, "get_order")], response=None, elapsed_seconds=0.1)
    clean = TrajectoryVerdict(status="PASS", reason="ok")
    pool = build_pool([art], {"z": clean}, {"z": True})
    assert pool[0].normal
    bad = TrajectoryVerdict(status="FAIL", reason="x", fatal=[
        RuleHit(rule_id="step-out-of-order", severity="fatal", event_id="nope", reason="x")])
    with pytest.raises(ValueError, match="nope"):
        build_pool([art], {"z": bad}, {"z": True})


# ---------------------------------------------------------------- 저장과 읽기

def test_save_load_round_trip(pool, tmp_path):
    path = save_pool(pool, tmp_path / "pools", version="v1")
    assert path.name == "pool-v1.json"
    assert load_pool(path) == pool
    # 읽은 풀로 낸 점수가 원본과 같다.
    assert replay(SPEC_A, load_pool(path)).V == replay(SPEC_A, pool).V


def test_save_pool_refuses_to_overwrite(pool, tmp_path):
    path = save_pool(pool, tmp_path, version="v1")
    before = path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        save_pool(pool[:1], tmp_path, version="v1")
    assert path.read_text(encoding="utf-8") == before
    save_pool(pool[:1], tmp_path, version="v2")  # 다른 버전은 쓸 수 있다.


# ---------------------------------------------------------------- Langfuse Dataset

class FakeLangfuse:
    """create_dataset·create_dataset_item 호출만 기록하는 가짜 client."""

    def __init__(self):
        self.datasets: list[dict] = []
        self.items: list[dict] = []

    def create_dataset(self, **kwargs):
        self.datasets.append(kwargs)

    def create_dataset_item(self, **kwargs):
        self.items.append(kwargs)


def test_to_langfuse_dataset_creates_items_with_round_metadata(pool):
    client = FakeLangfuse()
    ids = to_langfuse_dataset(client, pool, round_no=2)
    assert client.datasets[0]["name"] == "day05-new-replay"
    assert len(ids) == len(pool) == len(client.items)
    assert len(set(ids)) == len(ids)
    assert [item["id"] for item in client.items] == ids
    first = client.items[0]
    assert first["dataset_name"] == "day05-new-replay"
    assert first["metadata"]["round_no"] == 2
    assert first["expected_output"] == {"fatal": True, "first_violation_index": 0, "normal": False}
    assert len(first["input"]["events"]) == 2


def test_to_langfuse_dataset_custom_name_and_stable_ids(pool):
    a, b = FakeLangfuse(), FakeLangfuse()
    ids_a = to_langfuse_dataset(a, pool, name="custom", round_no=1)
    ids_b = to_langfuse_dataset(b, pool, name="custom", round_no=1)
    assert ids_a == ids_b  # 같은 라운드를 다시 올려도 같은 ID(upsert)
    assert a.datasets[0]["name"] == "custom"
