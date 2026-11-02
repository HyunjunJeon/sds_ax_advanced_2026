"""kv_math의 손계산 검증. 기대값은 손으로 푼 숫자이고 구현 식을 되풀이하지 않는다."""

from __future__ import annotations

import re

import pytest

from vllm_lab import kv_math
from vllm_lab.kv_math import (
    METRIC_NAMES,
    UnsupportedKVShape,
    block_bytes,
    capacity_from_budget,
    glm53_kv_note,
    histogram_mean_delta,
    metric_delta,
    metric_value,
    metrics_from_chunks,
    metrics_report,
    parse_prometheus,
    prefix_hit_rate_delta,
    raw_kv_bytes,
    tokens_processed_without_kv,
)

GIB = 2**30
NO_ENGINE_LABELS = 'engine="0",model_name="m"'


def chunk(t, *, choices=True, content=None, reasoning=None, tokens=None):
    return {"t": t, "has_choices": choices, "content": content, "reasoning": reasoning, "completion_tokens": tokens}


# --- 산수 -------------------------------------------------------------------------------


def test_tokens_without_kv_54_prompt_8_outputs():
    # 54+55+...+61 = 8*54 + (0+...+7) = 432 + 28 = 460. KV를 쓰면 54 + 7 = 61.
    result = tokens_processed_without_kv(54, 8)
    assert result["without_kv"] == 460
    assert result["with_kv"] == 61
    assert result["ratio"] == pytest.approx(460 / 61)


def test_tokens_without_kv_single_output_has_ratio_one():
    assert tokens_processed_without_kv(10, 1) == {"without_kv": 10, "with_kv": 10, "ratio": 1.0}


def test_tokens_without_kv_rejects_zero_output():
    with pytest.raises(ValueError, match="output_tokens=0"):
        tokens_processed_without_kv(54, 0)


def test_block_bytes_bf16_gqa_block():
    # 8 head * 16 token * (128 + 128) * 2 byte = 65536
    assert block_bytes(8, 128) == 65536


def test_block_bytes_head_size_v_zero_drops_the_two_factor():
    # MLA처럼 별도 V가 없는 모양: 1 * 16 * (576 + 0) * 2 = 18432
    assert block_bytes(1, 576, head_size_v=0) == 18432


def test_block_bytes_unknown_dtype_is_rejected():
    with pytest.raises(ValueError, match="int4"):
        block_bytes(8, 128, dtype="int4")


def test_fp8_halves_only_the_block_payload_not_the_rest_of_the_budget():
    # 24 GiB, 가중치 12 GiB, 기타 2 GiB, 32층, KV head 8, head 128.
    # budget = int(24 GiB * 0.92) = 23,708,219,473, kv = budget - 14 GiB = 8,675,833,937.
    # bf16 block(전 층) = 65536 * 32 = 2,097,152 -> 4136 block. fp8는 1,048,576 -> 8273 block.
    layers = 32
    bf16_block = block_bytes(8, 128, "bfloat16")
    fp8_block = block_bytes(8, 128, "fp8")
    assert fp8_block * 2 == bf16_block

    common = dict(gpu_total_bytes=24 * GIB, weights_bytes=12 * GIB, other_bytes=2 * GIB)
    bf16 = capacity_from_budget(**common, block_bytes_all_layers=bf16_block * layers)
    fp8 = capacity_from_budget(**common, block_bytes_all_layers=fp8_block * layers)

    assert bf16.budget_bytes == fp8.budget_bytes == 23_708_219_473
    assert bf16.kv_bytes == fp8.kv_bytes == 8_675_833_937
    assert bf16.num_blocks == 4136
    assert fp8.num_blocks == 8273
    # KV 몫만 두 배로 담긴다. 가중치와 기타 14 GiB는 그대로라 전체 메모리 절감이 2배가 아니다.
    assert bf16.budget_bytes - bf16.kv_bytes == 14 * GIB


