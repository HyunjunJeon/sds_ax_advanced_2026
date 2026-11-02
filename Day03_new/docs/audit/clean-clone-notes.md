# Clean clone notes (node clean-clone, run dag_mvxjjtgg_181ytn)

P = <P>
Tools written under P/clone-tools/: make_candidate.py, write_anthropic_only_env.py, key_scan.py.
Logs: P/clone-sync.log, P/clone-pytest.log, P/clone-check-notebook.log, P/clone-step4.{out,err}, P/clone-step5.{out,err}, P/clone-keyscan.txt.
Step 4 run record kept at P/clone-step4-live/ (the clone's own outputs/live was overwritten by the step 5 run).

## 1. Candidate and clone

- `git ls-files -co --exclude-standard -z` in the real repo listed 22166 paths. 22160 exist and were copied to P/clone-src (22124 files, 36 symlinks, symlinks recreated as symlinks). 6 listed paths do not exist because they are deletions in the working tree: Day02/uv.lock, Day03/uv.lock, Day05/uv.lock, Day07/uv.lock, Day08/uv.lock, Day04/requirements.txt.
- `git init -q`, `git add -A`, commit `candidate` in P/clone-src. `git add -A` skipped 24 Day06 paths that are tracked in the real repo but match an ignore rule once the history is gone (Day06/ouroboros/.ouroboros/*, Day06/ouroboros/.python-version, ouroboros canonical evidence traces, pi doom.js and doom.wasm). I added exactly those 24 with `git add -f --pathspec-from-file` and amended the commit so the candidate holds every path the listing named. Result: 22160 tracked files, clean status.
- `git clone -q P/clone-src P/clone-dst`: 22160 tracked files. In the clone before any run: .env files = 0, .venv = 0, outputs = 0 (only `.env.example` files exist).
- LIMIT: the candidate is the author's working tree, not a pushed commit. Other sessions' uncommitted edits (Allganize files in Day02_new, Day02/Day03 edits, anything untracked and not ignored) are inside it. The proof is "this working tree, cloned clean, installs and passes", not "origin/main passes".
- LIMIT: the clone has no remote history of the real repo and no Lecture_Note (git-ignored).

## 2. uv sync --locked, empty cache

Command (in P/clone-dst): `env -u VIRTUAL_ENV UV_CACHE_DIR=P/clone-uv-cache PYTHONDONTWRITEBYTECODE=1 uv sync --locked`; cache directory removed and recreated empty immediately before.
uv 0.13.6 (Homebrew). Log: Using CPython 3.13.14, Resolved 363 packages, Prepared 345 packages in 9.84s, Installed 345 packages in 759ms, exit=0 (wall time 17:04:39 to 17:04:50). Cache after: 2296115200 bytes (2.1G). .venv after: 1988149248 bytes (1.9G).
Versions from the clone's .venv/bin/python:
- Python 3.13.14
- deepagents 0.7.32
- langgraph 1.2.19
- langchain-anthropic 1.7.7
(identical to P/versions-before.txt from the preflight node.)

## 3. Offline checks in P/clone-dst/Day03_new (clone's .venv/bin/python, ANTHROPIC_API_KEY and EXA_API_KEY stripped with env -u)

- `python -m pytest -p no:cacheprovider -q -rs`: 503 passed, 0 failed, 0 skipped, 14.79s, rc=0.
- check_notebook.py: 00-Setup --minutes 10 OK; 01, 02, 03, 04, 05, 06 --minutes 60 all OK. 7 of 7, every rc=0.

## 4. 00-Setup via tests/run_live.py, no .env, both keys stripped

No .env existed in the clone. Result: rc=1 ("LIVE RUN FAILED 00-Setup errors=1"), the expected stop.
- Stop cell: notebook cell index 5 (code cell, shown as In[3]), line 5 `settings = require_key()`.
- Error: RuntimeError, message quoted: "ANTHROPIC_API_KEY가 미설정입니다. Day03_new/.env.example을 .env로 복사한 뒤 ANTHROPIC_API_KEY에 본인의 키를 직접 채우세요."
- Cells that ran before it: index 2 and 3, both ok, 0 model calls.
- Model calls: 0 (report model_calls=0, input_tokens=0, output_tokens=0; the usage log file was never created).

## 5. 00-Setup with only the ANTHROPIC_API_KEY line (announced first: "at most 5 model calls")

P/clone-tools/write_anthropic_only_env.py copied one line (the ANTHROPIC_API_KEY line, nothing else, mode 0600) from the real Day03_new/.env to P/clone-dst/Day03_new/.env and printed only "wrote 1 line". The run used `env -u ANTHROPIC_API_KEY -u EXA_API_KEY`, so the key reached the kernel only through the .env file. The .env was deleted right after the run; `ls` confirms it is gone and the clone holds 0 .env files at the end.
- Stop cell: notebook cell index 5 again (In[3]), now at line 6 `require_exa_key()`. `require_key()` on line 5 passed.
- Error: RuntimeError, message quoted: "EXA_API_KEY가 미설정입니다. https://exa.ai/ 에서 발급해 Day03_new/.env의 EXA_API_KEY에 본인의 키를 직접 채우세요."
- Model calls: 0 (model_calls=0, tokens 0). This is the expected behavior: the EXA check sits before `make_model` and before any model cell. The EXA key was never copied and no EXA call was made.

## 6. Key scan of P/clone-dst (excluding .venv)

Script P/clone-tools/key_scan.py parsed the real Day03_new/.env without printing values. It has 7 entries; the scan covers the entries whose names contain KEY/TOKEN/SECRET/PASSWORD/LANGFUSE/LANGSMITH/RUNPOD and whose value is at least 12 characters: ANTHROPIC_API_KEY and EXA_API_KEY (OPENROUTER_API_KEY is empty and was skipped). Needles: each full value and its last 12 characters = 4 needles.
- Working-tree byte scan: 22212 files scanned (symlinks not followed, .venv excluded; includes .git files, outputs/live from steps 4 and 5): total hits = 0. ANTHROPIC_API_KEY full 0, last12 0; EXA_API_KEY full 0, last12 0.
- Positive control: a temp file inside the clone (Day03_new/outputs/keyscan-control.tmp) holding the full ANTHROPIC key and the last 12 of the EXA key: scan hits = 3 (ANTHROPIC full 1, ANTHROPIC last12 1, EXA last12 1). Control file removed; rescan back to 0 hits.
- Extra: `git grep -F -a -f <needles file>` on HEAD blobs (the packed history, decompressed): 0 matching files; `git grep --no-index` on the working tree: 0 matching files. The needle file was deleted right after.
- Not scanned for: the plain (non-secret) entries OPENROUTER_BASE_URL, DAY02_MODEL, DAY02_EFFORT, DAY02_EMBEDDING_MODEL. Their values are model names and URLs that legitimately appear in code, so a hit would not mean a leak.

## 7. Real-repo hashes and cleanup

- Real root pyproject.toml: 59dfcfc2d720158f33a30b845506ff60fbbf7b58da428f8bd16079d44ff5830c before and after.
- Real root uv.lock: e39fee03edbc931007298a611bafdc3543b003add9139295c288543b3a863ac4 before and after.
- Real root .venv: 0 entries (depth 2) newer than P/run-b-start-marker; no .git/index.lock. No git command that writes (status, add, stash, config) was run in the real repo; only the read-only `git ls-files`.
- Deleted at the end after recording sizes: P/clone-uv-cache (2296115200 bytes) and P/clone-dst/.venv (1988149248 bytes). Kept: P/clone-src (455M) and P/clone-dst (627M) for later inspection.

## Not proved

- Notebooks 01-06 were not run in the clone (that is the paid rerun in other nodes).
- A clone of the pushed remote (origin/main) was not tested; see the limit in section 1.
- Windows or Linux installs were not tested; this ran on macOS aarch64 only.
- The live path with both keys was not run in the clone: no EXA call, no model call was made by this node.
- Python came from this machine: the sync log says only "Using CPython 3.13.14" with no CPython download, so the interpreter was already installed outside the empty uv cache. A student with no Python 3.13 would also trigger a Python download; that path was not tested.

Clean clone: PASS
