"""falsify6.py --work DIR --snapshot DIR [row ids... | a:b]: for each row make a fresh copy, inject ONE defect, diff against this repository's Day03_new and the start-of-run Day02_new/rag_lab snapshot, run the full tests in the copy, record results.

BASELINE: test ids that are red in every copy by the author's decision; they are removed from `failed`, never count as a catch, and the clean copy must show exactly these and nothing else. It is empty since Day03_new/rag_lab was synced with Day02_new/rag_lab (the two byte-identical cells that were red before the sync are green), so the clean copy must show no failure at all.

--work and --snapshot have no default (see mkcopy.py). Results: <work>/results.jsonl (one JSON object per row; a later run of the same row replaces the earlier one when merged by report.py).
Per row: <work>/<row>/{out.txt,diff.txt}. No model call, no EXA call: API keys are removed from the environment, the copies have no .env,
and every row that injects into exa.py additionally runs behind a dead proxy. data/gold.jsonl is copied by rsync (the copy's own tests read it) but is left out of the diff.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import mkcopy  # noqa: E402
from rows import ROWS, LINECAP, matches  # noqa: E402

ROOT = mkcopy.REPO
KEYS = {"EXA_API_KEY", "TYPESAFE_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_PUBLIC_KEY"}
DIFF_EX = ["-x", ".env", "-x", "outputs", "-x", "__pycache__", "-x", ".ipynb_checkpoints", "-x", ".ruff_cache", "-x", "gold.jsonl"]
NB = "01-Workflow-vs-Agent.ipynb"
BASELINE: list[str] = []


def base_env(extra: dict) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in KEYS and not k.lower().endswith("_proxy")}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "COLUMNS": "400", "PYTHONUNBUFFERED": "1"})
    env.update(extra)
    return env


def inject(path: Path, edits: list[tuple[str, str]]) -> str | None:
    text = path.read_text(encoding="utf-8")
    for old, new in edits:
        found = text.count(old)
        if found != 1:
            return f"INJECT FAILED: expected 1 occurrence, found {found}: {old[:90]!r} in {path.name}"
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    return None


def inject_nb(path: Path, edits: list[tuple[str, str, str]]) -> str | None:
    """Edit the source of ONE code cell per edit (found by cell id); old must occur exactly once in that cell. Written back the way nbformat does (indent 1, ensure_ascii False)."""
    raw = path.read_text(encoding="utf-8")
    nb = json.loads(raw)
    for cell_id, old, new in edits:
        cells = [c for c in nb["cells"] if c.get("id") == cell_id]
        if len(cells) != 1:
            return f"INJECT FAILED: cell {cell_id} found {len(cells)} times in {path.name}"
        cell = cells[0]
        text = cell["source"] if isinstance(cell["source"], str) else "".join(cell["source"])
        found = text.count(old)
        if found != 1:
            return f"INJECT FAILED: expected 1 occurrence in cell {cell_id}, found {found}: {old[:90]!r} in {path.name}"
        text = text.replace(old, new)
        cell["source"] = text.splitlines(keepends=True) if isinstance(cell["source"], list) else text
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")  # keep the file's own final newline: the diff is the cell edit only
    return None


def row14(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    nb = json.loads(raw)
    first = next(c for c in nb["cells"] if c["cell_type"] == "code")
    src = first["source"] if isinstance(first["source"], list) else first["source"].splitlines(keepends=True)
    src[-1] = src[-1] + "\n"
    src.append("model = ScriptedChatModel(steps=[])")
    first["source"] = src
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")


def diffcheck(copy: Path, snapshot: Path) -> list[str]:
    lines = []
    for a, b in ((ROOT / "Day03_new", copy / "Day03_new"), (snapshot, copy / "Day02_new" / "rag_lab")):
        out = subprocess.run(["diff", "-rq", *DIFF_EX, str(a), str(b)], capture_output=True, text=True).stdout
        lines += [l for l in out.splitlines() if l.strip()]
    for name in (".env", "outputs", "__pycache__", ".ipynb_checkpoints", ".ruff_cache"):
        found = subprocess.run(["find", str(copy), "-name", name, "-prune", "-print"], capture_output=True, text=True).stdout.split()
        lines += [f"EXCLUDED-NAME-PRESENT-IN-COPY: {f}" for f in found]
    return lines


def run_pytest(copy: Path, env: dict) -> tuple[str, int]:
    r = subprocess.run(["uv", "run", "--no-sync", "--project", str(ROOT), "pytest", "-p", "no:cacheprovider", "-q", "tests"],
                       cwd=copy / "Day03_new", env=env, capture_output=True, text=True, timeout=420)
    return r.stdout + r.stderr, r.returncode


def run_notebook(copy: Path, env: dict) -> tuple[str, int]:
    r = subprocess.run(["uv", "run", "--no-sync", "--project", str(ROOT), "python", "-I", "tests/check_notebook.py", NB, "--minutes", "60"],
                       cwd=copy / "Day03_new", env=env, capture_output=True, text=True, timeout=300)
    return r.stdout + r.stderr, r.returncode


def parse(text: str) -> dict:
    failed = [l[len("FAILED "):] for l in text.splitlines() if l.startswith("FAILED ")]
    errors = [l for l in text.splitlines() if l.startswith("ERROR ")]
    summary = ""
    for l in text.splitlines():
        if re.search(r"\b\d+ (passed|failed|error|errors)\b", l) and " in " in l:
            summary = l.strip("= ").strip()
    counts = {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed|skipped|xfailed|xpassed|errors?|deselected)", summary)}
    all_ids = [f.split(" - ", 1)[0] for f in failed]
    msgs = {f.split(" - ", 1)[0]: (f.split(" - ", 1)[1] if " - " in f else "") for f in failed}
    ids = [i for i in all_ids if i not in BASELINE]
    return dict(summary=summary, counts=counts, failed=ids, failed_all=all_ids, baseline_present=[b for b in BASELINE if b in all_ids], messages=msgs, errors=errors)


def do_row(rid: str, work: Path, snapshot: Path) -> dict:
    row = ROWS[rid]
    started = time.time()
    copy = mkcopy.make(rid, work, snapshot)
    env = base_env(row["env"])
    res = dict(id=rid, label=row["label"], file=row["file"], note=row["note"], kind=row["kind"], expect=row["expect"],
               edits=[[o, n] for o, n in row["edits"]], nb_edits=[list(e) for e in row["nb_edits"]])
    if row["kind"] == "notebook":
        row14(copy / "Day03_new" / row["file"])
    elif row["edits"] or row["nb_edits"]:
        bad = inject(copy / "Day03_new" / row["file"], row["edits"]) if row["edits"] else inject_nb(copy / "Day03_new" / row["file"], row["nb_edits"])
        if bad:
            res.update(inject_error=bad, caught=False)
            return res
    diff = diffcheck(copy, snapshot)
    (copy / "diff.txt").write_text("\n".join(diff) + "\n", encoding="utf-8")
    res["diff"] = diff
    if row["kind"] == "notebook":
        out, code = run_notebook(copy, env)
        (copy / "out.txt").write_text(out + f"\nexit={code}\n", encoding="utf-8")
        fail_line = next((l for l in out.splitlines() if l.startswith("FAIL")), "")
        res.update(exit=code, failed=[f"tests/check_notebook.py {NB} --minutes 60"] if code else [], messages={f"tests/check_notebook.py {NB} --minutes 60": fail_line},
                   summary=out.strip().splitlines()[-1] if out.strip() else "", counts={}, errors=[])
        res["caught"] = code == 1 and fail_line.startswith("FAIL") and "ScriptedChatModel" in fail_line and len(diff) == 1
        p_out, p_code = run_pytest(copy, env)  # the whole tests directory is run as well; recorded, not required for this row
        (copy / "out-pytest.txt").write_text(p_out + f"\nexit={p_code}\n", encoding="utf-8")
        parsed = parse(p_out)
        res.update(pytest_exit=p_code, pytest_summary=parsed["summary"], pytest_failed=parsed["failed"])
    else:
        out, code = run_pytest(copy, env)
        (copy / "out.txt").write_text(out + f"\nexit={code}\n", encoding="utf-8")
        res.update(parse(out), exit=code)
        if row["kind"] == "clean":
            nb_out, nb_code = run_notebook(copy, env)
            (copy / "out-notebook.txt").write_text(nb_out + f"\nexit={nb_code}\n", encoding="utf-8")
            res.update(notebook_exit=nb_code, notebook_line=nb_out.strip().splitlines()[0] if nb_out.strip() else "")
    runs = copy / "Day03_new" / "outputs" / "runs"
    res["copy_runs_files"] = len(list(runs.glob("*"))) if runs.exists() else 0
    res["seconds"] = round(time.time() - started, 1)
    if row["kind"] == "pytest":
        failed = res["failed"]
        res["failed_nocap"] = [f for f in failed if LINECAP not in f]
        res["expect_missing"] = [e for e in row["expect"] if not any(matches(e, f) for f in failed)]
        res["collection_errors"] = len(res["errors"])
        res["diff_ok"] = len(diff) == (1 if (row["edits"] or row["nb_edits"]) else 0) and (not diff or Path(row["file"]).name in diff[0])
        res["baseline_still_red"] = len(res["baseline_present"]) == len(BASELINE)  # recorded; a row that turns a baseline id green would be odd but is not a catch either way
        res["caught"] = bool(res["failed_nocap"]) and not res["expect_missing"] and res["diff_ok"] and not res["collection_errors"]
        if row["id"] in ("t15", "b10"):  # the two rows that remove the redirect: the copy's outputs/runs must receive the fake rows
            res["caught"] = res["caught"] and res["copy_runs_files"] > 0
        elif res["copy_runs_files"]:
            res["caught"] = False
    elif row["kind"] == "clean":
        res["caught"] = (res["counts"].get("passed", 0) > 0 and res["counts"].get("failed", 0) == len(BASELINE) and not res["failed"] and len(res["baseline_present"]) == len(BASELINE)
                         and res["counts"].get("skipped", 0) == 0 and res["counts"].get("xfailed", 0) == 0
                         and not res["errors"] and not diff and res["copy_runs_files"] == 0 and res.get("notebook_exit") == 0)
    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="*", help="row ids (default: every row), or one slice a:b over the row order")
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args()
    work, snapshot = args.work.resolve(), args.snapshot.resolve()
    ids = args.ids or list(ROWS)
    if len(ids) == 1 and re.fullmatch(r"\d*:\d*", ids[0]):  # slice syntax a:b over the row order
        lo, hi = ids[0].split(":")
        ids = list(ROWS)[int(lo or 0):int(hi) if hi else None]
    for rid in ids:
        r = do_row(rid, work, snapshot)
        with (work / "results.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        tag = "ok" if r.get("caught") else "NOT-CAUGHT"
        print(f"[{rid}] {tag} | {r.get('summary', '')} | failed={len(r.get('failed', []))} nocap={len(r.get('failed_nocap', []))} "
              f"missing={r.get('expect_missing')} collect_err={r.get('collection_errors')} diff={len(r.get('diff', []))} runs_in_copy={r.get('copy_runs_files')} "
              f"{r.get('inject_error', '')} ({r.get('seconds')}s)", flush=True)
