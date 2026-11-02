"""GPU, CPU, 디스크로 층을 나눈 prefix 저장소를 손으로 따라가 보는 교육용 모델이다 (teaching model).

이것은 vLLM도 LMCache도 아니다. 요청 하나씩 순서대로 처리하며 hit이 어느 층에서 왔는지와 다시 계산한 token 수를
센다. 층마다 LRU로 밀어내고, 밀려난 block은 아래 층으로 내려가며, 마지막 층에서 밀리면 사라진다.
시간 값은 ToyCosts에 선언한 toy 상수의 결과다. 실제 지연이 아니고 측정이 아니다. 방향만 본다.

인용한 `vllm/...:줄`은 v0.32.0(commit 5df63a7) 소스 기준이다. 모델링하지 않은 것은 NOT_MODELED에 있다.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TypedDict

TIERS = ("gpu", "cpu", "disk")
TOY_NOTE = "toy 비용의 결과이고 측정이 아니다. 실제 지연으로 인용하지 않는다."

NOT_MODELED: tuple[str, ...] = (
    "실제 지연과 대역폭은 없다. toy_* 상수는 층의 순서만 보이려고 고른 값이고 어떤 하드웨어의 측정값도 아니다.",
    "실제 KV 값과 record 크기는 없다. block 하나는 어느 층에서나 같은 한 칸이다. 크기 계산은 kv_cases를 본다.",
    "동시 실행, 비동기 load, 전송 대기(WAITING_FOR_REMOTE_KVS)는 없다. 요청은 하나씩 끝까지 처리한다(P8-31).",
    "LMCache의 저장 시점과 조회 절차는 따르지 않는다. 밀려날 때 아래 층으로 옮기는 write-back 하나만 있다(P7-54, P8-25).",
    "load 실패와 kv_load_failure_policy는 없다. 층에 있으면 항상 읽힌다(P8-33).",
    "sliding window와 scratch group은 없다. SWA 재생 비용과 저장하지 않는 group은 세지 않는다(P8-18, P8-32).",
    "group별 block 크기와 lcm 정렬은 없다. 층 전체가 block_tokens 하나를 쓴다(P8-20, P8-21).",
    "KDA 상태는 경계 block과 수명이 같다고 놓았다. 상태 자체의 크기와 따로 일어나는 축출은 없다(P7-53, P7-54).",
    "FlashKDA checkpoint block을 LMCache가 저장하는 방식은 확인하지 못해 넣지 않았다(P8-26).",
    "align 모드의 '스텝 끝이 block 경계일 때만 저장'은 없다. 계산을 지나간 경계에는 모두 상태가 있다고 놓았다(P8-23).",
    "경계로 내려 버린 block을 읽는 비용은 세지 않는다.",
    "실행 중인 요청의 block 고정(ref count)은 없다. 대신 요청 하나의 block이 GPU 층보다 많으면 거부한다.",
    "cache salt와 요청 사이 격리는 없다. token이 같으면 같은 block이다.",
)


@dataclass(frozen=True)
class ToyCosts:
    """toy ms. 측정값이 아니다."""

    toy_gpu_ms_per_block: float = 0.0
    toy_cpu_ms_per_block: float = 1.0
    toy_disk_ms_per_block: float = 4.0
    toy_recompute_ms_per_token: float = 1.0


DEFAULT_TOY_COSTS = ToyCosts()


@dataclass(frozen=True)
class AgentRequest:
    request_id: str
    tokens: tuple[int, ...]


class RequestRow(TypedDict):
    request_id: str
    prompt_tokens: int
    gpu_hit_blocks: int
    cpu_hit_blocks: int
    disk_hit_blocks: int
    hit_tokens: int
    discarded_by_checkpoint_tokens: int
    recomputed_tokens: int
    toy_ms: float


class TierTotals(TypedDict):
    prompt_tokens: int
    gpu_hit_blocks: int
    cpu_hit_blocks: int
    disk_hit_blocks: int
    hit_tokens: int
    discarded_by_checkpoint_tokens: int
    recomputed_tokens: int
    demoted_blocks: int
    dropped_blocks: int
    toy_ms: float


class TierSimResult(TypedDict):
    enabled_tiers: list[str]
    state_checkpoint_blocks: int | None
    rows: list[RequestRow]
    totals: TierTotals
    note: str


def agent_workload(
    *,
    sessions: int,
    turns: int,
    shared_prefix_tokens: int,
    tokens_per_turn: int,
) -> list[AgentRequest]:
    """모든 세션이 같은 앞부분(system prompt, 도구 정의)을 쓰고 턴마다 대화가 자라는 요청열을 만든다.

    세션을 번갈아 돈다. 난수가 없어 항상 같은 요청열이다. 모델 출력은 다음 턴 prompt의 token으로만 나타난다.
    """
    if min(sessions, turns, tokens_per_turn) < 1 or shared_prefix_tokens < 0:
        raise ValueError(
            f"sessions={sessions}, turns={turns}, tokens_per_turn={tokens_per_turn}은 1 이상, "
            f"shared_prefix_tokens={shared_prefix_tokens}는 0 이상이어야 합니다"
        )
    shared = tuple(range(shared_prefix_tokens))
    session_offset = shared_prefix_tokens + turns * tokens_per_turn
    requests: list[AgentRequest] = []
    for turn in range(1, turns + 1):
        for session in range(sessions):
            start = (session + 1) * session_offset
            own = tuple(range(start, start + turn * tokens_per_turn))
            requests.append(AgentRequest(f"s{session}-t{turn}", shared + own))
    return requests


class _TierStore:
    """층마다 LRU 순서를 가진 저장소. 한 block은 한 층에만 있다."""

    def __init__(self, capacities: dict[str, int]) -> None:
        self._capacities = capacities
        self._order = tuple(capacities)
        self._stores: dict[str, OrderedDict[int, None]] = {tier: OrderedDict() for tier in capacities}
        self.demoted = 0
        self.dropped = 0

    def locate(self, key: int) -> str | None:
        for tier in self._order:
            if key in self._stores[tier]:
                return tier
        return None

    def bring_to_gpu(self, key: int) -> None:
        """계산했거나 읽은 block을 GPU의 가장 최근 칸에 둔다. 넘치면 아래 층으로 밀린다."""
        tier = self.locate(key)
        if tier is not None:
            del self._stores[tier][key]
        self._stores["gpu"][key] = None
        self._spill_from(0)

    def _spill_from(self, index: int) -> None:
        tier = self._order[index]
        store = self._stores[tier]
        if len(store) <= self._capacities[tier]:
            return
        oldest, _ = store.popitem(last=False)
        if index + 1 == len(self._order):
            self.dropped += 1
            return
        self.demoted += 1
        self._stores[self._order[index + 1]][oldest] = None
        self._spill_from(index + 1)


def _enabled_capacities(
    gpu_blocks: int, cpu_blocks: int, disk_blocks: int, disabled_tiers: Iterable[str]
) -> dict[str, int]:
    disabled = set(disabled_tiers)
    unknown = disabled - set(TIERS)
    if unknown:
        raise ValueError(f"disabled_tiers에 모르는 층 {sorted(unknown)}이 있습니다. 가능한 값: {TIERS}")
    if "gpu" in disabled:
        raise ValueError("gpu 층은 끌 수 없습니다. 이 모델에서 실행 중인 요청의 block은 GPU에 있어야 합니다")
    if gpu_blocks < 1 or min(cpu_blocks, disk_blocks) < 0:
        raise ValueError(
            f"gpu_blocks={gpu_blocks}는 1 이상, cpu_blocks={cpu_blocks}, disk_blocks={disk_blocks}는 0 이상이어야 합니다"
        )
    sizes = {"gpu": gpu_blocks, "cpu": cpu_blocks, "disk": disk_blocks}
    return {tier: size for tier, size in sizes.items() if size > 0 and tier not in disabled}


def _prefix_chain_keys(
    tokens: Sequence[int], block_tokens: int, interned: dict[tuple[int, tuple[int, ...]], int]
) -> list[int]:
    """앞 block에 이어지는 꽉 찬 block만 key를 받는다. 앞이 다르면 같은 token이어도 다른 block이다."""
    keys: list[int] = []
    parent = -1
    for start in range(0, len(tokens) - block_tokens + 1, block_tokens):
        chunk = tuple(tokens[start : start + block_tokens])
        parent = interned.setdefault((parent, chunk), len(interned))
        keys.append(parent)
    return keys


def _matched_tiers(store: _TierStore, keys: Sequence[int], prompt_tokens: int, block_tokens: int) -> list[str]:
    """앞에서부터 처음 없는 block까지 찾는다. 상한은 (prompt - 1) // block이다.

    logit을 내려면 마지막 token은 계산해야 한다. vllm/v1/core/kv_cache_manager.py:290-295.
    """
    limit = (prompt_tokens - 1) // block_tokens
    found: list[str] = []
    for key in keys[:limit]:
        tier = store.locate(key)
        if tier is None:
            break
        found.append(tier)
    return found


def simulate_tiers(
    requests: Iterable[AgentRequest],
    *,
    gpu_blocks: int,
    cpu_blocks: int = 0,
    disk_blocks: int = 0,
    disabled_tiers: Iterable[str] = (),
    block_tokens: int = 16,
    state_checkpoint_blocks: int | None = None,
    toy_costs: ToyCosts = DEFAULT_TOY_COSTS,
) -> TierSimResult:
    """요청을 순서대로 처리해 층별 hit과 다시 계산한 token을 센다. 같은 입력이면 항상 같은 결과다.

    state_checkpoint_blocks는 KDA 층이 있는 hybrid 모델의 규칙이다. KV block이 더 있어도 hit은 상태가 저장된
    마지막 경계(이 값의 배수)까지만 닿는다. 상태 칸 p는 정확히 (p+1) * block 뒤의 상태이고, 그 경계에 유효한 상태가
    없으면 scheduler가 모두 동의하는 경계로 되돌린다. vllm/config/cache.py:189-195,
    vllm/v1/core/sched/scheduler.py:502-503, :1029-1037, 대장 P7-53, P8-23, P8-25.
    """
    if block_tokens < 1:
        raise ValueError(f"block_tokens={block_tokens}: 1 이상이어야 합니다")
    if state_checkpoint_blocks is not None and state_checkpoint_blocks < 1:
        raise ValueError(f"state_checkpoint_blocks={state_checkpoint_blocks}: 1 이상이어야 합니다")
    capacities = _enabled_capacities(gpu_blocks, cpu_blocks, disk_blocks, disabled_tiers)
    store = _TierStore(capacities)
    block_costs = {
        "gpu": toy_costs.toy_gpu_ms_per_block,
        "cpu": toy_costs.toy_cpu_ms_per_block,
        "disk": toy_costs.toy_disk_ms_per_block,
    }
    interned: dict[tuple[int, tuple[int, ...]], int] = {}
    rows: list[RequestRow] = []
    for request in requests:
        prompt_tokens = len(request.tokens)
        if prompt_tokens < 1:
            raise ValueError(f"{request.request_id}: prompt가 비었습니다")
        keys = _prefix_chain_keys(request.tokens, block_tokens, interned)
        if len(keys) > gpu_blocks:
            raise ValueError(f"{request.request_id}: block {len(keys)}개가 gpu_blocks={gpu_blocks}보다 많습니다")
        matched = _matched_tiers(store, keys, prompt_tokens, block_tokens)
        usable = len(matched)
        if state_checkpoint_blocks is not None:
            usable = usable // state_checkpoint_blocks * state_checkpoint_blocks
        used = matched[:usable]
        hit_tokens = usable * block_tokens
        recomputed = prompt_tokens - hit_tokens
        rows.append(
            RequestRow(
                request_id=request.request_id,
                prompt_tokens=prompt_tokens,
                gpu_hit_blocks=used.count("gpu"),
                cpu_hit_blocks=used.count("cpu"),
                disk_hit_blocks=used.count("disk"),
                hit_tokens=hit_tokens,
                discarded_by_checkpoint_tokens=(len(matched) - usable) * block_tokens,
                recomputed_tokens=recomputed,
                toy_ms=sum(block_costs[tier] for tier in used) + recomputed * toy_costs.toy_recompute_ms_per_token,
            )
        )
        for key in keys:
            store.bring_to_gpu(key)
    return TierSimResult(
        enabled_tiers=list(capacities),
        state_checkpoint_blocks=state_checkpoint_blocks,
        rows=rows,
        totals=TierTotals(
            prompt_tokens=sum(row["prompt_tokens"] for row in rows),
            gpu_hit_blocks=sum(row["gpu_hit_blocks"] for row in rows),
            cpu_hit_blocks=sum(row["cpu_hit_blocks"] for row in rows),
            disk_hit_blocks=sum(row["disk_hit_blocks"] for row in rows),
            hit_tokens=sum(row["hit_tokens"] for row in rows),
            discarded_by_checkpoint_tokens=sum(row["discarded_by_checkpoint_tokens"] for row in rows),
            recomputed_tokens=sum(row["recomputed_tokens"] for row in rows),
            demoted_blocks=store.demoted,
            dropped_blocks=store.dropped,
            toy_ms=sum(row["toy_ms"] for row in rows),
        ),
        note=TOY_NOTE,
    )
