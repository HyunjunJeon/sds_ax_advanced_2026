"""sched_sim의 규칙마다 손으로 계산한 값과 비교한다. 기대값은 모두 리터럴이다."""

from __future__ import annotations

import pytest

from vllm_lab.sched_sim import (
    Req,
    SchedConfig,
    SimStuck,
    doc_faq_chat,
    e1_workload,
    mixed_workload,
    run_sim,
    sweep,
)


def step_tokens(result):
    return [dict(s.tokens) for s in result.steps]


def kinds(result, step):
    return [e["kind"] for e in result.events if e["step"] == step]


def test_running_is_scheduled_before_waiting():
    # running인 chat 1, doc 22를 먼저 잡고, 남은 예산 9를 waiting의 faq가 받는다.
    result = run_sim(e1_workload(), SchedConfig(max_num_batched_tokens=32, num_blocks=11))
    first = result.steps[0]
    assert list(first.tokens.items()) == [("chat", 1), ("doc", 22), ("faq", 9)]
    assert first.blocks_in_use == 8
    step1 = kinds(result, 1)
    last_running = max(i for i, k in enumerate(step1) if k == "schedule_running")
    assert step1.index("schedule_waiting") > last_running


def test_token_budget_caps_a_step_and_chunks_the_rest():
    reqs = [Req("a", 6, 2), Req("b", 6, 2), Req("c", 6, 2)]
    result = run_sim(reqs, SchedConfig(max_num_batched_tokens=10))
    assert step_tokens(result)[0] == {"a": 6, "b": 4}
    assert result.steps[0].budget_left == 0
    # a는 decode 1, b는 남은 prompt 2, c는 예산 7 중 6
    assert step_tokens(result)[1] == {"a": 1, "b": 2, "c": 6}
    assert all(sum(s.tokens.values()) <= 10 for s in result.steps)


def test_max_num_seqs_blocks_waiting_admission():
    reqs = [Req("a", 5, 2), Req("b", 5, 2), Req("c", 5, 2)]
    result = run_sim(reqs, SchedConfig(max_num_batched_tokens=100, max_num_seqs=2))
    assert step_tokens(result)[:3] == [{"a": 5, "b": 5}, {"a": 1, "b": 1}, {"c": 5}]
    assert "stop_waiting_seqs_cap" in kinds(result, 1)
    assert result.steps[0].budget_left == 90


def test_chunked_prefill_on_splits_prompt_across_steps():
    result = run_sim([Req("a", 20, 1)], SchedConfig(max_num_batched_tokens=8))
    assert step_tokens(result) == [{"a": 8}, {"a": 8}, {"a": 4}]
    assert "chunk" in kinds(result, 1)
    assert "chunk" not in kinds(result, 3)


def test_chunked_prefill_off_stops_waiting_when_prompt_exceeds_budget():
    reqs = [Req("a", 5, 2), Req("b", 6, 1)]
    off = SchedConfig(max_num_batched_tokens=8, max_model_len=8, enable_chunked_prefill=False)
    result = run_sim(reqs, off)
    assert step_tokens(result)[0] == {"a": 5}
    assert "stop_waiting_no_chunk" in kinds(result, 1)
    assert step_tokens(result)[1] == {"a": 1, "b": 6}
    on = run_sim(reqs, SchedConfig(max_num_batched_tokens=8, max_model_len=8))
    assert step_tokens(on)[0] == {"a": 5, "b": 3}


def test_validate_chunked_off_boundary():
    SchedConfig(max_num_batched_tokens=4096, enable_chunked_prefill=False).validate()
    with pytest.raises(ValueError, match=r"4095.*4096"):
        SchedConfig(max_num_batched_tokens=4095, enable_chunked_prefill=False).validate()
    with pytest.raises(ValueError, match="-1"):
        SchedConfig(long_prefill_token_threshold=-1).validate()