def test_raw_kv_bytes_mha_hand_value():
    # 2 * B2 * L32 * T1000 * n32 * d128 * 2byte = 1,048,576,000
    got = raw_kv_bytes(batch=2, layers=32, tokens=1000, head_type="MHA", num_heads=32, head_dim=128)
    assert got == 1_048_576_000


def test_raw_kv_bytes_gqa_uses_kv_heads_and_mqa_uses_one():
    base = dict(batch=2, layers=32, tokens=1000, num_heads=32, head_dim=128)
    assert raw_kv_bytes(head_type="GQA", num_kv_heads=8, **base) == 262_144_000
    assert raw_kv_bytes(head_type="MQA", **base) == 32_768_000


def test_raw_kv_bytes_fp8_is_half_of_bf16():
    base = dict(batch=1, layers=2, tokens=3, head_type="MHA", num_heads=4, head_dim=5)
    assert raw_kv_bytes(dtype="bfloat16", **base) == 2 * 1 * 2 * 3 * 4 * 5 * 2
    assert raw_kv_bytes(dtype="fp8", **base) == 2 * 1 * 2 * 3 * 4 * 5 * 1


def test_raw_kv_bytes_gqa_without_kv_heads_is_rejected():
    with pytest.raises(ValueError, match="num_kv_heads"):
        raw_kv_bytes(batch=1, layers=1, tokens=1, head_type="GQA", num_heads=8, head_dim=64)


@pytest.mark.parametrize("head_type", ["MLA", "recurrent", "glm5next"])
def test_raw_kv_bytes_refuses_shapes_the_formula_cannot_cover(head_type):
    with pytest.raises(UnsupportedKVShape, match="glm53_kv_note"):
        raw_kv_bytes(batch=1, layers=1, tokens=1, head_type=head_type, num_heads=8, head_dim=64)


def test_unsupported_shape_is_a_value_error():
    assert issubclass(UnsupportedKVShape, ValueError)


def test_raw_kv_bytes_unknown_head_type_is_a_plain_value_error():
    with pytest.raises(ValueError) as caught:
        raw_kv_bytes(batch=1, layers=1, tokens=1, head_type="XYZ", num_heads=8, head_dim=64)
    assert not isinstance(caught.value, UnsupportedKVShape)


def test_glm53_note_gives_reasons_and_no_invented_numbers():
    note = glm53_kv_note()
    for term in ("KDA", "MLA", "indexer", "tail", "padding", "02b"):
        assert term in note
    assert not re.search(r"(kv_lora_rank|index_kpool)\s*[=:]?\s*\d", note)
    assert len(re.findall(r"^\d\. ", note, flags=re.M)) == 5


def test_capacity_e5_hand_value():
    got = capacity_from_budget(
        gpu_total_bytes=24 * GIB,
        weights_bytes=12 * GIB,
        other_bytes=2 * GIB,
        block_bytes_all_layers=262144,
        max_model_len=8192,
    )
    assert got.num_blocks == 33095
    assert got.capacity_tokens == 529520
    assert got.max_concurrency == pytest.approx(64.638, abs=1e-3)
    assert got.log_line == (
        "GPU KV cache size: 529,520 tokens, Maximum concurrency for 8,192 tokens per request: 64.64x"
    )


def test_capacity_with_no_room_for_kv_is_rejected_with_the_number():
    with pytest.raises(ValueError, match="-"):
        capacity_from_budget(
            gpu_total_bytes=10 * GIB, weights_bytes=12 * GIB, other_bytes=0, block_bytes_all_layers=1024
        )


# --- Prometheus -------------------------------------------------------------------------

