"""build_notes6.py --work DIR --snapshot DIR --record DIR --prefix NAME --prev-rows FILE --out FILE: writes the falsify 7 notes from <work>/results.jsonl (last entry per row; every `clean` entry counts as a clean run) and the record files.

--work       the folder given to falsify6.py (results.jsonl and one folder per row)
--snapshot   the Day02_new/rag_lab snapshot given to falsify6.py
--record     the folder of the run's own record files; their names start with --prefix (for example falsify-7):
             <prefix>-realtree-before.txt and <prefix>-realtree-after.txt (hashtree.sh output before the first and after the last row),
             <prefix>-start-marker (an empty file touched before the first row and after the last edit of the tools), <prefix>-snapshot-hash-start.txt (the snapshot's content hash at the start),
             <prefix>-prereg.md (the pre-registration, written before the start marker), <prefix>-scratch/collected-ids.txt (pytest --collect-only ids of the clean copy),
             <prefix>-scratch/dryrun.out (the output of dryrun.py); the secret scan also reads the other plain files of this folder and writes a control file into <prefix>-scratch
--prefix     the name those record files start with
--prev-rows  the rows.py of the run before (falsify 6), to list which rows were adapted or are new
--out        the notes file to write
Reads the `.env` files of this repository and the key-like environment variables IN PROCESS to look for their values in the run's files (values are never printed). Do not run it where that is not allowed.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from falsify6 import BASELINE  # noqa: E402
from rows import ROWS, LINECAP, matches  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
for flag in ("--work", "--snapshot", "--record", "--prev-rows", "--out"):
    parser.add_argument(flag, required=True, type=Path)
parser.add_argument("--prefix", required=True)
args = parser.parse_args()
WORK, SNAP, P3, NOTES, PFX = args.work.resolve(), args.snapshot.resolve(), args.record.resolve(), args.out.resolve(), args.prefix
REAL = Path(__file__).resolve().parents[4]  # tools -> audit -> docs -> Day03_new -> repository

spec = importlib.util.spec_from_file_location("rows_prev", args.prev_rows)
rows_prev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rows_prev)

last, clean_runs = OrderedDict(), []
for line in (WORK / "results.jsonl").read_text(encoding="utf-8").splitlines():
    r = json.loads(line)
    last[r["id"]] = r
    if r["id"] == "clean":
        clean_runs.append(r)


def esc(s):
    return s.replace("|", "\\|").replace("\n", " ⏎ ")


def short(s, n):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def suite_size(r):
    c = r.get("counts", {})
    return sum(c.get(k, 0) for k in ("passed", "failed", "skipped", "xfailed", "xpassed")) + c.get("error", 0) + c.get("errors", 0)


def statement(rid: str, test_id: str) -> str:
    name = test_id.split("::")[-1].split("[")[0]
    take = False
    for line in (WORK / rid / "out.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^_{3,} (.+?) _{3,}$", line)
        if m:
            take = m.group(1).split("[")[0] == name
            continue
        if take and line.startswith(">"):
            return short(line[1:].strip(), 110)
    return ""


def tests_cell(r):
    failed, expect = r.get("failed", []), r.get("expect", [])
    groups = OrderedDict()
    for f in failed:
        groups.setdefault(f.split("[")[0], []).append(f)
    names = sorted(groups, key=lambda g: 0 if any(matches(e, g) or matches(e.split("&&")[0], g) for e in expect) else 1)
    parts = []
    for g in names[:3]:
        n = len(groups[g])
        one = groups[g][0]
        param = one[one.index("["):] if n == 1 and "[" in one and len(one) - one.index("[") <= 40 else ""
        parts.append(f"`{g.split('::')[-1]}{param}`" + (f" ({n} params)" if n > 1 else ""))
    more = len(names) - 3
    return "; ".join(parts) + (f"; +{more} more test functions" if more > 0 else "") + f" [{len(failed)} failed of {suite_size(r)}]"


def decisive(r):
    failed, expect = r.get("failed", []), r.get("expect", [])
    pick = next((f for f in failed if any(matches(e, f) for e in expect)), None) or next((f for f in failed if LINECAP not in f), None)
    if not pick:
        return ""
    msg = short(r["messages"].get(pick, ""), 150)
    if r["kind"] == "pytest" and len(msg) < 60:
        stmt = statement(r["id"], pick)
        if stmt:
            msg += f"  [at `{stmt}`]"
    if r["copy_runs_files"] and r["id"] in ("t15", "b10"):
        msg += f"; files written in the COPY's outputs/runs: {r['copy_runs_files']} (0 in every row with the redirect intact)"
    if r["id"] == "11":
        msg += "; second test `test_blocked_query_never_reaches_the_network`: `'error' == 'blocked'` (the tool answered status `error`, which it gives to an httpx.HTTPError: the fixture's fake key `test` let the query pass the injected check, `client.searches` became 1 before the POST, as `ExaClient.search` counts first, and the call failed at the dead proxy)"
    return msg


def code_lines(path):
    return sum(bool(l.strip()) for l in path.read_text(encoding="utf-8").splitlines())


def secret_values():
    vals = {}
    for k, v in os.environ.items():
        if re.search(r"KEY|TOKEN|SECRET", k) and len(v) >= 8:
            vals[f"env:{k}"] = v.encode()
    for env in [REAL / ".env", REAL / "Day03_new" / ".env", REAL / "Day02_new" / ".env"]:
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.match(r"\s*([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$", line)
                if m and re.search(r"KEY|TOKEN|SECRET", m.group(1)) and len(m.group(2).strip("'\"")) >= 8:
                    vals[f"{env.parent.name}/.env:{m.group(1)}"] = m.group(2).strip("'\"").encode()
    return vals


def secret_scan(extra_top=()):
    """Values are matched as bytes and never printed. Copies carry data/gold.jsonl as a verbatim rsync copy of the real file; it is excluded from the byte scan
    so that this node never opens the answer key, even as bytes (a verbatim copy of the real file cannot hold a value generated here)."""
    vals = secret_values()
    own = [p for root in (WORK, Path(__file__).parent, SNAP) for p in root.rglob("*") if p.is_file() and not (p.name == "gold.jsonl" and p.parent.name == "data")]
    top = [p for p in P3.glob("*") if p.is_file() and p.name != NOTES.name] + [p for p in extra_top]
    own_hits = [str(p) for p in own if any(v in p.read_bytes() for v in vals.values())]
    top_hits = [str(p) for p in top if any(v in p.read_bytes() for v in vals.values())]
    control = P3 / f"{PFX}-scratch" / "scan-control.bin"  # positive control with a synthetic value: the same walk and the same byte match must find a planted value
    control.write_bytes(b"x" + b"SCAN-CONTROL-VALUE-0123456789" + b"y")
    try:
        found = any(b"SCAN-CONTROL-VALUE-0123456789" in p.read_bytes() for p in P3.joinpath(f"{PFX}-scratch").rglob("*") if p.is_file())
    finally:
        control.unlink()
    return len(vals), len(own), len(own_hits), len(top), len(top_hits), found


def snapshot_hash():
    h = subprocess.run("find . -type f | LC_ALL=C sort | while read -r f; do shasum -a 256 \"$f\"; done | shasum -a 256 | cut -c1-64", shell=True, cwd=SNAP, capture_output=True, text=True).stdout.strip()
    return h


def live_vs_snapshot():
    out = subprocess.run(["diff", "-rq", "-x", "__pycache__", str(REAL / "Day02_new" / "rag_lab"), str(SNAP)], capture_output=True, text=True).stdout.splitlines()
    return sorted(l.split(" and ")[0].replace("Files ", "").rsplit("/", 1)[-1] for l in out if l.startswith("Files "))


def read_hash(path):
    return path.read_text(encoding="utf-8").strip().splitlines()


def newer_than_marker():
    flt = ["!", "-path", "*/outputs/*", "!", "-path", "*/__pycache__/*", "!", "-name", "*.pyc", "!", "-path", "*/.ipynb_checkpoints/*", "!", "-path", "*/.ruff_cache/*"]
    d3 = subprocess.run(["find", "Day03_new", "-newer", str(P3 / f"{PFX}-start-marker"), "-type", "f", *flt], cwd=REAL, capture_output=True, text=True).stdout.split()
    d2 = subprocess.run(["find", "Day02_new/rag_lab", "-newer", str(P3 / f"{PFX}-start-marker"), "-type", "f", *flt], cwd=REAL, capture_output=True, text=True).stdout.split()
    return d3, d2


collected = (P3 / f"{PFX}-scratch" / "collected-ids.txt").read_text(encoding="utf-8").splitlines()
prereg_before = (P3 / f"{PFX}-prereg.md").stat().st_mtime < (P3 / f"{PFX}-start-marker").stat().st_mtime
dry_lines = (P3 / f"{PFX}-scratch" / "dryrun.out").read_text(encoding="utf-8").splitlines()
dry_noexpect = [l.split("'")[1] for l in dry_lines if l.startswith("NOEXPECT")]
dry_ok = dry_lines[0].startswith(f"rows {len(ROWS)} bad 0 noop [] ") and sorted(dry_noexpect) == ["n10", "n11", "n12", "n13"] and not any(l.startswith("BAD") for l in dry_lines)
per_file = OrderedDict()
for c in collected:
    per_file[c.split("::")[0].split("/")[-1]] = per_file.get(c.split("::")[0].split("/")[-1], 0) + 1
per_file = OrderedDict(sorted(per_file.items(), key=lambda kv: -kv[1]))

# ---- rows adapted in this run: compare the falsify 5 row with the falsify 6 row
adapted = [k for k, row in ROWS.items() if "ADAPTED (falsify 7)" in row["note"]]
changed_edits = [k for k in rows_prev.ROWS if k in ROWS and k != "clean" and rows_prev.ROWS[k]["edits"] != ROWS[k]["edits"]]
assert sorted(changed_edits) == sorted(adapted), (changed_edits, adapted)  # every row whose injection text differs from falsify 5 is a declared adaptation, and vice versa
changed_expect = [k for k in rows_prev.ROWS if k in ROWS and rows_prev.ROWS[k]["expect"] != ROWS[k]["expect"]]
changed_env = [k for k in rows_prev.ROWS if k in ROWS and rows_prev.ROWS[k]["env"] != ROWS[k]["env"]]
new_ids = [k for k in ROWS if k not in rows_prev.ROWS]


def fence(text):
    return "`" + text.replace("`", "'").replace("\n", "\\n") + "`"


adapted_lines = []
for k in adapted:
    old_e, new_e = rows_prev.ROWS[k]["edits"], ROWS[k]["edits"]
    for (o1, n1), (o2, n2) in zip(old_e, new_e):
        adapted_lines.append(f"- {k} ({ROWS[k]['file']}): old text {fence(o1)} -> {fence(n1)}; new text {fence(o2)} -> {fence(n2)}.")

lines = []
for rid, row in ROWS.items():
    r = last[rid]
    defect = row["label"] + (f" **{row['note']}**" if row["note"] else "")
    if rid == "clean":
        cell = (f"{r['summary']} (3 runs: " + "; ".join(c["summary"].split(" in ")[0] for c in clean_runs)
                + f"); no failure; skipped {r['counts'].get('skipped', 0)}; notebook check `{r['notebook_line']}` exit {r['notebook_exit']}; copy outputs/runs files {r['copy_runs_files']}")
        lines.append(f"| clean | {esc(defect)} | {esc(cell)} | no failure |")
        continue
    if r["kind"] == "notebook":
        cell = esc("`" + r["failed"][0] + "` exits 1 (the checker script, not collected by pytest); whole `tests` directory in the same copy: " + r["pytest_summary"] + " (no failure)")
    else:
        cell = esc(tests_cell(r))
    lines.append(f"| {rid} | {esc(defect)} | {cell} | {esc('`' + decisive(r) + '`')} |")

injected = [last[k] for k in ROWS if k != "clean"]
missing_rows = [k for k in ROWS if k not in last]
survivors = [r["id"] for r in injected if not r.get("caught")]
pyrows = [r for r in injected if r["kind"] == "pytest"]
clean_sizes = {suite_size(c) for c in clean_runs}
clean_ok = (len(clean_runs) == 3 and all(c["caught"] and c["counts"].get("skipped", 0) == 0 and c["counts"].get("failed", 0) == len(BASELINE) and not c["failed"]
                                         and c["counts"].get("passed", 0) == len(collected) - len(BASELINE)
                                         and sorted(c["failed_all"]) == sorted(BASELINE) for c in clean_runs) and clean_sizes == {len(collected)})
SUITE = clean_sizes.pop() if len(clean_sizes) == 1 else -1
before_lines, after_lines = read_hash(P3 / f"{PFX}-realtree-before.txt"), read_hash(P3 / f"{PFX}-realtree-after.txt")
d02_before = [l for l in before_lines if l.startswith("Day02_new/rag_lab")]
d02_after = [l for l in after_lines if l.startswith("Day02_new/rag_lab")]
d03_before = [l for l in before_lines if not l.startswith("Day02_new/rag_lab")]
d03_after = [l for l in after_lines if not l.startswith("Day02_new/rag_lab")]
same_d03, same_d02 = d03_before == d03_after, d02_before == d02_after
runs_before = next(l for l in before_lines if "outputs/runs" in l)
runs_after = next(l for l in after_lines if "outputs/runs" in l)
newer3, newer2 = newer_than_marker()
snap_start = (P3 / f"{PFX}-snapshot-hash-start.txt").read_text(encoding="utf-8").split()[0]
snap_now = snapshot_hash()
live_changed = live_vs_snapshot()
all_ids = {f for r in injected for f in r.get("failed", [])}
all_funcs = {f.split("[")[0] for f in all_ids}
earlier = [k for k in ROWS if k[0].isdigit()]
tk = [k for k in ROWS if re.fullmatch(r"t\d\d", k)]
gk = [k for k in ROWS if re.fullmatch(r"g\d\d", k)]
wk = [k for k in ROWS if re.fullmatch(r"w\d\d", k)]
bk = [k for k in ROWS if re.fullmatch(r"b\d\d", k)]
nk = [k for k in ROWS if re.fullmatch(r"n\d\d", k)]
gik = [k for k in ROWS if k.startswith("gi")]
exk = [k for k in ROWS if k.startswith("ex")]
wpk = [k for k in ROWS if k.startswith("wp")]
syk = [k for k in ROWS if k.startswith("sy")]
sizes = {r["id"]: suite_size(r) for r in pyrows}
off_size = {k: v for k, v in sizes.items() if v != SUITE}
n_secrets, n_own, own_hits, n_top, top_hits, control_found = secret_scan()
n_envs = len(list(WORK.rglob(".env")))
copy_runs = {r["id"]: r["copy_runs_files"] for r in injected if r["copy_runs_files"]}
baseline_gone = [r["id"] for r in pyrows if len(r.get("baseline_present", [])) != len(BASELINE)]
verdict_ok = (snap_start == snap_now and not survivors and not missing_rows and clean_ok and same_d03 and runs_before == runs_after and "files=1893" in runs_after and own_hits == 0 and control_found and n_envs == 0 and not newer3
              and set(copy_runs) == {"t15", "b10"} and not [r["id"] for r in injected if r.get("inject_error")] and all(len(r["diff"]) == 1 for r in injected)
              and not baseline_gone and len(ROWS) == 175 and sorted(new_ids) == ["sy01", "sy02"] and not adapted and prereg_before and dry_ok)

deltas, hybrid_rows, biggest = {}, [], 0
for rid, row in ROWS.items():
    if row["file"] and row["file"].startswith("mas_lab/") and (WORK / rid).exists():
        deltas[rid] = code_lines(WORK / rid / "Day03_new" / row["file"]) - code_lines(REAL / "Day03_new" / row["file"])
        biggest = max(biggest, max(code_lines(q) for q in (WORK / rid / "Day03_new" / "mas_lab").glob("*.py")))
        if row["file"].endswith("hybrid.py"):
            hybrid_rows.append(rid)
changed = {rid: d for rid, d in deltas.items() if d}
hy = code_lines(REAL / "Day03_new" / "mas_lab" / "hybrid.py")
wk_lines = code_lines(REAL / "Day03_new" / "mas_lab" / "workers.py")
linecap_fail = [r["id"] for r in pyrows if any(LINECAP in f for f in r["failed_all"])]
cap_text = (f"Line-count test (`{LINECAP}`): it fails in {len(linecap_fail)} of the {len(pyrows)} pytest rows {linecap_fail if linecap_fail else ''} (every row is also required to fail some other test, and does). `hybrid.py` has {hy} non-blank lines (cap 150), so the {len(hybrid_rows)} injections into it "
            f"({', '.join(hybrid_rows)}) keep the count (delta {sorted({deltas[r] for r in hybrid_rows})}). {len(changed)} other `mas_lab` rows change the non-blank line count of the injected file: "
            + ", ".join(f"{rid} ({ROWS[rid]['file'].split('/')[-1]}, {d:+d})" for rid, d in changed.items())
            + f". `workers.py` has {wk_lines} non-blank lines in the real tree (it grew with the labelled-ref recovery), so a row that adds lines to it can cross the cap: {linecap_fail if linecap_fail else 'none does'}. The largest `mas_lab` file in any row has {biggest} non-blank lines; no row is caught on size alone, because every row is also required to fail a test that is not the line-count test. The other {len(deltas) - len(changed) - len(hybrid_rows)} `mas_lab` rows are line-neutral.")
off_text = ", ".join(f"{k} ({v})" for k, v in off_size.items())
pre_new = [k for k in ROWS if k in set(adapted) | set(new_ids) | set(changed_expect)]
pre_lines = [f"- {k}: " + ("; ".join(f"`{e}`" for e in ROWS[k]["expect"]) if ROWS[k]["expect"] else "caught rule only") for k in pre_new]

d02_text = ("IDENTICAL before and after" if same_d02 else
            "DIFFERENT before and after, which is the other session's edit of Day02_new during this run; every copy used the snapshot, so no row is affected")
dry_text = (f"was run on the edited tools before the start marker: `{dry_lines[0]}`" + (f"; the NOEXPECT lines are exactly {', '.join(dry_noexpect)}, whose failing case exists only after the injection adds it ({SUITE + 1} tests instead of {SUITE})" if dry_noexpect else "")
            + "; every pre-registered test name of the two new rows matches a test collected in the clean copy")
sy_text = "; ".join(f"{k}: {len(last[k]['failed'])} failed of {suite_size(last[k])} (" + ", ".join(f"`{f.split('::')[-1]}`" for f in last[k]["failed"]) + ")" for k in syk)
head = f"""# Falsify 7: Day03_new falsification table rerun on the synced tree (2026-11-02)

