"""vLLM v0.32.0 scheduler의 한 step을 따라 하는 교육용 모델이다(teaching model, 측정값이 아니다).

`vllm/v1/core/sched/scheduler.py`의 `schedule()`과 `_preempt_request`를 FCFS, 한 프로세스로 줄여
옮겼다. running 요청을 먼저 돌고, 이번 step에 preempt가 하나도 없을 때만 waiting을 본다.
KV는 이 모듈 안에서 block 수만 센다(`kv_sim`을 쓰지 않는다).

시간은 모두 선언한 toy 상수(`toy_step_ms`, `toy_ms_per_token`, `toy_network_ms`)의 결과다.
실제 GPU에서 잰 값이 아니므로 이 숫자로 vLLM의 실제 지연을 말하지 않는다.
`stream_interval`에 따른 TTFT 차이는 이 모델이 만든 값이고 vLLM 동작으로 확인한 것이 아니다.
모델링하지 않은 것은 `NOT_MODELED`에 적었다.
"""

from __future__ import annotations

import dataclasses
from collections import deque
from dataclasses import dataclass, field

import numpy as np

from vllm_lab import DEFAULT_BLOCK_SIZE

NOT_MODELED: tuple[str, ...] = (
    "prefix cache는 모델링하지 않는다. 입력 cached_tokens는 첫 스케줄 때 이미 계산한 것으로 칠 뿐이고, preempt 뒤 복귀할 때의 prefix 적중은 없다.",
    "speculative decoding의 draft token과 draft slot은 모델링하지 않는다.",
    "async scheduling은 모델링하지 않는다. step은 항상 앞 step이 끝난 뒤 시작한다.",
    "PRIORITY 정책은 모델링하지 않는다. FCFS만 있고 희생양은 항상 running의 마지막 요청이다.",
    "KV watermark와 block 안의 부분 공유는 모델링하지 않는다. block 수만 센다.",
    "실제 시간은 모델링하지 않는다. step 시간은 선언한 toy 상수의 결과다.",
    "scheduler_reserve_full_isl의 기본값(vLLM은 True)은 따르지 않는다. SchedConfig.reserve_full_isl의 기본이 False라 첫 chunk에 필요한 block만 보고, 켜면 전체 입력이 들어갈 free block이 없을 때 들여보내지 않는다. vllm/config/scheduler.py:190, vllm/v1/core/sched/scheduler.py:1270, vllm/v1/core/kv_cache_manager.py:522-539",
    "cached_tokens 몫도 요청별 block으로 센다. 실제로는 다른 요청이 쥔 block에 적중하면 ref_cnt만 늘고 새 block을 쓰지 않으므로, 이 모델의 쓰는 block과 kv_cache_usage_perc가 더 크게 나온다. vllm/v1/core/single_type_kv_cache_manager.py:245-248, :267-278",
    "적중 block이 free 칸을 쓰는 입장 규칙은 모델링하지 않는다. 실제로는 ref_cnt 0으로 free queue에 있는 적중 block도 free 칸을 쓰는 수로 세므로 복귀 입장이 더 늦어질 수 있다. vllm/v1/core/single_type_kv_cache_manager.py:255-260, :265",
    "prefix cache를 끄는 칸이 없다. 이 모델은 입장 때 조회 수를 항상 세지만, prefix cache를 끈 실제 Scheduler의 prefix_queries는 0이다. vllm/v1/core/kv_cache_manager.py:253-256",
    "stream_interval의 첫 chunk 시점과 그에 따른 TTFT 차이를 vLLM 동작으로 읽지 않는다. 이 모델의 규칙이다.",
)

EVENT_ACTOR = "Scheduler"

_PHASE_PREFILL = "prefill"
_PHASE_DECODE = "decode"


class SimStuck(RuntimeError):
    """더 진행할 수 없거나 max_steps를 넘었을 때 낸다."""