def test_long_prefill_threshold_caps_each_request():
    reqs = [Req("a", 20, 1), Req("b", 3, 5)]
    capped = run_sim(reqs, SchedConfig(long_prefill_token_threshold=4))
    assert step_tokens(capped)[0] == {"a": 4, "b": 3}
    assert step_tokens(capped)[1] == {"a": 4, "b": 1}  # running 쪽에도 같은 상한
    free = run_sim(reqs, SchedConfig())
    assert step_tokens(free)[0] == {"a": 20, "b": 3}


def test_long_prefill_threshold_ignored_for_lone_request():
    result = run_sim([Req("a", 20, 1)], SchedConfig(long_prefill_token_threshold=4))
    assert step_tokens(result) == [{"a": 20}]


def test_adaptive_threshold_floors_at_fair_share():
    reqs = [Req("a", 20, 1), Req("b", 6, 1)]
    cfg = SchedConfig(long_prefill_token_threshold=2, long_prefill_token_threshold_adaptive=True)
    # max(2, 32 // 2) = 16
    assert step_tokens(run_sim(reqs, cfg))[0] == {"a": 16, "b": 6}


def preempt_scenario(extra=()):
    # block_size 4, block 5개. A와 B는 8 token 중 7을 계산한 채 시작해 block 2개씩 쥔다.
    reqs = [
        Req("A", 8, 4, start_running=True, start_computed=7),
        Req("B", 8, 4, start_running=True, start_computed=7),
        *extra,
    ]
    return run_sim(reqs, SchedConfig(num_blocks=5, block_size=4))


def test_preempt_picks_last_running_and_recomputes_everything():
    result = preempt_scenario()
    assert step_tokens(result)[0] == {"A": 1, "B": 1}
    assert result.steps[1].preempted == ["B"]
    assert step_tokens(result)[1] == {"A": 1}
    # B는 생성 token 1개를 지닌 채 9 token 전부를 다시 계산한다.
    assert step_tokens(result)[4] == {"B": 9}
    m = {x.request_id: x for x in result.metrics()}
    assert (m["A"].num_preemptions, m["B"].num_preemptions) == (0, 1)
    assert m["B"].output_tokens == 4
    assert len(result.steps) == 7
    assert result.counters()["vllm:num_preemptions"] == 1


def test_waiting_is_skipped_on_a_step_with_preemption():
    # block_size 16, block 4개, 예산 17. A와 B는 32 token 중 31을 계산한 채 시작해 block 2개씩 쥔다.
    reqs = [
        Req("A", 32, 4, start_running=True, start_computed=31),
        Req("B", 32, 4, start_running=True, start_computed=31),
    ]
    result = run_sim(reqs, SchedConfig(max_num_batched_tokens=17, num_blocks=4))
    # step 2: A가 B를 내보내고 block 하나를 더 잡는다. free block 1개와 예산 16이 남아
    # B의 16 token chunk가 들어갈 수 있는데도 waiting을 보지 않는다.
    assert result.steps[1].preempted == ["B"]
    assert step_tokens(result)[1] == {"A": 1}
    assert result.steps[1].budget_left == 16
    assert result.steps[1].blocks_in_use == 3
    assert "stop_waiting_preempted" in kinds(result, 2)
    assert "schedule_waiting" not in kinds(result, 2)
    # preempt가 없는 다음 step에는 같은 chunk가 들어간다.
    assert step_tokens(result)[2] == {"A": 1, "B": 16}


def test_head_of_waiting_blocks_later_requests():
    # block_size 16, block 5개. A와 B는 block 2개씩 쥐고 시작하고, C(block 1개)는 step 2에 도착한다.
    reqs = [
        Req("A", 32, 4, start_running=True, start_computed=31),
        Req("B", 32, 4, start_running=True, start_computed=31),
        Req("C", 16, 1, arrival_ms=1.0),
    ]
    result = run_sim(reqs, SchedConfig(max_num_batched_tokens=64, num_blocks=5))
    assert result.steps[1].waiting_before == ["C"]
    assert result.steps[1].preempted == ["B"]
    # step 3, 4: 맨 앞 B는 33 token에 block 3개가 필요한데 free는 2개다. C는 1개면 되지만 건너뛰지 않는다.
    for step in (2, 3):
        assert result.steps[step].waiting_before == ["B", "C"]
        assert step_tokens(result)[step] == {"A": 1}
        assert result.steps[step].blocks_in_use == 3
    # A가 끝난 step 5에 B와 C가 순서대로 들어간다.
    assert step_tokens(result)[4] == {"B": 33, "C": 16}


