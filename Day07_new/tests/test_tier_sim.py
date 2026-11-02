"""tier_sim의 손 추적 검증. 기대값은 요청열을 손으로 따라간 결과다. block_tokens는 4를 쓴다."""

from __future__ import annotations

import inspect
from dataclasses import fields

import pytest

from vllm_lab import tier_sim
from vllm_lab.tier_sim import (
    NOT_MODELED,
    AgentRequest,
    ToyCosts,
    agent_workload,
    simulate_tiers,
)

TOKENS_17 = tuple(range(17))


def prompt(name: str, length: int = 9) -> AgentRequest:
    """이름마다 다른 token을 쓴다. block 4개짜리 token 9개면 꽉 찬 block 2개다."""
    base = 1000 * (ord(name[0]) - ord("A") + 1)
    return AgentRequest(name, tuple(range(base, base + length)))


def run(requests, **kwargs):
    return simulate_tiers(requests, block_tokens=4, **kwargs)


def tier_counts(row):
    return (row["gpu_hit_blocks"], row["cpu_hit_blocks"], row["disk_hit_blocks"])


# --- 적중 상한과 재계산 ---


def test_first_request_recomputes_everything_and_repeat_hits_full_blocks():
    rows = run([AgentRequest("a", TOKENS_17), AgentRequest("b", TOKENS_17)], gpu_blocks=10)["rows"]
    assert (rows[0]["hit_tokens"], rows[0]["recomputed_tokens"]) == (0, 17)
    assert tier_counts(rows[1]) == (4, 0, 0)
    assert (rows[1]["hit_tokens"], rows[1]["recomputed_tokens"]) == (16, 1)


def test_block_aligned_prompt_recomputes_its_whole_last_block():
    tokens = tuple(range(16))
    rows = run([AgentRequest("a", tokens), AgentRequest("b", tokens)], gpu_blocks=10)["rows"]
    assert (rows[1]["hit_tokens"], rows[1]["recomputed_tokens"]) == (12, 4)


def test_prompt_shorter_than_one_block_never_hits():
    tokens = (1, 2, 3)
    rows = run([AgentRequest("a", tokens), AgentRequest("b", tokens)], gpu_blocks=2)["rows"]
    assert (rows[1]["hit_tokens"], rows[1]["recomputed_tokens"]) == (0, 3)


def test_same_tokens_after_a_different_prefix_do_not_hit():
    first = AgentRequest("a", (1, 2, 3, 4, 5, 6, 7, 8, 9))
    second = AgentRequest("b", (9, 9, 9, 9, 5, 6, 7, 8, 9))
    rows = run([first, second], gpu_blocks=10)["rows"]
    assert rows[1]["hit_tokens"] == 0


def test_a_block_only_counts_when_every_block_before_it_matches():
    first = AgentRequest("a", (1, 2, 3, 4, 5, 6, 7, 8, 0))
    second = AgentRequest("b", (11, 12, 13, 14, 15, 16, 17, 18, 0))
    mixed = AgentRequest("c", (1, 2, 3, 4, 15, 16, 17, 18, 0))  # 앞 block은 a, 뒤 block은 b의 것
    rows = run([first, second, mixed], gpu_blocks=10)["rows"]
    assert rows[2]["hit_tokens"] == 4


def test_hit_stops_at_the_first_differing_block():
    first = AgentRequest("a", tuple(range(13)))
    second = AgentRequest("b", (0, 1, 2, 3, 4, 5, 6, 7, 99, 9, 10, 11, 12))
    rows = run([first, second], gpu_blocks=10)["rows"]
    assert rows[1]["hit_tokens"] == 8


# --- 층 사이 이동 ---


def test_evicted_blocks_step_down_and_a_hit_names_the_tier_it_came_from():
    a, b, c = prompt("A"), prompt("B"), prompt("C")
    tiers = {"gpu_blocks": 2, "cpu_blocks": 2, "disk_blocks": 2}
    assert tier_counts(run([a, b, a], **tiers)["rows"][2]) == (0, 2, 0)
    assert tier_counts(run([a, b, c, a], **tiers)["rows"][3]) == (0, 0, 2)
    assert tier_counts(run([a, a], **tiers)["rows"][1]) == (2, 0, 0)