SCRAPE_BEFORE = f"""\
# HELP vllm:num_preemptions_total Cumulative preemptions
# TYPE vllm:num_preemptions_total counter
vllm:num_preemptions_total{{{NO_ENGINE_LABELS}}} 1.0

vllm:prefix_cache_queries_total{{{NO_ENGINE_LABELS}}} 100.0
vllm:prefix_cache_hits_total{{{NO_ENGINE_LABELS}}} 40.0
vllm:num_requests_waiting{{{NO_ENGINE_LABELS}}} 0.0
vllm:time_to_first_token_seconds_bucket{{le="0.5",{NO_ENGINE_LABELS}}} 3.0
vllm:time_to_first_token_seconds_sum{{{NO_ENGINE_LABELS}}} 2.0
vllm:time_to_first_token_seconds_count{{{NO_ENGINE_LABELS}}} 4.0
"""

SCRAPE_AFTER = f"""\
vllm:num_preemptions_total{{{NO_ENGINE_LABELS}}} 4.0
vllm:prefix_cache_queries_total{{{NO_ENGINE_LABELS}}} 300.0
vllm:prefix_cache_hits_total{{{NO_ENGINE_LABELS}}} 100.0
vllm:num_requests_waiting{{{NO_ENGINE_LABELS}}} 7.0
vllm:kv_cache_usage_perc{{{NO_ENGINE_LABELS}}} 0.25
vllm:time_to_first_token_seconds_sum{{{NO_ENGINE_LABELS}}} 5.0
vllm:time_to_first_token_seconds_count{{{NO_ENGINE_LABELS}}} 6.0
"""


def test_parse_prometheus_keys_are_name_and_sorted_label_tuple():
    samples = parse_prometheus(SCRAPE_BEFORE)
    key = ("vllm:num_preemptions_total", (("engine", "0"), ("model_name", "m")))
    assert samples[key] == 1.0
    assert len(samples) == 7


def test_parse_prometheus_label_with_comma_and_escaped_quote():
    samples = parse_prometheus('vllm:x{model_name="a,b\\"c",engine="0"} 2')
    assert samples == {("vllm:x", (("engine", "0"), ("model_name", 'a,b"c'))): 2.0}


def test_parse_prometheus_value_without_labels_and_with_timestamp():
    assert parse_prometheus("vllm:y 3.5 1700000000") == {("vllm:y", ()): 3.5}


def test_parse_prometheus_unreadable_line_is_a_value_error():
    with pytest.raises(ValueError, match="not a sample"):
        parse_prometheus("# fine\nnot a sample\n")


def test_metric_value_falls_back_to_total_suffix():
    samples = parse_prometheus(SCRAPE_BEFORE)
    assert metric_value(samples, METRIC_NAMES["preemptions"]) == 1.0


def test_metric_value_missing_is_none_never_zero():
    samples = parse_prometheus(SCRAPE_BEFORE)
    assert metric_value(samples, METRIC_NAMES["kv_usage"]) is None
    assert metric_value(samples, "vllm:no_such_metric") is None


def test_metric_value_reads_the_registered_name_and_the_exposed_total_name():
    # P3-38: 등록 이름에는 _total이 없고 prometheus_client가 노출할 때 붙인다. 서버 출력은 저자가 확인하지 않아 둘 다 읽는다.
    for text in ('vllm:num_preemptions_total{engine="0"} 2', 'vllm:num_preemptions{engine="0"} 2'):
        assert metric_value(parse_prometheus(text), METRIC_NAMES["preemptions"]) == 2.0


def test_parse_prometheus_doc_states_the_settled_total_suffix():
    assert "붙을 수 있다" not in parse_prometheus.__doc__
    assert "_total이 붙는다" in parse_prometheus.__doc__ and "P3-38" in parse_prometheus.__doc__


def test_metric_value_real_zero_stays_zero():
    samples = parse_prometheus(SCRAPE_BEFORE)
    assert metric_value(samples, METRIC_NAMES["waiting"]) == 0.0


