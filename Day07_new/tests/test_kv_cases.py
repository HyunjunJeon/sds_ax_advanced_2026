"""kv_cases의 손계산 검증. 기대값은 손으로 푼 숫자와 제작사 그림 값이고 구현 식을 되풀이하지 않는다."""

from __future__ import annotations

import ast
import json
import re

import pytest

from vllm_lab import DATA_DIR, ROOT, kv_cases
from vllm_lab.kv_cases import (
    GLM,
    KINDS,
    MODELS,
    REAL_CLASS_ASSUMPTIONS,
    V4,
    V41,
    capacity_estimate,
    global_kv_per_token,
    glm_context_comparison,
    glm_kda_fixed_state,
    layer_table,
    real_block_size,
    real_kda_table,
    real_pages,
    real_scenarios,
    real_stride,
    reported_figures,
    tail_bytes_per_request,
)

GB = 10**9
BUDGET = {"gpu_total_bytes": 100 * GB, "weights_bytes": 10 * GB, "other_bytes": 0, "gpu_memory_utilization": 0.5}


def part(result, cache, ratio):
    return next(p for p in result["parts"] if p["cache"] == cache and p["tokens_per_state"] == ratio)


# --- DeepSeek-V4.1-Flash: 288B main, 68B indexer, kv_source [2, 8, 14](비율 2)와 [20](비율 1) ---


def test_v41_main_720_plus_indexer_170_is_890_and_reproduces_the_paper_figure():
    result = global_kv_per_token(V41)
    assert result["main_bytes_per_token"] == 720
    assert result["indexer_bytes_per_token"] == 170
    assert result["total_bytes_per_token"] == 890
    assert result["reported_bytes_per_token"] == 890
    assert result["kind"] == "reproduced"


def test_v41_parts_name_the_source_layers_and_records():
    result = global_kv_per_token(V41)
    assert part(result, "main", 2) == {
        "cache": "main", "tokens_per_state": 2, "layers": [2, 8, 14], "record_bytes": 288, "bytes_per_token": 432}
    assert part(result, "main", 1)["layers"] == [20]
    assert part(result, "main", 1)["bytes_per_token"] == 288
    assert part(result, "indexer", 2)["bytes_per_token"] == 102
    assert part(result, "indexer", 1) == {
        "cache": "indexer", "tokens_per_state": 1, "layers": [20], "record_bytes": 68, "bytes_per_token": 68}


def test_v41_index_only_layers_and_consumers_own_no_cache():
    rows = {row["layer"]: row for row in layer_table(V41)["rows"]}
    assert rows[0]["role"] == "swa_only"
    assert rows[2]["role"] == "kv_source"
    assert rows[3]["role"] == "consumer"
    assert (rows[24]["role"], rows[24]["compress_ratio"]) == ("index_source", 1)
    assert rows[24]["main_bytes_per_token"] == rows[24]["indexer_bytes_per_token"] == 0
    assert rows[3]["main_bytes_per_token"] == rows[3]["indexer_bytes_per_token"] == 0


def test_v41_table_stops_before_the_mtp_entries():
    assert [row["layer"] for row in layer_table(V41)["rows"]] == list(range(40))


# --- DeepSeek-V4-Flash: 584B main, 68B indexer, 21층 m=4, 20층 m=128 ---


def test_v4_3066_plus_91_25_plus_357_is_3514_25_and_reproduces_the_paper_figure():
    result = global_kv_per_token(V4)
    assert part(result, "main", 4)["bytes_per_token"] == 3066
    assert part(result, "main", 128)["bytes_per_token"] == 91.25
    assert part(result, "indexer", 4)["bytes_per_token"] == 357
    assert result["total_bytes_per_token"] == 3514.25
    assert result["reported_bytes_per_token"] == 3514
    assert result["kind"] == "reproduced"


def test_v4_layer_counts_and_hca_layers_have_no_indexer():
    result = global_kv_per_token(V4)
    assert len(part(result, "main", 4)["layers"]) == 21
    assert len(part(result, "main", 128)["layers"]) == 20
    assert part(result, "main", 128)["record_bytes"] == 584
    assert part(result, "indexer", 4)["record_bytes"] == 68
    assert not any(p["cache"] == "indexer" and p["tokens_per_state"] == 128 for p in result["parts"])