@dataclass(frozen=True)
class SchedConfig:
    """시뮬레이터 설정. 이름은 vLLM 설정을 따르되 기본값이 모두 vLLM 기본값은 아니다.

    reserve_full_isl은 vLLM의 scheduler_reserve_full_isl이다. v0.32.0의 기본은 True이고
    (vllm/config/scheduler.py:190) 여기 기본은 False다. 첫 chunk만 보는 기존 표가 그대로 유지되도록 끈 채로 두고,
    차이는 True로 다시 돌려 보여 준다.
    """

    max_num_batched_tokens: int = 32
    max_num_seqs: int = 4
    enable_chunked_prefill: bool = True
    long_prefill_token_threshold: int = 0
    long_prefill_token_threshold_adaptive: bool = False
    num_blocks: int = 64  # 할당 가능 수. null block을 뺀 값으로 쓴다
    block_size: int = DEFAULT_BLOCK_SIZE
    max_model_len: int = 4096
    stream_interval: int = 1
    toy_step_ms: float = 10.0
    toy_ms_per_token: float = 0.5
    toy_network_ms: float = 0.0
    reserve_full_isl: bool = False

    def validate(self) -> None:
        """chunked 끔이고 max_num_batched_tokens < max_model_len이면 ValueError. 같은 값은 허용한다."""
        positive = {
            "max_num_batched_tokens": self.max_num_batched_tokens,
            "max_num_seqs": self.max_num_seqs,
            "num_blocks": self.num_blocks,
            "block_size": self.block_size,
            "max_model_len": self.max_model_len,
            "stream_interval": self.stream_interval,
        }
        for name, value in positive.items():
            if value < 1:
                raise ValueError(f"{name}은 1 이상이어야 합니다(받은 값 {value}).")
        # vllm/config/scheduler.py:314 - 같은 값은 허용하고 작을 때만 거부한다.
        if not self.enable_chunked_prefill and self.max_num_batched_tokens < self.max_model_len:
            raise ValueError(
                f"chunked prefill를 끄면 max_num_batched_tokens({self.max_num_batched_tokens})가 "
                f"max_model_len({self.max_model_len}) 이상이어야 합니다."
            )
        # vllm/config/scheduler.py:352 - threshold는 음수가 될 수 없다.
        if self.long_prefill_token_threshold < 0:
            raise ValueError(
                f"long_prefill_token_threshold는 0 이상이어야 합니다(받은 값 {self.long_prefill_token_threshold})."
            )


@dataclass(frozen=True)
class Req:
    request_id: str
    prompt_tokens: int
    max_tokens: int
    arrival_ms: float = 0.0
    cached_tokens: int = 0  # 첫 스케줄 때 계산한 것으로 치는 수. block_size의 배수여야 한다
    start_running: bool = False  # True면 t=0에 running에서 시작
    start_computed: int = 0  # start_running일 때의 계산 수


@dataclass
class StepRecord:
    step: int
    start_ms: float
    end_ms: float
    tokens: dict[str, int]  # 스케줄 순서 유지
    running_before: list[str]
    waiting_before: list[str]
    preempted: list[str]
    blocks_in_use: int  # 이번 step에 할당을 마친 직후(끝난 요청을 돌려주기 전)
    budget_left: int
    running_after: int = 0
    waiting_after: int = 0
    blocks_after: int = 0  # step 결과를 반영하고 끝난 요청의 block을 돌려준 뒤
    prefix_queries: int = 0  # 누적 token 수
    prefix_hits: int = 0  # 누적 token 수
    preemptions_total: int = 0

    def to_row(self) -> dict:
        return {
            "step": self.step,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "tokens": " ".join(f"{rid}:{n}" for rid, n in self.tokens.items()),
            "합계": sum(self.tokens.values()),
            "남은 예산": self.budget_left,
            "쓰는 block": self.blocks_in_use,
            "preempt": " ".join(self.preempted),
        }


