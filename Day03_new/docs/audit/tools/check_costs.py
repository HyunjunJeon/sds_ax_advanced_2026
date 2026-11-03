#!/usr/bin/env python3
"""Check the cost tables of a Day03_new document against `tests/cost_report.py`.

usage: check_costs.py <doc> [--require all|base|exercises|none] [--root <Day03_new dir>] [--quiet]
       check_costs.py --self-test

How it works
- Runs `python -B <Day03_new>/tests/cost_report.py` (no model call, no EXA call, it only reads outputs/live) and parses its
  markdown table: one row per record (`00-Setup`, `01-Workflow-vs-Agent`, ... and the `*.exercises` records) with calls,
  seconds, input tokens, output tokens and USD.
- In <doc>, every markdown table row whose first cell is a record name (`NN-Name` or `NN-Name.exercises`, with optional
  backticks or bold) must equal that record: calls and tokens as integers (thousands commas are tolerated), seconds as the
  string with one decimal, USD as the string with four decimals. Columns are found by the table's header cell text
  ('모델 호출', '초', '입력', '출력', 'USD' or '비용'). A record row in a table whose header lacks a calls column is reported as
  SKIPPED (visible, but not an error), because a table such as `| 05 ... | RUN_OPTIONAL | 252 | 700.9 |` is not a record table.
- A row whose first cell names a record that cost_report does not list is an error.
- A `합계` row in a table that has record rows must equal the sum over exactly those records, summed from the UNROUNDED
  values (seconds with one decimal, USD with four). A `합계` row in a table without record rows is not checked.
- --require says which records must appear in the document at least once: `all` (default, all 13), `base` (the 7 without
  `.exercises`), `exercises` (the 6 with it) or `none`. A document that is not supposed to hold a cost table (for example
  docs/DESIGN.md) should be checked with `--require none` so a missing table is not misread as a defect.

Exit 0 when every checked row matches and every required record has a row; exit 1 otherwise.
No bytecode is written and nothing is written to disk by the checker itself.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

DAY03_NEW = Path(__file__).resolve().parents[3]  # tools -> audit -> docs -> Day03_new
RECORD_NAME = re.compile(r"^\d{2}[ab]?-[\w-]+?(?:\.exercises)?$")  # 03, 04, 05는 a/b로 나뉜 이름도 읽는다
COLUMNS = {
    "calls": lambda h: "모델 호출" in h or h in {"호출", "calls"},
    "seconds": lambda h: h in {"초", "seconds"} or h.startswith("초 ") or h.startswith("초("),
    "input": lambda h: "입력" in h,
    "output": lambda h: "출력" in h,
    "usd": lambda h: "USD" in h or "비용" in h,
}


def clean(cell: str) -> str:
    return re.sub(r"[`*$\s,]", "", cell)


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def load_cost_report(day03: Path):
    path = day03 / "tests" / "cost_report.py"
    spec = importlib.util.spec_from_file_location("cost_report_for_check", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def reference(day03: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """(parsed printed rows, unrounded values) per record. The two must agree; if they do not, the checker stops."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    out = subprocess.run([sys.executable, "-B", str(day03 / "tests" / "cost_report.py")], capture_output=True, text=True, env=env, check=True).stdout
    printed: dict[str, dict] = {}
    for line in out.splitlines():
        if not line.startswith("|"):
            continue
        cells = split_row(line)
        if len(cells) != 7 or not RECORD_NAME.match(cells[0]):
            continue
        name, _model, calls, seconds, tokens_in, tokens_out, cost = cells
        printed[name] = {"calls": int(calls), "seconds": seconds, "input": int(tokens_in), "output": int(tokens_out), "usd": cost}
    module = load_cost_report(day03)
    exact: dict[str, dict] = {}
    for row in module.read_rows(module.LIVE):
        entry = exact.setdefault(row["notebook"], {"calls": 0, "seconds": 0.0, "input": 0, "output": 0, "usd": 0.0, "cached": 0})
        entry["calls"] += row["calls"]
        entry["seconds"] += row["seconds"] or 0.0
        entry["input"] += row["input"]
        entry["output"] += row["output"]
        entry["cached"] += row["cached"]
        entry["usd"] += row["cost"] or 0.0
    for name, values in printed.items():
        e = exact.get(name)
        got = (e["calls"], f"{e['seconds']:.1f}", e["input"], e["output"], f"{e['usd']:.4f}") if e else None
        if got != (values["calls"], values["seconds"], values["input"], values["output"], values["usd"]):
            raise SystemExit(f"check_costs: cost_report output and read_rows disagree for {name}: {values} vs {got}")
    if set(printed) != set(exact):
        raise SystemExit(f"check_costs: record sets differ: {sorted(set(printed) ^ set(exact))}")
    return printed, exact


