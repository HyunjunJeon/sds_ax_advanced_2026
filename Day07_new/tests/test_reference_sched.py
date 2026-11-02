"""저장된 실제 vLLM 0.32.0 Scheduler 실행(data/reference_sched.json)을 sched_sim과 대조한다.

실제 클래스는 여기서 돌리지 않는다. 저장된 행을 읽고, 같은 입력을 sched_sim에 다시 넣는다.
isl=on 변형은 reserve_full_isl=True로, isl=off 변형은 기본값으로 다시 돌린 행과 비교한다.
xfail은 쓰지 않는다. 실제 차이는 EXPECTED_DIFFERENCES에 변형 이름과 이유로 적는다. 거기 없는 새 차이는 실패하고,
더 이상 나지 않는 차이를 남겨 두어도 실패한다. 차이 목록을 늘려 새 차이를 감추지 않는다.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
from typing import NamedTuple

import pytest

from vllm_lab.sched_sim import (
    Req,
    SchedConfig,
    SimStuck,
    _check_requests,
    _Sim,
    doc_faq_chat,
    e1_workload,
    mixed_workload,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "reference_sched.json"
DOC_PATH = ROOT / "docs" / "reference" / "sched.md"

CORE = ("step", "tokens", "preempted", "running_before", "waiting_before",
        "blocks_in_use", "blocks_after", "running_after", "waiting_after", "preemptions_total")
VARIANT_SUFFIXES = ("isl=off|prefix=off", "isl=off|prefix=on", "isl=on|prefix=off", "isl=on|prefix=on")

CAUSES = {
    "reserve_full_isl": (
        "scheduler_reserve_full_isl=True는 새 요청의 전체 입력이 들어갈 free block이 없으면 waiting에서 꺼내지 않는다"
        "(vllm/config/scheduler.py:190, vllm/v1/core/sched/scheduler.py:1270, vllm/v1/core/kv_cache_manager.py:522-539). "
        "sched_sim 기본값은 첫 chunk에 필요한 block만 보므로 다르고, SchedConfig(reserve_full_isl=True)로 돌리면 같다."
    ),
    "prefix_comeback": (
        "preempt 뒤 복귀할 때 num_computed_tokens가 0이라 prefix cache를 다시 조회해 적중한 token은 계산하지 않는다"
        "(vllm/v1/core/sched/scheduler.py:959-967). sched_sim은 복귀 적중이 없어 전부 다시 계산한다(NOT_MODELED에 적혀 있다)."
    ),
    "evictable_admission": (
        "적중한 block이 ref_cnt 0으로 free queue에 있으면 그 block도 free 칸을 쓰는 수로 센다"
        "(vllm/v1/core/single_type_kv_cache_manager.py:255-260, :265). 적중으로 입력 끝까지 한 번에 잡으므로 free block이 더 필요해 "
        "입장이 늦어지고 그만큼 다시 밀려나지 않는다. sched_sim에 없는 효과다(NOT_MODELED에 적혀 있다)."
    ),
    "block_sharing": (
        "다른 요청이 쥔 block에 적중하면 ref_cnt만 늘고 새 block을 쓰지 않는다"
        "(vllm/v1/core/single_type_kv_cache_manager.py:245-248, :267-278). sched_sim은 cached_tokens 몫도 요청별 block으로 세어 "
        "쓰는 block이 더 크게 나온다. token 배정은 같다(NOT_MODELED에 적혀 있다)."
    ),
    "pool_smaller_than_input": (
        "입력이 pool보다 큰 상태. 실제 서버는 max_model_len 한 건을 담지 못하는 KV면 기동 때 ValueError로 막으므로"
        "(vllm/v1/core/kv_cache_utils.py:1104-1132) create_scheduler로 그 검사를 건너뛴 이 실행에서만 생긴다. "
        "sched_sim은 chunk로 계속 들여보내 밀어내기를 반복하고(step_cap), 실제 쪽은 복귀 적중 때문에 "
        "waiting에서 0 token으로 멈춘다(waiting 경로는 preempt를 하지 않는다)."
    ),
}


class Diff(NamedTuple):
    cause: str
    first_step: int | None
    first_field: str
    outcome: str
    num_steps: int
    preemptions: int | None
    fields: tuple[str, ...]


_ALL = ("blocks_after", "blocks_in_use", "preempted", "preemptions_total", "running_after", "running_before",
        "tokens", "waiting_after", "waiting_before")
_NO_PREEMPT_CHANGE = ("blocks_after", "blocks_in_use", "running_after", "running_before", "tokens",
                      "waiting_after", "waiting_before")

# isl=on 변형 중 reserve_full_isl=True로 돌리면 사라지는 차이. 값은 기본값(False)으로 다시 돌린 행과 비교한 결과다.
FULL_INPUT_DIFFERENCES: dict[str, Diff] = {
    "preempt_blocks_5|isl=on|prefix=off": Diff("reserve_full_isl", 2, "tokens", "finished", 15, 0, _ALL),
    "preempt_blocks_5|isl=on|prefix=on": Diff("reserve_full_isl", 2, "tokens", "finished", 15, 0, _ALL),
    "preempt_blocks_6|isl=on|prefix=off": Diff("reserve_full_isl", 9, "tokens", "finished", 14, 0, _NO_PREEMPT_CHANGE),
    "preempt_blocks_6|isl=on|prefix=on": Diff("reserve_full_isl", 9, "tokens", "finished", 14, 0, _NO_PREEMPT_CHANGE),
    "preempt_blocks_8|isl=on|prefix=off": Diff("reserve_full_isl", 3, "tokens", "finished", 13, 0, _ALL),
    "preempt_blocks_8|isl=on|prefix=on": Diff("reserve_full_isl", 3, "tokens", "finished", 13, 0, _ALL),
    "prompt_larger_than_pool|isl=on|prefix=off": Diff("reserve_full_isl", None, "outcome", "stuck", 0, None, ()),
    "prompt_larger_than_pool|isl=on|prefix=on": Diff("reserve_full_isl", None, "outcome", "stuck", 0, None, ()),
}

# 변형 이름 -> 차이. 값은 그 변형의 isl 설정으로 다시 돌린 sched_sim 행과 비교한 결과와 같아야 한다.
EXPECTED_DIFFERENCES: dict[str, Diff] = {
    "preempt_blocks_8|isl=off|prefix=on": Diff("evictable_admission", 5, "tokens", "finished", 12, 1, _ALL),
    "self_preempt_tail|isl=off|prefix=on": Diff("prefix_comeback", 4, "tokens", "finished", 22, 1, ("tokens",)),
    "self_preempt_tail|isl=on|prefix=on": Diff("prefix_comeback", 4, "tokens", "finished", 22, 1, ("tokens",)),
    "self_preempt_after_other|isl=off|prefix=on": Diff("prefix_comeback", 4, "tokens", "finished", 7, 2, ("tokens",)),
    "self_preempt_after_other|isl=on|prefix=on": Diff("prefix_comeback", 4, "tokens", "finished", 7, 2, ("tokens",)),
    "waiting_skipped_then_head_blocks|isl=off|prefix=on": Diff("prefix_comeback", 5, "tokens", "finished", 7, 1, ("tokens",)),
    "waiting_skipped_then_head_blocks|isl=on|prefix=on": Diff("prefix_comeback", 5, "tokens", "finished", 7, 1, ("tokens",)),
    "comeback_faq|isl=off|prefix=on": Diff("prefix_comeback", 71, "tokens", "finished", 135, 2, ("tokens",)),
    "comeback_faq|isl=on|prefix=on": Diff("prefix_comeback", 71, "tokens", "finished", 135, 2, ("tokens",)),
    "sample_shared_prefix|isl=off|prefix=on": Diff("block_sharing", 3, "blocks_in_use", "finished", 9, 0, ("blocks_after", "blocks_in_use")),
    "sample_shared_prefix|isl=on|prefix=on": Diff("block_sharing", 3, "blocks_in_use", "finished", 9, 0, ("blocks_after", "blocks_in_use")),
    "prompt_larger_than_pool|isl=off|prefix=on": Diff("pool_smaller_than_input", None, "outcome", "stuck", 2, 1, ()),
}

# prefix=off일 때 실제 Scheduler는 조회를 하지 않아 queries가 0이고, sched_sim은 입장 때 prompt token을 더한다.
# vllm/v1/core/kv_cache_manager.py:253-256. sched_sim에는 prefix cache를 끄는 칸이 없다.
PREFIX_OFF_COUNTER_DIFFERENCE = "prefix=off에서 실제 prefix_queries는 0이고 sched_sim은 prompt token 수를 센다"


def _load() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


DOC = _load()
BASES = {b["name"]: b for b in DOC.get("bases", [])}
VARIANTS = {v["name"]: (b, v) for b in BASES.values() for v in b["variants"]}


@pytest.fixture(autouse=True)
def _skip_when_not_run():
    assert DOC["status"] in ("ran", "not_run")
    if DOC["status"] == "not_run":
        assert DOC["reason"], "not_run이면 이유를 적어야 합니다"
        pytest.skip(f"reference_sched.json이 not_run입니다: {DOC['reason']}")


def replay(base: dict, *, reserve_full_isl: bool) -> dict:
    """저장된 입력을 sched_sim에 넣는다. 멈춘 실행의 행도 보려고 run_sim 대신 한 step씩 돈다."""
    inputs = base["inputs"]
    requests = [Req(**r) for r in inputs["requests"]]
    config = SchedConfig(**inputs["sim_config"], reserve_full_isl=reserve_full_isl)
    try:
        if inputs["validate"]:
            config.validate()
        _check_requests(requests, config)
    except ValueError:
        return {"outcome": "config_error", "steps": []}
    sim = _Sim(requests, config)
    outcome = "finished"
    while not sim.done():
        if sim.step >= inputs["max_steps"]:
            outcome = "step_cap"
            break
        try:
            sim.run_one_step()
        except SimStuck:
            outcome = "stuck"
            break
    return {
        "outcome": outcome,
        "steps": [
            {
                "step": s.step, "start_ms": s.start_ms, "end_ms": s.end_ms,
                "tokens": [[rid, n] for rid, n in s.tokens.items()], "preempted": list(s.preempted),
                "running_before": list(s.running_before), "waiting_before": list(s.waiting_before),
                "running_after": s.running_after, "waiting_after": s.waiting_after,
                "blocks_in_use": s.blocks_in_use, "blocks_after": s.blocks_after,
                "preemptions_total": s.preemptions_total,
                "prefix_queries": s.prefix_queries, "prefix_hits": s.prefix_hits,
            }
            for s in sim.steps
        ],
    }


REPLAYS = {name: replay(base, reserve_full_isl=False) for name, base in BASES.items()}
FULL_INPUT_REPLAYS = {name: replay(base, reserve_full_isl=True) for name, base in BASES.items()}


def core_sha(outcome: str, steps: list[dict]) -> str:
    rows = [{k: row[k] for k in CORE} for row in steps]
    text = json.dumps({"outcome": outcome, "steps": rows}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def result_sha(result: dict) -> str:
    return core_sha(result["outcome"], result["steps"])


def matching_replay(variant_name: str) -> dict:
    """변형과 같은 isl 설정으로 다시 돌린 sched_sim 결과."""
    base_name = variant_name.split("|", 1)[0]
    return FULL_INPUT_REPLAYS[base_name] if "|isl=on|" in variant_name else REPLAYS[base_name]


def real_tokens(variant_name: str) -> list[list]:
    return [row["tokens"] for row in VARIANTS[variant_name][1]["steps"]]


def test_file_has_true_status_and_environment():
    assert DOC["status"] == "ran"
    assert DOC["vllm"] == "0.32.0"
    assert DOC["reason"] is None
    assert DOC["commit"].startswith("5df63a7")
    env = DOC["environment"]
    assert env["source_git"] == {"head": DOC["commit"], "describe": "v0.32.0", "clean": True}
    assert env["scheduler_class"] == "vllm.v1.core.sched.scheduler.Scheduler"
    assert env["gpu"] is False and env["model_forward"] is False and env["paid_calls"] == 0
    assert env["VLLM_TARGET_DEVICE"] == "cpu"
    defaults = env["defaults_seen"]
    # 서버 쪽 기본은 둘 다 켜짐이고 create_scheduler는 prefix cache만 꺼서 만든다.
    assert defaults["SchedulerConfig.scheduler_reserve_full_isl"] is True
    assert defaults["CacheConfig.enable_prefix_caching"] is True
    assert defaults["create_scheduler.enable_prefix_caching"] is False
    assert defaults["SchedulerConfig.watermark"] == 0.0


def test_every_base_ran_with_all_four_variants():
    for name, base in BASES.items():
        got = [v["name"].split("|", 1)[1] for v in base["variants"]]
        if name in ("sample_shared_prefix", "comeback_faq"):  # prefix 적중을 보려는 입력이라 prefix=on만 돌렸다
            assert got == ["isl=off|prefix=on", "isl=on|prefix=on"], name
        else:
            assert got == list(VARIANT_SUFFIXES), name


def test_inputs_are_the_course_workloads():
    def as_dict(requests: list[Req]) -> list[dict]:
        return [{f.name: getattr(r, f.name) for f in dataclasses.fields(r)
                 if f.name in ("request_id", "prompt_tokens", "max_tokens") or getattr(r, f.name) != f.default}
                for r in requests]

    assert BASES["doc_faq_chat_b32"]["inputs"]["requests"] == as_dict(doc_faq_chat())
    assert BASES["preempt_blocks_5"]["inputs"]["requests"] == as_dict(doc_faq_chat())
    assert BASES["preempt_blocks_8"]["inputs"]["requests"] == as_dict(doc_faq_chat())
    assert BASES["e1"]["inputs"]["requests"] == as_dict(e1_workload())
    assert BASES["mixed_threshold_16"]["inputs"]["requests"] == as_dict(mixed_workload())
    assert BASES["mixed_seqs_2"]["inputs"]["requests"] == as_dict(mixed_workload())
    assert BASES["preempt_blocks_5"]["inputs"]["sim_config"] == {"max_num_batched_tokens": 32, "num_blocks": 5}
    assert BASES["preempt_blocks_8"]["inputs"]["sim_config"] == {"num_blocks": 8}
    assert SchedConfig().max_num_batched_tokens == 32 and SchedConfig().block_size == 16


@pytest.mark.parametrize("name", list(BASES))
def test_sched_sim_replays_to_saved_rows(name):
    base = BASES[name]
    fresh = REPLAYS[name]
    saved = base["sim"]
    assert fresh["outcome"] == saved["outcome"]
    assert len(fresh["steps"]) == saved["num_steps"]
    assert result_sha(fresh) == saved["core_sha256"]
    for row in saved["steps"]:  # 긴 표는 일부 행만 저장했다. 저장한 행은 시각까지 그대로여야 한다
        assert fresh["steps"][row["step"] - 1] == row


@pytest.mark.parametrize("name", list(VARIANTS))
def test_real_variant_against_fresh_replay(name):
    variant = VARIANTS[name][1]
    fresh = matching_replay(name)
    if variant["core_sha256"] == result_sha(fresh):
        assert name not in EXPECTED_DIFFERENCES, f"더 이상 나지 않는 차이입니다: {name}"
        assert variant["outcome"] == fresh["outcome"]
        assert variant["num_steps"] == len(fresh["steps"])
    else:
        assert name in EXPECTED_DIFFERENCES, f"새 차이입니다. 이유를 확인하고 적으세요: {name}"


@pytest.mark.parametrize("name", list(VARIANTS))
def test_saved_match_core_compares_against_the_default_replay(name):
    base, variant = VARIANTS[name]
    same = variant["core_sha256"] == result_sha(REPLAYS[base["name"]])
    assert variant["match_core"] is same, "저장된 match_core가 다시 계산한 결과와 다릅니다"


@pytest.mark.parametrize("name", list(VARIANTS))
def test_saved_real_rows_are_consistent(name):
    _, variant = VARIANTS[name]
    rows = variant["steps"]
    if rows is None:  # 행을 저장하지 않는 변형은 일치 변형뿐이다
        assert variant["match_core"] is True
        assert not name.endswith("isl=on|prefix=on")
        return
    if len(rows) == variant["num_steps"]:
        assert core_sha(variant["outcome"], rows) == variant["core_sha256"], "저장된 행과 sha가 다릅니다"


def test_expected_differences_have_no_stale_or_unknown_names():
    differing = {n for n, (_, v) in VARIANTS.items() if v["core_sha256"] != result_sha(matching_replay(n))}
    assert set(EXPECTED_DIFFERENCES) == differing
    assert set(FULL_INPUT_DIFFERENCES) == {n for n, (_, v) in VARIANTS.items() if not v["match_core"]} - differing
    causes = {d.cause for d in (*EXPECTED_DIFFERENCES.values(), *FULL_INPUT_DIFFERENCES.values())}
    assert causes == set(CAUSES)
    assert all(CAUSES.values())


def _assert_difference(name: str, expected: Diff, replayed: dict) -> None:
    variant = VARIANTS[name][1]
    fresh = replayed["steps"]
    assert variant["outcome"] == expected.outcome
    assert variant["num_steps"] == expected.num_steps
    assert variant["final"]["preemptions_total"] == expected.preemptions
    rows = variant["steps"]
    assert rows is not None, "차이 있는 변형은 행을 저장해야 합니다"
    first = variant["first_core_diff"]
    assert (first.get("step"), first["field"]) == (expected.first_step, expected.first_field)
    if expected.first_step is None:  # 결과 자체가 다르다
        assert variant["outcome"] != replayed["outcome"]
        assert first == {"field": "outcome", "real": variant["outcome"], "sim": replayed["outcome"]}
        return
    by_step = {row["step"]: row for row in rows}
    at = by_step[expected.first_step]
    assert at[expected.first_field] == first["real"]
    assert fresh[expected.first_step - 1][expected.first_field] == first["sim"]
    assert first["real"] != first["sim"]
    for row in rows:
        if row["step"] < expected.first_step:  # 첫 차이 앞의 행은 모두 같아야 한다
            for key in CORE:
                assert row[key] == fresh[row["step"] - 1][key], (name, row["step"], key)
    seen = {k for row in rows if row["step"] <= len(fresh) for k in CORE if row[k] != fresh[row["step"] - 1][k]}
    assert set(variant["fields_differ"]) == set(expected.fields)
    assert seen <= set(expected.fields)
    if len(rows) == variant["num_steps"]:
        assert seen == set(expected.fields)


@pytest.mark.parametrize("name", list(EXPECTED_DIFFERENCES))
def test_expected_difference_reproduces_against_replay(name):
    _assert_difference(name, EXPECTED_DIFFERENCES[name], matching_replay(name))


@pytest.mark.parametrize("name", list(FULL_INPUT_DIFFERENCES))
def test_full_input_difference_shows_against_default_and_disappears_with_the_flag(name):
    base_name = name.split("|", 1)[0]
    _assert_difference(name, FULL_INPUT_DIFFERENCES[name], REPLAYS[base_name])
    assert VARIANTS[name][1]["core_sha256"] == result_sha(FULL_INPUT_REPLAYS[base_name])


def test_flag_on_without_prefix_cache_replays_every_scenario():
    names = [n for n in VARIANTS if n.endswith("isl=on|prefix=off")]
    assert len(names) == 38
    for name in names:
        assert VARIANTS[name][1]["core_sha256"] == result_sha(matching_replay(name)), name
    scheduled = [n for n in names if VARIANTS[n][1]["outcome"] != "config_error"]
    assert len(scheduled) == DOC["probes"]["isl_prototype"]["replayed"] == 37


def test_without_reservation_and_prefix_cache_every_scenario_matches():
    # 수업 모델의 기본 규칙만 켠 조합이다. 이 조합에서 차이가 나면 sched_sim의 규칙이 틀린 것이다.
    names = [n for n in VARIANTS if n.endswith("isl=off|prefix=off")]
    assert len(names) == 38
    for name in names:
        assert VARIANTS[name][1]["match_core"] is True, name


def test_final_prefix_counters_match_when_cache_is_on():
    # vllm:prefix_cache_queries, hits는 첫 입장만 세므로(vllm/v1/metrics/stats.py:147-155) 복귀 적중이 있어도 sched_sim과 같다.
    for name, (base, variant) in VARIANTS.items():
        rows = REPLAYS[base["name"]]["steps"]
        if not name.endswith("prefix=on") or variant["outcome"] != "finished" or not rows:
            continue
        assert variant["final"]["prefix_queries"] == rows[-1]["prefix_queries"], name
        assert variant["final"]["prefix_hits"] == rows[-1]["prefix_hits"], name


def test_prefix_off_counter_difference_is_real():
    for name, (base, variant) in VARIANTS.items():
        rows = REPLAYS[base["name"]]["steps"]
        if name.endswith("prefix=off") and variant["num_steps"] and rows:
            assert variant["final"]["prefix_queries"] == 0 and variant["final"]["prefix_hits"] == 0, name
    final_sim = REPLAYS["doc_faq_chat_b32"]["steps"][-1]["prefix_queries"]
    assert final_sim == 108, PREFIX_OFF_COUNTER_DIFFERENCE


def test_doc_faq_chat_rows_are_the_same_in_every_variant():
    expected = [
        [["doc", 32]],
        [["doc", 22], ["faq", 10]],
        [["doc", 1], ["faq", 10], ["chat", 21]],
        [["doc", 1], ["faq", 1], ["chat", 13]],
        [["doc", 1], ["faq", 1], ["chat", 1]],
        [["doc", 1], ["faq", 1], ["chat", 1]],
        [["doc", 1], ["faq", 1], ["chat", 1]],
        [["doc", 1], ["faq", 1]],
        [["doc", 1]],
    ]
    assert [row["tokens"] for row in REPLAYS["doc_faq_chat_b32"]["steps"]] == expected
    assert real_tokens("doc_faq_chat_b32|isl=on|prefix=on") == expected
    assert all(v["match_core"] for v in BASES["doc_faq_chat_b32"]["variants"])


def test_preempt_walkthrough_with_block_count_five():
    sim_rows = REPLAYS["preempt_blocks_5"]["steps"]
    assert sim_rows[1]["tokens"] == [["doc", 22], ["faq", 10]]
    assert (sim_rows[2]["tokens"], sim_rows[2]["preempted"]) == ([["doc", 1]], ["faq"])
    # 전체 입력 검사를 끈 실제 Scheduler는 이 표와 행이 같다.
    assert VARIANTS["preempt_blocks_5|isl=off|prefix=off"][1]["match_core"] is True
    # 기본인 True에서는 faq가 들어오지 못하고 preempt도 없다.
    rows = VARIANTS["preempt_blocks_5|isl=on|prefix=on"][1]["steps"]
    assert rows[1]["tokens"] == [["doc", 22]]
    assert rows[1]["waiting_after"] == 2
    assert [row["preempted"] for row in rows] == [[]] * 15
    # reserve_full_isl=True인 sched_sim도 같은 행을 낸다.
    flagged = FULL_INPUT_REPLAYS["preempt_blocks_5"]["steps"]
    assert flagged[1]["tokens"] == [["doc", 22]]
    assert [row["preempted"] for row in flagged] == [[]] * 15


def test_preemption_counts_over_block_counts():
    # 값 순서는 isl=off|prefix=off, isl=off|prefix=on, isl=on|prefix=off, isl=on|prefix=on
    expected = {5: [1, 1, 0, 0], 6: [0, 0, 0, 0], 7: [0, 0, 0, 0], 8: [3, 1, 0, 0], 9: [0, 0, 0, 0], 10: [0, 0, 0, 0]}
    for blocks, counts in expected.items():
        variants = BASES[f"preempt_blocks_{blocks}"]["variants"]
        assert [v["final"]["preemptions_total"] for v in variants] == counts, blocks
        assert FULL_INPUT_REPLAYS[f"preempt_blocks_{blocks}"]["steps"][-1]["preemptions_total"] == 0, blocks


def test_block_count_eight_case_from_notebook_01():
    sim_rows = REPLAYS["preempt_blocks_8"]["steps"]
    assert [row["preempted"] for row in sim_rows if row["preempted"]] == [["chat"]] * 3
    rows = VARIANTS["preempt_blocks_8|isl=off|prefix=on"][1]["steps"]
    # 복귀한 chat은 34 token 중 16을 적중으로 건지고 18만 계산한다.
    assert rows[8]["tokens"] == [["doc", 1], ["chat", 18]]
    assert VARIANTS["preempt_blocks_8|isl=off|prefix=on"][1]["final"]["preempted_hits"] == 16
    probe = DOC["probes"]["evictable_admission"]
    assert (probe["free_blocks"], probe["hit_tokens"], probe["hit_block_ref_cnts"], probe["new_tokens"]) == (2, 16, [0], 18)
    assert probe["allocate_slots_returned_none"] is True


def test_fcfs_self_preemption():
    for suffix in VARIANT_SUFFIXES:
        name = f"self_preempt_tail|{suffix}"
        rows = VARIANTS[name][1]["steps"] or REPLAYS["self_preempt_tail"]["steps"]
        assert (rows[1]["running_before"], rows[1]["tokens"], rows[1]["preempted"]) == (["a", "b"], [["a", 1]], ["b"])
    alone = BASES["self_preempt_alone_decode"]
    assert all(v["match_core"] and v["outcome"] == "stuck" for v in alone["variants"])
    rows = REPLAYS["self_preempt_alone_decode"]["steps"]
    assert rows[1]["tokens"] == [] and rows[1]["preempted"] == ["a"]
    # 복귀 적중: sched_sim은 17 token 전부, 실제는 prefix=on일 때 1 token.
    assert REPLAYS["self_preempt_tail"]["steps"][3]["tokens"] == [["b", 17]]
    real = VARIANTS["self_preempt_tail|isl=on|prefix=on"][1]
    assert real["steps"][3]["tokens"] == [["b", 1]]
    assert (real["final"]["preempted_queries"], real["final"]["preempted_hits"], real["final"]["prefix_hits"]) == (17, 16, 0)


def test_waiting_is_skipped_on_preempt_step_and_head_blocks():
    assert all(v["match_core"] for v in BASES["waiting_skipped_then_head_blocks"]["variants"]
               if v["name"].endswith("prefix=off"))
    rows = REPLAYS["waiting_skipped_then_head_blocks"]["steps"]
    assert (rows[1]["preempted"], rows[1]["waiting_before"], rows[1]["tokens"]) == (["B"], ["C"], [["A", 1]])
    assert (rows[2]["waiting_before"], rows[2]["tokens"]) == (["B", "C"], [["A", 1]])


def test_threshold_and_max_num_seqs_cases_match_in_every_variant():
    first = {"threshold_alone": [["doc", 64]], "threshold_pair": [["doc", 16], ["faq", 16]],
             "threshold_pair_adaptive": [["doc", 32], ["faq", 30]]}
    for name, tokens in first.items():
        assert REPLAYS[name]["steps"][0]["tokens"] == tokens
        assert all(v["match_core"] for v in BASES[name]["variants"])
    sweep_steps = {"mixed_seqs_1": 82, "mixed_seqs_2": 46, "mixed_seqs_4": 31, "mixed_seqs_6": 22,
                   "mixed_threshold_0": 31, "mixed_threshold_8": 48, "mixed_threshold_16": 37,
                   "mixed_threshold_32": 27, "mixed_threshold_48": 28, "mixed_threshold_64": 31}
    for name, steps in sweep_steps.items():
        assert len(REPLAYS[name]["steps"]) == steps
        assert all(v["match_core"] for v in BASES[name]["variants"]), name


def test_chunked_prefill_off_paths():
    for v in BASES["chunk_off_validated"]["variants"]:
        assert v["outcome"] == "config_error" and "smaller than max_model_len" in v["message"]
    # 셀 28은 faq가 도착하기 전에 멈추고, 모두 도착한 경우에만 맨 앞 doc이 faq를 막는다.
    late = BASES["chunk_off_unvalidated"]["variants"][0]["stuck_state"]
    assert late["waiting"] == ["doc"] and late["running"] == []
    same = BASES["chunk_off_unvalidated_same_arrival"]["variants"][0]["stuck_state"]
    assert same["waiting"] == ["doc", "faq-1", "faq-2", "faq-3", "faq-4", "faq-5"]
    assert same["next_schedules_tokens"] == [0, 0]


def test_small_pool_rows_do_not_depend_on_the_harness_max_model_len():
    rows = DOC["probes"]["reachable_max_model_len"]["rows"]
    assert len(rows) == 16
    assert all(r["same_core_sha256"] for r in rows)


def test_report_names_every_cause_and_differing_scenario():
    text = DOC_PATH.read_text(encoding="utf-8")
    for cause in CAUSES:
        assert f"### `{cause}`" in text, cause
    for name in {n.split("|")[0] for n in (*EXPECTED_DIFFERENCES, *FULL_INPUT_DIFFERENCES)}:
        assert f"`{name}`" in text, name
