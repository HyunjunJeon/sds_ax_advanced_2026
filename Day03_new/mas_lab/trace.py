"""구조를 비교하기 위한 측정 장치. 누가 언제 일했고 무엇이 얼마나 들었는지를 같은 칸으로 낸다."""
from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler


class ModelMeter(BaseCallbackHandler):
    """config의 callbacks로 넘기면 subagent 호출까지 잡는다. 모델 응답은 바꾸지 않는다."""

    def __init__(self):
        self.lock, self.calls, self._open = threading.Lock(), [], {}

    def on_chat_model_start(self, serialized, messages, *, run_id: UUID, **kwargs) -> None:
        tools = kwargs.get("invocation_params", {}).get("tools", []) or []
        call = {"start": time.perf_counter(), "end": None, "model": None,
                "tools": [t.get("name") or t.get("function", {}).get("name") for t in tools],
                "messages": len(messages[0]), "input_chars": sum(len(str(m.content)) for m in messages[0]),
                "input_tokens": None, "output_tokens": None, "cache_read_tokens": None}
        with self.lock:
            self.calls.append(call)
            self._open[run_id] = call

    def on_llm_end(self, response, *, run_id: UUID, **kwargs) -> None:
        message = response.generations[0][0].message
        usage = message.usage_metadata or {}
        with self.lock:
            call = self._open.pop(run_id, None)
            if call is not None:
                call.update(end=time.perf_counter(), model=message.response_metadata.get("model"),
                            input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"),
                            cache_read_tokens=usage.get("input_token_details", {}).get("cache_read"))

    def on_llm_error(self, error, *, run_id: UUID, **kwargs) -> None:
        with self.lock:
            call = self._open.pop(run_id, None)
            if call is not None:
                call.update(end=time.perf_counter(), error=type(error).__name__)

    def totals(self) -> dict:
        """usage가 없는 호출은 0으로 세지 않고 usage_missing으로 센다."""
        with self.lock:
            calls = list(self.calls)
        seen = [c for c in calls if c["input_tokens"] is not None]
        return {"model_calls": len(calls), "input_tokens": sum(c["input_tokens"] for c in seen) if seen else None,
                "output_tokens": sum(c["output_tokens"] or 0 for c in seen) if seen else None,
                "cache_read_tokens": sum(c["cache_read_tokens"] or 0 for c in seen) if seen else None,
                "usage_missing": len(calls) - len(seen), "model_seconds": round(sum(
                    c["end"] - c["start"] for c in calls if c["end"]), 3)}


class Trace:
    """스레드 안전한 사건과 구간 기록. 노드와 도구가 남긴다."""

    def __init__(self, label: str = ""):
        self.label, self.lock, self.events, self.spans = label, threading.Lock(), [], []
        self.started = time.perf_counter()

    def event(self, kind: str, actor: str, **details) -> None:
        with self.lock:
            self.events.append({"at": round(time.perf_counter() - self.started, 3), "kind": kind,
                                "actor": actor, **details})

    @contextmanager
    def span(self, actor: str, kind: str = "work") -> Iterator[None]:
        start = time.perf_counter() - self.started
        try:
            yield
        finally:
            with self.lock:
                self.spans.append({"actor": actor, "kind": kind, "start": round(start, 3),
                                   "end": round(time.perf_counter() - self.started, 3)})


def overlap_seconds(spans: list[dict]) -> float:
    """둘 이상이 동시에 도는 시간. 0이면 겹침이 없었다는 뜻이다."""
    points = sorted([(s["start"], 1) for s in spans] + [(s["end"], -1) for s in spans], key=lambda p: (p[0], p[1]))
    active, last, total = 0, None, 0.0
    for at, delta in points:
        if active >= 2:
            total += at - last
        active, last = active + delta, at
    return round(total, 3)


def longest_path(durations: dict[str, float], depends_on: dict[str, list[str]]) -> float:
    """의존을 지키며 무한히 병렬로 돌렸을 때의 최소 시간."""
    memo: dict[str, float] = {}

    def finish(name: str) -> float:
        if name not in memo:
            memo[name] = durations[name] + max((finish(d) for d in depends_on.get(name, [])), default=0.0)
        return memo[name]

    return round(max(map(finish, durations), default=0.0), 3)


def timeline(spans: list[dict], width: int = 48) -> str:
    """구간을 문자 막대로 그린다. 세로로 겹치는 칸이 동시 실행이다."""
    if not spans:
        return "(구간 없음)"
    first, last = min(s["start"] for s in spans), max(s["end"] for s in spans)
    scale = width / max(last - first, 1e-9)
    label = max(len(s["actor"]) for s in spans)
    lines = []
    for s in sorted(spans, key=lambda s: s["start"]):
        left = int((s["start"] - first) * scale)
        lines.append(f"{s['actor']:<{label}} |{' ' * left}{'#' * max(1, int((s['end'] - s['start']) * scale))}"
                     f"  {s['end'] - s['start']:.2f}s")
    return "\n".join(lines)