def expected_cells(values: dict) -> dict[str, str]:
    return {"calls": str(values["calls"]), "seconds": f"{float(values['seconds']):.1f}", "input": str(values["input"]),
            "output": str(values["output"]), "usd": f"{float(values['usd']):.4f}"}


def check_doc(text: str, printed: dict[str, dict], exact: dict[str, dict], *, require: str, doc_name: str = "doc") -> tuple[list[str], list[str], list[str], set[str]]:
    """Return (errors, skipped notes, ok notes, names found)."""
    errors: list[str] = []
    skipped: list[str] = []
    ok: list[str] = []
    found: set[str] = set()
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        start = index
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            index += 1
        block = lines[start:index]
        if len(block) < 2 or not re.match(r"^\s*\|[\s:\-|]+$", block[1]):
            continue
        header = [clean_header(c) for c in split_row(block[0])]
        columns = {key: next((i for i, h in enumerate(header) if test(h)), None) for key, test in COLUMNS.items()}
        table_names: list[str] = []
        for offset, line in enumerate(block[2:], start + 3):
            cells = split_row(line)
            first = re.sub(r"[`*]", "", cells[0]).strip()
            if RECORD_NAME.match(first):
                where = f"{doc_name}:{offset} {first}"
                if first not in printed:
                    errors.append(f"{where}: no such record in cost_report (records: {', '.join(sorted(printed))})")
                    continue
                if columns["calls"] is None:
                    skipped.append(f"{where}: table header has no 모델 호출 column, row not compared")
                    continue
                want = expected_cells(printed[first])
                bad = []
                for key, position in columns.items():
                    if position is None or position >= len(cells):
                        continue
                    cell = clean(cells[position])
                    if cell != want[key]:
                        bad.append(f"{key} doc={cells[position].strip()!r} cost_report={want[key]}")
                if bad:
                    errors.append(f"{where}: " + "; ".join(bad))
                else:
                    ok.append(where)
                found.add(first)
                table_names.append(first)
            elif "합계" in cells[0] and table_names:
                where = f"{doc_name}:{offset} 합계"
                sums = {"calls": sum(exact[n]["calls"] for n in table_names), "seconds": sum(exact[n]["seconds"] for n in table_names),
                        "input": sum(exact[n]["input"] for n in table_names), "output": sum(exact[n]["output"] for n in table_names),
                        "usd": sum(exact[n]["usd"] for n in table_names)}
                want = expected_cells(sums)
                bad = []
                for key, position in columns.items():
                    if position is None or position >= len(cells) or not clean(cells[position]):
                        continue
                    if clean(cells[position]) != want[key]:
                        bad.append(f"{key} doc={cells[position].strip()!r} sum_of_unrounded={want[key]}")
                if bad:
                    errors.append(f"{where}: " + "; ".join(bad))
                else:
                    ok.append(where)
    wanted = {"all": set(printed), "base": {n for n in printed if not n.endswith(".exercises")},
              "exercises": {n for n in printed if n.endswith(".exercises")}, "none": set()}[require]
    for name in sorted(wanted - found):
        errors.append(f"{doc_name}: no table row for required record {name} (--require {require})")
    return errors, skipped, ok, found


def clean_header(cell: str) -> str:
    return re.sub(r"[`*]", "", cell).strip()


def run(doc: Path, day03: Path, require: str, quiet: bool) -> int:
    printed, exact = reference(day03)
    errors, skipped, ok, found = check_doc(doc.read_text(encoding="utf-8"), printed, exact, require=require, doc_name=doc.name)
    for message in errors:
        print("FAIL   ", message)
    for message in skipped:
        print("SKIPPED", message)
    if not quiet:
        for message in ok:
            print("ok     ", message)
    print(f"records_in_cost_report={len(printed)} rows_ok={len(ok)} rows_failed={len(errors)} skipped={len(skipped)} "
          f"records_found_in_doc={len(found)} require={require}")
    return 1 if errors else 0


