"""KV cache 메모리 산수와 /metrics 읽기를 모은 교육용(teaching) 계산 모듈.

이 모듈은 vLLM을 import하지 않는다. 식과 정의를 v0.32.0 소스에서 옮겨 적은 산수이고,
측정값을 만들지 않는다. 메모리 식은 일반 full attention 층(MHA, GQA, MQA)만 다룬다.
MLA와 recurrent state(KDA 등)는 식에 들어가지 않으므로 GLM-5.3-Flash는 숫자 대신
`glm53_kv_note()`의 설명을 쓴다. TP 샤딩, block 단위 올림, hybrid pool padding도 계산하지 않는다.

코드 근거는 vLLM v0.32.0(commit 5df63a7) 소스 루트 기준 `경로:줄`이다.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from vllm_lab import DEFAULT_BLOCK_SIZE

# vllm/utils/torch_utils.py:87 is_quantized_kv_cache는 "fp8"로 시작하는 이름을 양자화로 분류한다.
# 여기 바이트 수는 원소 하나의 payload뿐이다. per_token_head 같은 scale 저장분은 세지 않는다.
DTYPE_BYTES: dict[str, int] = {
    "float32": 4,
    "float16": 2,
    "bfloat16": 2,
    "fp8": 1,
    "fp8_e4m3": 1,
    "fp8_e5m2": 1,
}
HEAD_TYPES = ("MHA", "GQA", "MQA")
UNSUPPORTED_HEAD_TYPES = ("MLA", "recurrent", "glm5next")

# 짧은 이름 -> 정확한 지표 이름. 등록 문자열은 vllm/v1/metrics/loggers.py에 있다.
METRIC_NAMES: dict[str, str] = {
    "prefix_queries": "vllm:prefix_cache_queries",  # loggers.py:662
    "prefix_hits": "vllm:prefix_cache_hits",  # loggers.py:673
    "kv_usage": "vllm:kv_cache_usage_perc",  # loggers.py:620
    "preemptions": "vllm:num_preemptions",  # loggers.py:739
    "waiting": "vllm:num_requests_waiting",  # loggers.py:538
    "running": "vllm:num_requests_running",  # loggers.py:528
    "ttft": "vllm:time_to_first_token_seconds",  # loggers.py:931
    "itl": "vllm:inter_token_latency_seconds",  # loggers.py:941
    "tpot": "vllm:request_time_per_output_token_seconds",  # loggers.py:951
    "e2e": "vllm:e2e_request_latency_seconds",  # loggers.py:961
    "queue": "vllm:request_queue_time_seconds",  # loggers.py:971
}

_REPORT_LAYOUT: tuple[tuple[str, str, str], ...] = (
    ("prefix_queries", "prefix cache 조회", "Counter"),
    ("prefix_hits", "prefix cache 적중", "Counter"),
    ("kv_usage", "KV 사용률", "Gauge"),
    ("preemptions", "preemption 누적", "Counter"),
    ("waiting", "waiting", "Gauge"),
    ("running", "running", "Gauge"),
    ("ttft", "TTFT(서버)", "Histogram"),
    ("itl", "ITL", "Histogram"),
    ("tpot", "TPOT(서버)", "Histogram"),
    ("e2e", "E2E", "Histogram"),
    ("queue", "대기 시간", "Histogram"),
)


class UnsupportedKVShape(ValueError):
    """원식 2*B*L*T*n*d*b로 셀 수 없는 KV 구조(MLA, recurrent, glm5next)."""


def tokens_processed_without_kv(prompt_tokens: int, output_tokens: int) -> dict:
    """KV 없이 매 step 전체를 다시 넣을 때와 KV를 쓸 때 모델에 넣는 token 수를 센다.

    without_kv = sum(P + i for i in range(n)), with_kv = P + n - 1, ratio = 둘의 비.
    산수일 뿐 연산량 주장이 아니다. attention 연산량이 제곱으로 는다는 말은 대장에 근거가 없다(P2-02, 미확인).
    """
    if prompt_tokens < 1 or output_tokens < 1:
        raise ValueError(
            f"prompt_tokens={prompt_tokens}, output_tokens={output_tokens}: 둘 다 1 이상이어야 합니다"
        )
    without_kv = sum(prompt_tokens + i for i in range(output_tokens))
    with_kv = prompt_tokens + output_tokens - 1
    return {"without_kv": without_kv, "with_kv": with_kv, "ratio": without_kv / with_kv}


def _dtype_size(dtype: str) -> int:
    if dtype not in DTYPE_BYTES:
        raise ValueError(f"dtype={dtype!r}은 표에 없습니다. 가능한 값 {len(DTYPE_BYTES)}개: {sorted(DTYPE_BYTES)}")
    return DTYPE_BYTES[dtype]


def block_bytes(
    num_kv_heads: int,
    head_size: int,
    dtype: str = "bfloat16",
    block_size: int = DEFAULT_BLOCK_SIZE,
    head_size_v: int | None = None,
) -> int:
    """층 하나, block 하나의 원시 payload byte 수(P2-05).

    num_kv_heads * block_size * (head_size + head_size_v) * dtype 크기.
    head_size_v를 주지 않으면 head_size와 같아 K와 V를 합친 2배 항이 된다.
    vllm/v1/kv_cache_interface.py:536(head_size_v 기본값), :549(state 크기), :552-553(page 크기).
    dtype이 절반이면 이 값만 절반이다. 가중치, activation, CUDA graph 몫은 이 식에 없다(P4-10).
    """
    if min(num_kv_heads, head_size, block_size) < 1:
        raise ValueError(
            f"num_kv_heads={num_kv_heads}, head_size={head_size}, block_size={block_size}: 모두 1 이상이어야 합니다"
        )
    size_v = head_size if head_size_v is None else head_size_v
    return num_kv_heads * block_size * (head_size + size_v) * _dtype_size(dtype)


def raw_kv_bytes(
    *,
    batch: int,
    layers: int,
    tokens: int,
    head_type: str,
    num_heads: int,
    head_dim: int,
    dtype: str = "bfloat16",
    num_kv_heads: int | None = None,
) -> int:
    """원식 2*B*L*T*n*d*b. n은 MHA면 num_heads, GQA면 num_kv_heads(필수), MQA면 1(D-12).

    범위: 모든 층이 일반 full attention인 model만 맞다. MLA, recurrent state, glm5next는
    UnsupportedKVShape로 거부한다. TP 샤딩, block 단위 올림, hybrid pool padding은 계산하지 않는다.
    """
    if head_type in UNSUPPORTED_HEAD_TYPES:
        raise UnsupportedKVShape(
            f"head_type={head_type!r}은 2*B*L*T*n*d*b로 셀 수 없습니다. 숫자 대신 glm53_kv_note()의 설명을 읽으세요"
        )
    if head_type not in HEAD_TYPES:
        raise ValueError(f"head_type={head_type!r}은 모르는 값입니다. 가능한 값: {HEAD_TYPES}")
    if min(batch, layers, tokens, num_heads, head_dim) < 0:
        raise ValueError(
            f"batch={batch}, layers={layers}, tokens={tokens}, num_heads={num_heads}, "
            f"head_dim={head_dim}: 음수는 쓸 수 없습니다"
        )
    if head_type == "MHA":
        n = num_heads
    elif head_type == "MQA":
        n = 1
    else:
        if num_kv_heads is None:
            raise ValueError(f"head_type='GQA'에는 num_kv_heads가 필요합니다. num_heads={num_heads}만 받았습니다")
        n = num_kv_heads
    return 2 * batch * layers * tokens * n * head_dim * _dtype_size(dtype)


def glm53_kv_note() -> str:
    """원식을 GLM-5.3-Flash에 쓸 수 없는 이유 다섯 가지. 숫자를 만들지 않는다.

    층 구성 숫자는 HF 설정에서 오고 v0.32.0 소스 트리에 없다. 값은 part7.md P7-41~P7-43.
    근거: 02b-KV-Sharing.ipynb의 6절(hybrid KV와 GLM-5.3-Flash).
    """
    return (
        "2*B*L*T*n*d*b는 GLM-5.3-Flash에 쓸 수 없습니다. 이유는 다섯 가지입니다.\n"
        "1. 선형 attention(KDA) 층은 request당 고정 크기 state라 token 수 T 항이 없습니다 "
        "(vllm/models/glm5next/common/kda.py:163).\n"
        "2. sparse MLA 층은 K와 V를 따로 두지 않고 잠재 벡터 하나만 둡니다. 2배 항이 없고 "
        "head 차원은 kv_lora_rank + qk_rope_head_dim입니다 "
        "(vllm/models/glm5next/common/attention.py:385).\n"
        "3. MLA 층마다 indexer cache가 따로 있고 index_kpool token당 state 하나라 T에 비례하되 계수가 다릅니다 "
        "(vllm/models/glm5next/common/attention.py:260).\n"
        "4. tail cache가 request당 고정 크기 링 버퍼로 하나 더 붙습니다 "
        "(vllm/models/glm5next/common/attention.py:271).\n"
        "5. hybrid pool은 group 크기를 맞추려 padding하므로 실제 점유가 이론식보다 클 수 있습니다.\n"
        "층 구성 숫자는 체크포인트 config에서 읽었습니다(P7-41~P7-43). "
        "층 종류별로 따로 더해야 합니다. "
        "자세한 설명: 02b-KV-Sharing.ipynb의 6절, 02c-KV-Modern-Models.ipynb."
    )


@dataclass(frozen=True)
class CapacityEstimate:
    budget_bytes: int
    kv_bytes: int
    num_blocks: int
    capacity_tokens: int
    max_concurrency: float
    log_line: str


def capacity_from_budget(
    *,
    gpu_total_bytes: int,
    weights_bytes: int,
    other_bytes: int,
    block_bytes_all_layers: int,
    block_size: int = DEFAULT_BLOCK_SIZE,
    gpu_memory_utilization: float = 0.92,
    max_model_len: int = 8192,
) -> CapacityEstimate:
    """KV 예산에서 block 수와 token 용량을 구한다. 가상의 산수다.

    budget = int(total * 비율), kv = budget - weights - other, blocks = kv // block_bytes_all_layers,
    capacity = blocks * block_size. 실제 vLLM은 profiling으로 정한다(P1-22).
    gpu_memory_utilization 기본값 0.92는 part3.md 파라미터 표를 따른다.
    """
    if not 0 < gpu_memory_utilization <= 1:
        raise ValueError(f"gpu_memory_utilization={gpu_memory_utilization}: 0 초과 1 이하여야 합니다")
    if min(block_bytes_all_layers, block_size, max_model_len) < 1:
        raise ValueError(
            f"block_bytes_all_layers={block_bytes_all_layers}, block_size={block_size}, "
            f"max_model_len={max_model_len}: 모두 1 이상이어야 합니다"
        )
    budget = int(gpu_total_bytes * gpu_memory_utilization)
    kv = budget - weights_bytes - other_bytes
    if kv <= 0:
        raise ValueError(
            f"KV 예산이 {kv} byte입니다: budget={budget} - weights={weights_bytes} - other={other_bytes}"
        )
    num_blocks = kv // block_bytes_all_layers
    capacity = num_blocks * block_size
    concurrency = capacity / max_model_len
    log_line = (
        f"GPU KV cache size: {capacity:,} tokens, "
        f"Maximum concurrency for {max_model_len:,} tokens per request: {concurrency:.2f}x"
    )
    return CapacityEstimate(budget, kv, num_blocks, capacity, concurrency, log_line)


# --- Prometheus 텍스트 형식 ---------------------------------------------------------------

_LABEL_PAIR = re.compile(r'\s*([A-Za-z_][A-Za-z0-9_]*)="((?:[^"\\]|\\.)*)"\s*(?:,|$)')
_SAMPLE_LINE = re.compile(r"^([A-Za-z_:][A-Za-z0-9_:]*)(?:\{(.*)\})?\s+(\S+)(?:\s+-?\d+)?$")
_ESCAPES = {"n": "\n", '"': '"', "\\": "\\"}

Samples = dict[tuple[str, tuple[tuple[str, str], ...]], float]


def _parse_labels(body: str, line: str) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    pos = 0
    while pos < len(body):
        match = _LABEL_PAIR.match(body, pos)
        if match is None:
            raise ValueError(f"라벨을 읽지 못했습니다(위치 {pos}): {line!r}")
        value = re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(0)), match.group(2))
        pairs.append((match.group(1), value))
        pos = match.end()
    return tuple(sorted(pairs))


def parse_prometheus(text: str) -> Samples:
    """Prometheus 텍스트를 {(이름, 정렬한 라벨 튜플): 값}으로 읽는다.

    '#'로 시작하는 줄과 빈 줄은 건너뛴다. 읽지 못하는 줄은 ValueError.
    Histogram은 _bucket, _sum, _count가 각각 다른 이름의 표본이고 Counter는 노출될 때 _total이 붙는다(P3-38).
    P3-38은 prometheus_client 0.26.0으로 확인한 것이고 vLLM 서버 출력은 아니므로 metric_value는 두 이름을 모두 읽는다.
    """
    samples: Samples = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _SAMPLE_LINE.match(line)
        if match is None:
            raise ValueError(f"표본 줄을 읽지 못했습니다: {line!r}")
        name, label_body, value_text = match.groups()
        try:
            value = float(value_text)
        except ValueError:
            raise ValueError(f"값을 숫자로 읽지 못했습니다({value_text!r}): {line!r}") from None
        samples[(name, _parse_labels(label_body or "", line))] = value
    return samples


def _sum_matching(samples: Samples, name: str, labels: dict[str, str]) -> float | None:
    matched = [
        value
        for (sample_name, sample_labels), value in samples.items()
        if sample_name == name and labels.items() <= dict(sample_labels).items()
    ]
    return math.fsum(matched) if matched else None


def metric_value(samples: Samples, name: str, **labels: str) -> float | None:
    """name과 라벨이 맞는 표본의 합. 없으면 name+'_total'을 찾는다. 둘 다 없으면 None.

    주어진 라벨은 표본 라벨의 부분집합이면 맞는다. 없는 지표에 0을 돌려주지 않는다.
    """
    found = _sum_matching(samples, name, labels)
    if found is None:
        found = _sum_matching(samples, name + "_total", labels)
    return found


def metric_delta(before: Samples, after: Samples, name: str, **labels: str) -> float | None:
    """after - before. 둘 중 하나라도 지표가 없으면 None."""
    old = metric_value(before, name, **labels)
    new = metric_value(after, name, **labels)
    if old is None or new is None:
        return None
    return new - old


def histogram_mean_delta(before: Samples, after: Samples, name: str, **labels: str) -> float | None:
    """두 시점 사이 새로 관측된 값의 평균 = (_sum 변화량) / (_count 변화량).

    표본이 없거나 _count 변화량이 0 이하(관측 없음, 또는 서버 재시작으로 누적값이 줄어듦)면 None.
    """
    total = metric_delta(before, after, name + "_sum", **labels)
    count = metric_delta(before, after, name + "_count", **labels)
    if total is None or count is None or count <= 0:
        return None
    return total / count


def prefix_hit_rate_delta(before: Samples, after: Samples) -> float | None:
    """prefix cache 적중 token 변화량 / 조회 token 변화량. 조회 변화량이 0이거나 지표가 없으면 None."""
    hits = metric_delta(before, after, METRIC_NAMES["prefix_hits"])
    queries = metric_delta(before, after, METRIC_NAMES["prefix_queries"])
    if hits is None or queries is None or queries == 0:
        return None
    return hits / queries


def metrics_report(before: Samples, after: Samples) -> list[dict]:
    """METRIC_NAMES 전부를 행 {"항목", "이름", "종류", "값"}으로 돌려준다.

    Gauge는 after 값, Counter는 변화량, Histogram은 평균 변화량. 없으면 값은 None.
    """
    rows: list[dict] = []
    for key, label, kind in _REPORT_LAYOUT:
        name = METRIC_NAMES[key]
        if kind == "Gauge":
            value = metric_value(after, name)
        elif kind == "Counter":
            value = metric_delta(before, after, name)
        else:
            value = histogram_mean_delta(before, after, name)
        rows.append({"항목": label, "이름": name, "종류": kind, "값": value})
    return rows


# --- 클라이언트가 본 chunk 시각 -----------------------------------------------------------


@dataclass(frozen=True)
class ChunkMetrics:
    ttft_s: float | None
    itl_s: list[float]
    e2el_s: float | None
    tpot_s: float | None
    output_tokens: int | None
    num_chunks: int
    first_visible_s: float | None
    warnings: list[str]


def metrics_from_chunks(send_ts: float, chunks: list[dict]) -> ChunkMetrics:
    """SSE chunk 시각에서 클라이언트 지표를 계산한다.

    chunks[i]: {"t", "has_choices", "content", "reasoning", "completion_tokens"}.
    TTFT는 choices가 있는 첫 chunk까지, text가 비어도 친다(P3-26,
    vllm/benchmarks/lib/endpoint_request_func.py:255-266). ITL은 choices가 있는 chunk 사이 간격이며
    token 단위가 아니다(P3-27, endpoint_request_func.py:267-272). E2EL은 마지막 choices chunk까지이고
    usage 전용 chunk는 끝 시각을 옮기지 않는다(P3-29, endpoint_request_func.py:443-447).
    TPOT은 (E2EL - TTFT) / (출력 수 - 1)이며 출력 수가 2 이상으로 알려졌을 때만 낸다(P3-28,
    vllm/benchmarks/serve.py:601-631). first_visible_s는 content가 비지 않은 첫 chunk(D-36)다.
    출력 수는 completion_tokens가 있는 마지막 chunk에서 읽는다.
    """
    token_times: list[float] = []
    first_visible: float | None = None
    output_tokens: int | None = None
    for index, chunk in enumerate(chunks):
        if chunk.get("completion_tokens") is not None:
            output_tokens = chunk["completion_tokens"]
        if not chunk["has_choices"]:
            continue
        t = chunk["t"]
        previous = token_times[-1] if token_times else send_ts
        if t < previous:
            raise ValueError(f"chunks[{index}]의 t={t}가 앞선 시각 {previous}보다 이릅니다")
        token_times.append(t)
        if first_visible is None and chunk.get("content"):
            first_visible = t - send_ts

    warnings: list[str] = []
    if not token_times:
        warnings.append(f"choices가 있는 chunk가 없습니다(전체 chunk {len(chunks)}개). TTFT를 계산할 수 없습니다")
    num_chunks = len(token_times)
    if output_tokens is None:
        warnings.append("출력 token 수를 모릅니다. usage chunk가 없어 TPOT을 계산하지 않습니다")
    elif output_tokens > num_chunks:
        warnings.append(
            f"한 chunk에 token이 여럿입니다. ITL은 token당 지연이 아닙니다 (출력 {output_tokens}개, chunk {num_chunks}개)"
        )

    ttft = token_times[0] - send_ts if token_times else None
    e2el = token_times[-1] - send_ts if token_times else None
    itl = [later - earlier for earlier, later in zip(token_times, token_times[1:])]
    tpot = None
    if ttft is not None and e2el is not None and output_tokens is not None and output_tokens >= 2:
        tpot = (e2el - ttft) / (output_tokens - 1)
    return ChunkMetrics(ttft, itl, e2el, tpot, output_tokens, num_chunks, first_visible, warnings)