@dataclass
class ReqMetrics:
    request_id: str
    prompt_tokens: int
    output_tokens: int
    num_chunks: int
    client_ttft_ms: float
    client_itl_ms: list[float]
    client_itl_mean_ms: float | None
    client_tpot_ms: float | None  # 출력 1개 이하면 None
    client_e2el_ms: float
    server_ttft_ms: float
    server_tpot_ms: float  # 출력 1개 이하면 0.0
    server_e2e_ms: float
    queue_ms: float
    num_preemptions: int
    chunk_times_ms: list[float]
    send_ms: float


@dataclass
class _Run:
    """요청 하나의 가변 상태. SimResult가 지표를 만들 때도 쓴다."""

    req: Req
    server_arrival_ms: float
    num_tokens: int = 0  # prompt + 생성 token. vllm Request.num_tokens에 해당한다
    computed: int = 0
    generated: int = 0
    held: int = 0
    scheduled_once: bool = False
    recomputing: bool = False
    num_preemptions: int = 0
    first_start_ms: float = 0.0
    first_sched_step: int = 0
    token_end_ms: list[float] = field(default_factory=list)
    token_steps: list[int] = field(default_factory=list)
    chunk_server_ms: list[float] = field(default_factory=list)
    chunk_client_ms: list[float] = field(default_factory=list)
    sent_tokens: int = 0
    finish_step: int | None = None


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def _group(request_id: str) -> str:
    return request_id.split("-", 1)[0]


