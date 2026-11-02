"""kv_sim 규칙 검사. 기대값은 손으로 센 값이다(구현 식을 다시 계산하지 않는다)."""
from __future__ import annotations

import json

import pytest

from vllm_lab import kv_sim
from vllm_lab.kv_sim import (
    PAD_SLOT_ID, BlockPool, GroupSpec, HybridPoolToy, KVManagerSim, KVPoolExhausted,
    agreed_hit, packed_batch, reference_rows, request_block_hashes, slot_id, slot_mapping,
)


def toks(n: int, base: int = 1000) -> list[int]:
    return list(range(base, base + n))


def schedule_new(mgr: KVManagerSim, rid: str, tokens: list[int], **kw):
    return mgr.schedule(mgr.add_request(rid, tokens, **kw))


def kinds(mgr: KVManagerSim, kind: str) -> list[dict]:
    return [e for e in mgr.events if e["kind"] == kind]


# ---- slot 식과 연속이 아닌 block

def test_slot_id_uses_block_number_times_size_plus_offset():
    # position 20은 표의 1번 칸(block 9)의 4번째: 9*16+4
    assert slot_id([5, 9, 2], 20, 16) == 148


def test_slot_id_blocks_need_not_be_contiguous():
    table = [7, 2, 11]
    assert [slot_id(table, p, 4) for p in (0, 3, 4, 8, 11)] == [28, 31, 8, 44, 47]


def test_slot_id_outside_table_raises_index_error_with_korean_numbers():
    with pytest.raises(IndexError, match="2개"):
        slot_id([3, 4], 32, 16)
    with pytest.raises(IndexError):
        slot_id([3, 4], -1, 16)


def test_slot_mapping_pads_with_minus_one():
    assert slot_mapping([3, 4], 14, 4, 16, pad_to=6) == [62, 63, 64, 65, PAD_SLOT_ID, PAD_SLOT_ID]
    with pytest.raises(ValueError):
        slot_mapping([3, 4], 0, 5, 16, pad_to=4)


def test_packed_batch_concatenates_only_new_tokens():
    batch = packed_batch(
        [
            {"request_id": "a", "token_ids": [7, 8, 9], "num_computed_tokens": 0, "block_table": [1]},
            {"request_id": "b", "token_ids": [5], "num_computed_tokens": 4, "block_table": [6, 2]},
        ],
        block_size=4, pad_to=6,
    )
    assert batch["input_ids"] == [7, 8, 9, 5]
    assert batch["query_start_loc"] == [0, 3, 4]
    assert batch["positions"] == [0, 1, 2, 4]
    assert batch["seq_lens"] == [3, 5]
    assert batch["slot_mapping"] == [4, 5, 6, 8, PAD_SLOT_ID, PAD_SLOT_ID]
    assert (batch["num_tokens"], batch["num_tokens_after_padding"]) == (4, 6)


# ---- hash: 꽉 찬 block만, salt는 첫 block만

def test_only_full_blocks_are_hashed():
    assert len(request_block_hashes(toks(54), 16)) == 3
    assert len(request_block_hashes(toks(48), 16)) == 3
    assert request_block_hashes(toks(15), 16) == []


def test_hash_chains_on_parent_so_same_block_after_different_prefix_differs():
    same_tail = toks(16, 5000)
    a = request_block_hashes(toks(16) + same_tail, 16)
    b = request_block_hashes(toks(16, 9000) + same_tail, 16)
    assert a[1] != b[1]


def test_salt_changes_first_block_hash_and_therefore_whole_chain():
    plain = request_block_hashes(toks(48), 16)
    salted = request_block_hashes(toks(48), 16, "s1")
    assert all(p != s for p, s in zip(plain, salted))
    assert salted != request_block_hashes(toks(48), 16, "s2")


def test_salt_is_not_in_later_blocks_extra_keys():
    # 둘째 block부터는 salt를 직접 쓰지 않는다: 첫 block hash가 같으면 이후 hash도 같아야 한다.
    first = kv_sim.hash_block_tokens(None, toks(16), (("cache_salt", "s1"),))
    second_salted_chain = request_block_hashes(toks(32), 16, "s1")[1]
    assert second_salted_chain == kv_sim.hash_block_tokens(first, toks(16, 1016), None)


def test_empty_salt_behaves_like_no_salt():
    assert request_block_hashes(toks(16), 16, "") == request_block_hashes(toks(16), 16, None)