def test_pool_smaller_than_input_repeats_until_max_steps_without_full_input_check():
    # block 2개면 32 token까지만 잡는다. 첫 chunk만 보므로 들어와서 자기를 내보내기를 끝없이 반복한다.
    with pytest.raises(SimStuck, match=r"max_steps\(40\).*waiting \['big'\]"):
        run_sim([Req("big", 100, 1)], SchedConfig(num_blocks=2), max_steps=40)


def test_stuck_when_request_can_never_fit():
    # 전체 입력 검사를 켜면 첫 step부터 한 token도 못 넣고 멈춘다. max_steps에 닿지 않는다.
    with pytest.raises(SimStuck, match=r"step 1에서.*토큰을 하나도.*waiting \['big'\]"):
        run_sim([Req("big", 100, 1)], SchedConfig(num_blocks=2, reserve_full_isl=True))


def test_stuck_message_names_requests_that_have_not_arrived_separately():
    # chunked를 끄고 검사도 건너뛰면 doc은 t=0에 예산을 넘어 멈춘다. faq-1은 그때 아직 도착 전이다.
    config = SchedConfig(max_num_batched_tokens=32, enable_chunked_prefill=False)
    with pytest.raises(SimStuck) as caught:
        run_sim([Req("doc", 400, 1), Req("faq-1", 30, 1, arrival_ms=10.0)], config, validate=False)
    assert str(caught.value).endswith("running [], waiting ['doc'], 아직 도착하지 않음 ['faq-1'].")


def test_stuck_message_lists_requests_that_arrived_as_waiting():
    config = SchedConfig(max_num_batched_tokens=32, enable_chunked_prefill=False)
    with pytest.raises(SimStuck) as caught:
        run_sim([Req("doc", 400, 1), Req("faq-1", 30, 1)], config, validate=False)
    assert str(caught.value).endswith("running [], waiting ['doc', 'faq-1'], 아직 도착하지 않음 [].")


def test_reserve_full_isl_is_off_by_default_so_existing_tables_hold():
    assert SchedConfig().reserve_full_isl is False
    result = run_sim(doc_faq_chat(), SchedConfig(num_blocks=5))
    assert step_tokens(result)[1] == {"doc": 22, "faq": 10}
    assert result.counters()["vllm:num_preemptions"] == 1


def test_reserve_full_isl_holds_back_a_request_whose_input_does_not_fit():
    # step 2 뒤 doc이 block 4개를 쥐어 free는 1개다. faq는 20 token에 block 2개가 필요하므로 첫 chunk 10 token만으로는 들어오지 못한다.
    result = run_sim(doc_faq_chat(), SchedConfig(num_blocks=5, reserve_full_isl=True))
    assert step_tokens(result)[1] == {"doc": 22}
    assert result.steps[1].waiting_after == 2
    assert result.counters()["vllm:num_preemptions"] == 0
    assert len(result.steps) == 15
    assert step_tokens(result)[9] == {"faq": 20, "chat": 12}


def test_reserve_full_isl_checks_the_whole_input_not_the_first_chunk():
    # block 16, 예산 16이면 첫 chunk는 block 1개면 된다. 전체 입력이 block 몇 개인지가 입장을 가른다.
    tight = SchedConfig(max_num_batched_tokens=16, num_blocks=3, reserve_full_isl=True)
    fits = run_sim([Req("a", 47, 1)], tight)  # 47 token은 block 3개
    assert step_tokens(fits)[0] == {"a": 16}
    with pytest.raises(SimStuck, match="waiting \\['a'\\]"):
        run_sim([Req("a", 49, 1)], tight)  # 49 token은 block 4개