def test_v4_table_has_43_layers_with_two_leading_swa_layers():
    rows = layer_table(V4)["rows"]
    assert len(rows) == 43
    assert [row["role"] for row in rows[:4]] == ["swa_only", "swa_only", "csa", "hca"]
    assert rows[42]["role"] == "csa"


# --- GLM-5.3-Flash: 제작사 토큰당 값이 없다 ---


def test_glm_is_estimate_never_reported_with_1057_per_layer_times_11():
    result = global_kv_per_token(GLM)
    assert result["main_bytes_per_token"] == 1024 * 11
    assert result["indexer_bytes_per_token"] == 33 * 11
    assert result["total_bytes_per_token"] == 11627
    assert result["kind"] == "estimate"
    assert result["reported_bytes_per_token"] is None


def test_glm_indexer_record_is_132_over_kpool_4():
    result = global_kv_per_token(GLM)
    indexer = part(result, "indexer", 4)
    assert indexer["record_bytes"] == 132
    assert indexer["layers"] == [3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43]


def test_reported_figures_never_name_glm_and_keep_the_figure_values():
    figures = {row["model"]: row for row in reported_figures()}
    assert {name: row["bytes_per_token"] for name, row in figures.items()} == {
        "DeepSeek-V1": 389120, "DeepSeek-V3.2": 48068, V4: 3514, V41: 890}
    assert GLM not in figures
    assert {row["kind"] for row in figures.values()} == {"reported"}
    assert {row["source_id"] for row in figures.values()} == {"P7-29"}


def test_kda_state_with_no_speculation_is_4341760_bytes_per_layer():
    state = glm_kda_fixed_state()
    assert state["kind"] == "estimate"
    assert state["layers"] == 34
    assert state["conv_bytes_per_state"] == 147456  # 24576 폭 * 길이 3 * BF16 2
    assert state["recurrent_bytes_per_state"] == 4194304  # 64 * 128 * 128 * float32 4
    assert state["state_bytes_per_layer"] == 4341760
    assert state["resident_states"] == 1
    assert state["fixed_bytes_per_request"] == 147619840


def test_kda_num_spec_widens_conv_and_adds_a_state_block_per_draft():
    state = glm_kda_fixed_state(num_spec=5)
    assert state["conv_bytes_per_state"] == 393216  # 24576 * 8 * 2
    assert state["recurrent_bytes_per_state"] == 4194304
    assert state["resident_states"] == 6
    assert state["fixed_bytes_per_request"] == 4587520 * 6 * 34


def test_kda_align_mode_holds_two_states_plus_checkpoint_blocks():
    assert glm_kda_fixed_state(mamba_cache_mode="align")["resident_states"] == 2
    flashkda = glm_kda_fixed_state(mamba_cache_mode="align", prefill_checkpoint_blocks=1, num_spec=2)
    assert flashkda["resident_states"] == 5


def test_kda_none_mode_ignores_checkpoint_blocks():
    assert glm_kda_fixed_state(mamba_cache_mode="none", prefill_checkpoint_blocks=1)["resident_states"] == 1


@pytest.mark.parametrize("kwargs", [{"num_spec": -1}, {"prefill_checkpoint_blocks": -1}, {"mamba_cache_mode": "all"}])
def test_kda_bad_arguments_are_rejected(kwargs):
    with pytest.raises(ValueError):
        glm_kda_fixed_state(**kwargs)


def test_glm_table_marks_fixed_state_only_on_kda_layers():
    rows = layer_table(GLM)["rows"]
    assert len(rows) == 45
    assert sum(row["role"] == "kda" for row in rows) == 34
    assert rows[3]["role"] == "sparse_mla" and rows[3]["fixed_state_bytes"] is None
    assert rows[44]["role"] == "kda" and rows[44]["fixed_state_bytes"] == 4341760
    assert rows[44]["main_bytes_per_token"] == 0


def test_glm_comparison_crossover_is_about_12696_tokens():
    result = glm_context_comparison([0, 12696, 12697, 1_048_576])
    assert result["kind"] == "estimate"
    assert result["bytes_per_token"] == 11627
    assert result["crossover_tokens"] == pytest.approx(12696.29, abs=0.01)
    rows = result["rows"]
    assert rows[0] == {
        "context_tokens": 0, "fixed_state_bytes": 147619840, "accumulated_kv_bytes": 0, "fixed_share": 1.0}
    assert rows[1]["accumulated_kv_bytes"] < rows[1]["fixed_state_bytes"]
    assert rows[2]["accumulated_kv_bytes"] > rows[2]["fixed_state_bytes"]
    assert rows[3]["accumulated_kv_bytes"] == 12191793152
    assert rows[3]["fixed_share"] == pytest.approx(0.01196, abs=0.00001)