Folders of this run: work `{WORK.name}`, snapshot `{SNAP.name}`, record `{P3.name}`. The run wrote no project file; the tools in `docs/audit/tools/` were edited before the start marker `{PFX}-start-marker` was touched, and the pre-registration `{PFX}-prereg.md` {'was written before the start marker' if prereg_before else 'WAS NOT WRITTEN BEFORE THE START MARKER'}.
Why a rerun: falsify 6 ran before `Day03_new/rag_lab/{{corpus,retrieval,evidence,pipeline}}.py` were made byte-identical to `Day02_new/rag_lab`. The sync replaced `retrieval.py` and `evidence.py`, added `pipeline.py`, and added the cell `[pipeline.py]` to `test_rag_lab_copies_are_byte_identical` (`tests/test_layout.py:13`). The two cells that were red in falsify 6 (`[retrieval.py]`, `[evidence.py]`) are green now, so the baseline list is empty. The suite grew from 610 to {SUITE} tests. By the author's decision of 2026-11-02 there is no paid rerun: this run reads no execution record (`outputs/live`, `outputs/runs`) and calls no model and no EXA; those records predate the sync.
Tools (the falsify 6 tools, changed only as far as the sync required): `docs/audit/tools/{{rows.py, row_tables.py, falsify6.py, mkcopy.py, report.py, build_notes6.py, hashtree.sh, dryrun.py}}`. What changed: `falsify6.py` `BASELINE` is the empty list and the clean rule also requires `passed > 0`; `rows.py` gained `sy01` and `sy02`; this builder takes `--prefix` and `--prev-rows` and requires every clean run to show the collected test count passed and 0 failed. `rows.py` is the row table; the upstream mutation points are in `row_tables.py`. Per row output: `<work>/<row>/{{out.txt,diff.txt}}`; all results: `<work>/results.jsonl`.
Changes of method from falsify 6: (a) a NEW snapshot of `Day02_new/rag_lab` was taken at the start into `{SNAP.name}/` ({len(list(SNAP.rglob('*.py')))} files, no `__pycache__`) and every copy and every `diff -rq` uses that snapshot, not the live folder; (b) the BASELINE is empty: no test id may be red in a clean copy, which must show {SUITE} passed and 0 failed, and every row's failed list is its whole failed list; (c) rows {', '.join(new_ids)} are new (below) and adapted rows: {', '.join(adapted) if adapted else 'none'}; (d) `dryrun.py` {dry_text}; (e) rows that inject into `exa.py` (the 11, 12 and ex rows) still all run behind the dead proxy `127.0.0.1:9`.