# ---- free queue 순서

def test_pool_starts_with_null_block_zero_and_ids_in_order():
    pool = BlockPool(6)
    assert pool.null_block.block_id == 0 and pool.null_block.is_null
    assert pool.free_queue.ids() == [1, 2, 3, 4, 5]
    assert pool.num_free() == 5
    assert pool.usage() == 0.0


def test_usage_excludes_null_block_from_denominator():
    pool = BlockPool(5)
    pool.get_new_blocks(2)
    assert pool.usage() == pytest.approx(0.5)


def test_free_order_hashless_block_goes_front_hashed_goes_back_tail_first():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(54))
    assert mgr.block_table(mgr.requests["r1"]) == [1, 2, 3, 4]
    mgr.free(mgr.requests["r1"])
    # 꼬리(4, hash 없음)는 앞, hash 있는 3, 2, 1은 역순으로 뒤
    assert mgr.free_queue_ids() == [4, 5, 6, 7, 8, 9, 10, 11, 3, 2, 1]
    assert [e["detail"]["block_ids"] for e in kinds(mgr, "free_front")] == [[4]]
    assert [e["detail"]["block_ids"] for e in kinds(mgr, "free_back")] == [[3, 2, 1]]


def test_free_then_reuse_takes_hashless_tail_first():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(54))
    mgr.free(mgr.requests["r1"])
    r2 = schedule_new(mgr, "r2", toks(16, 7000))
    r3 = schedule_new(mgr, "r3", toks(32, 8000))
    assert r2.block_table == [4]
    assert r3.block_table == [5, 6]


def test_caching_disabled_frees_everything_to_front_and_never_hits():
    mgr = KVManagerSim(12, enable_caching=False)
    schedule_new(mgr, "r1", toks(48))
    mgr.free(mgr.requests["r1"])
    assert mgr.free_queue_ids()[:3] == [3, 2, 1]
    assert mgr.cached_block_ids() == []
    assert schedule_new(mgr, "r2", toks(48)).hit_tokens == 0


# ---- 적중, 상한, 마지막 partial block

def test_prefix_hit_reuses_full_blocks_and_recomputes_last_partial_block():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(54))
    mgr.free(mgr.requests["r1"])
    r2 = schedule_new(mgr, "r2", toks(54))
    assert r2.hit_tokens == 48
    assert r2.hit_block_ids == [1, 2, 3]
    assert r2.new_block_ids == [4]
    assert r2.num_scheduled_tokens == 6  # 54 - 48: 꼬리 6 token은 다시 계산한다


def test_hit_is_capped_at_num_tokens_minus_one_so_exact_multiple_loses_last_block():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(48))
    mgr.free(mgr.requests["r1"])
    r2 = schedule_new(mgr, "r2", toks(48))
    assert r2.hit_tokens == 32  # 3개 block이 다 캐시돼 있어도 47 // 16 = 2개까지만
    assert r2.num_scheduled_tokens == 16


def test_hit_stops_at_first_missing_block():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(48))
    mgr.free(mgr.requests["r1"])
    other = toks(16) + toks(16, 9000) + toks(17, 1032)
    r2 = mgr.add_request("r2", other)
    blocks, hit = mgr.get_computed_blocks(r2)
    assert hit == 16 and [b.block_id for b in blocks] == [1]


def test_get_computed_blocks_does_not_touch():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(48))
    mgr.free(mgr.requests["r1"])
    before = mgr.ref_cnts()
    mgr.get_computed_blocks(mgr.add_request("r2", toks(48)))
    assert mgr.ref_cnts() == before == []


def test_salt_separation_prevents_hit_across_salts_but_not_within_salt():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(54), cache_salt="s1")
    mgr.free(mgr.requests["r1"])
    assert schedule_new(mgr, "r2", toks(54), cache_salt="s2").hit_tokens == 0
    mgr.free(mgr.requests["r2"])
    assert schedule_new(mgr, "r3", toks(54), cache_salt="s1").hit_tokens == 48


# ---- 공유와 반납

def test_running_requests_share_prefix_blocks_by_ref_cnt():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(54))
    r2 = schedule_new(mgr, "r2", toks(54))
    assert r2.hit_block_ids == [1, 2, 3]
    assert mgr.ref_cnts() == [[1, 2], [2, 2], [3, 2], [4, 1], [5, 1]]
    states = {c["block_id"]: c["state"] for c in mgr.snapshot()}
    assert (states[1], states[4], states[6], states[0]) == ("shared", "used", "free", "null")