def test_glm_comparison_crossover_moves_with_resident_states():
    result = glm_context_comparison([], mamba_cache_mode="align", prefill_checkpoint_blocks=1)
    assert result["fixed_bytes_per_request"] == 442859520  # 147619840 * 3
    assert result["crossover_tokens"] == pytest.approx(38088.9, abs=0.1)
    assert result["rows"] == []


def test_glm_comparison_rejects_a_negative_context():
    with pytest.raises(ValueError, match="-1"):
        glm_context_comparison([-1])


# --- capacity_from_budget 위에 얹은 용량 ---


def test_capacity_v41_counts_blocks_from_890_per_token():
    # budget 50GB - weights 10GB = 40GB, block 890 * 128 = 113920B, 40GB // 113920 = 351123 block
    result = capacity_estimate(V41, block_size=128, **BUDGET)
    assert result["kind"] == "estimate"
    assert result["block_bytes_all_layers"] == 113920
    assert result["num_blocks"] == 351123
    assert result["capacity_tokens"] == 351123 * 128
    assert result["max_concurrency"] == pytest.approx(351123 * 128 / 8192)


def test_capacity_v4_block_of_128_holds_whole_records():
    result = capacity_estimate(V4, block_size=128, **BUDGET)
    assert result["block_bytes_all_layers"] == 449824  # 3514.25 * 128


def test_capacity_rejects_a_block_that_splits_a_record():
    with pytest.raises(ValueError, match="block_size=16.*128의 배수"):
        capacity_estimate(V4, block_size=16, **BUDGET)
    with pytest.raises(ValueError, match="block_size=6.*4의 배수"):
        capacity_estimate(GLM, block_size=6, **BUDGET)
    with pytest.raises(ValueError, match="block_size=3.*2의 배수"):
        capacity_estimate(V41, block_size=3, **BUDGET)


def test_capacity_glm_reserves_kda_state_before_counting_tokens():
    # 4 * 147619840 = 590479360B를 먼저 뺀다. 40GB - 그 값 = 39409520640B, block 11627 * 128 = 1488256B
    result = capacity_estimate(GLM, block_size=128, kda_requests=4, **BUDGET)
    assert result["reserved_kda_bytes"] == 590479360
    assert result["kv_bytes"] == 39409520640
    assert result["num_blocks"] == 26480
    assert result["kind"] == "estimate"


def test_capacity_glm_uses_the_given_state_when_counting_reservation():
    state = glm_kda_fixed_state(mamba_cache_mode="align")
    result = capacity_estimate(GLM, block_size=128, kda_requests=2, kda_state=state, **BUDGET)
    assert result["reserved_kda_bytes"] == 590479360  # 2 * 2벌 * 147619840


def test_capacity_refuses_kda_reservation_on_a_model_without_kda():
    with pytest.raises(ValueError, match="KDA 층이 없습니다"):
        capacity_estimate(V41, block_size=128, kda_requests=1, **BUDGET)


def test_capacity_reports_the_shortfall_when_the_reservation_uses_the_budget():
    with pytest.raises(ValueError, match="KV 예산이"):
        capacity_estimate(GLM, block_size=128, kda_requests=1000, **BUDGET)


def test_capacity_defaults_to_the_real_block_size():
    # V4는 256, 3514.25 * 256 = 899648B. GLM은 4352, 11627 * 4352 = 50600704B. V4.1은 128, 890 * 128 = 113920B.
    expected = {V4: (256, 899648), GLM: (4352, 50600704), V41: (128, 113920)}
    for model, (block, block_bytes) in expected.items():
        result = capacity_estimate(model, **BUDGET)
        assert (result["block_size"], result["block_bytes_all_layers"]) == (block, block_bytes), model
        assert result["kind"] == "estimate"


def test_capacity_still_takes_an_explicit_block_size():
    assert capacity_estimate(V4, block_size=128, **BUDGET)["block_size"] == 128