Method, per row: (1) fresh copy of real `Day03_new` plus the snapshot of `Day02_new/rag_lab` (rsync, excluding exactly `.env outputs __pycache__ .ipynb_checkpoints .ruff_cache`); (2) ONE defect injected into ONE file of the copy; each `old` text must occur exactly once or the row aborts (`INJECT FAILED`; none did); (3) `diff -rq` real `Day03_new` vs copy and snapshot vs copy's `Day02_new/rag_lab`, with the five excluded names filtered, run before pytest: it must name exactly the injected file (clean: nothing); (4) the FULL `tests` directory in the copy, `PYTHONDONTWRITEBYTECODE=1 uv run --no-sync --project <root> pytest -p no:cacheprovider -q tests` from the copy's `Day03_new`; row 14 uses `tests/check_notebook.py 01-Workflow-vs-Agent.ipynb --minutes 60` as its deciding check (as in falsify 4 to 6). A row counts as caught only if: every pre-registered test of the row is among the failed ids, at least one failed id is not the line-count test, there is no collection error, the diff is one file, and the copy's `outputs/runs` has 0 files ({copy_runs.get('t15', '?')} in the two rows that remove the redirect, t15 and b10). A row with no pre-registered test (g, w, b rows) is caught by that last rule alone (the caught rule).
No model call and no EXA call: API key variables (EXA, TYPESAFE, ANTHROPIC, OPENROUTER, OPENAI, LANGFUSE) and every `*_proxy` variable were removed from each row's environment; the copies have no `.env`; the exa.py rows ran behind the dead proxy. `data/gold.jsonl` was not read by this node; the copies carry it as part of `Day03_new/data` (rsync, never opened here) and only the suite reads it inside a copy; the secret scan skips that file so that it is not opened even as bytes. Secret scan (counts only) of {n_own} files under the work folder `{WORK.name}/`, `docs/audit/tools/` and the snapshot `{SNAP.name}/` for {n_secrets} secret values (shell environment and the `.env` files, read in process only, values never printed): {own_hits} hits (positive control with a planted synthetic value: {'detected' if control_found else 'NOT DETECTED'}); the {n_top} other files directly in `{P3.name}/` (earlier files, not this run's output): {top_hits} hits; `.env` files found in the copies: {n_envs}.

