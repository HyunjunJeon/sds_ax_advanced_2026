"""outputs/live/*.usage.jsonl을 읽어 노트북별 비용을 Markdown 표로 출력한다. 실행: python tests/cost_report.py

단가는 각 줄에 기록된 모델로 찾는다. 표에 없는 모델은 '단가 미확인'으로 두고 합계를 부분 합계로 표시한다.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1] / "outputs" / "live"

# 100만 토큰당 USD: (입력, 출력, 캐시 읽기). 출처: Anthropic first-party API rates as of 2026-10
PRICES: dict[str, tuple[float, float, float | None]] = {
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, None),  # 캐시 읽기 단가 미지정
}
UNKNOWN = "단가 미확인"
PER_TOKENS = 1_000_000


def cost_usd(model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int) -> float | None:
    """입력 토큰에는 캐시 읽기가 포함되어 기록된다. 캐시 읽기는 따로 계산하고 나머지를 입력 단가로 계산한다."""
    price = PRICES.get(model)
    if price is None:
        return None
    input_price, output_price, cache_price = price
    if cache_read_tokens and cache_price is None:
        return None
    uncached = input_tokens - cache_read_tokens
    cache_cost = cache_read_tokens * cache_price if cache_price is not None else 0.0
    return (uncached * input_price + output_tokens * output_price + cache_cost) / PER_TOKENS


def read_rows(live: Path) -> list[dict]:
    rows = []
    for usage in sorted(live.glob("*.usage.jsonl")):
        stem = usage.name.removesuffix(".usage.jsonl")
        totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
        for line in usage.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            bucket = totals[entry.get("model") or "(기록 없음)"]
            bucket[0] += 1
            bucket[1] += entry.get("input_tokens", 0)
            bucket[2] += entry.get("output_tokens", 0)
            bucket[3] += entry.get("cache_read_tokens", 0)
        record = live / f"{stem}.json"
        seconds = json.loads(record.read_text(encoding="utf-8")).get("total_seconds") if record.exists() else None
        for position, (model, (calls, tokens_in, tokens_out, cached)) in enumerate(sorted(totals.items())):
            rows.append({"notebook": stem, "model": model, "calls": calls, "input": tokens_in, "output": tokens_out,
                         "cached": cached, "cost": cost_usd(model, tokens_in, tokens_out, cached),
                         "seconds": seconds if position == 0 else None})
    return rows


def render(rows: list[dict]) -> str:
    lines = ["| 노트북 | 모델 | 모델 호출 | 초 | 입력 토큰 | 출력 토큰 | 비용(USD) |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        seconds = "" if row["seconds"] is None else f"{row['seconds']:.1f}"
        cost = UNKNOWN if row["cost"] is None else f"{row['cost']:.4f}"
        lines.append(f"| {row['notebook']} | {row['model']} | {row['calls']} | {seconds} | {row['input']} | "
                     f"{row['output']} | {cost} |")
    known = sum(row["cost"] for row in rows if row["cost"] is not None)
    partial = any(row["cost"] is None for row in rows)
    total = f"{known:.4f} (부분 합계: {UNKNOWN} 행 제외)" if partial else f"{known:.4f}"
    lines.append(f"| **합계** | | {sum(r['calls'] for r in rows)} | {sum(r['seconds'] or 0 for r in rows):.1f} | "
                 f"{sum(r['input'] for r in rows)} | {sum(r['output'] for r in rows)} | **{total}** |")
    price_lines = [f"- {model}: 입력 ${i:g}, 출력 ${o:g}, 캐시 읽기 {'$' + format(c, 'g') if c is not None else UNKNOWN}"
                   for model, (i, o, c) in PRICES.items()]
    return "\n".join([*lines, "", "단가(100만 토큰당, 출처: Anthropic first-party API rates as of 2026-10)", *price_lines, "",
                      "주: 기록된 입력 토큰은 캐시 읽기를 포함하므로 캐시 읽기분은 캐시 단가로, 나머지는 입력 단가로 계산했다. "
                      "캐시 쓰기 단가는 모델링하지 않았다(기록에 캐시 쓰기 토큰이 없다)."])


def main() -> int:
    rows = read_rows(LIVE)
    if not rows:
        print(f"{LIVE}에 *.usage.jsonl이 없습니다.", file=sys.stderr)
        return 1
    print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