def test_capacity_assumptions_name_the_block_source_and_say_it_is_not_a_start_log():
    assumptions = capacity_estimate(GLM, **BUDGET)["assumptions"]
    assert any("real_block_size" in text and "시작 로그" in text for text in assumptions)


# --- 실제 클래스 호출 값(data/reference_specs.json) ---


@pytest.mark.parametrize(
    ("model", "scenario", "block", "stride", "record"),
    [
        (V41, "v41.flashmla_sm100.nvfp4.mxfp4", 128, 896.0, 890.0),
        (V4, "v4.flashmla_sm100.mxfp4", 256, 3584.25, 3514.25),
        (GLM, "glm.flashmla.bf16", 4352, 11631.53, 11627.0),
    ],
)
def test_real_stride_sits_next_to_the_record_sum(model, scenario, block, stride, record):
    result = real_stride(model)
    assert result["kind"] == "real_class"
    assert result["scenario"] == scenario
    assert result["block_size"] == block
    assert result["bytes_per_token"] == pytest.approx(stride, abs=0.005)
    assert result["record_bytes_per_token"] == record
    assert result["block_stride_bytes"] == pytest.approx(stride * block, abs=30)
    assert result["assumptions"] == REAL_CLASS_ASSUMPTIONS


def test_record_sums_stay_reproduced_while_real_values_are_a_separate_kind():
    assert global_kv_per_token(V41)["kind"] == "reproduced"
    assert global_kv_per_token(V4)["kind"] == "reproduced"
    assert global_kv_per_token(GLM)["kind"] == "estimate"
    assert real_stride(V41)["kind"] == "real_class"
    assert "real_class" in KINDS


def test_real_pages_of_v4_show_the_padding_on_each_cache():
    rows = {(row["cache"], row["tokens_per_state"]): row for row in real_pages(V4)}
    assert {key: (row["layers"], row["record_bytes"], row["page_bytes"]) for key, row in rows.items()} == {
        ("main", 4): (21, 584, 37440),
        ("main", 128): (20, 584, 1728),
        ("indexer", 4): (21, 68, 4608),
    }
    # 37440 * 21 / 256 = 3071.25, 1728 * 20 / 256 = 135, 4608 * 21 / 256 = 378
    assert rows["main", 4]["page_bytes_per_token"] == 3071.25
    assert rows["main", 128]["page_bytes_per_token"] == 135
    assert rows["indexer", 4]["page_bytes_per_token"] == 378
    # record 몫은 padding 전 값이다.
    assert rows["main", 128]["record_bytes_per_token"] == 91.25
    assert {row["kind"] for row in rows.values()} == {"real_class"}


def test_real_pages_of_v41_pad_only_the_ratio_two_indexer():
    rows = {(row["cache"], row["tokens_per_state"]): row["page_bytes_per_token"] for row in real_pages(V41)}
    assert rows == {("main", 2): 432, ("main", 1): 288, ("indexer", 2): 108, ("indexer", 1): 68}


def test_real_pages_of_glm_have_no_padding_so_its_stride_comes_from_alignment():
    rows = {row["cache"]: row["page_bytes_per_token"] for row in real_pages(GLM)}
    assert rows == {"main": 11264, "indexer": 363}
    assert real_stride(GLM)["bytes_per_token"] > 11627


def test_real_kda_table_holds_every_speculation_mode_and_tp_case():
    rows = {
        (r["num_spec"], r["mamba_cache_mode"], r["prefill_checkpoint_blocks"], r["tp_ranks"]): (
            r["fixed_bytes_unpadded_all_ranks"], r["fixed_bytes_padded_all_ranks"])
        for r in real_kda_table()
    }
    assert rows == {
        (0, "none", 0, 1): (147619840, 151519232),
        (5, "none", 0, 1): (935854080, 935854080),
        (0, "none", 1, 1): (147619840, 151519232),
        (0, "align", 0, 1): (295239680, 303038464),
        (5, "align", 0, 1): (1091829760, 1091829760),
        (0, "align", 1, 1): (442859520, 454557696),
        (5, "align", 1, 1): (1247805440, 1247805440),
        (0, "none", 0, 4): (147619840, 160432128),
        (0, "align", 1, 4): (442859520, 481296384),
    }
    assert {r["kind"] for r in real_kda_table()} == {"real_class"}


