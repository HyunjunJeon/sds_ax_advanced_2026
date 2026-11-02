# Preflight C2 notes

P = <P>
Repo root: <repo>. No model call and no EXA call were made. `uv run --no-sync` only.

## 1. Code hashes
File: P/c2-code-hashes.txt (37 lines, sha256, paths relative to the repo root).
Covers: Day03_new/mas_lab/*.py (14 files, `__pycache__` excluded; there are no non-.py files outside it),
Day03_new/rag_lab/*.py (5), Day03_new/tests/*.py (16), pyproject.toml, uv.lock.
Later nodes check with: `cd <repo root> && shasum -a 256 -c P/c2-code-hashes.txt` (re-run just now: 0 mismatches).

Root manifests:
- pyproject.toml 59dfcfc2d720158f33a30b845506ff60fbbf7b58da428f8bd16079d44ff5830c (matches the required 59dfcfc2...)
- uv.lock        e39fee03edbc931007298a611bafdc3543b003add9139295c288543b3a863ac4 (matches the required e39fee03...)

Hashes of the files the rerun must be judged against (first 12 hex): gate.py 16c50d6ee3ec, exa.py c8f238a968aa, workers.py 2fde59e593fb,
structures.py 041311a76495, hybrid.py c5a5f4d9d0ad, runner.py ecbdd088db96, audit_live.py a1907b271f77, run_live.py 55578ea77c7f.
(Day03_new/rag_lab/settings.py d72fe2f6775b.)

## 2. Copies of the current records
Dir: P/live-before-c2/ (every copy was `cmp`-checked equal to its source).
- 04-Graph-Engineering.{executed.ipynb,exercises.executed.ipynb,exercises.json,exercises.usage.jsonl,json,usage.jsonl}
- 05-Choosing-Multi-Agent.{same six}
- design_log.json
- baseline/01.json

## 3. outputs/runs before the rerun
List: P/runs-before-c2.txt (sorted file names). Count: **1781** (expected 1781; real = 1781). `find -type f` also gives 1781 and there are no subdirectories.
(P/runs-before-list.txt is an older 1657-name snapshot with full paths; it is a subset of the current list and is not the baseline for this run.)

## 4. audit_live
`uv run --no-sync python Day03_new/tests/audit_live.py`, exit 0, full output in P/c2-audit-live.txt. Last line: **AUDIT OK**.
Per-record lines (calls / input tokens / output tokens / seconds) of the current records, for the later "saved sentences still true" check:
- 04-Graph-Engineering: 34 / 84,368 / 16,098 / 104
- 04-Graph-Engineering.exercises: 36 / 88,995 / 15,912 / 104
- 05-Choosing-Multi-Agent: 145 / 553,807 / 53,579 / 412
- 05-Choosing-Multi-Agent.exercises: 460 / 1,760,800 / 147,281 / 1238

## 5. Versions
File: P/versions-c2.txt. Compared with P/versions-before.txt: `diff` empty, VERSIONS-EQUAL.
- python 3.13.14 (<repo>/.venv/bin/python)
- deepagents 0.7.32
- langgraph 1.2.19
- langchain-anthropic 1.7.7

## 6. Key
`rag_lab.settings.key_status()` run from Day03_new: ANTHROPIC_API_KEY = **set**. No value, prefix or length was printed.

## 7. Other processes
`ps -axo pid,etime,command` filtered for run_live, jupyter, ipykernel, wait_live, nbconvert, papermill, Day02_new, Day03_new:
- no run_live, no jupyter, no ipykernel at the time of the check.
- one other-session process: `uv run --no-sync pytest -q Day02_new/tests/test_rag_lab_phases.py -k test_decomposition_is_on_by_default`
  (pid 1239 uv, pid 1244 pytest, elapsed 1 s). This is another session's Day02_new test. Whether it calls the API is unknown; if it does,
  it shares this API key's rate limit with the paid rerun. Not a reason to stop. `make_model` uses `max_retries=0`, so a 429 would show up as a
  `model_error` row and must be recorded, not hidden.

## 8. Marker
`P/run-c2-start-marker` is touched after this file is written (last step).

## Verdict
- root hashes equal: yes
- audit_live last line AUDIT OK: yes
- key set: yes
- versions equal to the earlier file: yes

Preflight C2: PASS