def test_release_keeps_shared_block_until_last_owner_frees():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(54))
    schedule_new(mgr, "r2", toks(54))
    mgr.free(mgr.requests["r1"])
    assert mgr.ref_cnts() == [[1, 1], [2, 1], [3, 1], [5, 1]]
    assert 1 not in mgr.free_queue_ids() and 4 in mgr.free_queue_ids()
    mgr.free(mgr.requests["r2"])
    assert mgr.ref_cnts() == []
    assert {1, 2, 3} <= set(mgr.free_queue_ids())


def test_touch_removes_free_block_from_queue_middle():
    mgr = KVManagerSim(12)
    schedule_new(mgr, "r1", toks(54))
    mgr.free(mgr.requests["r1"])
    assert 2 in mgr.free_queue_ids()
    schedule_new(mgr, "r2", toks(54))
    assert not {1, 2, 3} & set(mgr.free_queue_ids())
    assert kinds(mgr, "touch")[-1]["detail"]["from_free"] == [1, 2, 3]


def test_pool_rejects_returning_a_block_twice():
    pool = BlockPool(4)
    block = pool.get_new_blocks(1)[0]
    pool.free_blocks([block])
    with pytest.raises(ValueError, match="ref_cnt"):
        pool.free_blocks([block])


def test_null_block_ref_cnt_is_not_maintained_and_never_enters_queue():
    pool = BlockPool(4)
    pool.touch([pool.null_block])
    pool.free_blocks([pool.null_block])
    assert pool.null_block.block_id not in pool.free_queue.ids()
    assert pool.num_free() == 3


# ---- 축출

def test_eviction_takes_front_of_queue_and_drops_old_hash():
    mgr = KVManagerSim(6)
    schedule_new(mgr, "r1", toks(48))
    mgr.free(mgr.requests["r1"])
    assert mgr.free_queue_ids() == [4, 5, 3, 2, 1]
    r2 = schedule_new(mgr, "r2", toks(64, 5000))
    assert r2.block_table == [4, 5, 3, 2]
    assert r2.evicted_block_ids == [3, 2]
    mgr.free(mgr.requests["r2"])
    r3 = schedule_new(mgr, "r3", toks(48))
    assert (r3.hit_tokens, r3.hit_block_ids) == (16, [1])  # 블록 2, 3의 옛 hash는 사라졌다
    # r2가 3, 2를 밀어냈고(r1의 hash), r3의 새 block 할당이 r2의 hash를 밀어냈다
    assert [e["detail"]["block_id"] for e in kinds(mgr, "evict")] == [3, 2, 2, 3]


def test_duplicate_hash_returns_first_registered_block():
    pool = BlockPool(5)
    a, b = pool.get_new_blocks(2)
    pool.cache_block(a, "h", 16)
    pool.cache_block(b, "h", 16)
    assert pool.get_cached_block("h") is a
    pool.free_blocks([a])  # 먼저 들어간 block이 사라져도
    pool.get_new_blocks(pool.num_free())  # a가 축출되면
    assert pool.get_cached_block("h") is b


# ---- 고갈

def test_pool_exhaustion_raises_with_numbers():
    pool = BlockPool(4)
    with pytest.raises(KVPoolExhausted) as exc:
        pool.get_new_blocks(99)
    assert (exc.value.requested, exc.value.free) == (99, 3)
    assert "99" in str(exc.value) and "3" in str(exc.value)
    assert isinstance(exc.value, ValueError)
    assert pool.num_free() == 3  # 실패한 호출은 아무것도 꺼내지 않는다
    assert pool.events[-1]["kind"] == "alloc_failed"


def test_schedule_returns_none_without_side_effects_when_blocks_are_short():
    mgr = KVManagerSim(4)  # 쓸 수 있는 block 3개 = 48 token
    r = mgr.add_request("big", toks(49))
    assert mgr.schedule(r) is None
    assert mgr.free_queue_ids() == [1, 2, 3] and mgr.block_table(r) == []
    assert r.status == "WAITING" and r.num_computed_tokens == 0
    failed = kinds(mgr, "alloc_failed")[-1]["detail"]
    assert (failed["requested"], failed["free"]) == (4, 3)