def test_real_kda_table_keeps_per_rank_values_apart_from_the_rank_sum():
    tp4 = next(r for r in real_kda_table() if r["tp_ranks"] == 4 and r["mamba_cache_mode"] == "none")
    assert tp4["state_bytes_per_rank"] == 1085440
    assert tp4["page_bytes_per_rank"] == 1179648
    assert tp4["fixed_bytes_padded_per_rank"] == 40108032  # 1179648 * 34
    assert tp4["stride_bytes_per_token_per_rank"] == pytest.approx(11645.33, abs=0.01)  # 13415424 / 1152


@pytest.mark.parametrize(
    ("num_spec", "mode", "checkpoint", "tp", "crossover"),
    [
        (0, "none", 0, 1, 13026.60),  # 151519232 / (50620416 / 4352)
        (0, "align", 1, 1, 39079.79),  # 454557696 / (50620416 / 4352)
        # TP4는 rank 하나끼리 나눈다. MLA record는 rank마다 1024B로 그대로이고 KDA만 네 몫으로 나뉜다.
        (0, "none", 0, 4, 3444.13),  # 40108032 / (13415424 / 1152)
        (0, "align", 1, 4, 10332.39),  # 120324096 / (13415424 / 1152)
    ],
)
def test_real_kda_crossover_divides_one_rank_by_one_rank(num_spec, mode, checkpoint, tp, crossover):
    row = next(r for r in real_kda_table()
               if (r["num_spec"], r["mamba_cache_mode"], r["prefill_checkpoint_blocks"], r["tp_ranks"])
               == (num_spec, mode, checkpoint, tp))
    assert row["crossover_tokens"] == pytest.approx(crossover, abs=0.01)


@pytest.mark.parametrize(("model", "block"), [(GLM, 4352), (V4, 256), (V41, 128)])
def test_real_block_size_per_model(model, block):
    assert real_block_size(model) == block


@pytest.mark.parametrize("call", [real_block_size, real_stride, real_pages, tail_bytes_per_request])
def test_real_lookups_name_the_choices_for_an_unknown_model(call):
    with pytest.raises(ValueError, match="가능한 값 3개"):
        call("Kimi-K3")


@pytest.mark.parametrize(
    ("scenario", "block", "groups"),
    [
        ("glm.flashmla.bf16", 4352, [9, 9, 8, 8, 22, 11]),
        ("glm.flashmla.bf16.spec5", 4480, [9, 9, 8, 8, 22, 11]),
        ("glm.flashmla.bf16.tp4", 1152, [9, 9, 8, 8, 22, 11]),
        ("glm.flashinfer_sm90.fp8", 8576, [9, 9, 8, 8, 22, 11]),
        ("glm.flashmla.fp8_ds_mla", 8576, [12, 11, 11, 22, 11]),
        ("glm.flashmla.nvfp4_ds_mla", 8576, [7, 7, 7, 7, 6, 22, 11]),
        ("glm.flashinfer_sm120.auto", 8704, [12, 11, 11, 22, 11]),
        ("v4.flashmla_sm100.mxfp4", 256, [22, 21, 62, 42, 20]),
        ("v41.flashmla_sm90.auto", 64, [6, 6, 6, 6, 6, 5, 5, 8, 3]),
        ("v41.flashmla_sm100.nvfp4", 128, [8, 8, 8, 8, 8, 8, 3]),
        ("v41.flashmla_sm100.nvfp4.mxfp4", 128, [6, 6, 6, 6, 6, 5, 5, 8, 3]),
        ("v41.flashmla_sm100.auto", 128, [10, 10, 10, 10, 8, 3]),
    ],
)
def test_real_scenarios_report_block_and_groups_by_storage_format(scenario, block, groups):
    row = next(r for r in real_scenarios() if r["scenario"] == scenario)
    assert row["kind"] == "real_class"
    assert row["block_size"] == block
    assert sorted(row["group_layers"]) == sorted(groups)
    assert row["group_count"] == len(groups)


def test_real_scenarios_show_the_group_count_moves_with_the_format():
    counts = {r["cache_dtype"]: r["group_count"] for r in real_scenarios(GLM) if r["scenario"].startswith("glm.flashmla.")}
    assert counts == {"auto": 6, "fp8_ds_mla": 5, "nvfp4_ds_mla": 7}