Real tree unchanged: sha256 over `Day03_new/mas_lab`, `Day03_new/tests`, `Day03_new/rag_lab`, the seven notebooks `Day03_new/0*.ipynb`, the informational all-files hash of `Day03_new` and the `Day03_new/outputs/runs` file count, taken before the first copy and after the last row (`{PFX}-realtree-before.txt`, `{PFX}-realtree-after.txt`): {'IDENTICAL, line for line' if same_d03 else 'DIFFERENT - see the two files'}. `Day02_new/rag_lab` (listed on its own line): {d02_text}; at snapshot time `diff -rq` between the live folder and the snapshot showed no difference, and the snapshot's content hash is `{snap_start[:16]}...` at the start and `{snap_now[:16]}...` after the last row ({'unchanged' if snap_start == snap_now else 'CHANGED'}). After the last row the live folder differs from the snapshot in {', '.join(live_changed) if live_changed else 'no file'}; `corpus.py`, `retrieval.py`, `evidence.py` and `pipeline.py`, the four files the byte-identical test reads, are {'still equal to the snapshot' if not {'corpus.py', 'retrieval.py', 'evidence.py', 'pipeline.py'} & set(live_changed) else 'NOT equal to the snapshot'}.
```
{chr(10).join(after_lines)}
```
Before-hash lines for comparison:
```
{chr(10).join(before_lines)}
```
Real `outputs/runs` count before and after: `{runs_before}` and `{runs_after}` (the two lines are part of the compared files). `find Day03_new -newer {PFX}-start-marker -type f` (without `outputs`, caches, `.pyc`), checked after the last row: {('no file' if not newer3 else 'FILES: ' + ', '.join(newer3))}. The same `find` over `Day02_new/rag_lab`: {('no file' if not newer2 else 'files ' + ', '.join(newer2))}. The two rows that remove the pytest redirect (t15, b10) wrote their {copy_runs.get('t15', '?')} fake rows into their own copy only.