def test_reserve_full_isl_admits_at_exactly_the_free_block_count():
    # 48 token은 정확히 block 3개, free도 3개다.
    result = run_sim([Req("a", 48, 1)], SchedConfig(num_blocks=3, reserve_full_isl=True))
    assert step_tokens(result)[0] == {"a": 32}


def test_reserve_full_isl_counts_generated_tokens_when_a_request_returns():
    # A, B가 각각 block 2개. B가 step 2에 밀려나고 생성 token 1개를 지닌 채 돌아온다.
    # 복귀 때 33 token은 block 3개라 free 3개가 될 때까지 기다린다(A가 step 4에 끝난다).
    reqs = [
        Req("A", 32, 4, start_running=True, start_computed=31),
        Req("B", 32, 4, start_running=True, start_computed=31),
    ]
    result = run_sim(reqs, SchedConfig(num_blocks=5, max_num_batched_tokens=64, reserve_full_isl=True))
    assert result.steps[1].preempted == ["B"]
    assert step_tokens(result)[2] == {"A": 1}
    assert step_tokens(result)[3] == {"A": 1}
    assert step_tokens(result)[4] == {"B": 33}


def test_sweep_can_compare_the_full_input_check():
    rows = sweep(doc_faq_chat(), "reserve_full_isl", [False, True], SchedConfig(num_blocks=8))
    assert [(r["reserve_full_isl"], r["num_preemptions"]) for r in rows] == [(False, 3), (True, 0)]


def test_max_steps_raises():
    with pytest.raises(SimStuck, match="max_steps"):
        run_sim([Req("a", 100, 1)], SchedConfig(max_num_batched_tokens=1), max_steps=5)


def test_idle_clock_jumps_to_next_arrival():
    result = run_sim([Req("a", 4, 1), Req("b", 4, 1, arrival_ms=100.0)])
    assert result.steps[1].start_ms == 100.0
    assert result.steps[0].end_ms == 12.0


def test_metrics_hand_computed_with_network_delay():
    # server 도착 7, step1 7->27(20 token), step2 27->37.5, step3 37.5->48. client는 +2.
    cfg = SchedConfig(toy_network_ms=2.0)
    m = run_sim([Req("r", 20, 3, arrival_ms=5.0)], cfg).metrics()[0]
    assert m.chunk_times_ms == [29.0, 39.5, 50.0]
    assert m.send_ms == 5.0
    assert m.client_ttft_ms == 24.0
    assert m.client_itl_ms == [10.5, 10.5]
    assert m.client_itl_mean_ms == 10.5
    assert m.client_e2el_ms == 45.0
    assert m.client_tpot_ms == 10.5
    assert m.server_ttft_ms == 20.0
    assert m.server_e2e_ms == 41.0
    assert m.server_tpot_ms == 10.5
    assert m.queue_ms == 0.0
    assert m.num_chunks == 3


def test_queue_ms_counts_wait_for_first_schedule():
    reqs = [Req("a", 4, 1), Req("b", 4, 1)]
    m = {x.request_id: x for x in run_sim(reqs, SchedConfig(max_num_seqs=1)).metrics()}
    assert m["a"].queue_ms == 0.0
    assert m["b"].queue_ms == 12.0
    assert m["b"].server_ttft_ms == 24.0


def test_single_output_token_has_no_tpot_or_itl():
    m = run_sim([Req("a", 4, 1)]).metrics()[0]
    assert m.client_tpot_ms is None
    assert m.server_tpot_ms == 0.0
    assert m.client_itl_ms == []
    assert m.client_itl_mean_ms is None


def test_stream_interval_groups_tokens_but_first_token_is_sent_at_once():
    five = Req("a", 4, 5)
    assert run_sim([five], SchedConfig(stream_interval=1)).metrics()[0].num_chunks == 5
    # token 1, 3, 5에서 보낸다.
    assert run_sim([five], SchedConfig(stream_interval=2)).metrics()[0].num_chunks == 3


