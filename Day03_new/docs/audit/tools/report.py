"""report.py --work DIR [--table]: reads <work>/results.jsonl, the file falsify6.py appends to (last entry per row wins), and prints the totals (and with --table the table lines)."""
import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rows import ROWS, LINECAP, matches  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--work", required=True, type=Path, help="the --work folder given to falsify6.py")
parser.add_argument("--table", action="store_true", help="print the table lines as well")
args = parser.parse_args()
last = OrderedDict()
for line in (args.work / "results.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    last[r["id"]] = r


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ⏎ ")


def short(s: str, n: int) -> str:
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def tests_cell(r) -> str:
    failed = r.get("failed", [])
    groups = OrderedDict()
    for f in failed:
        groups.setdefault(f.split("[")[0], []).append(f)
    expect = r.get("expect", [])
    names = sorted(groups, key=lambda g: (0 if any(matches(e, g) for e in expect) else 1))  # stable: named ones first
    parts = []
    for g in names[:3]:
        n = len(groups[g])
        parts.append(f"`{g}`" + (f" ({n} params)" if n > 1 else ""))
    more = len(names) - 3
    cell = "; ".join(parts) + (f"; +{more} more functions" if more > 0 else "")
    return cell + f" [{len(failed)} failed]"


def decisive(r) -> tuple[str, str]:
    failed, expect = r.get("failed", []), r.get("expect", [])
    pick = next((f for f in failed if any(matches(e, f) for e in expect)), None) or next((f for f in failed if LINECAP not in f), None)
    return pick or "", short(r.get("messages", {}).get(pick, ""), 170)


rows = [last[k] for k in ROWS if k in last]
missing = [k for k in ROWS if k not in last]
lines = []
for r in rows:
    pick, msg = decisive(r)
    defect = r["label"] + (f" **{r['note']}**" if r.get("note") else "")
    lines.append(f"| {r['id']} | {esc(defect)} | {esc(tests_cell(r)) if r['kind'] != 'clean' else esc(r['summary'] + '; notebook check exit ' + str(r.get('notebook_exit')) + '; copy outputs/runs files ' + str(r['copy_runs_files']))} | {esc('`' + short(msg, 170) + '`') if msg else '-'} |")
if args.table:
    print("\n".join(lines))
survivors = [r["id"] for r in rows if not r.get("caught")]
pytest_rows = [r for r in rows if r["kind"] == "pytest"]
print("ROWS", len(rows), "missing", missing, "SURVIVORS", survivors)
print("clean summary:", last["clean"]["summary"], "| skipped:", last["clean"]["counts"].get("skipped", 0), "| notebook exit:", last["clean"].get("notebook_exit"))
print("distinct failing test ids across all rows:", len({f for r in rows for f in r.get("failed", [])}))
print("distinct failing test functions:", len({f.split('[')[0] for r in rows for f in r.get("failed", [])}))
print("rows caught only by the line-count test:", [r["id"] for r in pytest_rows if r["failed"] and not r["failed_nocap"]])
print("rows whose failing set includes the line-count test:", [r["id"] for r in pytest_rows if any(LINECAP in f for f in r["failed"])])
print("rows with collection errors:", [r["id"] for r in pytest_rows if r.get("collection_errors")])
print("rows with copy outputs/runs files>0:", [(r["id"], r["copy_runs_files"]) for r in rows if r["copy_runs_files"]])
print("rows with inject errors:", [r["id"] for r in rows if r.get("inject_error")])
print("rows with diff != 1 file:", [(r["id"], len(r["diff"])) for r in rows if r["kind"] != "clean" and len(r["diff"]) != 1])
print("tests run per pytest row (min,max):", min(sum(r["counts"].get(k, 0) for k in ("passed", "failed")) for r in pytest_rows), max(sum(r["counts"].get(k, 0) for k in ("passed", "failed")) for r in pytest_rows))