Clean copy: {len(clean_runs)} runs, {'; '.join(c['summary'] for c in clean_runs)}; no test fails (all four cells of `test_rag_lab_copies_are_byte_identical` pass); 0 skipped, 0 xfailed, 0 errors; `check_notebook.py 01-Workflow-vs-Agent.ipynb --minutes 60` exits 0 (`OK`) in each. The suite has {SUITE} tests (610 in falsify 6, 495 in falsify 5, 215 in falsify 4); collected per file in the clean copy: {', '.join(f'`{k}` {v}' for k, v in per_file.items())}.

Suite count per row: every pytest row ran the whole suite: {SUITE} tests in {len(pyrows) - len(off_size)} of the {len(pyrows)} pytest rows; {off_text} in the other {len(off_size)} (the injection into the notebook adds one parametrized import or slice case, so it has one test more than the clean copy, and that added case is the failing one). Row 14: the checker script decides; the whole `tests` directory in that copy gives {last['14']['pytest_summary']}, so the pytest suite alone does not see a stray `ScriptedChatModel` in a notebook cell (unchanged from falsify 4 to 6).

{cap_text}

Adapted in THIS run: {('rows ' + ', '.join(adapted)) if adapted else 'none'}. The sync changed only `rag_lab/evidence.py`, `rag_lab/retrieval.py`, `rag_lab/pipeline.py` and `tests/test_layout.py`; no old row injects into those files, and `dryrun.py` found no row whose old text occurs other than exactly once ({len(rows_prev.ROWS) - 1} injected rows of falsify 6, {len(changed_edits)} with a different injection text now). Row 13 (`rag_lab/corpus.py`) keeps its meaning and must still fail the `[corpus.py]` cell; row 10b (`rag_lab/settings.py`) is unchanged. Rows whose environment changed: {changed_env if changed_env else 'none'}; rows whose pre-registered tests changed: {changed_expect if changed_expect else 'none'}.