def test_real_scenarios_carry_the_records_of_that_format():
    rows = {r["scenario"]: (r["main_record_bytes"], r["indexer_record_bytes"]) for r in real_scenarios()}
    assert rows["v41.flashmla_sm100.nvfp4.mxfp4"] == (288, 68)
    assert rows["v41.flashmla_sm100.auto"] == (528, 132)
    assert rows["v41.flashmla_sm90.auto"] == (584, 132)
    assert rows["glm.flashmla.nvfp4_ds_mla"] == (352, 132)


def test_real_scenarios_filter_by_model_and_cover_every_run():
    assert {r["model"] for r in real_scenarios(V4)} == {V4}
    assert len(real_scenarios()) == 29
    with pytest.raises(ValueError, match="가능한 값 3개"):
        real_scenarios("Kimi-K3")


def test_v4_tail_adds_the_indexer_compressor_layers():
    result = tail_bytes_per_request(V4)
    rows = {(r["cache"], r["rows"]): r for r in result["rows"]}
    # CSA 8행 * 8192B * 21층, HCA 128행 * 4096B * 20층, indexer 8행 * 2048B * 21층
    assert rows["compressor_state", 8]["bytes_per_request"] == 1376256
    assert rows["compressor_state", 128]["bytes_per_request"] == 10485760
    assert rows["indexer_compressor_state", 8]["bytes_per_request"] == 344064
    assert result["total_bytes_per_request"] == 12206080
    assert result["kind"] == "estimate"


def test_tail_of_the_other_models_keeps_its_value():
    # V4.1: 8행 * 4096B * 3층. GLM: 4행 * 512B * 11층.
    assert tail_bytes_per_request(V41)["total_bytes_per_request"] == 98304
    assert tail_bytes_per_request(GLM)["total_bytes_per_request"] == 22528


def test_tail_says_it_is_a_lower_bound_computed_from_real_spec_inputs():
    assert any("하한" in text and "state_content_bytes" in text for text in tail_bytes_per_request(V4)["assumptions"])


def test_real_values_are_read_from_the_saved_run_not_written_in_the_module(tmp_path, monkeypatch):
    saved = json.loads((DATA_DIR / "reference_specs.json").read_text(encoding="utf-8"))
    for row in saved["rows"]:
        if row["id"] == "v41.flashmla_sm100.nvfp4.mxfp4.pool.bytes_per_token_stride":
            row["real"] = 1000.0
    for scenario in saved["scenarios"]:
        if scenario["scenario"] == "v41.flashmla_sm100.nvfp4.mxfp4":
            scenario["block_size"] = 512
    (tmp_path / "reference_specs.json").write_text(json.dumps(saved), encoding="utf-8")
    monkeypatch.setattr(kv_cases, "DATA_DIR", tmp_path)
    kv_cases._saved_specs.cache_clear()
    try:
        assert real_stride(V41)["bytes_per_token"] == 1000.0
        assert real_block_size(V41) == 512
    finally:
        kv_cases._saved_specs.cache_clear()


# --- 모든 반환값의 kind와 스냅샷 ---


@pytest.mark.parametrize("model", MODELS)
def test_every_result_carries_an_allowed_kind(model):
    assert global_kv_per_token(model)["kind"] in KINDS
    assert layer_table(model)["kind"] in KINDS
    assert capacity_estimate(model, block_size=128, **BUDGET)["kind"] in KINDS
    assert real_stride(model)["kind"] in KINDS
    assert tail_bytes_per_request(model)["kind"] in KINDS


@pytest.mark.parametrize("model", MODELS)
def test_layer_table_sums_to_the_global_total(model):
    rows = layer_table(model)["rows"]
    total = sum(row["main_bytes_per_token"] + row["indexer_bytes_per_token"] for row in rows)
    assert total == {GLM: 11627, V4: 3514.25, V41: 890}[model]


def test_unknown_model_names_the_choices():
    with pytest.raises(ValueError, match="가능한 값 3개"):
        global_kv_per_token("Kimi-K3")


def test_results_cite_the_snapshot_source():
    result = global_kv_per_token(V4)
    assert result["source_url"] == "https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash/raw/main/config.json"
    assert result["fetch_date"] == "2026-11-02"


def test_real_class_assumptions_keep_the_limits_of_a_class_call():
    text = " ".join(REAL_CLASS_ASSUMPTIONS)
    for phrase in ("서버를 띄우지 않았", "메모리를 재지 않았", "패치", "4-GPU", "drafter"):
        assert phrase in text