def test_block_falling_off_the_last_tier_is_gone():
    a, b, c, d = prompt("A"), prompt("B"), prompt("C"), prompt("D")
    result = run([a, b, c, d, a], gpu_blocks=2, cpu_blocks=2, disk_blocks=2)
    assert result["rows"][4]["hit_tokens"] == 0
    # 요청마다 2 block씩 민다. B: A->cpu. C: B->cpu, A->disk. D: C->cpu, B->disk, A 버림. A: D->cpu, C->disk, B 버림.
    assert result["totals"]["dropped_blocks"] == 4
    assert result["totals"]["demoted_blocks"] == 14


def test_a_hit_moves_the_block_back_to_gpu_and_pushes_others_down():
    a, b, c = prompt("A"), prompt("B"), prompt("C")
    rows = run([a, b, c, b, c], gpu_blocks=2, cpu_blocks=2, disk_blocks=2)["rows"]
    assert tier_counts(rows[3]) == (0, 2, 0)  # B는 CPU에서 GPU로 올라가고 C가 CPU로 내려간다
    assert tier_counts(rows[4]) == (0, 2, 0)  # 그래서 C는 CPU에서 찾는다


def test_lru_keeps_the_recently_used_prefix_on_gpu():
    a, b, c = prompt("A"), prompt("B"), prompt("C")
    rows = run([a, b, a, c, a], gpu_blocks=4)["rows"]
    assert tier_counts(rows[4]) == (2, 0, 0)
    assert run([a, b, a, c, b], gpu_blocks=4)["rows"][4]["hit_tokens"] == 0


# --- 층 끄기 ---


def test_disabled_lower_tiers_turn_a_cpu_hit_into_a_recompute():
    a, b = prompt("A"), prompt("B")
    assert run([a, b, a], gpu_blocks=2, cpu_blocks=2)["rows"][2]["hit_tokens"] == 8
    off = run([a, b, a], gpu_blocks=2, cpu_blocks=2, disabled_tiers=("cpu",))
    assert off["rows"][2]["hit_tokens"] == 0
    assert off["rows"][2]["recomputed_tokens"] == 9
    assert off["enabled_tiers"] == ["gpu"]
    assert off["totals"]["demoted_blocks"] == 0
    assert off["totals"]["dropped_blocks"] == 4


def test_disabling_cpu_sends_evictions_straight_to_disk():
    a, b = prompt("A"), prompt("B")
    result = run([a, b, a], gpu_blocks=2, cpu_blocks=2, disk_blocks=2, disabled_tiers=("cpu",))
    assert tier_counts(result["rows"][2]) == (0, 0, 2)
    assert result["enabled_tiers"] == ["gpu", "disk"]


def test_zero_capacity_tier_counts_as_absent():
    assert run([prompt("A")], gpu_blocks=2, cpu_blocks=0, disk_blocks=1)["enabled_tiers"] == ["gpu", "disk"]


def test_gpu_tier_cannot_be_disabled():
    with pytest.raises(ValueError, match="gpu 층은 끌 수 없습니다"):
        run([], gpu_blocks=2, disabled_tiers=("gpu",))


def test_unknown_tier_is_rejected_by_name():
    with pytest.raises(ValueError, match="nvme"):
        run([], gpu_blocks=2, disabled_tiers=("nvme",))


# --- KDA 상태 경계 ---


def test_kda_hit_stops_at_the_last_state_checkpoint_boundary():
    tokens = tuple(range(29))  # 꽉 찬 block 7개, 상한도 7개
    repeat = [AgentRequest("a", tokens), AgentRequest("b", tokens)]
    plain = run(repeat, gpu_blocks=10)["rows"][1]
    assert (plain["hit_tokens"], plain["recomputed_tokens"], plain["discarded_by_checkpoint_tokens"]) == (28, 1, 0)
    kda = run(repeat, gpu_blocks=10, state_checkpoint_blocks=3)["rows"][1]
    assert (kda["hit_tokens"], kda["recomputed_tokens"], kda["discarded_by_checkpoint_tokens"]) == (24, 5, 4)
    assert tier_counts(kda) == (6, 0, 0)