def test_metric_value_sums_over_engines_and_filters_by_label():
    text = (
        'vllm:num_requests_waiting_by_reason{engine="0",reason="capacity"} 2\n'
        'vllm:num_requests_waiting_by_reason{engine="0",reason="deferred"} 5\n'
        'vllm:num_requests_waiting_by_reason{engine="1",reason="capacity"} 11\n'
    )
    samples = parse_prometheus(text)
    name = "vllm:num_requests_waiting_by_reason"
    assert metric_value(samples, name) == 18.0
    assert metric_value(samples, name, reason="capacity") == 13.0
    assert metric_value(samples, name, reason="capacity", engine="1") == 11.0
    assert metric_value(samples, name, reason="other") is None


def test_metric_delta_counter_and_missing_side():
    before, after = parse_prometheus(SCRAPE_BEFORE), parse_prometheus(SCRAPE_AFTER)
    assert metric_delta(before, after, METRIC_NAMES["preemptions"]) == 3.0
    # kv_usage는 before에 없으므로 after 값이 있어도 변화량은 None이다.
    assert metric_delta(before, after, METRIC_NAMES["kv_usage"]) is None


def test_histogram_mean_delta_divides_sum_delta_by_count_delta():
    before, after = parse_prometheus(SCRAPE_BEFORE), parse_prometheus(SCRAPE_AFTER)
    # (5.0 - 2.0) / (6 - 4) = 1.5. 누적 평균 5/6이나 sum 변화량 3.0이 아니다.
    assert histogram_mean_delta(before, after, METRIC_NAMES["ttft"]) == 1.5


def test_histogram_mean_delta_no_new_observations_is_none():
    before = parse_prometheus(SCRAPE_BEFORE)
    assert histogram_mean_delta(before, before, METRIC_NAMES["ttft"]) is None


def test_histogram_mean_delta_counter_reset_is_none():
    before, after = parse_prometheus(SCRAPE_AFTER), parse_prometheus(SCRAPE_BEFORE)
    assert histogram_mean_delta(before, after, METRIC_NAMES["ttft"]) is None


def test_histogram_mean_delta_missing_histogram_is_none():
    before, after = parse_prometheus(SCRAPE_BEFORE), parse_prometheus(SCRAPE_AFTER)
    assert histogram_mean_delta(before, after, METRIC_NAMES["itl"]) is None


def test_prefix_hit_rate_delta_uses_changes_not_totals():
    before, after = parse_prometheus(SCRAPE_BEFORE), parse_prometheus(SCRAPE_AFTER)
    # (100 - 40) / (300 - 100) = 0.3. 누적 비율 100/300이 아니다.
    assert prefix_hit_rate_delta(before, after) == pytest.approx(0.3)


def test_prefix_hit_rate_delta_zero_queries_and_missing_are_none():
    before = parse_prometheus(SCRAPE_BEFORE)
    assert prefix_hit_rate_delta(before, before) is None
    assert prefix_hit_rate_delta({}, before) is None


def test_metrics_report_covers_every_metric_with_none_for_missing():
    before, after = parse_prometheus(SCRAPE_BEFORE), parse_prometheus(SCRAPE_AFTER)
    rows = {row["이름"]: row for row in metrics_report(before, after)}
    assert set(rows) == set(METRIC_NAMES.values())
    assert rows[METRIC_NAMES["kv_usage"]] | {"항목": ""} == {
        "항목": "", "이름": METRIC_NAMES["kv_usage"], "종류": "Gauge", "값": 0.25,
    }
    assert rows[METRIC_NAMES["waiting"]]["값"] == 7.0  # Gauge는 after 값
    assert rows[METRIC_NAMES["preemptions"]]["값"] == 3.0  # Counter는 변화량
    assert rows[METRIC_NAMES["preemptions"]]["종류"] == "Counter"
    assert rows[METRIC_NAMES["ttft"]]["값"] == 1.5  # Histogram은 평균 변화량
    assert rows[METRIC_NAMES["running"]]["값"] is None
    assert rows[METRIC_NAMES["e2e"]]["값"] is None


