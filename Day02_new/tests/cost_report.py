"""outputs/live/*.usage.jsonl을 읽어 노트북별 비용을 Markdown 표로 출력한다.

실행: python tests/cost_report.py                  노트북별 표
      python tests/cost_report.py --cells <stem>   한 노트북의 셀별 비용(보고서 JSON의 usage_lines 범위 사용)
      python tests/cost_report.py --check-docs     README.md·AGENTS.md의 비용 표가 이 표와 다르면 불일치를 찍고 1로 끝남

각 줄에 cost가 있으면 그 값을 쓰고, 없으면 기록된 모델의 단가로 계산한다. 표에 없는 모델은 '단가 미확인'으로 두고 합계를 부분 합계로 표시한다.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

DAY02_NEW = Path(__file__).resolve().parents[1]
LIVE = DAY02_NEW / "outputs" / "live"

# 100만 토큰당 USD: (입력, 출력, 캐시 읽기, 캐시 쓰기). 출처: Anthropic first-party API rates as of 2026-10
PRICES: dict[str, tuple[float, float, float | None, float | None]] = {
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-haiku-5-5": (0.10, 0.50, None, None),  # 캐시 단가 미지정
}
# 1시간 TTL 캐시 쓰기 단가(100만 토큰당 USD). 5분 TTL 쓰기는 위 표의 네 번째 값이다.
# Jev(모델 id가 jev-로 시작): 입력 10억 토큰당 USD 42. 출처: https://typesafe.ai/ (2026-11-01 확인).
# 공식 페이지에는 출력 단가가 없다. 2차 출처 https://www.eesel.ai/blog/typesafe-jev-pricing 은 출력이 무료라고 하므로
# 출력은 0으로 계산한다. 이 0은 공식 값이 아니라 2차 출처에 기댄 가정이다(보고서 주석에도 적는다).
JEV_PREFIX = "jev-"
JEV_INPUT_PER_BILLION = 42.0
JEV_NOTE = ("Jev(jev-*)는 입력 10억 토큰당 $42(출처: https://typesafe.ai/, 2026-11-01)로 계산했다. 공식 페이지에 출력 단가가 없고 "
            "2차 출처(https://www.eesel.ai/blog/typesafe-jev-pricing)가 출력 무료라고 하므로 출력은 0으로 둔 가정이다.")
WRITE_1H_PRICES = {"claude-sonnet-5-5": 4.00, "claude-opus-5-5": 8.00}
OPTIONAL = "optional"  # 이 낱말이 stem에 든 기록은 수업 합계에서 빼고 따로 보인다.
UNKNOWN = "단가 미확인"
PER_TOKENS = 1_000_000


def cost_usd(model: str, input_tokens: int, output_tokens: int, cache_read_tokens: int,
             cache_write_tokens: int = 0, cache_write_1h_tokens: int = 0) -> float | None:
    """기록된 입력 토큰은 캐시 읽기와 캐시 쓰기를 포함한다. 둘은 각자 단가로, 나머지만 입력 단가로 계산한다.

    cache_write_tokens는 1시간 TTL 몫(cache_write_1h_tokens)을 포함한 전체다. 5분 몫은 빼서 구한다.
    """
    if model.startswith(JEV_PREFIX):
        return input_tokens * JEV_INPUT_PER_BILLION / 1_000_000_000
    price = PRICES.get(model)
    if price is None:
        return None
    input_price, output_price, read_price, write_price = price
    one_hour_price = WRITE_1H_PRICES.get(model)
    if (cache_read_tokens and read_price is None) or (cache_write_tokens and write_price is None) \
            or (cache_write_1h_tokens and one_hour_price is None):
        return None
    uncached = input_tokens - cache_read_tokens - cache_write_tokens
    five_minutes = cache_write_tokens - cache_write_1h_tokens
    cache_cost = (cache_read_tokens * (read_price or 0.0) + five_minutes * (write_price or 0.0)
                  + cache_write_1h_tokens * (one_hour_price or 0.0))
    return (uncached * input_price + output_tokens * output_price + cache_cost) / PER_TOKENS


def is_priced(model: str) -> bool:
    return model in PRICES or model.startswith(JEV_PREFIX)


def read_rows(live: Path) -> list[dict]:
    rows = []
    for usage in sorted(live.glob("*.usage.jsonl")):
        stem = usage.name.removesuffix(".usage.jsonl")
        totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])
        # 공급자가 비용(cost)을 알려 준 줄은 그 값을 쓰고, 나머지 줄만 단가표로 계산한다.
        unreported: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0, 0, 0])  # 호출, 입력, 출력, 읽기, 쓰기, 1시간 쓰기
        reported: dict[str, float] = defaultdict(float)
        for line in usage.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            model = entry.get("model") or "(기록 없음)"
            bucket = totals[model]
            bucket[0] += 1
            bucket[1] += entry.get("input_tokens", 0)
            bucket[2] += entry.get("output_tokens", 0)
            bucket[3] += entry.get("cache_read_tokens", 0)
            bucket[4] += entry.get("cache_write_tokens", 0)
            bucket[5] += "cache_write_tokens" not in entry  # 필드 도입 전 줄: 0으로 센다
            bucket[6] += entry.get("cache_write_1h_tokens", 0)
            if entry.get("cost") is not None:
                reported[model] += entry["cost"]
                continue
            rest = unreported[model]
            for position, value in enumerate((1, entry.get("input_tokens", 0), entry.get("output_tokens", 0),
                                              entry.get("cache_read_tokens", 0), entry.get("cache_write_tokens", 0),
                                              entry.get("cache_write_1h_tokens", 0))):
                rest[position] += value
        record = live / f"{stem}.json"
        seconds = json.loads(record.read_text(encoding="utf-8")).get("total_seconds") if record.exists() else None
        for position, (model, (calls, tokens_in, tokens_out, cached, written, legacy, one_hour)) in enumerate(sorted(totals.items())):
            rest = unreported[model]
            priced = cost_usd(model, *rest[1:]) if rest[0] else 0.0
            rows.append({"notebook": stem, "model": model, "calls": calls, "input": tokens_in, "output": tokens_out,
                         "cached": cached, "written": written, "written_1h": one_hour, "legacy_lines": legacy,
                         "cost": None if priced is None else reported[model] + priced,
                         "unpriced": rest[0] if not is_priced(model) else 0,  # 비용도 단가도 없는 호출 줄 수
                         "seconds": seconds if position == 0 else None})
    return rows


def render(rows: list[dict]) -> str:
    lines = ["| 노트북 | 모델 | 모델 호출 | 초 | 입력 토큰 | 출력 토큰 | 비용(USD) |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        seconds = "" if row["seconds"] is None else f"{row['seconds']:.1f}"
        cost = UNKNOWN if row["cost"] is None else f"{row['cost']:.4f}"
        lines.append(f"| {row['notebook']} | {row['model']} | {row['calls']} | {seconds} | {row['input']} | "
                     f"{row['output']} | {cost} |")
    class_rows = [row for row in rows if OPTIONAL not in row["notebook"]]
    optional_rows = [row for row in rows if OPTIONAL in row["notebook"]]
    lines.append(_total_row("**합계**", class_rows))
    if optional_rows:
        lines.append(_total_row("**선택 측정** (수업 합계에서 제외)", optional_rows))
    price_lines = [f"- {model}: 입력 ${i:g}, 출력 ${o:g}, 캐시 읽기 {_price(r)}, 캐시 쓰기 {_price(w)}"
                   for model, (i, o, r, w) in PRICES.items()]
    price_lines += [f"- {model}: 1시간 TTL 캐시 쓰기 ${p:g}" for model, p in WRITE_1H_PRICES.items()]
    note = ("주: 기록된 입력 토큰은 캐시 읽기와 캐시 쓰기를 포함하므로 각각 캐시 단가로, 나머지는 입력 단가로 계산했다 "
            "(캐시 쓰기 토큰 합계 cache_write: " + str(sum(r["written"] for r in rows)) +
            ", 그중 1시간 TTL: " + str(sum(r["written_1h"] for r in rows)) + ").")
    unpriced = sum(r["unpriced"] for r in rows)
    if unpriced:
        note += f" unpriced: 비용도 단가도 없는 호출 {unpriced}줄은 0이 아니라 비용 미확인이며 합계에서 빠졌다."
    if any(r["model"].startswith(JEV_PREFIX) for r in rows):
        note += " " + JEV_NOTE
    legacy = sum(r["legacy_lines"] for r in rows)
    if legacy:
        note += f" 캐시 쓰기 필드가 없는 예전 기록 {legacy}줄은 0으로 계산했으므로 비용이 실제보다 적게 나왔을 수 있다."
    return "\n".join([*lines, "", "단가(100만 토큰당, 출처: Anthropic first-party API rates as of 2026-10)", *price_lines, "", note])


def _total_row(label: str, rows: list[dict]) -> str:
    known = sum(row["cost"] for row in rows if row["cost"] is not None)
    total = f"{known:.4f} (부분 합계: {UNKNOWN} 행 제외)" if any(row["cost"] is None for row in rows) else f"{known:.4f}"
    return (f"| {label} | | {sum(r['calls'] for r in rows)} | {sum(r['seconds'] or 0 for r in rows):.1f} | "
            f"{sum(r['input'] for r in rows)} | {sum(r['output'] for r in rows)} | **{total}** |")


def _price(value: float | None) -> str:
    return UNKNOWN if value is None else f"${value:g}"


def cell_costs(live: Path, stem: str) -> list[dict]:
    """보고서 JSON의 cells[].usage_lines 범위로 사용량 줄을 셀에 나눠 셀별 호출·토큰·비용을 낸다."""
    record = live / f"{stem}.json"
    usage = live / f"{stem}.usage.jsonl"
    if not record.exists() or not usage.exists():
        raise FileNotFoundError(f"{stem}.json 또는 {stem}.usage.jsonl이 없습니다")
    lines = usage.read_text(encoding="utf-8").splitlines()
    result = []
    for cell in json.loads(record.read_text(encoding="utf-8"))["cells"]:
        if "usage_lines" not in cell:
            raise ValueError(f"셀 {cell['index']}에 usage_lines가 없습니다: 셀 귀속 도입 전 보고서입니다")
        start, end = cell["usage_lines"]
        entries = [json.loads(line) for line in lines[start:end] if line.strip()]
        costs = [_entry_cost(entry) for entry in entries]
        result.append({"cell": cell["index"], "calls": len(entries),
                       "input": sum(e.get("input_tokens", 0) for e in entries),
                       "output": sum(e.get("output_tokens", 0) for e in entries),
                       "cost": sum(c for c in costs if c is not None), "unpriced": sum(c is None for c in costs)})
    return result


def _entry_cost(entry: dict) -> float | None:
    if entry.get("cost") is not None:
        return entry["cost"]
    return cost_usd(entry.get("model") or "(기록 없음)", entry.get("input_tokens", 0), entry.get("output_tokens", 0),
                    entry.get("cache_read_tokens", 0), entry.get("cache_write_tokens", 0),
                    entry.get("cache_write_1h_tokens", 0))


def render_cells(stem: str, cells: list[dict]) -> str:
    lines = [f"셀별 비용: {stem}", "", "| 셀 | 모델 호출 | 입력 토큰 | 출력 토큰 | 비용(USD) | 단가 미확인 줄 |", "|---:|---:|---:|---:|---:|---:|"]
    lines += [f"| {c['cell']} | {c['calls']} | {c['input']} | {c['output']} | {c['cost']:.4f} | {c['unpriced']} |" for c in cells]
    lines.append(f"| **합계** | {sum(c['calls'] for c in cells)} | {sum(c['input'] for c in cells)} | "
                 f"{sum(c['output'] for c in cells)} | **{sum(c['cost'] for c in cells):.4f}** | {sum(c['unpriced'] for c in cells)} |")
    return "\n".join(lines)


TABLE_HEADER = "| 노트북 | 모델 | 모델 호출 |"


def table_rows(markdown: str) -> dict[tuple[str, str], tuple[str, ...]]:
    """노트북 비용 표(머리줄 `| 노트북 | 모델 | 모델 호출 |`)의 데이터 행을 (노트북, 모델) 키로 읽는다."""
    rows: dict[tuple[str, str], tuple[str, ...]] = {}
    inside = False
    for line in markdown.splitlines():
        if line.startswith(TABLE_HEADER):
            inside = True
            continue
        if not inside:
            continue
        if not line.startswith("|"):
            break
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if set(cells[0]) <= set("-: "):
            continue
        rows[(cells[0], cells[1])] = cells
    return rows


def check_docs(rows: list[dict], documents: list[Path]) -> list[str]:
    """문서의 비용 표가 현재 기록에서 계산한 표와 다른 곳을 문장으로 돌려준다. 같으면 빈 목록."""
    expected = table_rows(render(rows))
    mismatches = []
    for document in documents:
        actual = table_rows(document.read_text(encoding="utf-8"))
        for key, cells in expected.items():
            label = " / ".join(part for part in key if part)
            if key not in actual:
                mismatches.append(f"{document.name}: '{label}' 행이 없습니다")
            elif actual[key] != cells:
                mismatches.append(f"{document.name}: '{label}' 행이 다릅니다. 문서 {' | '.join(actual[key])} / 기록 {' | '.join(cells)}")
        mismatches += [f"{document.name}: '{' / '.join(p for p in key if p)}' 행은 기록에 없습니다" for key in actual if key not in expected]
    return mismatches


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["--cells"] and len(args) == 2:
        try:
            print(render_cells(args[1], cell_costs(LIVE, args[1])))
        except (OSError, ValueError, KeyError) as error:
            print(f"셀별 비용을 낼 수 없습니다: {error}", file=sys.stderr)
            return 1
        return 0
    if args == ["--check-docs"]:
        mismatches = check_docs(read_rows(LIVE), [DAY02_NEW / "README.md", DAY02_NEW / "AGENTS.md"])
        print("\n".join(mismatches) if mismatches else "문서 비용 표가 기록과 같습니다")
        return 1 if mismatches else 0
    if args:
        print("사용법: cost_report.py [--cells <stem> | --check-docs]", file=sys.stderr)
        return 2
    rows = read_rows(LIVE)
    if not rows:
        print(f"{LIVE}에 *.usage.jsonl이 없습니다.", file=sys.stderr)
        return 1
    print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