def test_cached_hit_blocks_count_against_free_capacity():
    mgr = KVManagerSim(5)  # block 4개
    schedule_new(mgr, "r1", toks(48))
    mgr.free(mgr.requests["r1"])  # 1, 2, 3은 ref 0으로 free queue 안
    r2 = mgr.add_request("r2", toks(48) + toks(17, 9000))  # 65 token: 5칸 필요, 적중 3칸
    assert mgr.schedule(r2) is None
    assert kinds(mgr, "alloc_failed")[-1]["detail"]["requested"] == 5  # 새 2칸 + free에서 빠질 적중 3칸


# ---- 계산 수와 ID 검사

def test_duplicate_request_id_and_oversized_schedule_are_errors():
    mgr = KVManagerSim(12)
    r = mgr.add_request("r", toks(20))
    with pytest.raises(ValueError):
        mgr.add_request("r", toks(5))
    with pytest.raises(ValueError, match="20"):
        mgr.schedule(r, 21)


def test_chunked_schedule_continues_without_new_hit_lookup():
    mgr = KVManagerSim(12)
    r = mgr.add_request("r", toks(40))
    first = mgr.schedule(r, 20)
    second = mgr.schedule(r)
    assert first.block_table == [1, 2] and second.block_table == [1, 2, 3]
    assert (second.hit_tokens, second.num_computed_tokens, second.num_scheduled_tokens) == (0, 40, 20)
    assert [e["detail"]["hit_tokens"] for e in kinds(mgr, "hit")] == [0]


def test_decode_step_registers_hash_only_when_block_becomes_full():
    mgr = KVManagerSim(12)
    r = mgr.add_request("r", toks(15))
    mgr.schedule(r)
    assert mgr.cached_block_ids() == []
    mgr.append_output(r, [1, 2])  # 17 token: 첫 block이 꽉 찼다
    mgr.schedule(r)
    assert mgr.cached_block_ids() == [1]


# ---- preempt 재계산

def test_preempt_frees_in_reverse_resets_state_and_recomputes_from_cache():
    mgr = KVManagerSim(12)
    r = mgr.add_request("r", toks(40))
    mgr.schedule(r)
    mgr.append_output(r, [7])
    out = mgr.preempt(r)
    assert out == {"request_id": "r", "freed_block_ids": [3, 2, 1], "num_preemptions": 1}
    assert (r.status, r.num_computed_tokens, r.spec_token_ids) == ("PREEMPTED", 0, [])
    assert mgr.block_table(r) == [] and mgr.ref_cnts() == []
    again = mgr.schedule(r)
    # 41 token 중 hash가 있던 앞 2 block(32 token)은 캐시에서 되찾고 나머지만 다시 계산한다
    assert again.hit_tokens == 32
    assert again.num_scheduled_tokens == 9
    assert r.status == "RUNNING"


def test_preempt_recompute_rewrites_slots_that_other_request_reused():
    mgr = KVManagerSim(5)  # block 4개
    a = mgr.add_request("a", toks(16))
    mgr.schedule(a)
    mgr.preempt(a)
    b = schedule_new(mgr, "b", toks(64, 3000))  # 모든 block을 쓰고 a의 hash를 밀어낸다
    mgr.free(mgr.requests["b"])
    assert b.hit_tokens == 0
    r = mgr.schedule(a)
    assert r.hit_tokens == 0 and r.num_scheduled_tokens == 16
    assert kinds(mgr, "overwrite")  # 남아 있던 b의 표지를 덮었다
    assert mgr.slot_contents(slot_id(r.block_table, 0))["request_id"] == "a"


# ---- speculative 거부와 덮어쓰기

def spec_setup():
    mgr = KVManagerSim(12, block_size=4)
    r = mgr.add_request("r", toks(5))
    mgr.schedule(r)  # position 0..4
    mgr.set_draft_tokens(r, [101, 102, 103])
    res = mgr.schedule(r)  # 이번에 position 5, 6, 7이 draft
    return mgr, r, res


def test_draft_tokens_get_slots_but_are_not_hashed():
    mgr, r, res = spec_setup()
    assert res.num_scheduled_tokens == 3 and r.num_computed_tokens == 8
    slot = slot_id(res.block_table, 6, 4)
    assert mgr.slot_contents(slot) == {"request_id": "r", "position": 6, "token_id": 102, "is_draft": True}
    assert mgr.cached_block_ids() == [mgr.block_table(r)[0]]  # 확정된 첫 block만, 둘째(draft 포함)는 아니다
    assert len(kinds(mgr, "draft_write")) == 3