def test_metric_names_are_the_exact_registered_strings():
    assert METRIC_NAMES == {
        "prefix_queries": "vllm:prefix_cache_queries",
        "prefix_hits": "vllm:prefix_cache_hits",
        "kv_usage": "vllm:kv_cache_usage_perc",
        "preemptions": "vllm:num_preemptions",
        "waiting": "vllm:num_requests_waiting",
        "running": "vllm:num_requests_running",
        "ttft": "vllm:time_to_first_token_seconds",
        "itl": "vllm:inter_token_latency_seconds",
        "tpot": "vllm:request_time_per_output_token_seconds",
        "e2e": "vllm:e2e_request_latency_seconds",
        "queue": "vllm:request_queue_time_seconds",
    }


# --- chunk 지표 -------------------------------------------------------------------------


def test_chunks_one_token_per_chunk_has_no_warning_and_exact_times():
    chunks = [
        chunk(10.5, content=""),  # 비어 있어도 TTFT로 친다
        chunk(10.75, content="a"),
        chunk(11.0, content="b"),
        chunk(11.5, content="c"),
        chunk(99.0, choices=False, tokens=4),  # usage 전용: 시각을 옮기지 않는다
    ]
    got = metrics_from_chunks(10.0, chunks)
    assert got.ttft_s == 0.5
    assert got.itl_s == [0.25, 0.25, 0.5]
    assert got.e2el_s == 1.5
    assert got.tpot_s == pytest.approx(1.0 / 3)
    assert got.output_tokens == 4
    assert got.num_chunks == 4
    assert got.first_visible_s == 0.75
    assert got.warnings == []


def test_chunks_with_several_tokens_each_warn():
    chunks = [chunk(1.5, content="ab"), chunk(2.0, content="cd"), chunk(2.0, choices=False, tokens=10)]
    got = metrics_from_chunks(1.0, chunks)
    assert got.num_chunks == 2
    assert any("한 chunk에 token이 여럿입니다. ITL은 token당 지연이 아닙니다" in w for w in got.warnings)
    assert got.tpot_s == pytest.approx((1.0 - 0.5) / 9)


def test_chunks_equal_tokens_and_chunks_do_not_warn():
    got = metrics_from_chunks(0.0, [chunk(0.5, content="a", tokens=2), chunk(1.0, content="b")])
    assert got.warnings == []


def test_chunks_unknown_output_count_warns_and_has_no_tpot():
    got = metrics_from_chunks(0.0, [chunk(0.5, content="a"), chunk(1.0, content="b")])
    assert got.output_tokens is None
    assert got.tpot_s is None
    assert len(got.warnings) == 1 and "출력 token 수를 모릅니다" in got.warnings[0]


def test_chunks_single_output_token_has_no_tpot():
    got = metrics_from_chunks(0.0, [chunk(0.5, content="a"), chunk(0.5, choices=False, tokens=1)])
    assert got.tpot_s is None
    assert got.warnings == []


def test_chunks_reasoning_only_chunk_is_not_visible():
    chunks = [chunk(0.5, reasoning="hmm"), chunk(1.5, content="answer")]
    got = metrics_from_chunks(0.0, chunks)
    assert got.ttft_s == 0.5
    assert got.first_visible_s == 1.5


def test_chunks_without_choices_give_none_not_zero():
    got = metrics_from_chunks(0.0, [chunk(3.0, choices=False, tokens=5)])
    assert got.ttft_s is None
    assert got.e2el_s is None
    assert got.first_visible_s is None
    assert got.itl_s == []
    assert got.num_chunks == 0
    assert got.warnings


def test_chunks_going_back_in_time_are_rejected():
    with pytest.raises(ValueError, match=r"chunks\[1\]"):
        metrics_from_chunks(0.0, [chunk(2.0, content="a"), chunk(1.0, content="b")])


def test_module_does_not_import_sibling_lab_modules():
    source = open(kv_math.__file__, encoding="utf-8").read()
    for sibling in ("kv_sim", "sched_sim", "agent_sim"):
        assert sibling not in source