Pre-registered tests of the new rows (fixed in `rows.py` and in `{PFX}-prereg.md` before the first run; an entry `a&&b` means ONE failed id must contain both parts):
{chr(10).join(pre_lines)}

New rows ({len(new_ids)}): sy01 and sy02 change ONE byte inside a comment of a synced file and leave the Day02_new copy untouched, so only the copy test can see it: sy01 `rag_lab/pipeline.py` `str.format` -> `str.fornat` and sy02 `rag_lab/evidence.py` `1회가 1이다` -> `1회가 2이다`. Observed failing sets: {sy_text}. No row for the `[retrieval.py]` cell was added (exactly two rows were asked for), so that cell is guarded only by the copy test itself.

| Row | Injected defect (file, change) | Failing test ids | Decisive message |
|---|---|---|---|
"""

tail = f"""

Row key: `1` to `15b` = the 20 earlier rows; `16` to `23b` = the 9 earlier gate rows (M1 to M8b); `t01` to `t16` = rows named by the falsify 4 task, one per behavior; `g01` to `g34` = every defect of `gate_dev/mutate.py`; `w01` to `w21` = every mutation of `refs_dev/mutate.py`; `b01` to `b11` = every mutation of `budget_dev/mutate.py`; `f01`, `f02` = followup-handoff carry inside one turn; `n01` to `n13` = silent corners A and B and the notebook guard (falsify 5); `n14` to `n17`, `gi01` to `gi13`, `ex01` to `ex15`, `wp01` to `wp14` = added in falsify 6; `sy01`, `sy02` = new in this run. `b11` is a mutation of the test fixture (it also rebinds `rag_lab.settings.ROOT` and `mas_lab.desk.ROOT`) and fails many tests at their data load, so it shows that the fixture must stay narrow, not that a product defect is caught; it is listed and counted but is not evidence for the behavior rows. A row's defect text may still carry a falsify 6 or earlier note (ADAPTED ...); those are the history of that row, not adaptations made in this run.