def test_rollback_counts_and_next_step_overwrites_rejected_draft_slot():
    mgr, r, res = spec_setup()
    # 앞으로 1개만 승인: generated = [승인 1개, bonus 1개] -> accepted 1, rejected 2
    out = mgr.verify_drafts(r, [101, 555])
    assert (out["num_drafts"], out["num_accepted"], out["num_rejected"]) == (3, 1, 2)
    assert out["num_computed_tokens"] == 6 and out["num_tokens"] == 7
    assert out["block_table"] == res.block_table  # block은 그대로
    assert kinds(mgr, "rollback")[-1]["detail"]["num_computed_after"] == 6
    # 승인된 draft는 확정 표지로 바뀐다
    assert mgr.slot_contents(slot_id(res.block_table, 5, 4))["is_draft"] is False
    nxt = mgr.schedule(r)  # position 6만 계산한다
    assert nxt.num_scheduled_tokens == 1
    ow = kinds(mgr, "overwrite")[-1]["detail"]
    assert ow["slot"] == slot_id(res.block_table, 6, 4)
    assert ow["old"]["token_id"] == 102 and ow["old"]["is_draft"] is True
    assert ow["new"]["token_id"] == 555 and ow["new"]["is_draft"] is False
    # 되돌린 범위 밖의 draft(position 7)는 다시 쓰이기 전까지 그대로다
    assert mgr.slot_contents(slot_id(res.block_table, 7, 4))["token_id"] == 103


def test_verify_all_accepted_rolls_nothing_back():
    mgr, r, _ = spec_setup()
    out = mgr.verify_drafts(r, [101, 102, 103, 9])
    assert (out["num_accepted"], out["num_rejected"], out["num_computed_tokens"]) == (3, 0, 8)


def test_verify_without_drafts_is_an_error():
    mgr = KVManagerSim(12)
    r = mgr.add_request("r", toks(5))
    with pytest.raises(ValueError):
        mgr.verify_drafts(r, [1])


# ---- trace event 모양

def test_events_have_exactly_five_keys_and_known_kinds():
    mgr = KVManagerSim(6)
    schedule_new(mgr, "r1", toks(48))
    mgr.free(mgr.requests["r1"])
    schedule_new(mgr, "r2", toks(64, 5000))
    allowed = {"hit", "touch", "alloc", "alloc_failed", "hash_register", "evict",
               "free_front", "free_back", "preempt", "draft_write", "rollback", "overwrite"}
    assert mgr.events
    for e in mgr.events:
        assert set(e) == {"step", "actor", "kind", "request_id", "detail"}
        assert e["kind"] in allowed and e["actor"] in ("BlockPool", "KVManagerSim")
    steps = [e["step"] for e in mgr.events]
    assert steps == sorted(steps) and steps[0] == 1  # 관리자 호출 순번: schedule 안의 하위 호출은 같은 순번


# ---- replay와 reference

def test_replay_matches_hand_computed_scenarios():
    rows = KVManagerSim.replay({"num_blocks": 12, "block_size": 16, "ops": [
        {"op": "schedule", "request_id": "R1", "token_ids": toks(54), "cache_salt": None, "num_new_tokens": None},
        {"op": "schedule", "request_id": "R2", "token_ids": toks(20, 4000), "cache_salt": None, "num_new_tokens": None},
    ]})
    assert [r["new_block_ids"] for r in rows] == [[1, 2, 3, 4], [5, 6]]
    assert rows[1]["free_queue"] == [7, 8, 9, 10, 11]
    assert set(rows[0]) == {"op", "request_id", "returned_none", "hit_tokens", "hit_block_ids",
                            "new_block_ids", "block_table", "ref_cnts", "free_queue", "cached_block_ids"}


def test_replay_eviction_scenario_matches_design_table():
    ops = [
        {"op": "schedule", "request_id": "R1", "token_ids": toks(48), "cache_salt": None, "num_new_tokens": None},
        {"op": "free", "request_id": "R1"},
        {"op": "schedule", "request_id": "R2", "token_ids": toks(64, 5000), "cache_salt": None, "num_new_tokens": None},
        {"op": "free", "request_id": "R2"},
        {"op": "schedule", "request_id": "R3", "token_ids": toks(48), "cache_salt": None, "num_new_tokens": None},
    ]
    rows = KVManagerSim.replay({"num_blocks": 6, "block_size": 16, "ops": ops})
    assert rows[2]["new_block_ids"] == [4, 5, 3, 2]
    assert (rows[4]["hit_tokens"], rows[4]["hit_block_ids"]) == (16, [1])
    assert rows[1]["hit_tokens"] is None and rows[1]["returned_none"] is False