def test_kda_match_shorter_than_one_checkpoint_gets_nothing():
    a = prompt("A")
    row = run([a, a], gpu_blocks=10, state_checkpoint_blocks=3)["rows"][1]
    assert (row["hit_tokens"], row["recomputed_tokens"], row["discarded_by_checkpoint_tokens"]) == (0, 9, 8)
    assert tier_counts(row) == (0, 0, 0)


def test_kda_boundary_exact_match_keeps_all_blocks():
    tokens = tuple(range(13))  # 꽉 찬 block 3개
    row = run([AgentRequest("a", tokens)] * 2, gpu_blocks=10, state_checkpoint_blocks=3)["rows"][1]
    assert (row["hit_tokens"], row["discarded_by_checkpoint_tokens"]) == (12, 0)


def test_kda_rule_counts_only_blocks_reused_from_a_lower_tier():
    a, b = prompt("A", 13), prompt("B", 13)
    rows = run([a, b, a], gpu_blocks=3, cpu_blocks=3, state_checkpoint_blocks=2)["rows"]
    assert tier_counts(rows[2]) == (0, 2, 0)
    assert rows[2]["discarded_by_checkpoint_tokens"] == 4


@pytest.mark.parametrize("value", [0, -1])
def test_checkpoint_interval_must_be_positive(value):
    with pytest.raises(ValueError, match="state_checkpoint_blocks"):
        run([], gpu_blocks=2, state_checkpoint_blocks=value)


# --- toy 비용 ---


def test_toy_ms_adds_block_costs_by_tier_and_token_recomputes():
    a, b, c = prompt("A"), prompt("B"), prompt("C")
    costs = ToyCosts(toy_gpu_ms_per_block=1, toy_cpu_ms_per_block=10, toy_disk_ms_per_block=100,
                     toy_recompute_ms_per_token=1000)
    rows = run([a, a, b, a, b, c, b], gpu_blocks=2, cpu_blocks=2, disk_blocks=2, toy_costs=costs)["rows"]
    assert rows[0]["toy_ms"] == 9000
    assert rows[1]["toy_ms"] == 1002  # GPU 2 block + token 1개
    assert rows[3]["toy_ms"] == 1020  # CPU 2 block + token 1개
    assert rows[6]["toy_ms"] == 1020


def test_toy_disk_cost_comes_from_its_own_constant():
    a, b, c = prompt("A"), prompt("B"), prompt("C")
    costs = ToyCosts(toy_gpu_ms_per_block=1, toy_cpu_ms_per_block=10, toy_disk_ms_per_block=100,
                     toy_recompute_ms_per_token=1000)
    row = run([a, b, c, a], gpu_blocks=2, cpu_blocks=2, disk_blocks=2, toy_costs=costs)["rows"][3]
    assert row["toy_ms"] == 1200


def test_totals_add_up_the_rows():
    a, b = prompt("A"), prompt("B")
    result = run([a, b, a], gpu_blocks=2, cpu_blocks=2)
    totals = result["totals"]
    assert (totals["prompt_tokens"], totals["hit_tokens"], totals["recomputed_tokens"]) == (27, 8, 19)
    assert totals["cpu_hit_blocks"] == 2
    # 9 + 9 + (CPU 2 block * 1.0 + token 1개 * 1.0)
    assert totals["toy_ms"] == 21.0


def test_every_cost_and_time_name_is_toy():
    assert all(field.name.startswith("toy_") for field in fields(ToyCosts))
    result = run([prompt("A")], gpu_blocks=2)
    time_names = [name for name in {**result["totals"], **result["rows"][0]} if "ms" in name]
    assert time_names == ["toy_ms"]
    assert "측정이 아니다" in result["note"]


def test_module_never_claims_real_latency():
    source = inspect.getsource(tier_sim)
    assert "teaching" in source
    assert "latency" not in source.lower()
    assert "실제 지연이 아니고" in source


def test_not_modeled_states_what_the_model_omits():
    assert isinstance(NOT_MODELED, tuple) and len(NOT_MODELED) >= 8
    joined = "\n".join(NOT_MODELED)
    for needle in ("실제 지연", "LMCache", "FlashKDA", "동시 실행", "sliding window", "kv_load_failure_policy"):
        assert needle in joined