def test_spans_mark_wait_compute_and_preempted():
    spans = [s for s in preempt_scenario().spans() if s["lane"] == "B"]
    assert [(s["kind"], s["start"], s["end"]) for s in spans] == [
        ("prefill", 0.0, 11.0),
        ("preempted", 11.0, 42.5),
        ("prefill", 42.5, 57.0),
        ("decode", 57.0, 67.5),
        ("decode", 67.5, 78.0),
    ]


def test_counters_and_prometheus_text_for_one_request():
    result = run_sim([Req("r", 20, 3)])
    assert result.counters(at_step=1)["vllm:kv_cache_usage_perc"] == 2 / 64
    assert result.counters()["vllm:kv_cache_usage_perc"] == 0.0
    lines = result.to_prometheus_text(counter_suffix="_total").splitlines()
    assert lines[0] == "# constructed teaching sample, not measured"
    labels = 'model_name="GLM-5.3-Flash",engine="0"'
    assert f"vllm:num_preemptions_total{{{labels}}} 0" in lines
    assert f"vllm:time_to_first_token_seconds_sum{{{labels}}} 0.02" in lines
    assert f"vllm:e2e_request_latency_seconds_sum{{{labels}}} 0.041" in lines
    assert all(labels in line for line in lines[1:])
    early = result.to_prometheus_text(at_step=1).splitlines()
    assert f"vllm:time_to_first_token_seconds_count{{{labels}}} 1" in early
    assert f"vllm:e2e_request_latency_seconds_count{{{labels}}} 0" in early


def test_prefix_cache_counters_count_tokens():
    result = run_sim([Req("a", 40, 1, cached_tokens=32)])
    assert step_tokens(result) == [{"a": 8}]
    c = result.counters()
    assert (c["vllm:prefix_cache_queries"], c["vllm:prefix_cache_hits"]) == (40, 32)


def test_sweep_changes_one_parameter_and_groups_by_id_prefix():
    rows = sweep([Req("doc-1", 20, 1), Req("faq-1", 4, 1)], "max_num_batched_tokens", [8, 32])
    # 8 token 예산이면 doc이 8, 8, 4로 나뉘고 faq는 마지막 step에 합류한다.
    assert [r["steps"] for r in rows] == [3, 1]
    assert rows[1]["max_num_batched_tokens"] == 32
    assert {"ttft_mean_ms:doc", "ttft_mean_ms:faq"} <= rows[0].keys()
    with pytest.raises(ValueError, match="nope"):
        sweep([Req("a", 4, 1)], "nope", [1])


def test_preset_workloads():
    assert [(r.request_id, r.prompt_tokens, r.max_tokens) for r in doc_faq_chat()] == [
        ("doc", 54, 8),
        ("faq", 20, 6),
        ("chat", 34, 4),
    ]
    mixed = mixed_workload()
    assert [r.request_id for r in mixed] == ["doc", "faq-1", "faq-2", "faq-3", "faq-4", "faq-5"]
    assert mixed[3].arrival_ms == 30.0


def test_request_validation_messages_carry_numbers():
    with pytest.raises(ValueError, match="4096"):
        run_sim([Req("a", 4000, 200)])
    with pytest.raises(ValueError, match="10"):
        run_sim([Req("a", 40, 1, cached_tokens=10)])


def test_not_modeled_discloses_full_input_reservation():
    from vllm_lab import kv_sim, sched_sim
    for notes in (sched_sim.NOT_MODELED, kv_sim.NOT_MODELED):
        assert any("scheduler_reserve_full_isl" in s for s in notes)


def test_not_modeled_names_the_real_class_differences():
    from vllm_lab.sched_sim import NOT_MODELED
    required = {
        "cached_tokens 몫": "single_type_kv_cache_manager.py:245-248",
        "적중 block이 free 칸": "single_type_kv_cache_manager.py:255-260",
        "prefix cache를 끄는 칸": "kv_cache_manager.py:253-256",
    }
    for phrase, citation in required.items():
        assert any(phrase in line and citation in line for line in NOT_MODELED), phrase


def test_default_of_the_real_setting_is_stated_on_the_field():
    assert "기본은 True" in SchedConfig.__doc__