def self_test() -> None:
    printed, exact = reference(DAY03_NEW)
    base = [n for n in printed if not n.endswith(".exercises")]
    exer = [n for n in printed if n.endswith(".exercises")]
    assert len(base) == 10 and len(exer) == 9, (base, exer)  # 03~05는 a/b, 켠 실행도 01~06(9개) 모두 있음

    def table(names: list[str], total: bool = True, commas: bool = False) -> str:
        head = "| 노트북 | 모델 호출 | 초 | 입력 토큰 | 출력 토큰 | 모델 비용(USD) |\n|---|---:|---:|---:|---:|---:|\n"
        rows = ""
        for n in names:
            w = expected_cells(printed[n])
            tin = f"{int(w['input']):,}" if commas else w["input"]
            rows += f"| {n} | {w['calls']} | {w['seconds']} | {tin} | {w['output']} | {w['usd']} |\n"
        if total:
            w = expected_cells({k: sum(exact[n][k] for n in names) for k in ("calls", "seconds", "input", "output", "usd")})
            rows += f"| **합계** | {w['calls']} | {w['seconds']} | {w['input']} | {w['output']} | **{w['usd']}** |\n"
        return head + rows

    def verdict(text: str, require: str) -> list[str]:
        return check_doc(text, printed, exact, require=require)[0]

    good = table(base)
    assert verdict(good, "base") == [], verdict(good, "base")
    assert verdict(table(base, commas=True), "base") == [], "thousands commas are tolerated"
    assert verdict(good + "\n" + table(exer), "all") == []
    # a wrong row fails, naming the column
    first = base[1]
    wrong_calls = good.replace(f"| {first} | {printed[first]['calls']} |", f"| {first} | {printed[first]['calls'] + 1} |")
    errors = verdict(wrong_calls, "base")
    assert any(first in e and "calls" in e for e in errors), errors
    wrong_usd = good.replace(printed[first]["usd"], "0.0001", 1)
    assert any("usd" in e for e in verdict(wrong_usd, "base")), verdict(wrong_usd, "base")
    wrong_sec = good.replace(printed[first]["seconds"], "1.0", 1)
    assert any("seconds" in e for e in verdict(wrong_sec, "base"))
    wrong_tokens = good.replace(str(printed[first]["output"]), "1", 1)
    assert any("output" in e for e in verdict(wrong_tokens, "base"))
    # a wrong total fails
    bad_total = good.replace(f"**{expected_cells({k: sum(exact[n][k] for n in base) for k in ('calls', 'seconds', 'input', 'output', 'usd')})['usd']}**", "**0.0001**")
    assert any("합계" in e for e in verdict(bad_total, "base")), verdict(bad_total, "base")
    # a missing record fails when it is required, passes with --require none
    without = "\n".join(l for l in good.splitlines() if not l.startswith(f"| {base[0]} "))
    assert any(base[0] in e and "required" in e for e in verdict(without, "base"))
    assert not any("required" in e for e in verdict(without, "none"))
    assert any("required" in e for e in verdict(good, "exercises"))
    # an unknown record name is an error; non-record tables are ignored; a record row in a non-cost table is skipped, not compared
    unknown = good + "| 07-Nope | 1 | 1.0 | 1 | 1 | 0.0001 |\n"
    assert any("no such record" in e for e in verdict(unknown, "base"))
    switches = "| 노트북 | 켜는 것 | 더해진 모델 호출 |\n|---|---|---:|\n| 01 | RUN_EXERCISE | 6 |\n"
    assert verdict(switches, "none") == []
    _, skipped, _, _ = check_doc("| 노트북 | 켜는 것 | 초 |\n|---|---|---:|\n| 05b-Measure-Fast-Compare | RUN_OPTIONAL | 700.9 |\n", printed, exact, require="none")
    assert len(skipped) == 1
    print("self-test ok")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("doc", nargs="?")
    parser.add_argument("--require", choices=["all", "base", "exercises", "none"], default="all")
    parser.add_argument("--root", help="the Day03_new directory (default: the Day03_new that holds this script)")
    parser.add_argument("--quiet", action="store_true", help="do not print the ok rows")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if not args.doc:
        parser.error("a document is required")
    root = Path(args.root) if args.root else DAY03_NEW
    return run(Path(args.doc).resolve(), root.resolve(), args.require, args.quiet)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