## Totals
- Lines in the table: {len(ROWS)} = 1 clean + {len(injected)} injected-defect rows.
- Defects: {len(injected)} injected defects ({len(pyrows)} caught through the pytest suite + 1 through the notebook checker, row 14); {len(earlier)} earlier rows, {len(tk)} `t` rows, {len(gk) + len(wk) + len(bk) + 2} upstream and followup rows ({len(gk)} g + {len(wk)} w + {len(bk)} b + f01, f02), {len(nk)} `n` rows, {len(gik)} gi rows, {len(exk)} ex rows, {len(wpk)} wp rows, {len(syk)} sy rows.
- Caught: {len(injected) - len(survivors)} of {len(injected)}. Survivors: {len(survivors)} {survivors if survivors else ''}.
- Missing results: {missing_rows if missing_rows else 'none'}.
- Clean copy: {len(clean_runs)} runs, each {SUITE} passed and 0 failed, notebook check exit 0.
- Suite count per row: {SUITE} tests (see above for the {len(off_size)} rows with one more).
- Tests: the {len(pyrows)} pytest rows hold {len(all_ids)} distinct failing test ids in {len(all_funcs)} test functions. Every row names a failing test (see the table).
- Rows adapted in this run: {', '.join(adapted) if adapted else 'none'}. New rows: {', '.join(new_ids)}.
- Rows with a failing cell of the copy test other than the one they were registered for: {[r['id'] for r in injected if r['kind'] == 'pytest' and any('test_rag_lab_copies_are_byte_identical' in f for f in r['failed']) and r['id'] not in ('13', 'sy01', 'sy02')] or 'none'}.
- Real tree (Day03_new): hashes identical before and after, `outputs/runs` count {runs_after.split('=')[-1]} unchanged, no Day03_new file newer than the start marker: {same_d03 and runs_before == runs_after and not newer3}.