# --- 입력 경계와 재현성 ---


def test_request_bigger_than_gpu_is_refused_with_the_numbers():
    with pytest.raises(ValueError, match="block 4개가 gpu_blocks=3"):
        run([AgentRequest("big", TOKENS_17)], gpu_blocks=3)


def test_empty_prompt_is_refused_by_request_id():
    with pytest.raises(ValueError, match="empty-one"):
        run([AgentRequest("empty-one", ())], gpu_blocks=3)


@pytest.mark.parametrize("kwargs", [
    {"gpu_blocks": 0}, {"gpu_blocks": 2, "cpu_blocks": -1}, {"gpu_blocks": 2, "disk_blocks": -1}])
def test_bad_capacity_is_refused(kwargs):
    with pytest.raises(ValueError, match="gpu_blocks="):
        run([], **kwargs)


def test_block_tokens_must_be_positive():
    with pytest.raises(ValueError, match="block_tokens=0"):
        simulate_tiers([], gpu_blocks=2, block_tokens=0)


def test_no_requests_give_zero_totals():
    totals = run([], gpu_blocks=2)["totals"]
    assert (totals["prompt_tokens"], totals["toy_ms"]) == (0, 0)


def test_same_input_gives_the_same_result():
    workload = agent_workload(sessions=3, turns=5, shared_prefix_tokens=64, tokens_per_turn=16)
    kwargs = {"gpu_blocks": 36, "cpu_blocks": 12, "disk_blocks": 12, "state_checkpoint_blocks": 2}
    assert run(workload, **kwargs) == run(workload, **kwargs)


# --- 에이전트 요청열 ---


def test_agent_workload_shares_the_prefix_and_grows_each_turn():
    requests = agent_workload(sessions=2, turns=2, shared_prefix_tokens=8, tokens_per_turn=4)
    assert [r.request_id for r in requests] == ["s0-t1", "s1-t1", "s0-t2", "s1-t2"]
    assert [len(r.tokens) for r in requests] == [12, 12, 16, 16]
    assert requests[0].tokens[:8] == requests[1].tokens[:8] == tuple(range(8))
    assert requests[0].tokens[8:] != requests[1].tokens[8:]
    assert requests[2].tokens[:12] == requests[0].tokens


def test_agent_workload_session_tokens_do_not_collide():
    requests = agent_workload(sessions=3, turns=3, shared_prefix_tokens=2, tokens_per_turn=5)
    last_turn = requests[-3:]
    owned = [set(r.tokens[2:]) for r in last_turn]
    assert not (owned[0] & owned[1] or owned[1] & owned[2] or owned[0] & owned[2])
    assert not any(owned_set & {0, 1} for owned_set in owned)


def test_agent_workload_hand_trace_on_a_large_gpu():
    requests = agent_workload(sessions=2, turns=2, shared_prefix_tokens=8, tokens_per_turn=4)
    result = run(requests, gpu_blocks=100)
    assert [row["hit_tokens"] for row in result["rows"]] == [0, 8, 12, 12]
    assert result["totals"]["recomputed_tokens"] == 24


def test_small_gpu_loses_turn_hits_and_a_cpu_tier_brings_them_back():
    requests = agent_workload(sessions=4, turns=3, shared_prefix_tokens=16, tokens_per_turn=16)
    gpu_only = run(requests, gpu_blocks=16)["totals"]
    with_cpu = run(requests, gpu_blocks=16, cpu_blocks=40)["totals"]
    assert gpu_only["cpu_hit_blocks"] == 0
    assert with_cpu["cpu_hit_blocks"] > 0
    assert with_cpu["recomputed_tokens"] < gpu_only["recomputed_tokens"]


@pytest.mark.parametrize("kwargs", [
    {"sessions": 0}, {"turns": 0}, {"tokens_per_turn": 0}, {"shared_prefix_tokens": -1}])
def test_agent_workload_rejects_bad_sizes(kwargs):
    base = {"sessions": 1, "turns": 1, "shared_prefix_tokens": 0, "tokens_per_turn": 1}
    with pytest.raises(ValueError, match="sessions="):
        agent_workload(**{**base, **kwargs})
