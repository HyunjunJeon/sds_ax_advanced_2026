"""저장된 실제 vLLM 0.32.0 KV spec 실행(data/reference_specs.json)을 kv_cases와 대조한다.

실제 클래스는 여기서 돌리지 않는다. 저장된 행을 읽고 kv_cases를 지금 다시 불러 행마다 비교한다.
xfail은 쓰지 않는다. 실제 차이는 EXPECTED_DIFFERENCES에 행 ID와 값, 이유로 적는다. 거기 없는 새 차이는 실패하고,
더 이상 나지 않는 차이를 남겨 두어도 실패한다. 차이 목록을 늘려 새 차이를 감추지 않는다.
건너뛰는 경우는 파일의 status가 not_run일 때뿐이다. 설명은 docs/reference/specs.md에 있다.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import NamedTuple, TypedDict

import pytest

from vllm_lab import DATA_DIR, VLLM_COMMIT, VLLM_VERSION, kv_cases as kv

Value = int | float | list[list[int]]


class KvCasesCall(TypedDict):
    fn: str
    args: dict[str, str | int]


class SpecDetail(TypedDict):
    layers: int
    real_page_size_bytes: int
    page_size_padded: int | None


class Row(TypedDict, total=False):
    id: str
    scenario: str
    real: Value
    real_detail: SpecDetail
    kv_cases_call: KvCasesCall | None
    kv_cases_value: Value | None
    compare: str | None
    match: bool | None


class AssumptionClaim(TypedDict):
    id: str
    model: str
    real: int
    claimed: int
    assumption_contains: str
    match: bool


class Group(TypedDict):
    layers: int


class Scenario(TypedDict):
    scenario: str
    cache_dtype_after_build: str
    group_count: int
    groups: list[Group]


DATA = json.loads((DATA_DIR / "reference_specs.json").read_text(encoding="utf-8"))
if DATA["status"] == "not_run":
    pytest.skip(f"reference_specs.json status not_run: {DATA['reason']}", allow_module_level=True)

ROWS: list[Row] = DATA["rows"]
SCENARIOS: list[Scenario] = DATA["scenarios"]
CLAIMS: list[AssumptionClaim] = DATA["assumption_claims"]
CLAIM_ROWS = [row for row in ROWS if row["kv_cases_call"] is not None]


def _main_record(model: str) -> int:
    return next(r["main_record_bytes"] for r in kv.layer_table(model)["rows"] if r["main_record_bytes"])


def _indexer_record(model: str) -> int:
    return next(r["indexer_record_bytes"] for r in kv.layer_table(model)["rows"] if r["indexer_record_bytes"])


def _layer_map(model: str, cache: str) -> list[list[int]]:
    rows = kv.layer_table(model)["rows"]
    if cache == "main":
        return [[r["layer"], r["compress_ratio"], r["main_record_bytes"]] for r in rows if r["main_record_bytes"]]
    return [[r["layer"], r["indexer_tokens_per_state"], r["indexer_record_bytes"]] for r in rows if r["indexer_record_bytes"]]


def _per_token(model: str, field: str) -> float:
    return kv.global_kv_per_token(model)[field]


def _part_per_token(model: str, cache: str, tokens: int) -> float:
    parts = kv.global_kv_per_token(model)["parts"]
    return next(p["bytes_per_token"] for p in parts if p["cache"] == cache and p["tokens_per_state"] == tokens)


def _kda(field: str, num_spec: int, mode: kv.MambaCacheMode, checkpoint: int) -> int:
    state = kv.glm_kda_fixed_state(num_spec=num_spec, mamba_cache_mode=mode, prefill_checkpoint_blocks=checkpoint)
    return state[field]


def _crossover(num_spec: int, mode: kv.MambaCacheMode, checkpoint: int) -> float:
    comparison = kv.glm_context_comparison([0], num_spec=num_spec, mamba_cache_mode=mode, prefill_checkpoint_blocks=checkpoint)
    return comparison["crossover_tokens"]


def _min_block(model: str) -> int:
    return kv._min_block_size(kv.layer_table(model)["rows"])


KV_CASES_CALLS: dict[str, Callable[..., Value]] = {
    "main_record": _main_record,
    "indexer_record": _indexer_record,
    "layer_map": _layer_map,
    "per_token": _per_token,
    "part_per_token": _part_per_token,
    "kda": _kda,
    "crossover": _crossover,
    "min_block": _min_block,
}


class Difference(NamedTuple):
    real: float
    reason: str


_PAGE = "kv_cases는 record / tokens_per_state만 더한다. 실제 spec은 page를 alignment로 올린다(V4 576, V4.1 512)."
_STRIDE_DS = "kv_cases는 padding을 세지 않는다. 실제 block stride는 올림된 page의 합이다."
_STRIDE_GLM = "kv_cases는 padding을 세지 않는다. 실제 block stride는 block_stride_alignment의 배수로 올라간다."
_KDA_PAGE = "kv_cases는 page_size_padded를 계산하지 않는다고 적었다(_KDA_ASSUMPTIONS). 실제 KDA page는 attention page 크기로 올라간다."
_KDA_TP4 = "kv_cases는 TP와 page_size_padded를 계산하지 않는다고 적었다. TP4에서는 rank당 page가 attention page로 올라가 합이 더 커진다."
_CROSSOVER = "분자는 padding된 고정 state, 분모는 stride 기준 토큰당 byte다. kv_cases는 둘 다 padding 없는 값이다."

EXPECTED_DIFFERENCES: dict[str, Difference] = {
    "v4.flashmla_sm100.mxfp4.main.tps4.bytes_per_token_page": Difference(3071.25, _PAGE),
    "v4.flashmla_sm100.mxfp4.main.tps128.bytes_per_token_page": Difference(135.0, _PAGE),
    "v4.flashmla_sm100.mxfp4.indexer.tps4.bytes_per_token_page": Difference(378.0, _PAGE),
    "v4.flashmla_sm100.mxfp4.pool.bytes_per_token_stride": Difference(3584.25, _STRIDE_DS),
    "v41.flashmla_sm100.nvfp4.mxfp4.indexer.tps2.bytes_per_token_page": Difference(108.0, _PAGE),
    "v41.flashmla_sm100.nvfp4.mxfp4.pool.bytes_per_token_stride": Difference(896.0, _STRIDE_DS),
    "glm.flashmla.bf16.pool.bytes_per_token_stride": Difference(50620416 / 4352, _STRIDE_GLM),
    "glm.flashmla.bf16.kda.fixed_bytes_padded": Difference(151519232, _KDA_PAGE),
    "glm.flashmla.bf16.flashkda.kda.fixed_bytes_padded": Difference(151519232, _KDA_PAGE),
    "glm.flashmla.bf16.align.kda.fixed_bytes_padded": Difference(303038464, _KDA_PAGE),
    "glm.flashmla.bf16.align.flashkda.kda.fixed_bytes_padded": Difference(454557696, _KDA_PAGE),
    "glm.flashmla.bf16.kda.crossover_tokens_padded": Difference(151519232 / (50620416 / 4352), _CROSSOVER),
    "glm.flashmla.bf16.align.flashkda.kda.crossover_tokens_padded": Difference(454557696 / (50620416 / 4352), _CROSSOVER),
    "glm.flashmla.bf16.tp4.kda.fixed_bytes_padded_4ranks": Difference(160432128, _KDA_TP4),
    "glm.flashmla.bf16.align.flashkda.tp4.kda.fixed_bytes_padded_4ranks": Difference(481296384, _KDA_TP4),
}


def _live_value(row: Row) -> Value:
    request = row["kv_cases_call"]
    return KV_CASES_CALLS[request["fn"]](**request["args"])


def _agrees(row: Row, live: Value) -> bool:
    real = row["real"]
    if row["compare"] == "divides":
        assert isinstance(real, int) and isinstance(live, int)
        return real % live == 0
    return real == live


def test_file_header() -> None:
    assert DATA["status"] in ("ran", "partial")
    assert DATA["reason"]
    assert DATA["vllm"] == VLLM_VERSION
    assert DATA["commit"] == VLLM_COMMIT
    assert DATA["environment"]["cuda_available"] is False
    assert DATA["patches"]
    assert set(DATA["input_config"]["models"]) == set(kv.MODELS)


def test_rows_are_unique() -> None:
    ids = [row["id"] for row in ROWS]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("row", CLAIM_ROWS, ids=lambda row: row["id"])
def test_row_against_kv_cases(row: Row) -> None:
    live = _live_value(row)
    assert live == row["kv_cases_value"], "저장된 kv_cases 값이 지금의 kv_cases와 다릅니다. 파일을 다시 만들어야 합니다"
    expected = EXPECTED_DIFFERENCES.get(row["id"])
    if expected is None:
        assert _agrees(row, live), f"실제 {row['real']} / kv_cases {live}: 목록에 없는 새 차이입니다"
        assert row["match"] is True
    else:
        assert not _agrees(row, live), f"{row['id']}: 더 이상 차이가 아닙니다. 목록에서 지우세요"
        assert row["real"] == pytest.approx(expected.real)
        assert row["match"] is False


def test_expected_differences_all_exist_and_have_reasons() -> None:
    ids = {row["id"] for row in CLAIM_ROWS}
    assert set(EXPECTED_DIFFERENCES) <= ids
    assert all(item.reason for item in EXPECTED_DIFFERENCES.values())


@pytest.mark.parametrize("claim", CLAIMS, ids=lambda claim: claim["id"])
def test_assumption_sentence_matches_real_value(claim: AssumptionClaim) -> None:
    assumptions = kv.global_kv_per_token(claim["model"])["assumptions"]
    assert any(claim["assumption_contains"] in sentence for sentence in assumptions)
    assert claim["real"] == claim["claimed"]
    assert claim["match"] is True


@pytest.mark.parametrize(
    ("scenario", "dtype"),
    [
        ("glm.flashmla.bf16", "auto"),
        ("glm.flashmla.fp8_ds_mla", "fp8_ds_mla"),
        ("glm.flashmla.nvfp4_ds_mla", "nvfp4_ds_mla"),
        ("v4.flashmla_sm100.mxfp4", "fp8_ds_mla"),
        ("v4.flashinfer.bf16", "auto"),
        ("v41.flashmla_sm90.auto", "fp8_ds_mla"),
        ("v41.flashmla_sm100.nvfp4.mxfp4", "nvfp4_ds_mla"),
        ("v41.flashinfer.bf16", "auto"),
    ],
)
def test_requested_layouts_ran(scenario: str, dtype: str) -> None:
    ran = {item["scenario"]: item for item in SCENARIOS}
    assert ran[scenario]["cache_dtype_after_build"] == dtype


def test_requested_speculation_and_mamba_modes_ran() -> None:
    ran = {item["scenario"] for item in SCENARIOS}
    for scenario in (
        "glm.flashmla.bf16.spec5",
        "glm.flashmla.bf16.align",
        "glm.flashmla.bf16.align.spec5",
        "v4.flashmla_sm100.mxfp4.spec5",
        "v41.flashmla_sm100.nvfp4.mxfp4.spec5",
    ):
        assert scenario in ran


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario["scenario"])
def test_groups_cover_every_layer_once(scenario: Scenario) -> None:
    assert scenario["group_count"] == len(scenario["groups"])
    grouped = sum(group["layers"] for group in scenario["groups"])
    listed = sum(row["real_detail"]["layers"] for row in ROWS if row["scenario"] == scenario["scenario"] and "real_detail" in row)
    assert grouped == listed


@pytest.mark.parametrize("row", [row for row in ROWS if "real_detail" in row], ids=lambda row: row["id"])
def test_page_is_never_smaller_than_its_content(row: Row) -> None:
    detail = row["real_detail"]
    assert row["real"] == (detail["page_size_padded"] or detail["real_page_size_bytes"])
    assert row["real"] >= detail["real_page_size_bytes"]


@pytest.mark.parametrize("model", [kv.V4, kv.V41])
def test_page_sum_equals_the_saved_stride_when_padding_is_on_pages(model: str) -> None:
    assert sum(page["page_bytes_per_token"] for page in kv.real_pages(model)) == kv.real_stride(model)["bytes_per_token"]


@pytest.mark.parametrize(
    ("row_id", "mode", "checkpoint"),
    [
        ("glm.flashmla.bf16.kda.crossover_tokens_padded", "none", 0),
        ("glm.flashmla.bf16.align.flashkda.kda.crossover_tokens_padded", "align", 1),
    ],
)
def test_kda_table_crossover_equals_the_saved_row_at_one_rank(row_id: str, mode: str, checkpoint: int) -> None:
    saved = next(row["real"] for row in ROWS if row["id"] == row_id)
    computed = next(
        item["crossover_tokens"]
        for item in kv.real_kda_table()
        if (item["tp_ranks"], item["num_spec"], item["mamba_cache_mode"], item["prefill_checkpoint_blocks"]) == (1, 0, mode, checkpoint)
    )
    assert computed == pytest.approx(saved)


def test_tp4_keeps_the_mla_record_on_every_rank_while_kda_is_split() -> None:
    main = next(row for row in ROWS if row["id"] == "glm.flashmla.bf16.tp4.main.b1152.t1.spec")
    kda = next(row for row in ROWS if row["id"] == "glm.flashmla.bf16.tp4.kda.b8192.tNone.spec")
    assert main["real_detail"]["state_content_bytes"] == 1024
    assert kda["real_detail"]["real_page_size_bytes"] == 1085440  # TP1 4341760의 1/4


def test_code_rejections_are_recorded_apart_from_limits() -> None:
    rejected = {item["scenario"] for item in DATA["rejected_by_code"]}
    assert rejected == {"v4.flashmla_sm90.mxfp4", "v41.flashmla_sm90.nvfp4", "v41.flashinfer_sm100.fp8_ds_mla"}
    limits = {item["scenario"] for item in DATA["not_constructed"]}
    assert limits == {"v41.mega_sm100.auto", "glm.full_model", "v4.full_model", "v41.full_model"}
    assert DATA["mega_auto_dtype"]["auto_resolves_to"] == "nvfp4_ds_mla"