Rulings:
- Ruling: every row runs the FULL `tests` directory, not only `test_structures.py` as the upstream mutation scripts did - a full run also exposes a defect that a different file would catch - cost if wrong: about 8 s per row.
- Ruling: the upstream mutation points were read from the upstream scripts rather than retyped (they are now copied text for text into `row_tables.py`) - the strings stay the upstream authors' - cost if wrong: a later edit of those scripts silently changes the rows (this run's `results.jsonl` keeps the text that ran).
- Ruling: a row with no pre-registered test (g, w, b rows) counts as caught when at least one failing test is not the line-count test - the upstream tables name tests only per behavior - cost if wrong: a row caught only by an unrelated failing test would pass; the table lists every failing test function so this can be read.
- Ruling: no old row was adapted - `dryrun.py` found every old text exactly once on the synced tree because the sync touched no file an old row injects into - cost if wrong: a row that still applies but no longer aims at the code it was written for would count as caught without testing the same thing; the table shows each row's failing tests.
- Ruling: sy01 and sy02 change one ASCII byte inside a comment (the id prefix `sy` keeps them out of the digit-led `earlier` group) - a comment change cannot move any other test, so the failing set shows whether the copy cell alone sees the drift - cost if wrong: a one-byte change in executable code would also test that no other test notices, which this pair does not.
- Ruling: exactly the two rows asked for were added, so the `[retrieval.py]` cell has no injected row - the task fixed the number of rows - cost if wrong: a copy test that ignored `retrieval.py` would go unnoticed by this table.
- Ruling: `BASELINE` stays in `falsify6.py` as an empty list instead of being deleted - the code paths that read it become vacuous, and a later accepted-red id has a place - cost if wrong: dead code remains; the clean rule also requires `passed > 0`, so an empty summary cannot count as a clean run.
- Ruling: `build_notes6.py` now builds the falsify 7 notes (its falsify 6 text and the two fixed baseline ids are gone) instead of keeping two builders - one 340-line near-duplicate would drift from the row table - cost if wrong: the falsify 6 notes cannot be regenerated from this folder; they were written by the earlier version of this script.
- Ruling: row 14 keeps `check_notebook.py` as its deciding check although the whole pytest directory passes in that copy - the row was defined as the checker's row in falsify 4 and `test_notebook_code.py` reads imports and slice markers, not forbidden names - cost if wrong: if the author wants pytest alone to catch a stray fake model in a notebook, row 14 is a survivor and a pytest case is missing.
- Ruling: the real-tree claim compares the Day03_new lines line for line and reports the `Day02_new/rag_lab` line separately - Day02_new belongs to another session - cost if wrong: none for the copies, which used the snapshot.
- Ruling: every row that injects into `exa.py` (11, 12 and ex01 to ex15) runs behind the dead proxy `127.0.0.1:9` - an injection there can let a test query reach `ExaClient.search` with the fixture's fake key, and the task forbids any EXA call - cost if wrong: none (row 12 and the ex rows fail the same tests with or without it).
- Ruling: the three clean runs were spread over the run (before the first injected row, in the middle, after the last row) - they show the clean copy stays green while the rows run - cost if wrong: none.

"""
final = "Falsify 7: PASS\n" if verdict_ok else ("Falsify 7 failing rows: " + ", ".join(survivors + [f"missing:{m}" for m in missing_rows]) + "\nFalsify 7: FAIL\n")
NOTES.write_text(head + "\n".join(lines) + tail + final, encoding="utf-8")
print("written", len(lines), "table lines; survivors", survivors, "verdict_ok", verdict_ok, "same_d03", same_d03, "same_d02", same_d02, "clean_ok", clean_ok, "newer3", newer3, "newer2", newer2,
      "off_size", off_size, "adapted", adapted, "own_hits", own_hits, "top_hits", top_hits, "baseline_gone", baseline_gone, "prereg_before", prereg_before, "dry_ok", dry_ok)