def _mean(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _fmt(value: float) -> str:
    return format(value, ".9g")


@dataclass
class SimResult:
    steps: list[StepRecord]
    events: list[dict]
    config: SchedConfig
    _runs: list[_Run] = field(default_factory=list, repr=False)
    _phases: dict[tuple[int, str], str] = field(default_factory=dict, repr=False)

    def step_rows(self) -> list[dict]:
        return [s.to_row() for s in self.steps]

    def metrics(self) -> list[ReqMetrics]:
        """serve.py의 식(client)과 stats.py의 식(server)을 toy 시각에 적용한다. 요청 입력 순서."""
        out: list[ReqMetrics] = []
        for run in self._runs:
            n = run.generated
            send = run.req.arrival_ms
            chunks = run.chunk_client_ms
            # vllm/benchmarks/lib/endpoint_request_func.py:436 - 첫 chunk까지가 TTFT.
            ttft = chunks[0] - send
            # vllm/benchmarks/lib/endpoint_request_func.py:462 - 마지막 chunk까지가 E2EL.
            e2el = chunks[-1] - send
            # vllm/benchmarks/lib/endpoint_request_func.py:270 - ITL은 연속 chunk 간격이다.
            itl = [b - a for a, b in zip(chunks, chunks[1:])]
            # vllm/benchmarks/serve.py:628 - (E2EL - TTFT) / (출력 - 1). 출력 1개 이하는 통계에서 빠진다.
            tpot = (e2el - ttft) / (n - 1) if n > 1 else None
            ends = run.token_end_ms
            out.append(
                ReqMetrics(
                    request_id=run.req.request_id,
                    prompt_tokens=run.req.prompt_tokens,
                    output_tokens=n,
                    num_chunks=len(chunks),
                    client_ttft_ms=ttft,
                    client_itl_ms=itl,
                    client_itl_mean_ms=_mean(itl),
                    client_tpot_ms=tpot,
                    client_e2el_ms=e2el,
                    # vllm/v1/metrics/stats.py:521 - 서버 도착부터 첫 token이 처리된 iteration 시각까지.
                    server_ttft_ms=ends[0] - run.server_arrival_ms,
                    # vllm/v1/metrics/stats.py:608 - 첫 token부터 마지막 token까지를 (n-1)로 나눈다.
                    server_tpot_ms=(ends[-1] - ends[0]) / (n - 1) if n > 1 else 0.0,
                    # vllm/v1/metrics/stats.py:590
                    server_e2e_ms=ends[-1] - run.server_arrival_ms,
                    # vllm/v1/metrics/stats.py:592 - 처음 스케줄된 시각까지가 queue 시간이다.
                    queue_ms=run.first_start_ms - run.server_arrival_ms,
                    num_preemptions=run.num_preemptions,
                    chunk_times_ms=list(chunks),
                    send_ms=send,
                )
            )
        return out

    def metrics_rows(self) -> list[dict]:
        rows = []
        for m in self.metrics():
            row = dataclasses.asdict(m)
            del row["client_itl_ms"], row["chunk_times_ms"]
            rows.append(row)
        return rows

    def spans(self) -> list[dict]:
        """view.timeline 입력. 대기 wait, 계산 prefill/decode, preempt 뒤 preempted."""
        cursor: dict[str, tuple[float, str]] = {
            r.req.request_id: (r.req.arrival_ms, "wait") for r in self._runs
        }
        spans: list[dict] = []

        def close_gap(rid: str, until: float) -> None:
            start, kind = cursor[rid]
            if until > start:
                spans.append({"lane": rid, "start": start, "end": until, "label": kind, "kind": kind})

        for rec in self.steps:
            for rid in rec.preempted:
                close_gap(rid, rec.start_ms)
                cursor[rid] = (rec.start_ms, "preempted")
            for rid, n in rec.tokens.items():
                close_gap(rid, rec.start_ms)
                kind = self._phases[(rec.step, rid)]
                spans.append(
                    {"lane": rid, "start": rec.start_ms, "end": rec.end_ms, "label": f"{n} tok", "kind": kind}
                )
                cursor[rid] = (rec.end_ms, "wait")
        return spans

    def _step_at(self, at_step: int | None) -> StepRecord | None:
        if at_step is None:
            return self.steps[-1] if self.steps else None
        return self.steps[at_step - 1] if 1 <= at_step <= len(self.steps) else None

    def counters(self, at_step: int | None = None) -> dict[str, float]:
        """vllm 지표 이름으로 본 누적/순간 값. queries와 hits는 token 수, usage는 0~1 비율."""
        rec = self._step_at(at_step)
        if rec is None:
            return {
                "vllm:num_preemptions": 0,
                "vllm:prefix_cache_queries": 0,
                "vllm:prefix_cache_hits": 0,
                "vllm:num_requests_running": 0,
                "vllm:num_requests_waiting": 0,
                "vllm:kv_cache_usage_perc": 0.0,
            }
        return {
            "vllm:num_preemptions": rec.preemptions_total,
            "vllm:prefix_cache_queries": rec.prefix_queries,
            "vllm:prefix_cache_hits": rec.prefix_hits,
            "vllm:num_requests_running": rec.running_after,
            "vllm:num_requests_waiting": rec.waiting_after,
            "vllm:kv_cache_usage_perc": rec.blocks_after / self.config.num_blocks,
        }

    def to_prometheus_text(
        self,
        at_step: int | None = None,
        *,
        counter_suffix: str = "",
        model_name: str = "GLM-5.3-Flash",
        engine: str = "0",
    ) -> str:
        """Prometheus 텍스트 모양의 구성한 표본. 히스토그램은 _sum, _count(초)만 낸다."""
        last = len(self.steps) if at_step is None else at_step
        labels = f'model_name="{model_name}",engine="{engine}"'
        ms: dict[str, list[float]] = {key: [] for key in ("ttft", "itl", "tpot", "e2e", "queue")}
        for run in self._runs:
            if run.token_steps and run.token_steps[0] <= last:
                ms["ttft"].append(run.token_end_ms[0] - run.server_arrival_ms)
            for i in range(1, len(run.token_end_ms)):
                if run.token_steps[i] <= last:
                    # vllm/v1/metrics/stats.py:549 - token 사이 간격마다 표본 하나.
                    ms["itl"].append(run.token_end_ms[i] - run.token_end_ms[i - 1])
            if run.finish_step is not None and run.finish_step <= last:
                n = run.generated
                ends = run.token_end_ms
                ms["e2e"].append(ends[-1] - run.server_arrival_ms)
                ms["queue"].append(run.first_start_ms - run.server_arrival_ms)
                ms["tpot"].append((ends[-1] - ends[0]) / (n - 1) if n > 1 else 0.0)
        names = {
            "ttft": "vllm:time_to_first_token_seconds",
            "itl": "vllm:inter_token_latency_seconds",
            "tpot": "vllm:request_time_per_output_token_seconds",
            "e2e": "vllm:e2e_request_latency_seconds",
            "queue": "vllm:request_queue_time_seconds",
        }
        lines = ["# constructed teaching sample, not measured"]
        for key, value in self.counters(at_step).items():
            name = key + counter_suffix if key in _COUNTER_KEYS else key
            lines.append(f"{name}{{{labels}}} {_fmt(value)}")
        for key, name in names.items():
            lines.append(f"{name}_sum{{{labels}}} {_fmt(sum(ms[key]) / 1000)}")
            lines.append(f"{name}_count{{{labels}}} {len(ms[key])}")
        return "\n".join(lines) + "\n"


_COUNTER_KEYS = frozenset(
    {"vllm:num_preemptions", "vllm:prefix_cache_queries", "vllm:prefix_cache_hits"}
)


class _Sim:
    """run_sim이 한 번 쓰는 scheduler 상태."""

    def __init__(self, requests: list[Req], config: SchedConfig) -> None:
        self.cfg = config
        self.runs = [_Run(r, r.arrival_ms + config.toy_network_ms, num_tokens=r.prompt_tokens) for r in requests]
        self.pending = deque(
            sorted((r for r in self.runs if not r.req.start_running), key=lambda r: r.server_arrival_ms)
        )
        self.running: list[_Run] = [r for r in self.runs if r.req.start_running]
        self.waiting: deque[_Run] = deque()
        self.used = 0
        for r in self.running:
            r.computed = r.req.start_computed
            r.held = _ceil_div(r.computed, config.block_size)
            r.scheduled_once = True
            self.used += r.held
        if self.used > config.num_blocks:
            raise ValueError(
                f"시작 시 running 요청이 쥔 block {self.used}개가 num_blocks({config.num_blocks})를 넘습니다."
            )
        self.steps: list[StepRecord] = []
        self.events: list[dict] = []
        self.phases: dict[tuple[int, str], str] = {}
        self.step = 0
        self.now = 0.0
        self.queries = 0
        self.hits = 0
        self.preemptions = 0
        self.last_stop = ""

    def emit(self, kind: str, rid: str | None, **detail: object) -> None:
        self.events.append(
            {"step": self.step, "actor": EVENT_ACTOR, "kind": kind, "request_id": rid, "detail": detail}
        )

    def done(self) -> bool:
        return not (self.pending or self.running or self.waiting)

    def threshold(self) -> int:
        cfg = self.cfg
        eligible = len(self.running) + len(self.waiting)
        # vllm/v1/core/sched/scheduler.py:645 - 경쟁 요청이 없으면(1개) 적용하지 않는다.
        threshold = cfg.long_prefill_token_threshold if eligible > 1 else 0
        # vllm/v1/core/sched/scheduler.py:650 - adaptive는 공평 몫 아래로 내려가지 않게 바닥을 둔다.
        if threshold > 0 and cfg.long_prefill_token_threshold_adaptive:
            threshold = max(threshold, cfg.max_num_batched_tokens // eligible)
        return threshold

    def preempt(self, victim: _Run) -> None:
        # vllm/v1/core/sched/scheduler.py:1589-1612 - block 반납, computed 0, 생성 token 유지, waiting 맨 앞.
        freed = victim.held
        self.used -= freed
        victim.held = 0
        victim.computed = 0
        victim.recomputing = True
        victim.num_preemptions += 1
        self.waiting.appendleft(victim)
        self.preemptions += 1
        self.emit("preempt", victim.req.request_id, freed_blocks=freed)

    def schedule_running(self, budget: int, tokens: dict[str, int], preempted: list[str]) -> int:
        cfg = self.cfg
        threshold = self.threshold()
        index = 0
        # vllm/v1/core/sched/scheduler.py:659 - running을 앞에서부터, 예산이 남은 동안.
        while index < len(self.running) and budget > 0:
            run = self.running[index]
            n = run.num_tokens - run.computed
            if 0 < threshold < n:  # vllm/v1/core/sched/scheduler.py:708
                n = threshold
            n = min(n, budget)
            need = _ceil_div(run.computed + n, cfg.block_size) - run.held
            scheduled = True
            while need > cfg.num_blocks - self.used:
                # vllm/v1/core/sched/scheduler.py:802 - FCFS는 running의 마지막 요청이 희생양이다.
                victim = self.running.pop()
                self.preempt(victim)
                preempted.append(victim.req.request_id)
                if victim is run:  # vllm/v1/core/sched/scheduler.py:842
                    scheduled = False
                    break
            if not scheduled:
                break
            self.grant(run, n, need, tokens)
            budget -= n
            self.emit("schedule_running", run.req.request_id, tokens=n, computed=run.computed)
            self.mark_chunk(run, n)
            index += 1
        return budget

    def grant(self, run: _Run, n: int, need: int, tokens: dict[str, int]) -> None:
        self.used += need
        run.held += need
        if run.first_sched_step == 0:
            run.first_sched_step = self.step
            run.first_start_ms = self.now
        tokens[run.req.request_id] = n
        phase = _PHASE_PREFILL if run.recomputing or run.generated == 0 else _PHASE_DECODE
        self.phases[(self.step, run.req.request_id)] = phase

    def mark_chunk(self, run: _Run, n: int) -> None:
        if run.computed + n < run.num_tokens:
            self.emit(
                "chunk", run.req.request_id, tokens=n, remaining=run.num_tokens - run.computed - n
            )

    def schedule_waiting(self, budget: int, tokens: dict[str, int]) -> int:
        cfg = self.cfg
        threshold = self.threshold()
        while budget > 0 and self.waiting:
            # vllm/v1/core/sched/scheduler.py:923 - running이 상한이면 waiting에서 더 꺼내지 않는다.
            if len(self.running) >= cfg.max_num_seqs:
                self.last_stop = "stop_waiting_seqs_cap"
                self.emit(self.last_stop, self.waiting[0].req.request_id,
                          running=len(self.running), max_num_seqs=cfg.max_num_seqs)
                return budget
            run = self.waiting[0]
            first = not run.scheduled_once
            computed = run.req.cached_tokens if run.computed == 0 and first else run.computed
            n = run.num_tokens - computed
            if 0 < threshold < n:  # vllm/v1/core/sched/scheduler.py:1155
                n = threshold
            # vllm/v1/core/sched/scheduler.py:1159-1166 - chunked를 끄면 예산보다 큰 요청은 여기서 멈춘다.
            if not cfg.enable_chunked_prefill and n > budget:
                self.last_stop = "stop_waiting_no_chunk"
                self.emit(self.last_stop, run.req.request_id, needed=n, budget=budget)
                return budget
            n = min(n, budget)
            need = _ceil_div(computed + n, cfg.block_size) - run.held
            # vllm/v1/core/kv_cache_manager.py:522-539 - 켜면 이번 chunk가 아니라 전체 입력이 들어가는지 본다.
            required = _ceil_div(run.num_tokens, cfg.block_size) - run.held if cfg.reserve_full_isl else need
            if required > cfg.num_blocks - self.used:
                # waiting에서는 preempt하지 않고 멈춘다(FCFS라 뒤 요청도 건너뛰지 않는다).
                self.last_stop = "stop_waiting_budget"
                self.emit(self.last_stop, run.req.request_id, reason="kv_blocks",
                          need_blocks=required, free_blocks=cfg.num_blocks - self.used)
                return budget
            self.waiting.popleft()
            if first:
                self.queries += run.req.prompt_tokens
                self.hits += run.req.cached_tokens
            run.computed = computed
            run.scheduled_once = True
            self.running.append(run)
            self.grant(run, n, need, tokens)
            budget -= n
            self.emit("schedule_waiting", run.req.request_id, tokens=n, computed=computed)
            self.mark_chunk(run, n)
        if self.waiting and budget <= 0:
            self.last_stop = "stop_waiting_budget"
            self.emit(self.last_stop, self.waiting[0].req.request_id, reason="token_budget", budget=0)
        return budget

    def apply_results(self, tokens: dict[str, int], end: float) -> None:
        cfg = self.cfg
        by_id = {r.req.request_id: r for r in self.running}
        for rid, n in tokens.items():
            run = by_id[rid]
            run.computed += n
            if run.computed < run.num_tokens:
                continue
            run.recomputing = False
            run.generated += 1
            run.num_tokens += 1
            run.token_end_ms.append(end)
            run.token_steps.append(self.step)
            if run.generated == 1:
                self.emit("first_token", rid, end_ms=end)
            finished = run.generated >= run.req.max_tokens
            # vllm/v1/engine/output_processor.py:324-338 - 첫 token, stream_interval개마다, 끝날 때 보낸다.
            if finished or run.sent_tokens == 0 or run.generated - run.sent_tokens >= cfg.stream_interval:
                run.sent_tokens = run.generated
                run.chunk_server_ms.append(end)
                run.chunk_client_ms.append(end + cfg.toy_network_ms)
            if finished:
                self.used -= run.held
                run.held = 0
                run.finish_step = self.step
                self.running.remove(run)
                self.emit("finish", rid, output_tokens=run.generated)

    def arrive(self) -> None:
        for run in self.runs:
            if run.req.start_running and self.step == 1:
                self.emit("arrive", run.req.request_id, start_running=True)
        while self.pending and self.pending[0].server_arrival_ms <= self.now:
            run = self.pending.popleft()
            self.waiting.append(run)
            self.emit("arrive", run.req.request_id, server_arrival_ms=run.server_arrival_ms)

    def stuck(self, why: str) -> SimStuck:
        running = [r.req.request_id for r in self.running]
        waiting = [r.req.request_id for r in self.waiting]
        not_arrived = [r.req.request_id for r in self.pending]
        return SimStuck(
            f"step {self.step}에서 더 진행할 수 없습니다: {why}. "
            f"running {running}, waiting {waiting}, 아직 도착하지 않음 {not_arrived}."
        )

    def run_one_step(self) -> None:
        cfg = self.cfg
        if not self.running and not self.waiting and self.pending:
            # 할 일이 없으면 다음 도착 시각으로 건너뛴다.
            self.now = max(self.now, self.pending[0].server_arrival_ms)
        self.step += 1
        self.arrive()
        running_before = [r.req.request_id for r in self.running]
        waiting_before = [r.req.request_id for r in self.waiting]
        tokens: dict[str, int] = {}
        preempted: list[str] = []
        budget = self.schedule_running(cfg.max_num_batched_tokens, tokens, preempted)
        if preempted:
            self.emit("stop_waiting_preempted", None, preempted=list(preempted))
        else:
            budget = self.schedule_waiting(budget, tokens)
        blocks_in_use = self.used
        total = sum(tokens.values())
        if total == 0 and not preempted:
            raise self.stuck(f"토큰을 하나도 배정하지 못했습니다(마지막 멈춤 {self.last_stop or '없음'})")
        start = self.now
        end = start + cfg.toy_step_ms + cfg.toy_ms_per_token * total
        self.apply_results(tokens, end)
        self.now = end
        self.steps.append(
            StepRecord(
                step=self.step, start_ms=start, end_ms=end, tokens=tokens,
                running_before=running_before, waiting_before=waiting_before, preempted=preempted,
                blocks_in_use=blocks_in_use, budget_left=budget,
                running_after=len(self.running), waiting_after=len(self.waiting),
                blocks_after=self.used, prefix_queries=self.queries, prefix_hits=self.hits,
                preemptions_total=self.preemptions,
            )
        )


def _check_requests(requests: list[Req], config: SchedConfig) -> None:
    seen: set[str] = set()
    for r in requests:
        if r.request_id in seen:
            raise ValueError(f"request_id가 겹칩니다: {r.request_id}")
        seen.add(r.request_id)
        if r.prompt_tokens < 1 or r.max_tokens < 1:
            raise ValueError(f"{r.request_id}: prompt_tokens({r.prompt_tokens})와 max_tokens({r.max_tokens})는 1 이상이어야 합니다.")
        if r.prompt_tokens + r.max_tokens > config.max_model_len:
            raise ValueError(
                f"{r.request_id}: prompt_tokens({r.prompt_tokens}) + max_tokens({r.max_tokens})가 "
                f"max_model_len({config.max_model_len})을 넘습니다."
            )
        if r.cached_tokens % config.block_size or not 0 <= r.cached_tokens < r.prompt_tokens:
            raise ValueError(
                f"{r.request_id}: cached_tokens({r.cached_tokens})는 block_size({config.block_size})의 배수이고 "
                f"prompt_tokens({r.prompt_tokens}) 미만이어야 합니다."
            )
        if r.start_running and not 0 <= r.start_computed < r.prompt_tokens:
            raise ValueError(
                f"{r.request_id}: start_computed({r.start_computed})는 0 이상 prompt_tokens({r.prompt_tokens}) 미만이어야 합니다."
            )


def run_sim(
    requests: list[Req],
    config: SchedConfig = SchedConfig(),
    *,
    validate: bool = True,
    max_steps: int = 10000,
) -> SimResult:
    if validate:
        config.validate()
    _check_requests(requests, config)
    sim = _Sim(requests, config)
    while not sim.done():
        if sim.step >= max_steps:
            raise sim.stuck(f"max_steps({max_steps})를 넘었습니다")
        sim.run_one_step()
    return SimResult(sim.steps, sim.events, config, _runs=sim.runs, _phases=sim.phases)


def sweep(requests: list[Req], param: str, values: list, base: SchedConfig = SchedConfig()) -> list[dict]:
    """param 하나만 바꿔 다시 돌린다. 지표는 client 쪽(serve.py 식)을 쓴다."""
    fields = {f.name for f in dataclasses.fields(SchedConfig)}
    if param not in fields:
        raise ValueError(f"SchedConfig에 없는 칸입니다: {param}. 가능한 칸 {sorted(fields)}")
    rows = []
    for value in values:
        result = run_sim(requests, dataclasses.replace(base, **{param: value}))
        metrics = result.metrics()
        makespan_ms = result.steps[-1].end_ms
        out_tokens = sum(m.output_tokens for m in metrics)
        ttfts = [m.client_ttft_ms for m in metrics]
        itls = [x for m in metrics for x in m.client_itl_ms]
        tpots = [m.client_tpot_ms for m in metrics if m.client_tpot_ms is not None]
        row = {
            param: value,
            "steps": len(result.steps),
            "num_preemptions": sum(m.num_preemptions for m in metrics),
            "toy_tokens_per_s": out_tokens / (makespan_ms / 1000),
            "ttft_mean_ms": _mean(ttfts),
            "ttft_p99_ms": float(np.percentile(ttfts, 99)),
            "itl_mean_ms": _mean(itls),
            "tpot_mean_ms": _mean(tpots),
            "e2el_mean_ms": _mean([m.client_e2el_ms for m in metrics]),
        }
        for group in dict.fromkeys(_group(m.request_id) for m in metrics):
            row[f"ttft_mean_ms:{group}"] = _mean([m.client_ttft_ms for m in metrics if _group(m.request_id) == group])
        rows.append(row)
    return rows


def doc_faq_chat() -> list[Req]:
    return [Req("doc", 54, 8), Req("faq", 20, 6), Req("chat", 34, 4)]


def e1_workload() -> list[Req]:
    return [
        Req("chat", 34, 4, start_running=True, start_computed=33),
        Req("doc", 54, 8, start_running=True, start_computed=32),
        Req("faq", 20, 6),
    ]


def mixed_workload() -> list[Req]:
    return [Req("doc", 400, 16)] + [Req(f"faq-{i}", 30, 12, arrival_ms=10.0 * i) for i in range(1, 6)]