def test_reference_rows_reads_status_honestly(tmp_path):
    ran = tmp_path / "ran.json"
    ran.write_text(json.dumps({"status": "ran", "reason": None, "scenarios": [
        {"name": "x", "inputs": {}, "real": [], "sim": [], "match": True}]}), encoding="utf-8")
    assert reference_rows(ran) == [{"name": "x", "match": True, "status": "ran", "reason": None}]
    skipped = tmp_path / "skip.json"
    skipped.write_text(json.dumps({"status": "not_run", "reason": "vllm 없음", "scenarios": []}), encoding="utf-8")
    assert reference_rows(skipped) == [{"name": "(전체)", "match": None, "status": "not_run", "reason": "vllm 없음"}]
    with pytest.raises(FileNotFoundError):
        reference_rows(tmp_path / "missing.json")


# ---- hybrid toy

def test_agreed_hit_shrinks_until_all_groups_agree():
    out = agreed_hit({"full": {16, 32, 48}, "mamba": {32}}, 48)
    assert out["length"] == 32
    assert out["rounds"] == 2
    assert agreed_hit({"a": {16}, "b": {16}}, 48)["length"] == 16
    assert agreed_hit({"a": {16}, "b": {32}}, 48)["length"] == 0


def test_hybrid_allocate_counts_per_group_and_advance_frees_front_blocks():
    groups = [GroupSpec("full", "full"), GroupSpec("swa", "sliding_window", window=8),
              GroupSpec("mam", "mamba"), GroupSpec("ring", "circular_buffer")]
    pool = HybridPoolToy(20, groups, block_size=4)
    got = pool.allocate("r", 16)
    assert len(got["full"]) == 4 and len(got["mam"]) == 1 and len(got["ring"]) == 1
    # window 8, 16 token: 앞 skipped = 16-8+1 = 9 token = 2 block은 null, 실제 block 2개
    assert len(got["swa"]) == 2
    assert pool.owner_of(got["full"][0]) == "full" and pool.owner_of(got["mam"][0]) == "mam"
    freed = pool.advance("r", 16)
    assert freed["full"] == [] and freed["mam"] == [] and freed["ring"] == []
    pool.free("r")
    assert pool.pool.num_free() == 19


def test_hybrid_exhaustion_is_atomic():
    pool = HybridPoolToy(5, [GroupSpec("a", "full"), GroupSpec("b", "full")], block_size=4)
    with pytest.raises(KVPoolExhausted) as exc:
        pool.allocate("r", 12)  # 3 + 3 = 6칸, free는 4
    assert (exc.value.requested, exc.value.free) == (6, 4)
    assert pool.pool.num_free() == 4


def test_hybrid_sliding_window_advance_releases_front_block():
    pool = HybridPoolToy(12, [GroupSpec("swa", "sliding_window", window=4)], block_size=4)
    pool.allocate("r", 4)  # 아직 건너뛴 칸 없음: 실제 block 1개
    pool.allocate("r", 8)
    freed = pool.advance("r", 8)  # skipped = 8-4+1 = 5 token = 1 block
    assert len(freed["swa"]) == 1
    assert pool.owner_of(freed["swa"][0]) is None


def test_glm_like_groups_have_four_toy_kinds():
    assert [g.kind for g in kv_sim.glm_like_groups()] == ["mamba", "full", "full", "circular_buffer"]


def test_module_contract_docstring_and_not_modeled():
    assert "teaching" in kv_sim.__doc__
    assert all(isinstance(s, str) and s for s in kv_sim.NOT_MODELED)
    assert any("watermark" in s for s in kv_sim.NOT_MODELED)
    assert "vllm" not in __import__("sys").modules and "torch" not in __import__("sys").modules


def test_hybrid_snapshot_label_is_the_whole_group_name():
    pool = HybridPoolToy(8, [GroupSpec("full_attention", "full"), GroupSpec("indexer", "full")], block_size=4)
    got = pool.allocate("r", 4)
    labels = {c["block_id"]: c["label"] for c in pool.snapshot()}
    assert labels[got["full_attention"][0]] == "full_attention"
    assert labels[got["indexer"][0]] == "indexer"
