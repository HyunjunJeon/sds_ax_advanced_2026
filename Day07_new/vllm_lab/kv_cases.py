"""최근 모델의 KV cache 크기를 config와 코드의 record 크기로 다시 세어 보는 교육용(teaching) 계산 모듈.

이 모듈은 vLLM을 import하지 않고 네트워크를 쓰지 않는다. config 값은 data/model_configs.json 스냅샷에서,
record 크기는 vLLM v0.32.0(commit 5df63a7) 소스 루트 기준 `경로:줄`에서, 실제 클래스 호출 값은
data/reference_specs.json에서 온다. 측정값을 만들지 않는다.

돌려주는 값마다 `kind`가 붙는다.
- reported: 제작사가 자기 논문에 쓴 값이다. 제3자가 재현한 값이 아니다.
- reproduced: config와 record 크기로 계산했더니 제작사 값과 맞았다. 저장 형식은 그 값이 가정한 것이다.
- estimate: 이 자료가 계산한 값이고 맞춰 볼 제작사 값이 없다. GLM-5.3-Flash는 항상 이것이다.
- real_class: 실제 vLLM 클래스를 CPU에서 불러 저장한 값을 읽었다. 서버를 띄운 값이 아니다(REAL_CLASS_ASSUMPTIONS).
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from typing import Literal, TypedDict

from vllm_lab import DATA_DIR
from vllm_lab.kv_math import capacity_from_budget

GLM = "GLM-5.3-Flash"
V4 = "DeepSeek-V4-Flash"
V41 = "DeepSeek-V4.1-Flash"
MODELS = (GLM, V4, V41)
KINDS = ("reported", "reproduced", "estimate", "real_class")

Kind = Literal["reported", "reproduced", "estimate", "real_class"]
MambaCacheMode = Literal["none", "align"]

BF16_BYTES = 2
FLOAT32_BYTES = 4

# vllm/models/deepseek_v4/attention.py:876-878 fp8_ds_mla: 448B NoPE + 128B RoPE + 8B scale.
V4_MAIN_RECORD_BYTES = 584
# vllm/models/deepseek_v4/attention.py:298, :858 compress_ratios 값. 0은 SWA만 있는 층이다.
V4_CSA_RATIO = 4
V4_HCA_RATIO = 128
# vllm/models/deepseek_v41/attention.py:514-518 nvfp4_ds_mla: 256B e2m1 쌍 + 32개 e4m3 scale.
V41_MAIN_RECORD_BYTES = 288
# vllm/model_executor/layers/sparse_attn_indexer.py:64 MXFP4_BLOCK_SIZE.
MXFP4_BLOCK_VALUES = 32
# vllm/models/glm5next/common/attention.py:253 quant_block_size.
FP8_INDEXER_BLOCK_VALUES = 128
FP32_SCALE_BYTES = 4

_STRIDE_ROW_SUFFIX = ".pool.bytes_per_token_stride"
_KDA_PADDED_MARK = ".kda.fixed_bytes_padded"
_FOUR_RANKS_SUFFIX = "_4ranks"
_TAIL_LAYER_TYPES = ("compressor_state", "indexer_compressor_state", "tail")

# 2609.19969 그림 1(b)의 토큰당 global KV. 대장 P7-29. 그림에서 읽은 값이고 제작사 자체 보고다.
_REPORTED_BYTES_PER_TOKEN: dict[str, int] = {
    "DeepSeek-V1": 389_120,
    "DeepSeek-V3.2": 48_068,
    V4: 3_514,
    V41: 890,
}
_ASSUMPTIONS: dict[str, tuple[str, ...]] = {
    V4: (
        "main record 584B는 --kv-cache-dtype fp8_ds_mla일 때다. vllm/models/deepseek_v4/attention.py:878",
        "indexer record 68B는 indexer_kv_dtype=mxfp4일 때다. SM10x에서만 받고 SM90은 거부한다(실제 클래스 실행). auto는 fp8로 풀려 132B다. "
        "vllm/v1/attention/backends/mla/indexer.py:61, :91, vllm/models/deepseek_v4/attention.py:1005-1014",
        "SWA 캐시와 압축 꼬리 상태는 세지 않았다. global KV만 센다(P7-17, P7-29).",
    ),
    V41: (
        "main record 288B는 nvfp4_ds_mla(SM100 전용)일 때다. fp8_ds_mla면 528B 또는 584B다. "
        "vllm/models/deepseek_v41/attention.py:513-527",
        "indexer record 68B는 indexer_kv_dtype=mxfp4일 때다. SM10x에서만 받는다(V4.1은 코드 읽기, 같은 함수를 V4에서 실행). auto는 fp8로 풀려 132B다. "
        "vllm/v1/attention/backends/mla/indexer.py:61, :91, vllm/models/deepseek_v41/attention.py:92-100",
        "SWA 캐시와 압축 꼬리 상태는 세지 않았다. global KV만 센다(P7-27, P7-29).",
        "kv_source와 index_source를 논문의 Full, Reindex 층으로 읽는 것은 추정이다(P7-23).",
    ),
    GLM: (
        "제작사가 낸 토큰당 바이트 값이 없어 맞춰 볼 수 없다. Z.ai가 자체 보고한 4.44배는 이 값으로 재현되지 않는다(P7-46, P7-47).",
        "main은 BF16 512원소(rope 0)로 놓았다. Z.ai 비교가 BF16 기준이어서다. 실제 cache dtype은 서버 설정을 따른다(P7-46).",
        "indexer record 132B는 FP8 값 128B와 FP32 scale 4B다. vllm/models/glm5next/common/attention.py:261",
        "KDA 고정 state, tail ring, hybrid pool padding은 토큰당 값에 들어가지 않는다(P2-61, P2-62).",
    ),
}
_KDA_ASSUMPTIONS: tuple[str, ...] = (
    "mamba_cache_mode none의 state 1벌이 하한이다. prefix caching을 켜면 align으로 바뀌어 더 많이 잡는다(P8-23, P8-24).",
    "conv state는 BF16(model dtype), recurrent state는 float32다. 둘 다 dtype 설정이 auto일 때다. "
    "vllm/model_executor/layers/mamba/mamba_utils.py:139-141",
    "TP 샤딩과 page_size_padded는 계산하지 않았다. 실제 클래스 호출 값은 real_kda_table에 있다. vllm/v1/kv_cache_interface.py:1063-1070",
    "sparse MLA 층마다 tail ring(CircularBufferSpec)이 요청당 더 있지만 세지 않았다. "
    "vllm/models/glm5next/common/attention.py:156-177, :271",
    "측정이 아니라 코드 식에 config 값을 넣은 추정이다. GLM-5.3-Flash 전용 보고서는 찾지 못했다(P7-48).",
    "KDA라는 이름은 config의 kda_layers와 vLLM의 kda.py에서 왔다. Z.ai 문서가 이 이름을 쓰는지는 확인하지 못했다(P7-44).",
)
_CAPACITY_ASSUMPTIONS: tuple[str, ...] = (
    "토큰당 global KV만으로 block을 센다. 실제 vLLM은 profiling으로 정한다(P1-22).",
    "block_size를 주지 않으면 real_block_size를 쓴다. CPU에서 실제 클래스를 부른 값이고 서버 시작 로그가 아니다(P8-20).",
    "max_concurrency는 token 용량을 max_model_len으로 나눈 값이다. kda_requests와 맞춰 계산하지 않는다.",
    "block_size 검사는 record가 나누어떨어지는지만 본다. hybrid MLA/Mamba 모델이면 vLLM이 block을 128의 배수이면서 attention page가 "
    "Mamba page 이상이 되도록 키우므로 작은 값은 서버에서 그대로 쓰이지 않는다. vllm/platforms/interface.py:1077-1082, :1086-1100",
    "hybrid pool padding, SWA 캐시, tail ring은 빠져 있어 실제 점유보다 작게 나온다. padding을 넣은 값은 real_stride에 있다.",
)
REAL_CLASS_ASSUMPTIONS: tuple[str, ...] = (
    "CPU에서 실제 층 클래스와 get_kv_cache_groups, get_kv_cache_configs를 부른 값이다. 서버를 띄우지 않았고 메모리를 재지 않았다.",
    "SM 값, backend, weight 커널, FlashInfer 유무를 패치했다. 어느 GPU에서 어느 backend가 잡히는지는 이 값으로 말할 수 없다.",
    "TP4는 TP 그룹만 값으로 바꾼 호출이다. 실제 4-GPU 실행이 아니다.",
    "모델 클래스 전체는 만들지 못해 층만 만들었다. spec 5의 group 수에 MTP drafter 층은 들어 있지 않다.",
)
_TAIL_ASSUMPTIONS: tuple[str, ...] = (
    "행 수와 행 크기는 실제 spec의 sliding_window, state_content_bytes, page 크기에서 읽었고 곱은 이 자료가 계산했다. 요청당 하한이다.",
    "page 올림과 in-flight token에 따른 max_memory_usage_bytes는 넣지 않았다.",
    *REAL_CLASS_ASSUMPTIONS,
)


class ReportedFigure(TypedDict):
    kind: Kind
    model: str
    bytes_per_token: int
    source_id: str


class LayerRow(TypedDict):
    layer: int
    role: str
    compress_ratio: int
    main_record_bytes: int
    main_bytes_per_token: float
    indexer_record_bytes: int
    indexer_tokens_per_state: int
    indexer_bytes_per_token: float
    fixed_state_bytes: int | None


class LayerTable(TypedDict):
    kind: Kind
    model: str
    source_url: str
    fetch_date: str
    rows: list[LayerRow]


class KVPart(TypedDict):
    cache: str
    tokens_per_state: int
    layers: list[int]
    record_bytes: int
    bytes_per_token: float


class KVPerToken(TypedDict):
    kind: Kind
    model: str
    source_url: str
    fetch_date: str
    main_bytes_per_token: float
    indexer_bytes_per_token: float
    total_bytes_per_token: float
    reported_bytes_per_token: int | None
    parts: list[KVPart]
    assumptions: tuple[str, ...]


class KDAFixedState(TypedDict):
    kind: Kind
    model: str
    layers: int
    num_spec: int
    conv_bytes_per_state: int
    recurrent_bytes_per_state: int
    state_bytes_per_layer: int
    resident_states: int
    fixed_bytes_per_request: int
    assumptions: tuple[str, ...]


class ContextRow(TypedDict):
    context_tokens: int
    fixed_state_bytes: int
    accumulated_kv_bytes: int
    fixed_share: float


class ContextComparison(TypedDict):
    kind: Kind
    model: str
    bytes_per_token: float
    fixed_bytes_per_request: int
    crossover_tokens: float
    rows: list[ContextRow]
    assumptions: tuple[str, ...]


class CapacityCase(TypedDict):
    kind: Kind
    model: str
    block_size: int
    block_bytes_all_layers: int
    reserved_kda_bytes: int
    budget_bytes: int
    kv_bytes: int
    num_blocks: int
    capacity_tokens: int
    max_concurrency: float
    assumptions: tuple[str, ...]


class RealStride(TypedDict):
    kind: Kind
    model: str
    scenario: str
    block_size: int
    block_stride_bytes: float
    bytes_per_token: float
    record_bytes_per_token: float
    assumptions: tuple[str, ...]


class RealPage(TypedDict):
    kind: Kind
    model: str
    scenario: str
    cache: str
    tokens_per_state: int
    layers: int
    record_bytes: int
    page_bytes: int
    record_bytes_per_token: float
    page_bytes_per_token: float


class RealKdaRow(TypedDict):
    kind: Kind
    model: str
    scenario: str
    num_spec: int
    mamba_cache_mode: MambaCacheMode
    prefill_checkpoint_blocks: int
    tp_ranks: int
    layers: int
    state_bytes_per_rank: int
    page_bytes_per_rank: int
    fixed_bytes_unpadded_all_ranks: int
    fixed_bytes_padded_all_ranks: int
    fixed_bytes_padded_per_rank: int
    stride_bytes_per_token_per_rank: float
    crossover_tokens: float


class RealScenario(TypedDict):
    kind: Kind
    model: str
    scenario: str
    cache_dtype: str
    main_record_bytes: int
    indexer_record_bytes: int
    block_size: int
    group_count: int
    group_layers: list[int]
    stride_bytes_per_token: float


class TailRow(TypedDict):
    cache: str
    spec_class: str
    rows: int
    row_bytes: int
    layers: int
    bytes_per_layer: int
    bytes_per_request: int


class TailBytes(TypedDict):
    kind: Kind
    model: str
    scenario: str
    rows: list[TailRow]
    total_bytes_per_request: int
    assumptions: tuple[str, ...]


class _SpecDetail(TypedDict):
    layers: int
    block_size: int
    tokens_per_state: int
    state_content_bytes: int
    real_page_size_bytes: int
    page_size_padded: int | None
    sliding_window: int | None


class _KdaCallArgs(TypedDict):
    num_spec: int
    mode: MambaCacheMode
    checkpoint: int


class _KdaCall(TypedDict):
    args: _KdaCallArgs


class _SpecRow(TypedDict, total=False):
    id: str
    model: str
    scenario: str
    layer_type: str
    spec_class: str
    real: float
    real_detail: _SpecDetail
    kv_cases_call: _KdaCall


class _SpecGroup(TypedDict):
    layers: int


class _SpecScenario(TypedDict):
    scenario: str
    model: str
    block_size: int
    cache_dtype_after_build: str
    group_count: int
    groups: list[_SpecGroup]
    block_stride_bytes: float


class _SavedSpecs(TypedDict):
    rows: list[_SpecRow]
    scenarios: list[_SpecScenario]


@dataclass(frozen=True)
class _DeepSeekConfig:
    num_hidden_layers: int
    compress_ratios: tuple[int, ...]
    index_head_dim: int
    kv_source_layer_ids: tuple[int, ...]
    index_source_layer_ids: tuple[int, ...]


@dataclass(frozen=True)
class _GlmConfig:
    layer_types: tuple[str, ...]
    kv_lora_rank: int
    qk_rope_head_dim: int
    index_kpool: int
    index_head_dim: int
    kda_num_heads: int
    kda_head_dim: int
    kda_conv_kernel: int


@dataclass(frozen=True)
class _Snapshot:
    source_url: str
    fetch_date: str
    fields: dict


@cache
def _snapshot(model: str) -> _Snapshot:
    if model not in MODELS:
        raise ValueError(f"model={model!r}은 스냅샷에 없습니다. 가능한 값 {len(MODELS)}개: {MODELS}")
    entry = json.loads((DATA_DIR / "model_configs.json").read_text(encoding="utf-8"))["models"][model]
    return _Snapshot(entry["source_url"], entry["fetch_date"], entry["fields"])


def _deepseek_config(model: str) -> _DeepSeekConfig:
    fields = _snapshot(model).fields
    return _DeepSeekConfig(
        num_hidden_layers=fields["num_hidden_layers"],
        compress_ratios=tuple(fields["compress_ratios"]),
        index_head_dim=fields["index_head_dim"],
        kv_source_layer_ids=tuple(fields.get("kv_source_layer_ids", ())),
        index_source_layer_ids=tuple(fields.get("index_source_layer_ids", ())),
    )


def _glm_config() -> _GlmConfig:
    """vLLM은 linear_num_heads 등을 읽고(vllm/models/glm5next/common/kda.py:218-220), transformers가 linear_attn_config로 채운다."""
    fields = _snapshot(GLM).fields
    linear = fields["linear_attn_config"]
    return _GlmConfig(
        layer_types=tuple(fields["layer_types"]),
        kv_lora_rank=fields["kv_lora_rank"],
        qk_rope_head_dim=fields["qk_rope_head_dim"],
        index_kpool=fields["index_kpool"],
        index_head_dim=fields["index_head_dim"],
        kda_num_heads=linear["num_heads"],
        kda_head_dim=linear["head_dim"],
        kda_conv_kernel=linear["short_conv_kernel_size"],
    )


def _mxfp4_indexer_record(index_head_dim: int) -> int:
    """vllm/models/deepseek_v41/attention.py:97 값 2개가 1 byte, 32값마다 scale 1 byte."""
    return index_head_dim // 2 + index_head_dim // MXFP4_BLOCK_VALUES


def _glm_indexer_record(index_head_dim: int) -> int:
    """vllm/models/glm5next/common/attention.py:261 FP8 값과 block마다 FP32 scale."""
    return index_head_dim + index_head_dim // FP8_INDEXER_BLOCK_VALUES * FP32_SCALE_BYTES


def _glm_main_record(config: _GlmConfig) -> int:
    """vllm/model_executor/layers/attention/mla_attention.py:479 head_size, 별도 V 없음(P7-59)."""
    return (config.kv_lora_rank + config.qk_rope_head_dim) * BF16_BYTES


def _row(
    layer: int,
    role: str,
    compress_ratio: int,
    main_record: int = 0,
    indexer_record: int = 0,
    indexer_tokens: int = 0,
    fixed_state_bytes: int | None = None,
) -> LayerRow:
    """record 하나가 token N개를 덮으면 토큰당 record/N이다. vllm/v1/kv_cache_interface.py:231-234."""
    return LayerRow(
        layer=layer,
        role=role,
        compress_ratio=compress_ratio,
        main_record_bytes=main_record,
        main_bytes_per_token=main_record / compress_ratio if main_record else 0.0,
        indexer_record_bytes=indexer_record,
        indexer_tokens_per_state=indexer_tokens,
        indexer_bytes_per_token=indexer_record / indexer_tokens if indexer_record else 0.0,
        fixed_state_bytes=fixed_state_bytes,
    )


def _v4_rows(config: _DeepSeekConfig) -> list[LayerRow]:
    """압축 KV는 ratio > 1 층에만(attention.py:858), indexer는 ratio == 4 층에만(attention.py:298) 있다."""
    indexer_record = _mxfp4_indexer_record(config.index_head_dim)
    rows: list[LayerRow] = []
    for layer in range(config.num_hidden_layers):
        ratio = config.compress_ratios[layer]
        if ratio == V4_CSA_RATIO:
            rows.append(_row(layer, "csa", ratio, V4_MAIN_RECORD_BYTES, indexer_record, ratio))
        elif ratio == V4_HCA_RATIO:
            rows.append(_row(layer, "hca", ratio, V4_MAIN_RECORD_BYTES))
        else:
            rows.append(_row(layer, "swa_only", ratio))
    return rows


def _v41_rows(config: _DeepSeekConfig) -> list[LayerRow]:
    """압축 KV(attention.py:1143)와 indexer K(attention.py:437)는 kv source 층만 소유한다."""
    indexer_record = _mxfp4_indexer_record(config.index_head_dim)
    rows: list[LayerRow] = []
    for layer in range(config.num_hidden_layers):
        ratio = config.compress_ratios[layer]
        if ratio == 0:
            rows.append(_row(layer, "swa_only", ratio))
        elif layer in config.kv_source_layer_ids:
            rows.append(_row(layer, "kv_source", ratio, V41_MAIN_RECORD_BYTES, indexer_record, ratio))
        elif layer in config.index_source_layer_ids:
            rows.append(_row(layer, "index_source", ratio))
        else:
            rows.append(_row(layer, "consumer", ratio))
    return rows


def _glm_rows(config: _GlmConfig) -> list[LayerRow]:
    """linear_attention은 KDA 고정 state, 나머지는 sparse MLA다. vllm/models/glm5next/common/model.py:370-371.

    이 체크포인트의 indexer_types는 모두 full이라 sparse 층마다 indexer를 소유한다(P7-43).
    """
    main_record = _glm_main_record(config)
    indexer_record = _glm_indexer_record(config.index_head_dim)
    state_bytes = _kda_conv_bytes(config, num_spec=0) + _kda_recurrent_bytes(config)
    rows: list[LayerRow] = []
    for layer, layer_type in enumerate(config.layer_types):
        if layer_type == "linear_attention":
            rows.append(_row(layer, "kda", 0, fixed_state_bytes=state_bytes))
        else:
            rows.append(_row(layer, "sparse_mla", 1, main_record, indexer_record, config.index_kpool))
    return rows


def reported_figures() -> list[ReportedFigure]:
    """제작사가 그림으로 낸 토큰당 global KV 바이트. GLM-5.3-Flash에는 이런 값이 없다(P7-46, P7-48)."""
    return [
        ReportedFigure(kind="reported", model=model, bytes_per_token=value, source_id="P7-29")
        for model, value in _REPORTED_BYTES_PER_TOKEN.items()
    ]


def layer_table(model: str) -> LayerTable:
    """층마다 무엇을 들고 있는지 보여 준다. 합은 global_kv_per_token과 같다.

    MTP 층은 세지 않는다. config 배열이 num_hidden_layers보다 긴 것은 MTP 몫이다
    (vllm/models/deepseek_v41/attention.py:332). fixed_state_bytes는 KDA 층의 요청당 state 하나, num_spec 0 기준이다.
    """
    snapshot = _snapshot(model)
    if model == GLM:
        rows = _glm_rows(_glm_config())
    elif model == V4:
        rows = _v4_rows(_deepseek_config(model))
    else:
        rows = _v41_rows(_deepseek_config(model))
    total = math.fsum(row["main_bytes_per_token"] + row["indexer_bytes_per_token"] for row in rows)
    return LayerTable(
        kind=_kind_for(model, total),
        model=model,
        source_url=snapshot.source_url,
        fetch_date=snapshot.fetch_date,
        rows=rows,
    )


def _kind_for(model: str, total_bytes_per_token: float) -> Kind:
    """맞춰 볼 제작사 값이 있고 반올림해 같을 때만 reproduced다. GLM-5.3-Flash는 값이 없어 estimate다."""
    reported = _REPORTED_BYTES_PER_TOKEN.get(model)
    return "reproduced" if reported is not None and round(total_bytes_per_token) == reported else "estimate"


def _parts(rows: Iterable[LayerRow]) -> list[KVPart]:
    """같은 cache, 같은 record, 같은 비율의 층을 한 항으로 묶는다."""
    grouped: dict[tuple[str, int], KVPart] = {}

    def add(cache_name: str, record: int, tokens: int, layer: int, per_token: float) -> None:
        part = grouped.setdefault(
            (cache_name, tokens),
            KVPart(cache=cache_name, tokens_per_state=tokens, layers=[], record_bytes=record, bytes_per_token=0.0),
        )
        part["layers"].append(layer)
        part["bytes_per_token"] += per_token

    for row in rows:
        if row["main_record_bytes"]:
            add("main", row["main_record_bytes"], row["compress_ratio"], row["layer"], row["main_bytes_per_token"])
        if row["indexer_record_bytes"]:
            add(
                "indexer",
                row["indexer_record_bytes"],
                row["indexer_tokens_per_state"],
                row["layer"],
                row["indexer_bytes_per_token"],
            )
    return list(grouped.values())


def global_kv_per_token(model: str) -> KVPerToken:
    """토큰이 하나 늘 때 쌓이는 global KV 바이트를 층별로 더한다. 고정 state와 SWA는 들어가지 않는다."""
    table = layer_table(model)
    main = math.fsum(row["main_bytes_per_token"] for row in table["rows"])
    indexer = math.fsum(row["indexer_bytes_per_token"] for row in table["rows"])
    return KVPerToken(
        kind=table["kind"],
        model=model,
        source_url=table["source_url"],
        fetch_date=table["fetch_date"],
        main_bytes_per_token=main,
        indexer_bytes_per_token=indexer,
        total_bytes_per_token=main + indexer,
        reported_bytes_per_token=_REPORTED_BYTES_PER_TOKEN.get(model),
        parts=_parts(table["rows"]),
        assumptions=_ASSUMPTIONS[model],
    )


def _kda_conv_bytes(config: _GlmConfig, num_spec: int) -> int:
    """vllm/model_executor/layers/mamba/mamba_utils.py:319-325. 폭 = q + k + v 투영, 길이 = kernel - 1 + num_spec."""
    proj_size = config.kda_num_heads * config.kda_head_dim
    conv_dim = proj_size + 2 * proj_size
    return conv_dim * (config.kda_conv_kernel - 1 + num_spec) * BF16_BYTES


def _kda_recurrent_bytes(config: _GlmConfig) -> int:
    """vllm/model_executor/layers/mamba/mamba_utils.py:326. head마다 head_dim x head_dim, 문맥 길이 T가 없다."""
    return config.kda_num_heads * config.kda_head_dim * config.kda_head_dim * FLOAT32_BYTES


def _resident_states(num_spec: int, mamba_cache_mode: MambaCacheMode, prefill_checkpoint_blocks: int) -> int:
    """vllm/v1/kv_cache_interface.py:1076-1082. align은 2 + 추측 + checkpoint, none은 1 + 추측 block이다."""
    if mamba_cache_mode == "align":
        return 2 + num_spec + prefill_checkpoint_blocks
    if mamba_cache_mode == "none":
        return 1 + num_spec
    raise ValueError(f"mamba_cache_mode={mamba_cache_mode!r}은 모르는 값입니다. 가능한 값: ('none', 'align')")


def glm_kda_fixed_state(
    *,
    num_spec: int = 0,
    mamba_cache_mode: MambaCacheMode = "none",
    prefill_checkpoint_blocks: int = 0,
) -> KDAFixedState:
    """GLM-5.3-Flash KDA 층의 요청당 고정 state 추정. 항상 estimate다.

    식은 vllm/model_executor/layers/mamba/mamba_utils.py:304-327의 kda_state_shape다. num_spec은 conv 길이를 늘리고
    (vllm/models/glm5next/common/kda.py:192-202) 층마다 state block 수도 늘린다
    (vllm/model_executor/layers/mamba/abstract.py:79-83). prefix caching을 켜면 align 모드이고,
    FlashKDA backend면 checkpoint block이 1개다(P8-24). ReplaySSM은 추측 block을 0으로 두지만 여기서 다루지 않는다.
    """
    if min(num_spec, prefill_checkpoint_blocks) < 0:
        raise ValueError(
            f"num_spec={num_spec}, prefill_checkpoint_blocks={prefill_checkpoint_blocks}: 음수는 쓸 수 없습니다"
        )
    resident = _resident_states(num_spec, mamba_cache_mode, prefill_checkpoint_blocks)
    config = _glm_config()
    conv = _kda_conv_bytes(config, num_spec)
    recurrent = _kda_recurrent_bytes(config)
    layers = config.layer_types.count("linear_attention")
    return KDAFixedState(
        kind="estimate",
        model=GLM,
        layers=layers,
        num_spec=num_spec,
        conv_bytes_per_state=conv,
        recurrent_bytes_per_state=recurrent,
        state_bytes_per_layer=conv + recurrent,
        resident_states=resident,
        fixed_bytes_per_request=(conv + recurrent) * resident * layers,
        assumptions=_KDA_ASSUMPTIONS,
    )


def glm_context_comparison(
    context_tokens: Iterable[int],
    *,
    num_spec: int = 0,
    mamba_cache_mode: MambaCacheMode = "none",
    prefill_checkpoint_blocks: int = 0,
) -> ContextComparison:
    """문맥이 길어질 때 쌓이는 KV와 요청당 고정 state를 나란히 놓는다. 항상 estimate다.

    crossover_tokens는 둘이 같아지는 문맥 길이다. 이보다 짧은 요청은 쌓인 KV보다 고정 state가 더 크다.
    """
    state = glm_kda_fixed_state(
        num_spec=num_spec, mamba_cache_mode=mamba_cache_mode, prefill_checkpoint_blocks=prefill_checkpoint_blocks
    )
    per_token = global_kv_per_token(GLM)["total_bytes_per_token"]
    fixed = state["fixed_bytes_per_request"]
    rows: list[ContextRow] = []
    for tokens in context_tokens:
        if tokens < 0:
            raise ValueError(f"context_tokens에 음수 {tokens}이 있습니다")
        accumulated = int(tokens * per_token)
        rows.append(
            ContextRow(
                context_tokens=tokens,
                fixed_state_bytes=fixed,
                accumulated_kv_bytes=accumulated,
                fixed_share=fixed / (fixed + accumulated),
            )
        )
    return ContextComparison(
        kind="estimate",
        model=GLM,
        bytes_per_token=per_token,
        fixed_bytes_per_request=fixed,
        crossover_tokens=fixed / per_token,
        rows=rows,
        assumptions=_KDA_ASSUMPTIONS + _ASSUMPTIONS[GLM],
    )


def _min_block_size(rows: Iterable[LayerRow]) -> int:
    """block 하나에 record가 나누어떨어져 들어가는 최소 크기. vllm/v1/kv_cache_interface.py:231-234, P7-18.

    최소 조건일 뿐 실제 block 크기가 아니다. 실제 값은 real_block_size에 있다.
    """
    tokens: list[int] = []
    for row in rows:
        if row["main_record_bytes"]:
            tokens.append(row["compress_ratio"])
        if row["indexer_record_bytes"]:
            tokens.append(row["indexer_tokens_per_state"])
    return math.lcm(*tokens)


def capacity_estimate(
    model: str,
    *,
    gpu_total_bytes: int,
    weights_bytes: int,
    other_bytes: int,
    block_size: int | None = None,
    gpu_memory_utilization: float = 0.92,
    max_model_len: int = 8192,
    kda_requests: int = 0,
    kda_state: KDAFixedState | None = None,
) -> CapacityCase:
    """kv_math.capacity_from_budget에 토큰당 global KV를 넣어 token 용량을 구한다. 항상 estimate다.

    그 함수의 계약은 "token에 비례하는 block"뿐이라 KDA 고정 state는 맞지 않는다. 그래서 kda_requests개 요청의
    state를 먼저 예산에서 빼고(other_bytes에 더해) 넘긴다. kda_state를 주지 않으면 요청당 state 1벌로 보며 이는 하한이다.
    KDA가 없는 모델에 kda_requests를 주면 ValueError다. block_size를 주지 않으면 real_block_size(model)을 쓴다.
    """
    if kda_requests < 0:
        raise ValueError(f"kda_requests={kda_requests}: 음수는 쓸 수 없습니다")
    if kda_requests and model != GLM:
        raise ValueError(f"{model}에는 KDA 층이 없습니다. kda_requests={kda_requests}를 뺄 수 없습니다")
    per_token = global_kv_per_token(model)["total_bytes_per_token"]
    size = real_block_size(model) if block_size is None else block_size
    smallest = _min_block_size(layer_table(model)["rows"])
    if size < 1 or size % smallest:
        raise ValueError(f"block_size={size}: {model}은 {smallest}의 배수여야 record가 나누어떨어집니다")
    reserved = kda_requests * (kda_state or glm_kda_fixed_state())["fixed_bytes_per_request"] if kda_requests else 0
    block_bytes = int(per_token * size)
    estimate = capacity_from_budget(
        gpu_total_bytes=gpu_total_bytes,
        weights_bytes=weights_bytes,
        other_bytes=other_bytes + reserved,
        block_bytes_all_layers=block_bytes,
        block_size=size,
        gpu_memory_utilization=gpu_memory_utilization,
        max_model_len=max_model_len,
    )
    return CapacityCase(
        kind="estimate",
        model=model,
        block_size=size,
        block_bytes_all_layers=block_bytes,
        reserved_kda_bytes=reserved,
        budget_bytes=estimate.budget_bytes,
        kv_bytes=estimate.kv_bytes,
        num_blocks=estimate.num_blocks,
        capacity_tokens=estimate.capacity_tokens,
        max_concurrency=estimate.max_concurrency,
        assumptions=_CAPACITY_ASSUMPTIONS + _ASSUMPTIONS[model],
    )


@cache
def _saved_specs() -> _SavedSpecs:
    return json.loads((DATA_DIR / "reference_specs.json").read_text(encoding="utf-8"))


def _require_known_model(model: str) -> None:
    if model not in MODELS:
        raise ValueError(f"model={model!r}은 실제 클래스 실행에 없습니다. 가능한 값 {len(MODELS)}개: {MODELS}")


def _stride_row(model: str) -> _SpecRow:
    """kv_cases가 가정한 조건의 pool 행. 모델마다 하나이고 그 scenario가 real_* 함수의 기준이다."""
    _require_known_model(model)
    return next(
        row for row in _saved_specs()["rows"] if row["model"] == model and row["id"].endswith(_STRIDE_ROW_SUFFIX)
    )


def _scenario(name: str) -> _SpecScenario:
    return next(item for item in _saved_specs()["scenarios"] if item["scenario"] == name)


def _spec_rows(scenario: str, layer_type: str) -> list[_SpecRow]:
    return [
        row
        for row in _saved_specs()["rows"]
        if row["scenario"] == scenario and row["layer_type"] == layer_type and "real_detail" in row
    ]


def _page_bytes(detail: _SpecDetail) -> int:
    return detail["page_size_padded"] or detail["real_page_size_bytes"]


def real_block_size(model: str) -> int:
    """실제 클래스 호출에서 나온 block 크기. kv_cases가 가정한 저장 형식, TP1 기준이다.

    다른 형식과 TP4의 값은 real_scenarios에 있다. CPU 호출 값이고 서버 시작 로그가 아니다.
    """
    return _scenario(_stride_row(model)["scenario"])["block_size"]


def real_stride(model: str) -> RealStride:
    """global KV pool의 block 하나가 실제로 차지하는 byte와 토큰당 값. record 합과 나란히 돌려준다.

    record 합이 제작사 값을 재현한 것(reproduced)과 실제 pool이 그보다 큰 것(real_class)은 다른 사실이다.
    """
    row = _stride_row(model)
    scenario = _scenario(row["scenario"])
    return RealStride(
        kind="real_class",
        model=model,
        scenario=row["scenario"],
        block_size=scenario["block_size"],
        block_stride_bytes=scenario["block_stride_bytes"],
        bytes_per_token=row["real"],
        record_bytes_per_token=global_kv_per_token(model)["total_bytes_per_token"],
        assumptions=REAL_CLASS_ASSUMPTIONS,
    )


def real_pages(model: str) -> list[RealPage]:
    """main과 indexer의 page를 record 기준 값과 나란히 돌려준다. 토큰당 값은 page * 층 수 / block 크기다.

    V4와 V4.1은 이 합이 real_stride와 같다. GLM은 page에 padding이 없고 stride 정렬이 차이를 만든다.
    """
    scenario = _scenario(_stride_row(model)["scenario"])
    name, block = scenario["scenario"], scenario["block_size"]
    rows: list[RealPage] = []
    for cache_name in ("main", "indexer"):
        for row in _spec_rows(name, cache_name):
            detail = row["real_detail"]
            page = _page_bytes(detail)
            rows.append(
                RealPage(
                    kind="real_class",
                    model=model,
                    scenario=name,
                    cache=cache_name,
                    tokens_per_state=detail["tokens_per_state"],
                    layers=detail["layers"],
                    record_bytes=detail["state_content_bytes"],
                    page_bytes=page,
                    record_bytes_per_token=detail["state_content_bytes"] * detail["layers"] / detail["tokens_per_state"],
                    page_bytes_per_token=page * detail["layers"] / block,
                )
            )
    return rows


def real_kda_table() -> list[RealKdaRow]:
    """GLM-5.3-Flash KDA 고정 state의 실제 클래스 호출 값. spec 0과 5, none과 align, TP1과 TP4 중 돌린 조합이다.

    all_ranks는 rank 전부를 더한 값이고 per_rank는 한 rank의 값이다. MLA record는 TP와 상관없이 rank마다 그대로이고
    KDA state만 나뉘므로, crossover_tokens는 rank 하나의 고정 state를 rank 하나의 stride 토큰당 값으로 나눈다.
    """
    rows = _saved_specs()["rows"]
    by_id = {row["id"]: row for row in rows}
    table: list[RealKdaRow] = []
    for row in rows:
        if _KDA_PADDED_MARK not in row["id"]:
            continue
        ranks = 4 if row["id"].endswith(_FOUR_RANKS_SUFFIX) else 1
        name = row["scenario"]
        scenario = _scenario(name)
        detail = _spec_rows(name, "kda")[0]["real_detail"]
        arguments = row["kv_cases_call"]["args"]
        per_rank = row["real"] // ranks
        stride_per_token = scenario["block_stride_bytes"] / scenario["block_size"]
        table.append(
            RealKdaRow(
                kind="real_class",
                model=GLM,
                scenario=name,
                num_spec=arguments["num_spec"],
                mamba_cache_mode=arguments["mode"],
                prefill_checkpoint_blocks=arguments["checkpoint"],
                tp_ranks=ranks,
                layers=detail["layers"],
                state_bytes_per_rank=detail["state_content_bytes"],
                page_bytes_per_rank=_page_bytes(detail),
                fixed_bytes_unpadded_all_ranks=by_id[row["id"].replace("_padded", "_unpadded")]["real"],
                fixed_bytes_padded_all_ranks=row["real"],
                fixed_bytes_padded_per_rank=per_rank,
                stride_bytes_per_token_per_rank=stride_per_token,
                crossover_tokens=per_rank / stride_per_token,
            )
        )
    return table


def real_scenarios(model: str | None = None) -> list[RealScenario]:
    """끝까지 돈 시나리오마다 저장 형식, record, block 크기, group 구성을 돌려준다.

    group 수는 저장 형식에 따라 움직여 모델당 단일 값이 없다. cache_dtype의 auto는 설정값을 그대로 둔 것이다.
    """
    if model is not None:
        _require_known_model(model)
    rows: list[RealScenario] = []
    for item in _saved_specs()["scenarios"]:
        if model is not None and item["model"] != model:
            continue
        name = item["scenario"]
        rows.append(
            RealScenario(
                kind="real_class",
                model=item["model"],
                scenario=name,
                cache_dtype=item["cache_dtype_after_build"],
                main_record_bytes=_spec_rows(name, "main")[0]["real_detail"]["state_content_bytes"],
                indexer_record_bytes=_spec_rows(name, "indexer")[0]["real_detail"]["state_content_bytes"],
                block_size=item["block_size"],
                group_count=item["group_count"],
                group_layers=[group["layers"] for group in item["groups"]],
                stride_bytes_per_token=item["block_stride_bytes"] / item["block_size"],
            )
        )
    return rows


def _tail_row(row: _SpecRow) -> TailRow:
    """sliding window spec은 창 * record, 고리 버퍼는 block 크기 * (page / block 크기)다."""
    detail = row["real_detail"]
    window = detail["sliding_window"]
    rows = detail["block_size"] if window is None else window
    row_bytes = detail["real_page_size_bytes"] // detail["block_size"] if window is None else detail["state_content_bytes"]
    return TailRow(
        cache=row["layer_type"],
        spec_class=row["spec_class"],
        rows=rows,
        row_bytes=row_bytes,
        layers=detail["layers"],
        bytes_per_layer=rows * row_bytes,
        bytes_per_request=rows * row_bytes * detail["layers"],
    )


def tail_bytes_per_request(model: str) -> TailBytes:
    """요청마다 고정으로 잡는 압축 꼬리와 tail ring의 하한. 입력은 실제 spec이고 곱은 추정이다.

    V4는 CSA, HCA 압축 상태에 indexer 압축 상태 21층을 더한다.
    """
    name = _stride_row(model)["scenario"]
    rows = [_tail_row(row) for layer_type in _TAIL_LAYER_TYPES for row in _spec_rows(name, layer_type)]
    return TailBytes(
        kind="estimate",
        model=model,
        scenario=name,
        rows=rows,
        total_bytes_per_request=sum(row["bytes_per_request"] for row in rows),
        assumptions=_TAIL_ASSUMPTIONS,
    )