def test_mxfp4_assumption_states_the_sm10x_condition():
    for model in (V4, V41):
        assert any("SM10x" in text and "mla/indexer.py:61, :91" in text for text in global_kv_per_token(model)["assumptions"])


def test_assumptions_state_the_storage_format_behind_the_reproduction():
    assert any("fp8_ds_mla" in text for text in global_kv_per_token(V4)["assumptions"])
    assert any("nvfp4_ds_mla" in text for text in global_kv_per_token(V41)["assumptions"])
    assert any("mxfp4" in text and "132B" in text for text in global_kv_per_token(V41)["assumptions"])
    assert any("4.44" in text for text in global_kv_per_token(GLM)["assumptions"])


def test_glm_444_ratio_is_labelled_self_reported():
    assert any("4.44" in text and "자체 보고" in text for text in global_kv_per_token(GLM)["assumptions"])


def test_kda_estimate_says_the_name_comes_from_config_and_vllm_not_zai():
    assert any("kda_layers" in text and "kda.py" in text and "P7-44" in text
               for text in glm_kda_fixed_state()["assumptions"])


def test_kda_estimate_places_the_tail_ring_on_sparse_layers():
    assert any("sparse MLA 층마다 tail ring" in text for text in glm_kda_fixed_state()["assumptions"])


def test_capacity_warns_that_block_check_is_only_record_alignment():
    assumptions = capacity_estimate(GLM, block_size=4, **BUDGET)["assumptions"]
    assert any("128의 배수" in text and "vllm/platforms/interface.py:1077-1082" in text for text in assumptions)


def test_snapshot_values_match_the_ledger():
    models = json.loads((DATA_DIR / "model_configs.json").read_text(encoding="utf-8"))["models"]
    assert set(models) == {GLM, V4, V41}
    for entry in models.values():
        assert entry["fetch_date"] == "2026-11-02"
        assert entry["source_url"].startswith("https://huggingface.co/")
    glm = models[GLM]["fields"]
    assert (glm["kv_lora_rank"], glm["qk_rope_head_dim"], glm["index_kpool"], glm["index_head_dim"]) == (512, 0, 4, 128)
    assert glm["linear_attn_config"]["num_heads"] == 64
    assert glm["linear_attn_config"]["head_dim"] == 128
    assert glm["linear_attn_config"]["short_conv_kernel_size"] == 4
    v4 = models[V4]["fields"]
    assert v4["compress_ratios"][:4] == [0, 0, 4, 128]
    assert (len(v4["compress_ratios"]), v4["compress_ratios"].count(4), v4["compress_ratios"].count(128)) == (44, 21, 20)
    v41 = models[V41]["fields"]
    assert v41["kv_source_layer_ids"] == [2, 8, 14, 20]
    assert v41["index_source_layer_ids"] == [2, 8, 14, 20, 24, 28, 32, 36]
    assert (len(v41["compress_ratios"]), v41["compress_ratios"].count(2), v41["compress_ratios"].count(1)) == (43, 18, 20)


@pytest.mark.parametrize("name", ["kv_cases", "tier_sim"])
def test_modules_import_no_vllm_torch_or_network_package(name):
    tree = ast.parse((ROOT / "vllm_lab" / f"{name}.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "collections", "dataclasses", "functools", "json", "math", "typing", "vllm_lab"}


def test_block_size_error_has_no_wrong_particle_after_model_name():
    with pytest.raises(ValueError) as err:
        capacity_estimate(V4, block_size=16, **BUDGET)
    assert "Flash은" not in str(err.value)
    assert f"model={V4}" in str(err.value)


def test_unknown_value_messages_put_no_particle_after_the_quoted_value():
    from vllm_lab.kv_cases import glm_kda_fixed_state

    with pytest.raises(ValueError) as unknown_model:
        real_block_size("Kimi-K3")
    with pytest.raises(ValueError) as unknown_mode:
        glm_kda_fixed_state(mamba_cache_mode="bogus")
    with pytest.raises(ValueError) as no_snapshot:
        global_kv_per_token("Kimi-K3")
    for error in (unknown_model, unknown_mode, no_snapshot):
        assert "'Kimi-K3'" in str(error.value) or "'bogus'" in str(error.value)
        assert not re.search(r"'[은는이가을를]", str(error.value))
