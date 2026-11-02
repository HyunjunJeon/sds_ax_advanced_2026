"""KV cache 관리 규칙을 손으로 따라가 보는 교육용 모델이다 (teaching model).

이것은 vLLM이 아니라 수업용 모델이다. vLLM v0.32.0의 BlockPool, KVCacheManager,
SingleTypeKVCacheManager가 정하는 규칙(free queue 순서, 꽉 찬 block만 hash, 첫 block hash에만
salt, 적중 상한 num_tokens-1, ref_cnt 공유와 반납, 캐시된 free block 축출)을 한 group,
block_size == hash_block_size로 줄여서 같은 순서로 실행한다. KV 값은 없고 block ID와 표지만 있다.
hash 값은 sha256 앞 12자라서 vLLM의 값과 다르다. 구조만 같다.

시뮬레이터 출력은 "vLLM이 이렇게 동작했다"가 아니다. 실제 클래스와의 대조는
data/reference_kv.json(reference_rows)이 status가 ran일 때 그 범위에서만 말할 수 있다.
모델링하지 않은 것은 NOT_MODELED에 있다.

인용한 `vllm/...:줄`은 v0.32.0(commit 5df63a7) 소스 기준이다.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import TypedDict

from vllm_lab import DATA_DIR, DEFAULT_BLOCK_SIZE

NOT_MODELED: tuple[str, ...] = (
    "watermark(대기 중이거나 preempt된 요청에 남겨 두는 여유 block)는 모델링하지 않았다. vllm/v1/core/kv_cache_manager.py:512-516",
    "scheduler_reserve_full_isl(기본 True)은 모델링하지 않았다. vLLM은 새 요청의 전체 입력이 들어갈 free block이 없으면 들여보내지 않지만 schedule은 첫 chunk에 필요한 block만 보고 들여보낸다. vllm/config/scheduler.py:190, vllm/v1/core/sched/scheduler.py:1270, vllm/v1/core/kv_cache_manager.py:522-539",
    "sliding window와 skipped block은 KVManagerSim에 없다. HybridPoolToy가 block 수 규칙만 장난감으로 보인다.",
    "KV connector(외부 KV 전송)와 외부 계산 token은 모델링하지 않았다.",
    "마지막 partial block 등록(partial tail 등록)은 모델링하지 않았다. 꽉 차지 않은 block은 hash가 없다.",
    "max_model_len 상한(allocate_slots의 min(..., max_model_len))은 적용하지 않았다.",
    "hash_block_size와 group block_size의 분리는 모델링하지 않았다. 둘이 같은 한 group만 있다.",
    "실제 KV 값은 없다. slot_contents는 어느 요청의 몇 번째 token이 쓰였는지 보여 주는 표지다.",
    "실제 hash 값은 vLLM과 다르다(sha256 앞 12자). 같은 token이면 같은 hash라는 구조만 같다.",
    "LoRA, 멀티모달, prompt embeds의 extra key와 copy-on-write(partial hit)는 모델링하지 않았다.",
    "pool을 직접 두 번 free하면 ValueError를 낸다. vLLM은 이 검사를 하지 않는다(교육용 안전장치).",
)

NONE_HASH = "NONE_HASH"
PAD_SLOT_ID = -1


class TraceEvent(TypedDict):
    step: int
    actor: str
    kind: str
    request_id: str | None
    detail: dict[str, object]


class KVPoolExhausted(ValueError):
    """free block이 모자란다. vllm/v1/core/block_pool.py:679는 같은 상황에서 ValueError를 낸다."""

    def __init__(self, requested: int, free: int) -> None:
        self.requested = requested
        self.free = free
        super().__init__(
            f"free block이 모자랍니다: {requested}개가 필요한데 free는 {free}개입니다 "
            f"(부족 {requested - free}개)."
        )


def _cdiv(a: int, b: int) -> int:
    return -(-a // b)


# --------------------------------------------------------------------------- hash

def hash_block_tokens(parent_hash: str | None, token_ids: Sequence[int],
                      extra_keys: tuple | None = None) -> str:
    """sha256(repr((parent_hash or NONE_HASH, tuple(token_ids), extra_keys)))의 hex 앞 12자."""
    # vllm/v1/core/kv_cache_utils.py:719-724: 부모가 없으면(falsy) NONE_HASH, 본문은 (부모, token 튜플, extra).
    parent = parent_hash or NONE_HASH
    payload = repr((parent, tuple(token_ids), extra_keys))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def request_block_hashes(token_ids: Sequence[int], block_size: int = DEFAULT_BLOCK_SIZE,
                         cache_salt: str | None = None) -> list[str]:
    """꽉 찬 block만. salt는 start_token_idx == 0인 block의 extra_keys에만 (("cache_salt", salt),)."""
    hashes: list[str] = []
    parent: str | None = None
    start = 0
    # vllm/v1/core/kv_cache_utils.py:979-980: end가 num_tokens를 넘으면 멈춘다(꽉 찬 block만 hash).
    while start + block_size <= len(token_ids):
        # vllm/v1/core/kv_cache_utils.py:647-650: salt는 첫 block(start == 0)이고 salt가 truthy일 때만.
        extra = (("cache_salt", cache_salt),) if (start == 0 and cache_salt) else None
        parent = hash_block_tokens(parent, token_ids[start:start + block_size], extra)
        hashes.append(parent)
        start += block_size
    return hashes


# --------------------------------------------------------------------------- slot

def slot_id(block_table: Sequence[int], position: int, block_size: int = DEFAULT_BLOCK_SIZE) -> int:
    """block_table[position // block_size] * block_size + position % block_size."""
    index = position // block_size
    if position < 0 or index >= len(block_table):
        raise IndexError(
            f"position {position}은 block 표 밖입니다: 표는 block {len(block_table)}개 "
            f"(token {len(block_table) * block_size}개)까지만 덮습니다."
        )
    # vllm/v1/worker/gpu/block_table.py:348: slot = block_number * block_size + 칸 안 offset.
    return block_table[index] * block_size + position % block_size


def slot_mapping(block_table: Sequence[int], start: int, num_tokens: int,
                 block_size: int = DEFAULT_BLOCK_SIZE, pad_to: int | None = None) -> list[int]:
    """pad_to가 있으면 뒤를 PAD_SLOT_ID로 채운다."""
    if pad_to is not None and pad_to < num_tokens:
        raise ValueError(f"pad_to {pad_to}가 token 수 {num_tokens}보다 작습니다.")
    slots = [slot_id(block_table, p, block_size) for p in range(start, start + num_tokens)]
    if pad_to is not None:
        # vllm/v1/worker/gpu/block_table.py:296-304: 남는 칸은 PAD_SLOT_ID(-1)로 채운다(CUDA graph용).
        slots += [PAD_SLOT_ID] * (pad_to - num_tokens)
    return slots


class BatchEntry(TypedDict):
    request_id: str
    token_ids: list[int]
    num_computed_tokens: int
    block_table: list[int]


def packed_batch(entries: Sequence[BatchEntry], block_size: int = DEFAULT_BLOCK_SIZE,
                 pad_to: int | None = None) -> dict:
    """이번 step에 계산할 token만 이어 붙인 배열. query_start_loc은 앞에 0이 붙은 누적합이다."""
    total = sum(len(e["token_ids"]) for e in entries)
    if pad_to is not None and pad_to < total:
        raise ValueError(f"pad_to {pad_to}가 이번 step의 token 수 {total}보다 작습니다.")
    input_ids: list[int] = []
    positions: list[int] = []
    seq_lens: list[int] = []
    slots: list[int] = []
    query_start_loc = [0]
    for e in entries:
        n = len(e["token_ids"])
        computed = e["num_computed_tokens"]
        input_ids += e["token_ids"]
        positions += range(computed, computed + n)
        seq_lens.append(computed + n)
        slots += slot_mapping(e["block_table"], computed, n, block_size)
        query_start_loc.append(query_start_loc[-1] + n)
    if pad_to is not None:
        slots += [PAD_SLOT_ID] * (pad_to - total)
    return {
        "request_ids": [e["request_id"] for e in entries],
        "input_ids": input_ids,
        "query_start_loc": query_start_loc,
        "positions": positions,
        "seq_lens": seq_lens,
        "slot_mapping": slots,
        "num_tokens": total,
        "num_tokens_after_padding": pad_to if pad_to is not None else total,
    }


# --------------------------------------------------------------------------- block, queue

@dataclass(eq=False)
class KVBlock:
    """metadata만 있다. KV 값은 없다. vllm/v1/core/kv_cache_utils.py:176-200."""

    block_id: int
    ref_cnt: int = 0
    block_hash: str | None = None
    block_hash_num_tokens: int | None = None
    is_null: bool = False
    prev_free: KVBlock | None = field(default=None, repr=False)
    next_free: KVBlock | None = field(default=None, repr=False)


class FreeQueue:
    """직접 만든 이중 연결 리스트. vllm/v1/core/kv_cache_utils.py:246."""

    def __init__(self, blocks: list[KVBlock]) -> None:
        # 양 끝 sentinel은 vllm/v1/core/kv_cache_utils.py:269 이후의 fake head/tail과 같은 생각이다.
        self._head = KVBlock(-1)
        self._tail = KVBlock(-1)
        self._count = 0
        self._head.next_free = self._tail
        self._tail.prev_free = self._head
        self.append_n(blocks)

    def __len__(self) -> int:
        return self._count

    def popleft(self) -> KVBlock:
        return self.popleft_n(1)[0]

    def popleft_n(self, n: int) -> list[KVBlock]:
        if n > self._count:
            raise ValueError(f"free queue에 {self._count}개뿐인데 {n}개를 꺼내려 했습니다.")
        out: list[KVBlock] = []
        for _ in range(n):
            block = self._head.next_free
            self._unlink(block)
            out.append(block)
        return out

    def remove(self, block: KVBlock) -> None:
        if block.prev_free is None or block.next_free is None:
            raise ValueError(f"block {block.block_id}은 free queue에 없습니다.")
        self._unlink(block)

    def prepend_n(self, blocks: list[KVBlock]) -> None:
        """주어진 순서가 앞에서부터의 순서. vllm/v1/core/kv_cache_utils.py:426."""
        self._insert_before(self._head.next_free, blocks)

    def append_n(self, blocks: list[KVBlock]) -> None:
        """vllm/v1/core/kv_cache_utils.py:447."""
        self._insert_before(self._tail, blocks)

    def ids(self) -> list[int]:
        out: list[int] = []
        node = self._head.next_free
        while node is not self._tail:
            out.append(node.block_id)
            node = node.next_free
        return out

    def _unlink(self, block: KVBlock) -> None:
        prev_block, next_block = block.prev_free, block.next_free
        prev_block.next_free = next_block
        next_block.prev_free = prev_block
        block.prev_free = block.next_free = None
        self._count -= 1

    def _insert_before(self, anchor: KVBlock, blocks: list[KVBlock]) -> None:
        for block in blocks:
            if block.prev_free is not None:
                raise ValueError(f"block {block.block_id}은 이미 free queue 안에 있습니다.")
            before = anchor.prev_free
            before.next_free = block
            block.prev_free = before
            block.next_free = anchor
            anchor.prev_free = block
            self._count += 1


# --------------------------------------------------------------------------- pool

class BlockPool:
    def __init__(self, num_blocks: int, enable_caching: bool = True,
                 events: list[TraceEvent] | None = None) -> None:
        """블록 전부 생성, 첫 popleft를 null block(ID 0, is_null=True)으로."""
        if num_blocks < 1:
            raise ValueError(f"num_blocks는 1 이상이어야 합니다: {num_blocks}")
        self.num_blocks = num_blocks
        self.enable_caching = enable_caching
        self.events: list[TraceEvent] = events if events is not None else []
        self.step = 0
        self.current_request: str | None = None
        self.evicted_ids: list[int] = []
        self.blocks = [KVBlock(i) for i in range(num_blocks)]
        self.free_queue = FreeQueue(self.blocks)
        # hash -> {block_id: block}. 같은 hash를 여러 block이 가질 수 있고 먼저 들어간 것이 앞이다.
        # vllm/v1/core/block_pool.py:203 "If there are duplicated blocks, we return the first block".
        self._cached: dict[str, dict[int, KVBlock]] = {}
        # vllm/v1/core/block_pool.py:187: 첫 popleft가 null block(ID 0)이다.
        self.null_block = self.free_queue.popleft()
        self.null_block.is_null = True

    def _emit(self, kind: str, **detail: object) -> None:
        self.events.append(
            {"step": self.step, "actor": "BlockPool", "kind": kind,
             "request_id": self.current_request, "detail": detail}
        )

    def num_free(self) -> int:
        return len(self.free_queue)

    def usage(self) -> float:
        # vllm/v1/core/block_pool.py:885-889: null block은 분모에서 뺀다.
        total = self.num_blocks - 1
        if not total:
            return 0.0
        return 1.0 - self.num_free() / total

    def get_cached_block(self, block_hash: str) -> KVBlock | None:
        holders = self._cached.get(block_hash)
        if not holders:
            return None
        return next(iter(holders.values()))

    def get_new_blocks(self, n: int) -> list[KVBlock]:
        """부족하면 KVPoolExhausted. 앞에서 꺼내고, hash가 있으면 지우고(evict), ref_cnt=1."""
        if n > self.num_free():
            self._emit("alloc_failed", requested=n, free=self.num_free())
            raise KVPoolExhausted(n, self.num_free())  # vllm/v1/core/block_pool.py:678-679
        out = self.free_queue.popleft_n(n)
        for block in out:
            # vllm/v1/core/block_pool.py:688-691: 꺼낸 block의 옛 hash를 지우고 ref_cnt를 1로.
            if self.enable_caching and block.block_hash is not None:
                self._emit("evict", block_id=block.block_id, block_hash=block.block_hash)
                self.evicted_ids.append(block.block_id)
                self._remove_hash(block)
            block.ref_cnt += 1
        self._emit("alloc", block_ids=[b.block_id for b in out])
        return out

    def touch(self, blocks: Sequence[KVBlock]) -> None:
        """ref_cnt==0이고 null이 아니면 queue 중간에서 빼고, ref_cnt += 1."""
        from_free: list[int] = []
        for block in blocks:
            # vllm/v1/core/block_pool.py:763-766: ref_cnt 0이면 free queue(축출 후보) 안에 있으므로 뺀다.
            if block.ref_cnt == 0 and not block.is_null:
                self.free_queue.remove(block)
                from_free.append(block.block_id)
            block.ref_cnt += 1
        self._emit("touch", block_ids=[b.block_id for b in blocks], from_free=from_free)

    def free_blocks(self, ordered_blocks: Iterable[KVBlock]) -> None:
        """ref_cnt -= 1. 0이 된 것 중 hash 없음(또는 caching 꺼짐)은 prepend_n, hash 있음은 append_n."""
        front: list[KVBlock] = []
        back: list[KVBlock] = []
        for block in ordered_blocks:
            if block.ref_cnt <= 0 and not block.is_null:
                raise ValueError(f"block {block.block_id}의 ref_cnt가 {block.ref_cnt}인데 다시 반납했습니다.")
            block.ref_cnt -= 1
            if block.ref_cnt == 0 and not block.is_null:
                # vllm/v1/core/block_pool.py:794-798: hash 없는 block은 LIFO로 앞에, hash 있는 block은 FIFO로 뒤에.
                if block.block_hash is None or not self.enable_caching:
                    front.append(block)
                else:
                    back.append(block)
        # vllm/v1/core/block_pool.py:801-802
        self.free_queue.prepend_n(front)
        self.free_queue.append_n(back)
        if front:
            self._emit("free_front", block_ids=[b.block_id for b in front])
        if back:
            self._emit("free_back", block_ids=[b.block_id for b in back])

    def cache_block(self, block: KVBlock, block_hash: str, num_tokens: int) -> None:
        """같은 hash를 여러 block이 가질 수 있다. get_cached_block은 먼저 들어간 것을 돌려준다."""
        # vllm/v1/core/block_pool.py:269-271: null block은 등록하지 않는다.
        if block.is_null or not self.enable_caching:
            return
        if block.block_hash is not None:
            # vllm/v1/core/block_pool.py:276-283: 이미 hash가 있는 block은 partial -> full 승격뿐이다.
            if block.block_hash_num_tokens is None or block.block_hash_num_tokens >= num_tokens:
                raise ValueError(f"block {block.block_id}은 이미 hash가 있고 승격이 아닙니다.")
            self._remove_hash(block)
        block.block_hash = block_hash
        block.block_hash_num_tokens = num_tokens
        self._cached.setdefault(block_hash, {})[block.block_id] = block
        self._emit("hash_register", block_id=block.block_id, block_hash=block_hash, num_tokens=num_tokens)

    def _remove_hash(self, block: KVBlock) -> None:
        holders = self._cached.get(block.block_hash)
        if holders is not None:
            holders.pop(block.block_id, None)
            if not holders:
                del self._cached[block.block_hash]
        block.block_hash = None
        block.block_hash_num_tokens = None


# --------------------------------------------------------------------------- manager

@dataclass
class SimRequest:
    request_id: str
    token_ids: list[int]
    cache_salt: str | None = None
    num_prompt_tokens: int = 0
    num_computed_tokens: int = 0
    spec_token_ids: list[int] = field(default_factory=list)
    status: str = "WAITING"
    num_preemptions: int = 0

    def __post_init__(self) -> None:
        if self.num_prompt_tokens == 0:
            self.num_prompt_tokens = len(self.token_ids)

    @property
    def num_tokens(self) -> int:
        return len(self.token_ids)

    @property
    def num_tokens_with_spec(self) -> int:
        return len(self.token_ids) + len(self.spec_token_ids)

    def block_hashes(self, block_size: int = DEFAULT_BLOCK_SIZE) -> list[str]:
        return request_block_hashes(self.token_ids, block_size, self.cache_salt)


@dataclass
class ScheduleResult:
    request_id: str
    hit_tokens: int
    hit_block_ids: list[int]
    new_block_ids: list[int]
    block_table: list[int]
    num_computed_tokens: int
    num_scheduled_tokens: int
    num_lookahead_tokens: int
    evicted_block_ids: list[int]

    def to_row(self) -> dict:
        return {
            "request_id": self.request_id,
            "hit_tokens": self.hit_tokens,
            "hit_block_ids": self.hit_block_ids,
            "new_block_ids": self.new_block_ids,
            "block_table": self.block_table,
            "num_computed_tokens": self.num_computed_tokens,
            "num_scheduled_tokens": self.num_scheduled_tokens,
            "num_lookahead_tokens": self.num_lookahead_tokens,
            "evicted_block_ids": self.evicted_block_ids,
        }


class KVManagerSim:
    def __init__(self, num_blocks: int, block_size: int = DEFAULT_BLOCK_SIZE,
                 enable_caching: bool = True) -> None:
        if block_size < 1:
            raise ValueError(f"block_size는 1 이상이어야 합니다: {block_size}")
        self.block_size = block_size
        self.events: list[TraceEvent] = []
        self.pool = BlockPool(num_blocks, enable_caching, self.events)
        self.requests: dict[str, SimRequest] = {}
        self._req_blocks: dict[str, list[KVBlock]] = {}
        self._num_cached_block: dict[str, int] = {}
        self._slots: dict[int, dict] = {}
        self._step = 0
        self._depth = 0

    # -- 호출 순번과 event
    def _enter(self, request_id: str | None) -> None:
        if self._depth == 0:
            self._step += 1
            self.pool.step = self._step
            self.pool.current_request = request_id
        self._depth += 1

    def _leave(self) -> None:
        self._depth -= 1

    def _emit(self, kind: str, request_id: str | None, **detail: object) -> None:
        self.events.append(
            {"step": self._step, "actor": "KVManagerSim", "kind": kind,
             "request_id": request_id, "detail": detail}
        )

    # -- 요청
    def add_request(self, request_id: str, token_ids: Sequence[int], *,
                    cache_salt: str | None = None) -> SimRequest:
        """같은 ID가 이미 있으면 ValueError."""
        if request_id in self.requests:
            raise ValueError(f"요청 ID {request_id!r}가 이미 있습니다.")
        request = SimRequest(request_id, list(token_ids), cache_salt)
        self.requests[request_id] = request
        return request

    def get_computed_blocks(self, request: SimRequest) -> tuple[list[KVBlock], int]:
        """상한 (num_tokens - 1) // block_size block. 사슬에서 처음 없는 곳에서 멈춘다. touch하지 않는다."""
        self._enter(request.request_id)
        try:
            return self._lookup(request)
        finally:
            self._leave()

    def _lookup(self, request: SimRequest) -> tuple[list[KVBlock], int]:
        if not self.pool.enable_caching:
            return [], 0
        # vllm/v1/core/kv_cache_manager.py:295: 전부 적중해도 마지막 token은 다시 계산해야 logits가 나온다.
        max_hit_tokens = request.num_tokens - 1
        hit: list[KVBlock] = []
        # vllm/v1/core/single_type_kv_cache_manager.py:784-789: 적중 상한 block 수까지 사슬을 따라가다 처음 miss에서 멈춘다.
        for block_hash in request.block_hashes(self.block_size)[:max_hit_tokens // self.block_size]:
            cached = self.pool.get_cached_block(block_hash)
            if cached is None:
                break
            hit.append(cached)
        self._emit(
            "hit", request.request_id,
            hit_tokens=len(hit) * self.block_size,
            block_ids=[b.block_id for b in hit],
            max_hit_tokens=max_hit_tokens,
        )
        return hit, len(hit) * self.block_size

    def allocate_slots(self, request: SimRequest, num_new_tokens: int, *,
                       new_computed_blocks: Sequence[KVBlock] = (), num_new_computed_tokens: int = 0,
                       num_lookahead_tokens: int = 0) -> list[KVBlock] | None:
        """필요 칸 = ceil((num_computed + num_new_computed + num_new_tokens + lookahead) / block_size).

        필요 새 block + ref_cnt==0인 적중 block 수 > free면 None. 아니면 touch, 새 block 할당,
        min(num_computed + num_new_computed + num_new_tokens, num_tokens)까지의 꽉 찬 block에 hash 등록.
        """
        self._enter(request.request_id)
        try:
            return self._allocate(request, num_new_tokens, list(new_computed_blocks),
                                  num_new_computed_tokens, num_lookahead_tokens)
        finally:
            self._leave()

    def _allocate(self, request: SimRequest, num_new_tokens: int, new_computed: list[KVBlock],
                  num_new_computed_tokens: int, lookahead: int) -> list[KVBlock] | None:
        bs = self.block_size
        # vllm/v1/core/kv_cache_manager.py:479-482: 새로 계산할 것도 받아들일 적중도 없으면 오류.
        if num_new_tokens == 0 and num_new_computed_tokens == 0:
            raise ValueError("num_new_tokens가 0이고 적중 token도 0입니다: 할당할 것이 없습니다.")
        if num_new_computed_tokens != len(new_computed) * bs:
            raise ValueError(
                f"num_new_computed_tokens {num_new_computed_tokens}가 적중 block {len(new_computed)}개 x "
                f"block_size {bs} = {len(new_computed) * bs}와 다릅니다."
            )
        request_id = request.request_id
        first = request_id not in self._num_cached_block
        if not first and new_computed:
            # vllm/v1/core/single_type_kv_cache_manager.py:230-232: 이미 돌고 있는 요청은 새 적중이 없다.
            raise ValueError("이미 block을 가진 요청에는 새 적중 block을 줄 수 없습니다.")
        held = self._req_blocks.get(request_id, [])
        local_computed = request.num_computed_tokens + num_new_computed_tokens
        # vllm/v1/core/kv_cache_manager.py:542-544, single_type_kv_cache_manager.py:213: 칸 수는 올림 나눗셈.
        required = _cdiv(local_computed + num_new_tokens + lookahead, bs)
        new_needed = max(required - len(held) - len(new_computed), 0)
        # vllm/v1/core/single_type_kv_cache_manager.py:258: ref_cnt 0인 적중 block은 touch하면 free queue에서 빠지므로 free에서 센다.
        evictable = sum(1 for b in new_computed if b.ref_cnt == 0 and not b.is_null)
        free = self.pool.num_free()
        if new_needed + evictable > free:  # vllm/v1/core/kv_cache_manager.py:577-579
            self._emit("alloc_failed", request_id, requested=new_needed + evictable, free=free,
                       new_blocks=new_needed, evictable_hits=evictable)
            return None
        # 적중 block을 먼저 touch해야 아래 get_new_blocks가 방금 적중한 block을 축출하지 않는다.
        if new_computed:
            self.pool.touch(new_computed)
        new_blocks = self.pool.get_new_blocks(new_needed)
        blocks = self._req_blocks.setdefault(request_id, [])
        blocks.extend(new_computed)
        blocks.extend(new_blocks)
        self._num_cached_block.setdefault(request_id, len(new_computed))
        if self.pool.enable_caching:
            # vllm/v1/core/kv_cache_manager.py:612-615: draft처럼 확정되지 않은 token은 num_tokens로 잘라 hash하지 않는다.
            to_cache = min(local_computed + num_new_tokens, request.num_tokens)
            num_full = to_cache // bs
            done = self._num_cached_block[request_id]
            hashes = request.block_hashes(bs)
            for i in range(done, num_full):
                self.pool.cache_block(blocks[i], hashes[i], (i + 1) * bs)
            self._num_cached_block[request_id] = max(done, num_full)
        return new_blocks

    def schedule(self, request: SimRequest, num_new_tokens: int | None = None, *,
                 num_lookahead_tokens: int = 0) -> ScheduleResult | None:
        """num_computed_tokens == 0이면 적중 조회. allocate 실패면 None. 남은 수보다 크게 주면 ValueError."""
        if request.status == "FINISHED":
            raise ValueError(f"요청 {request.request_id!r}는 이미 FINISHED입니다.")
        self._enter(request.request_id)
        try:
            evicted_before = len(self.pool.evicted_ids)
            hit: list[KVBlock] = []
            hit_tokens = 0
            if request.num_computed_tokens == 0:
                hit, hit_tokens = self._lookup(request)
            remaining = request.num_tokens_with_spec - request.num_computed_tokens - hit_tokens
            if num_new_tokens is None:
                num_new_tokens = remaining
            if num_new_tokens > remaining:
                raise ValueError(f"계산할 수 있는 token은 {remaining}개인데 {num_new_tokens}개를 요청했습니다.")
            if num_new_tokens < 1:
                raise ValueError(f"이번에 계산할 token이 없습니다(남은 수 {remaining}).")
            new_blocks = self._allocate(request, num_new_tokens, hit, hit_tokens, num_lookahead_tokens)
            if new_blocks is None:
                return None
            start = request.num_computed_tokens + hit_tokens
            table = self.block_table(request)
            self._write_slots(request, table, start, num_new_tokens)
            request.status = "RUNNING"
            request.num_computed_tokens = start + num_new_tokens
            return ScheduleResult(
                request.request_id, hit_tokens, [b.block_id for b in hit],
                [b.block_id for b in new_blocks], table, request.num_computed_tokens,
                num_new_tokens, num_lookahead_tokens, list(self.pool.evicted_ids[evicted_before:]),
            )
        finally:
            self._leave()

    def _write_slots(self, request: SimRequest, table: list[int], start: int, count: int) -> None:
        """이번 step에 계산하는 position의 slot에 쓰기 표지를 남긴다. 적중 구간은 쓰지 않는다."""
        tokens = request.token_ids + request.spec_token_ids
        for pos in range(start, start + count):
            slot = slot_id(table, pos, self.block_size)
            is_draft = pos >= request.num_tokens
            new = {"request_id": request.request_id, "position": pos,
                   "token_id": tokens[pos], "is_draft": is_draft}
            old = self._slots.get(slot)
            if old is not None:
                self._emit("overwrite", request.request_id, slot=slot, old=dict(old), new=dict(new))
            if is_draft:
                self._emit("draft_write", request.request_id, slot=slot, position=pos, token_id=tokens[pos])
            self._slots[slot] = new

    def append_output(self, request: SimRequest, token_ids: Sequence[int]) -> None:
        request.token_ids.extend(token_ids)

    def free(self, request: SimRequest) -> None:
        """block을 역순으로 반납. 상태 FINISHED."""
        self._enter(request.request_id)
        try:
            self._release(request.request_id)
            request.status = "FINISHED"
        finally:
            self._leave()

    def _release(self, request_id: str) -> list[int]:
        blocks = self._req_blocks.pop(request_id, [])
        self._num_cached_block.pop(request_id, None)
        # vllm/v1/core/single_type_kv_cache_manager.py:589: 꼬리 block이 먼저 축출되도록 역순으로 반납한다.
        self.pool.free_blocks(reversed(blocks))
        return [b.block_id for b in reversed(blocks) if b.ref_cnt == 0]

    def preempt(self, request: SimRequest) -> dict:
        """역순 반납, num_computed_tokens=0, spec 비움, 상태 PREEMPTED, num_preemptions+1."""
        self._enter(request.request_id)
        try:
            freed = self._release(request.request_id)
            # vllm/v1/core/sched/scheduler.py:1589-1595: block 반납, PREEMPTED, 계산 수 0, spec 비움.
            request.status = "PREEMPTED"
            request.num_computed_tokens = 0
            request.spec_token_ids = []
            request.num_preemptions += 1
            self._emit("preempt", request.request_id, freed_block_ids=freed,
                       num_preemptions=request.num_preemptions)
            return {"request_id": request.request_id, "freed_block_ids": freed,
                    "num_preemptions": request.num_preemptions}
        finally:
            self._leave()

    def set_draft_tokens(self, request: SimRequest, token_ids: Sequence[int]) -> None:
        request.spec_token_ids = list(token_ids)

    def verify_drafts(self, request: SimRequest, generated_token_ids: Sequence[int]) -> dict:
        """num_accepted = max(len(generated)-1, 0), num_rejected = drafts - num_accepted."""
        self._enter(request.request_id)
        try:
            drafts = len(request.spec_token_ids)
            if drafts == 0:
                raise ValueError("검증할 draft token이 없습니다.")
            # vllm/v1/core/sched/scheduler.py:2118-2126: 뽑힌 token에서 1개(bonus)를 뺀 만큼이 승인이고, 거부된 만큼 계산 수를 되돌린다.
            accepted = max(len(generated_token_ids) - 1, 0)
            rejected = drafts - accepted
            before = request.num_computed_tokens
            base = request.num_tokens
            if request.num_computed_tokens > 0:
                request.num_computed_tokens -= rejected
            table = self.block_table(request)
            for i in range(accepted):
                slot = slot_id(table, base + i, self.block_size)
                mark = self._slots.get(slot)
                if mark is not None:
                    mark["is_draft"] = False
                    mark["token_id"] = generated_token_ids[i]
            request.token_ids.extend(generated_token_ids)
            request.spec_token_ids = []
            self._emit("rollback", request.request_id, num_drafts=drafts, num_accepted=accepted,
                       num_rejected=rejected, num_computed_before=before,
                       num_computed_after=request.num_computed_tokens)
            return {"num_drafts": drafts, "num_accepted": accepted, "num_rejected": rejected,
                    "num_computed_tokens": request.num_computed_tokens,
                    "num_tokens": request.num_tokens, "block_table": table}
        finally:
            self._leave()

    # -- 관찰
    def block_table(self, request: SimRequest) -> list[int]:
        return [b.block_id for b in self._req_blocks.get(request.request_id, [])]

    def slot_contents(self, slot: int) -> dict | None:
        """KV 값이 아니라 표지다."""
        mark = self._slots.get(slot)
        return dict(mark) if mark is not None else None

    def free_queue_ids(self) -> list[int]:
        return self.pool.free_queue.ids()

    def cached_block_ids(self) -> list[int]:
        return [b.block_id for b in self.pool.blocks if b.block_hash is not None]

    def ref_cnts(self) -> list[list[int]]:
        return [[b.block_id, b.ref_cnt] for b in self.pool.blocks if b.ref_cnt > 0 and not b.is_null]

    def snapshot(self) -> list[dict]:
        """view.block_grid 입력. state: null, free, cached, used, shared."""
        owners: dict[int, list[str]] = {}
        for rid, blocks in self._req_blocks.items():
            for b in blocks:
                owners.setdefault(b.block_id, []).append(rid)
        out: list[dict] = []
        for b in self.pool.blocks:
            if b.is_null:
                state = "null"
            elif b.ref_cnt == 0:
                state = "cached" if b.block_hash is not None else "free"
            else:
                state = "used" if b.ref_cnt == 1 else "shared"
            label = "+".join(owners.get(b.block_id, []))
            label = "".join(c if c.isascii() else "?" for c in label)[:8]
            out.append({"block_id": b.block_id, "state": state, "label": label,
                        "ref_cnt": b.ref_cnt, "block_hash": b.block_hash})
        return out

    @classmethod
    def replay(cls, inputs: dict) -> list[dict]:
        """reference_kv.json의 inputs 실행. ops 하나에 행 하나."""
        mgr = cls(inputs["num_blocks"], inputs.get("block_size", DEFAULT_BLOCK_SIZE))
        rows: list[dict] = []
        for op in inputs["ops"]:
            rid = op["request_id"]
            returned_none, hit_tokens, hit_ids, new_ids = False, None, None, None
            if op["op"] == "schedule":
                request = mgr.requests.get(rid) or mgr.add_request(
                    rid, op["token_ids"], cache_salt=op.get("cache_salt"))
                result = mgr.schedule(request, op.get("num_new_tokens"))
                returned_none = result is None
                if result is not None:
                    hit_tokens, hit_ids, new_ids = result.hit_tokens, result.hit_block_ids, result.new_block_ids
            elif op["op"] == "append_output":
                mgr.append_output(mgr.requests[rid], op["token_ids"])
            elif op["op"] == "free":
                mgr.free(mgr.requests[rid])
            else:
                raise ValueError(f"알 수 없는 op: {op['op']!r}")
            rows.append({
                "op": op["op"], "request_id": rid, "returned_none": returned_none,
                "hit_tokens": hit_tokens, "hit_block_ids": hit_ids, "new_block_ids": new_ids,
                "block_table": mgr.block_table(mgr.requests[rid]), "ref_cnts": mgr.ref_cnts(),
                "free_queue": mgr.free_queue_ids(), "cached_block_ids": mgr.cached_block_ids(),
            })
        return rows


# --------------------------------------------------------------------------- hybrid toy

@dataclass(frozen=True)
class GroupSpec:
    name: str
    kind: str                  # "full", "sliding_window", "mamba", "circular_buffer"
    num_layers: int = 1        # 장난감 값이다. 실제 층 수가 아니다
    window: int | None = None  # sliding_window일 때 token 수

    def __post_init__(self) -> None:
        if self.kind not in ("full", "sliding_window", "mamba", "circular_buffer"):
            raise ValueError(f"알 수 없는 group 종류: {self.kind!r}")
        if self.kind == "sliding_window" and (self.window is None or self.window < 1):
            raise ValueError(f"sliding_window group {self.name!r}에는 window >= 1이 필요합니다: {self.window}")


def get_num_skipped_tokens(spec: GroupSpec, num_computed_tokens: int) -> int:
    """attention 계산에서 빠지는 앞쪽 token 수. group 종류마다 규칙이 다르다."""
    if spec.kind == "sliding_window":
        # vllm/v1/core/single_type_kv_cache_manager.py:1166-1170: 창 앞쪽.
        return max(0, num_computed_tokens - spec.window + 1)
    if spec.kind == "mamba":
        # vllm/v1/core/single_type_kv_cache_manager.py:1954-1959: 마지막 계산 token의 state만 필요하다.
        return max(0, num_computed_tokens - 1)
    # full은 vllm/v1/core/single_type_kv_cache_manager.py:712-727, circular_buffer는 :1259-1261: 건너뛰지 않는다.
    return 0


class HybridPoolToy:
    """한 pool을 여러 group이 나눠 쓴다. block ID 하나는 한 번에 한 group만 소유한다(vllm/v1/core/kv_cache_utils.py:1631)."""

    def __init__(self, num_blocks: int, groups: list[GroupSpec], block_size: int = DEFAULT_BLOCK_SIZE) -> None:
        if len({g.name for g in groups}) != len(groups):
            raise ValueError("group 이름이 겹칩니다.")
        self.groups = list(groups)
        self.block_size = block_size
        self.pool = BlockPool(num_blocks, enable_caching=False)
        self._held: dict[tuple[str, str], list[KVBlock]] = {}
        self._owner: dict[int, str] = {}

    def _target(self, spec: GroupSpec, num_tokens: int) -> tuple[int, int]:
        """(보유 칸 수, 앞쪽 null 칸 수)."""
        if spec.kind in ("mamba", "circular_buffer"):
            return 1, 0
        total = _cdiv(num_tokens, self.block_size)
        return total, min(get_num_skipped_tokens(spec, num_tokens) // self.block_size, total)

    def allocate(self, request_id: str, num_tokens: int) -> dict[str, list[int]]:
        """이미 가진 만큼 빼고 할당해 group 이름별 새 block ID를 돌려준다. 모자라면 KVPoolExhausted."""
        plan: list[tuple[GroupSpec, list[bool]]] = []
        for spec in self.groups:
            have = len(self._held.get((request_id, spec.name), []))
            total, null_prefix = self._target(spec, num_tokens)
            plan.append((spec, [i >= null_prefix for i in range(have, total)]))
        needed = sum(sum(real) for _, real in plan)
        if needed > self.pool.num_free():
            raise KVPoolExhausted(needed, self.pool.num_free())
        out: dict[str, list[int]] = {}
        for spec, real_flags in plan:
            held = self._held.setdefault((request_id, spec.name), [])
            new_ids: list[int] = []
            for is_real in real_flags:
                if is_real:
                    block = self.pool.get_new_blocks(1)[0]
                    self._owner[block.block_id] = spec.name
                    new_ids.append(block.block_id)
                    held.append(block)
                else:
                    held.append(self.pool.null_block)  # 건너뛴 앞 칸은 null block (single_type_kv_cache_manager.py:680)
            out[spec.name] = new_ids
        return out

    def advance(self, request_id: str, num_computed_tokens: int) -> dict[str, list[int]]:
        """get_num_skipped_tokens 규칙으로 앞 block을 푼다. 푼 ID를 group별로."""
        freed: dict[str, list[int]] = {}
        for spec in self.groups:
            held = self._held.get((request_id, spec.name), [])
            skipped = get_num_skipped_tokens(spec, num_computed_tokens) // self.block_size
            # mamba는 마지막 state 칸을 남긴다. 실제 할당 방식(:1676-1780)은 모델링하지 않았다.
            limit = min(skipped, len(held) - 1) if spec.kind == "mamba" else min(skipped, len(held))
            ids: list[int] = []
            for i in range(limit):
                block = held[i]
                if block.is_null:
                    continue
                self.pool.free_blocks([block])
                self._owner.pop(block.block_id, None)
                held[i] = self.pool.null_block
                ids.append(block.block_id)
            freed[spec.name] = ids
        return freed

    def free(self, request_id: str) -> None:
        for spec in self.groups:
            held = self._held.pop((request_id, spec.name), [])
            real = [b for b in reversed(held) if not b.is_null]
            self.pool.free_blocks(real)
            for b in real:
                self._owner.pop(b.block_id, None)

    def owner_of(self, block_id: int) -> str | None:
        return self._owner.get(block_id)

    def snapshot(self) -> list[dict]:
        """block_grid 입력, label은 group 이름 전체."""
        out: list[dict] = []
        for b in self.pool.blocks:
            state = "null" if b.is_null else ("free" if b.ref_cnt == 0 else "used")
            owner = self._owner.get(b.block_id)
            out.append({"block_id": b.block_id, "state": state,
                        "label": owner or "", "ref_cnt": b.ref_cnt})
        return out


def agreed_hit(group_boundaries: dict[str, set[int]], max_length: int) -> dict:
    """모든 group이 동의하는 적중 길이. 길이는 줄기만 한다."""
    length = max_length
    history: list[dict] = []
    rounds = 0
    # vllm/v1/core/kv_cache_coordinator.py:837-905: 한 group이라도 줄이면 처음부터 다시 돌고, 안 줄면 끝낸다.
    while True:
        rounds += 1
        round_start = length
        for name, boundaries in group_boundaries.items():
            usable = [b for b in boundaries if b <= length]
            new_length = max(usable, default=0)
            history.append({"round": rounds, "group": name, "length_in": length, "length_out": new_length})
            length = new_length
        if length >= round_start:
            break
    return {"length": length, "rounds": rounds, "history": history}


def glm_like_groups() -> list[GroupSpec]:
    """KDA, MLA, indexer, tail 네 종류를 가리키는 장난감 구성. 층 수는 임의 값이다."""
    return [
        GroupSpec("kda", "mamba", num_layers=3),
        GroupSpec("mla", "full", num_layers=1),
        GroupSpec("indexer", "full", num_layers=1),
        GroupSpec("tail", "circular_buffer", num_layers=1),
    ]


def reference_rows(path: pathlib.Path | None = None) -> list[dict]:
    """data/reference_kv.json의 시나리오별 행. 파일이 없으면 FileNotFoundError. 결과를 지어내지 않는다."""
    target = path if path is not None else DATA_DIR / "reference_kv.json"
    doc = json.loads(target.read_text(encoding="utf-8"))
    if doc["status"] != "ran":
        return [{"name": "(전체)", "match": None, "status": "not_run", "reason": doc.get("reason")}]
    return [
        {"name": s["name"], "match": s["match"],
         "status": "ran" if s.get("real") is not None else "not_run", "reason": doc.get("reason")}
        for s in doc["scenarios"]
    ]
