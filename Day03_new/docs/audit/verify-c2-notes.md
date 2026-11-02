# Verify C2 notes (run dag_mvxqwuxv_oit10v, node verify-c2, attempt 1)

P = <P>
Repo root: <repo>. No model call and no EXA call were made by this node. No project file was edited (only files under P were written). Every earlier node report was treated as a claim and re-read from the files. Times are local (KST); the transcripts store UTC, 9 hours earlier.

## Result per check

| # | Check | Result |
|---|---|---|
| 1 | `uv run --no-sync python Day03_new/tests/audit_live.py` ends `AUDIT OK` | holds (exit 0; output in `P/verify-c2-audit.txt`) |
| 2 | Code unchanged against `P/c2-code-hashes.txt` | holds (37 of 37 `OK`; file sets equal, 35 + `pyproject.toml` + `uv.lock`) |
| 3 | 04 and 05 records new, finished, 0 errors, model and tokens; 00 01 02 03 06 untouched | holds |
| 4 | Saved notebooks 04 and 05: no outputs, flags False, markdown-only differences | holds, with one note on four older markdown cells (below) |
| 5 | Rows: 0 names missing, new rows newer than marker, count per source | holds (1781 + 112 = 1893) |
| 6 | Spend table | 719 model calls of the cap 920; USD 4.54 as a lower bound |
| 7 | Event table | below, agrees with the node reports |
| 8 | Suite | 608 passed, 2 failed (both allowed by name); with the deselect 607 passed, 3 deselected, exit 0 |
| 9 | Key scan with positive control | 0 hits in the real scan; control gave 3 hits and was removed |
| 10 | Id-spelling expectation predates the rows | holds (transcript timestamps; file mtimes alone could not show it) |

## 1. audit_live
`uv run --no-sync python -B Day03_new/tests/audit_live.py`: exit 0, last line `AUDIT OK`. Lines for the new records: 04 base 33 calls / 78,655 in / 15,637 out / 100 s; 04 exercises 36 / 89,251 / 16,060 / 109 s; 05 base 135 / 498,484 / 53,211 / 395 s; 05 exercises 435 / 1,605,783 / 147,758 / 1272 s. These equal the numbers in the live-04 and live-05 reports.

## 2. Code unchanged
`cd <repo root> && shasum -a 256 -c P/c2-code-hashes.txt`: 37 lines, 37 `OK`, 0 mismatch. The hash file lists 35 `.py` files under `Day03_new/mas_lab`, `Day03_new/rag_lab`, `Day03_new/tests`, plus root `pyproject.toml` and `uv.lock`. A `find` of those three directories (excluding `__pycache__`) gives the same 35 paths: no file was added or removed. 34 `__pycache__` entries exist; they are ignored by the rule and my own runs used `-B`.
Scope drift: files in the repository newer than the start marker (20:28:30), outside `Day03_new/outputs`, `Day02_new`, `.git`, `.venv` and `.claude/dag`: `Day03_new/04-Graph-Engineering.ipynb` and `Day03_new/05-Choosing-Multi-Agent.ipynb` (the two markdown edits), `AGENTS.md` and `CURRICULUM.md` at the root, and `Day07_new/*`. `Day03/` has no newer file. The root `AGENTS.md`, `CURRICULUM.md`, `Day07_new` and `Day02_new` changes are other sessions' work, not this run's (no node of this run names them; I did not trace who wrote them).

## 3. Records
Marker `P/run-c2-start-marker` = 20:28:30.

| record | mtime of `.json` | newer than marker | finished | errors | usage lines | model in every line | input tokens non-null | `.json` totals = usage lines |
|---|---|---|---|---|---:|---|---|---|
| 04-Graph-Engineering | 20:30:37 | yes (all 3 files) | true | 0 | 33 | `claude-sonnet-5-5` | yes | yes (78,655 / 15,637) |
| 04-Graph-Engineering.exercises | 20:32:37 | yes | true | 0 | 36 | `claude-sonnet-5-5` | yes | yes (89,251 / 16,060) |
| 05-Choosing-Multi-Agent | 20:45:00 | yes | true | 0 | 135 | `claude-sonnet-5-5` | yes | yes (498,484 / 53,211) |
| 05-Choosing-Multi-Agent.exercises | 21:06:21 | yes | true | 0 | 435 | `claude-sonnet-5-5` | yes | yes (1,605,783 / 147,758) |

Also: every cell has status `ok` (42 cells in each 04 record, 35 in each 05 record); the four `.executed.ipynb` have 0 error outputs; per-cell `model_calls` sum equals the usage lines in all four. `outputs/design_log.json` and `outputs/baseline/01.json` are byte-identical to the preflight copies. `check_notebook.py --minutes 60` prints `OK` for both saved notebooks (static file check, I ran it).

Records not newer than the marker (all older, none touched by this run): 00-Setup (00:19), 01 (17:06 / 17:09), 02 (17:14 / 17:17), 03 (17:24 / 17:27), 06 (01:52 / 02:06).

Their `mas_lab` code differs from what they ran with. Method: mtime of each `mas_lab` module against the record time, over the modules the notebook's code cells import (static import closure, followed through `mas_lab` itself). `mas_lab` mtimes: `hybrid.py` 14:32, `structures.py` 14:44, `runner.py` 15:40, `gate.py` 19:24, `workers.py` 19:39, `exa.py` 20:04.
- 00-Setup (record 00:19): `hybrid`, `structures`, `runner`, `gate`, `workers`, `exa` all changed after it.
- 01, 02, 03 (records 17:06 to 17:27): `gate.py` and `workers.py` changed after them (the `gate.py` id-spelling work and the `workers.py` recovery); `hybrid`, `structures`, `runner` were already in place.
- 06 (records 01:52 / 02:06): `exa.py` and `workers.py` changed after them.
- 04 (20:30 / 20:32) and 05 (20:45 / 21:06): no `mas_lab` module in their closure is newer than the records; the records ran on the current `gate.py`, `exa.py` and `workers.py`.
So the sentences saved in notebooks 00 to 03 and 06 were not re-checked against the current code by this run and are outside this run's goal. Limit: this is mtime evidence; `Day03_new` is untracked by git, so no hash of the old code exists.

## 4. Saved notebooks 04 and 05
- Outputs: 0 output items and 0 cells with an `execution_count` in both.
- Flags: 04 has `RUN_EXERCISE = False` (cell 56) and no `RUN_OPTIONAL`; 05 has `RUN_OPTIONAL = False` (cell 1) and `RUN_EXERCISE = False` (cells 48, 50, 52).
- Against the pre-edit copies the nodes took (`P/live-04-c2-nb-before.ipynb`, `P/live-05-c2-nb-before.ipynb`): exactly one cell differs in each, both markdown: 04 cell 19, 05 cell 34. That is what the live-04 and live-05 reports say.
- Against the new executed base notebooks in `outputs/live/`: the same single cell (19 and 34). The new exercises executed copies differ only by those cells and the flag cells (04: cell 56; 05: cells 1, 48, 50, 52), as designed.
- Against the OLD executed copies in `P/live-before-c2/`: more markdown cells differ than the nodes named: 04 cells 19 and 50; 05 cells 15, 20, 34, 44. No code cell differs. The extra four (04:50, 05:15, 05:20, 05:44) are older edits with a written source each: 04 cell 50 is the edge-legend edit (`P/edge-legend-notes.md:17`, written 20:02); 05 cells 15, 20 and 44 are the edits of the previous live-05 node, listed in `P/live-05-notes.md:27` (cell 15), `:30` (cell 20) and `:39` (cell 44), written 18:18, after that node's records (17:49 and 18:09). The "Now reads" text in those notes is the text now in the saved notebook for the three cells (checked for the new wording of each). They are already in the pre-edit copies taken at node start (20:28:56 and 20:38:21). The transcript of this run's live-05 node (`<transcript>`) shows one `cmp` of the saved notebook against its pre-edit copy at 21:06:34 ("unchanged") and one write to the notebook, the cell 34 edit script at 21:09:51 (the notebook's mtime is 21:09:51); the live-04 and preflight transcripts show no write to the 05 notebook. So nothing in this run changed those cells, and after the rerun the new executed copies match the saved notebooks everywhere except the two edited cells.
- The `.executed.ipynb` of 04 and 05 hold the text of cell 19 and cell 34 as it was at run time, because the edits came after the runs (04 notebook 20:34, 05 notebook 21:09). Expected.
- The two edited sentences, checked: 04 cell 19 now says `180000` and `150000`; the new base output prints `150000` (the column spelling), so the old comma form could not be found there. 05 cell 34 says `dropped`, `recovered`, `filled` as `workers.py:151-170` computes them (`dropped` = refs with no registered id, `recovered` = kept ids not literally in the model's refs, `filled` = own ids added only when `result.facts` is non-empty and nothing was kept). One wording risk, see finding F1.

## 5. Rows
`ls Day03_new/outputs/runs` = 1893 files, 0 sub-directories. Against `P/runs-before-c2.txt` (1781): 0 names missing, 112 new. No pre-existing row file has an mtime newer than the marker (none modified). All 112 new rows are newer than the marker. All parse as JSON and `run_id` equals the file name. Status: 108 `ok`, 4 `budget_exceeded`, 0 `model_error`.
Method for the per-source count: the row files carry no cell index, so each new row is assigned by its mtime to the window between the record files' own times: 04 base = 20:28:30 to the 04 base record time (20:30:37); 04 exercises = to 20:32:37; 05 base = from the live-05 start marker (20:38:21) to 20:45:00; 05 exercises = to 21:06:21; ops-log = after `P/ops_log2_start_marker` (21:23:41). Every new row falls in exactly one window; the two gap windows hold no row.

| source | rows | expected |
|---|---:|---:|
| 04 base | 1 | 1 |
| 04 exercises | 1 | 1 |
| 05 base | 22 | 22 |
| 05 exercises | 79 | 79 |
| ops-log repeat 2 | 9 | 9 (the nine ids in `P/ops_log2_runs.json` are all among them) |
| total | 112 | 112 |

The three id-spelling rows are not in `Day03_new/outputs/runs`: the runner wrote them to `P/idspell_root/outputs/runs/` (3 files, none present in `Day03_new/outputs/runs`). The id-spelling notes say so (`id-spelling-rows-notes.md`, Scope and spend). See finding F2.

## 6. Spend
`uv run --no-sync python -B Day03_new/tests/cost_report.py > P/cost-report-c2.txt` (exit 0). That file lists all 13 records in `outputs/live` (989 calls, 3306.0 s, USD 7.1789); it is the sum of the whole folder including the unchanged 00 to 03 and 06 records, so it is NOT this run's spend.
This run's spend, built with `cost_report.read_rows` (records) and `cost_report.cost_usd` (rows that are not in any usage file: the id-spelling and ops-log rows, from the `input_tokens`, `output_tokens` and `cache_read_tokens` fields of each row file). The old figures come from `P/live-before-c2/`.

| item | calls now | calls replaced record | seconds now | seconds replaced | USD now | USD replaced |
|---|---:|---:|---:|---:|---:|---:|
| 04-Graph-Engineering | 33 | 34 | 100.4 | 104.2 | 0.2380 | 0.2421 |
| 04-Graph-Engineering.exercises | 36 | 36 | 109.0 | 103.8 | 0.2197 | 0.2271 |
| 05-Choosing-Multi-Agent | 135 | 145 | 394.6 | 412.2 | 0.9216 | 0.9379 |
| 05-Choosing-Multi-Agent.exercises | 435 | 460 | 1272.2 | 1238.1 | 2.6047 | 2.6589 |
| subtotal, four records | 639 | 675 | 1876.2 | 1858.3 | 3.9840 | 4.0660 |
| id-spelling rows S1 S2 S3 (3 rows, 9 + 7 + 9 calls) | 25 | | 61.3 | | 0.1901 | |
| ops-log repeat 2 (9 rows) | 55 | | 142.1 | | 0.3650 | |
| **total this run** | **719** | | **2079.6** | | **4.5391** | |

Against the announced figures and the cap:
- Announced about 760 calls (04 about 70, 05 about 605, id-spelling about 27, ops-log about 60) and about USD 5. Used 719 calls = 94.6 percent of 760; USD 4.54.
- Cap 920 (per-node limits 100 + 700 + 40 + 80): used 719 = 78.2 percent. By node: 04 used 69 of 100; 05 used 570 of 700; id-spelling used 25 of 40; ops-log used 55 of 80. No cap was exceeded: the cap holds.
- Recount from the files: the four usage files have 33, 36, 135 and 435 lines (639); the three id-spelling row files sum to 25 (`idspell_total.json` says 25); the nine ops-log rows sum to 55 (I checked that each row's `budget.model` equals its `model_calls`).
- The USD is a lower bound. `cost_report.py` has no cache-write price ("캐시 쓰기 단가는 모델링하지 않았다", `Day03_new/tests/cost_report.py:76`) and the usage lines carry no cache-write tokens (the `UsageLog` writes only `cache_read` from `input_token_details`, `Day03_new/rag_lab/settings.py:94-96`), so any cache-write charge is missing. The only prices used are the repository's `PRICES` entry for `claude-sonnet-5-5` (input 2.00, output 10.00, cache read 0.20 per million tokens, `cost_report.py:16`). I added no price from outside the repository and no estimate of the missing part.
- Calls I cannot see: a call that left no usage line and no row (for example a failed request) would not appear in any file. A pattern scan of the Bash commands in the transcripts of live-04, live-05, id-spelling-rows, ops-log-repeat-2 and preflight-c2 (patterns such as `run_live`, `make_model`, `run_case`, `.invoke(`) found no model-running command besides the runs counted above (the preflight one only prints the key status).

## 7. Events, from the row files
Each new row file read for `events`. `worker_checked` values: `dropped` counts refs in the list, `filled` and `recovered` are the integers in the event. Source is by the windows of check 5; the id-spelling rows are read from `P/idspell_root/outputs/runs`. Saved as `P/verify-c2-events.json`.

| source | rows | status budget_exceeded | event budget_exceeded | gate_skipped | earlier_turn_proposal_ungated | gate_text_replaced | gate_text_appended | worker_checked | dropped | filled | recovered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 04 base | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 9 |
| 04 exercises | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 |
| 05 base | 22 | 1 | 0 | 2 | 0 | 0 | 0 | 11 | 1 | 0 | 12 |
| 05 exercises | 79 | 3 | 0 | 8 | 0 | 0 | 10 | 33 | 0 | 0 | 10 |
| ops-log repeat 2 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 0 | 17 | 24 |
| id-spelling (in P) | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 6 | 0 | 0 | 0 |
| total | 115 | 4 | 0 | 10 | 0 | 3 | 10 | 70 | 1 | 17 | 55 |

- `worker_checked` with non-empty `problems`: 0 of 70. `model_error` rows: 0.
- `budget_exceeded` is a row status here (no event of that kind exists): 05 base 1 (cell 42, budget 2), 05 exercises 3 (cell 42, and the supervisor and hybrid rows of cell 50). 04 has none in its row files.
- Agrees with the node reports: live-04 (recovered 9 on the base policy Worker, 0 elsewhere), live-05 (gate_skipped 2 / 8, gate_text_appended 0 / 10, worker_checked 11 / 33, dropped 1, recovered 12 / 10), ops-log (14 events, filled 17 from row 6, recovered 12 + 12 from rows 4 and 7), id-spelling (one `gate` probe and one `gate_text_replaced` per row, no `gate_skipped`).
- Ops-log rows re-read one by one: 9 rows, all `ok` and `answered`, calls 6 3 6 8 3 6 10 7 6 = 55, same cited documents and refs counts as the node's table; row 6 is the one with `fail 인용 문서` (cited billing-policy and travel) and the one fill.
- Id-spelling rows: all `ok`, `denied`, ledger 0, `policy_violations` [], `usage_missing` 0.

## 8. Suite
From `Day03_new`: `../.venv/bin/python -B -m pytest tests -q -p no:cacheprovider`.
- Full: 610 collected, **608 passed, 2 failed** (6.6 s, exit 1). Output in `P/verify-c2-pytest-full.txt`.
- Failing ids: `Day03_new/tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]` and `Day03_new/tests/test_layout.py::test_rag_lab_copies_are_byte_identical[evidence.py]`. `[corpus.py]` passes. Both failing ids are the allowed name; no other test failed.
- With `--deselect Day03_new/tests/test_layout.py::test_rag_lab_copies_are_byte_identical` (exactly the plugin check's command): **607 passed, 3 deselected**, exit 0 (`P/verify-c2-pytest-deselect-taskform.txt`). Note for the next reader: the deselect string needs the `Day03_new/` prefix. The pytest rootdir is the repository root, so node ids start with `Day03_new/tests/...`, although the failure summary prints `tests/...`. With `--deselect tests/test_layout.py::...` nothing is deselected and the run fails again (checked, `P/verify-c2-pytest-deselect-relform.txt`).
- Which files differ: `Day03_new/rag_lab/retrieval.py` (67 changed diff lines against `Day02_new/rag_lab/retrieval.py`; the Day02_new copy was written 11-01 20:12) and `Day03_new/rag_lab/evidence.py` (71 lines; Day02_new copy 11-01 20:23). `corpus.py` is identical. No file in `Day02_new/rag_lab` is newer than the run marker, so this run did not touch them; `Day02_new` belongs to another active session, and the author decided that this test stays red until it settles. It is not a finding.
- The suite made no change in the project: the runs directory still has 1893 files and no file in `Day03_new` is newer than the suite start.

## 9. Key scan (counts only, no value printed)
Script: `P/verify_c2_keyscan.py` (the needle logic of `P/verify_b1_keyscan.py`; it also reads `Day03_new/.env` in process only). Needles: 4 (2 secret entries with a value of at least 12 characters, each as the full value and its last 12 characters).

| scope | files | hits |
|---|---:|---:|
| `Day03_new/outputs` | 1934 | 0 |
| P, files newer than `run-c2-start-marker` | 60 | 0 |
| extra: `Day03_new` top level without `.env`, `docs`, `mas_lab`, `rag_lab`, `tests`, `skills` | 51 | 0 |
| generic key shapes (`sk-ant-`, `sk-or-`, `Bearer`, `x-api-key`) over the first two scopes | 1994 | 0 |

Positive control: a control file with two needles was written under P, the scan found 3 needle hits, all in that file (full value of one key, last 12 of both), and the file was removed (`removed: True`, and `ls` confirms). So the scan can see the needles and the real result of 0 is meaningful. Output in `P/verify-c2-keyscan.out`.
Rescan after these notes were written (`P/verify-c2-keyscan-rescan.out`): `Day03_new/outputs` 1934 files, 0 hits; P newer than the marker 62 files (now including these notes, the audit and pytest outputs, the cost report and the events file), 0 hits; extra scope 51 files, 0 hits; no control file left.

## 10. Id-spelling expectation predates the rows
- File order in `P/id-spelling-rows-notes.md`: `## Expected before any run` at line 14, `## Run record (written AFTER the runs)` at line 32, `## Match with the expectation` at line 138. The Run record part is appended by `P/idspell_notes_gen.py`, whose first output is that heading.
- File mtimes cannot show it on their own: the rows are 21:18:15, 21:18:35, 21:18:56, but the notes (21:20:44) and the `pre-results` copy (21:20:32) are both later, because the copy was made after the run.
- The node transcript (`<transcript>`, UTC + 9 h) gives the order: runner written 21:15:52 (start marker the same second); notes with the expectation written 21:16:18 (Write); expectation amended once 21:17:49 (Edit, the pre-gate `denied` branch); run command 21:17:53; rows 21:18:15 to 21:18:56; generator 21:20:03; `cp notes pre-results.md` 21:20:32 (made before the run record was appended, so it holds the pre-run text); one `sed` citation fix 21:20:44.
- Content proof: the text of the Write (21:16:18) with the one Edit (21:17:49) applied is byte-for-byte equal to `pre-results.md` (compared from the transcript), and the Edit's `new_string` appears verbatim in `pre-results.md`. The transcript lists exactly one Write and one Edit to the notes before the run (a second transcript record with the same tool-use id is a duplicate of the Edit, not a second edit).
- `diff` of the Expected sections of `pre-results.md` and the final notes: one line only, the citation `gate.py:52-53` became `gate.py:55` (checked: `gate.py:55` holds `checkable`). The expectation itself did not change after the rows.
- One part: the only change between the first draft and the run was the 21:17:49 amendment, made 4 seconds before the run command and before any row existed. The notes state it (Ruling 2).

## Findings and observations (none blocks the verdict)
- F1. The cell 34 sentence in 05 says `filled`는 ... 결과를 ... 채운 수. The event value is the number of refs added (`filled=len(filled)`, `Day03_new/mas_lab/workers.py:169`: 17 in ops-log row 6), not a number of results. "채운 수" can be read either way. Suggestion for the author: say "채워 넣은 근거 참조의 수". Not changed here (outside this node's scope).
- F2. The three id-spelling rows exist only under `P/idspell_root/outputs/runs/` (the scratchpad), not under `Day03_new/outputs/runs`. That matches the node's design, and the verbatim texts and event details are in `P/id-spelling-rows-notes.md`. If the author wants the rows to live in the repository they need to be copied; the scratchpad is session-local.
- F3. `P/cost-report-c2.txt` totals the whole `outputs/live` folder (989 calls, USD 7.1789), including five record groups from earlier runs. Read this run's spend from the table in section 6.
- F4. Two numbers in the node reports deserve a careful reader: live-04's per-cell announce margin is zero for cells 15 and 22 (3 and 2 calls, deterministic); live-05's `recovered` 12 and 10 on the hybrid complex-ops-log policy Worker reach 24 in the ops-log rows. Both are recorded values, not defects, and the rows ended `ok` with `problems` empty. I did not investigate causes.
- F5. The ops-log probe borrowed helpers from `tests/test_structures.py`, which imports `mas_lab.evaluation` at line 15. I checked the two run scripts: `ops_log_run2.py` states it does not import `mas_lab.evaluation`, and `id_spelling_run.py` has no `gold` or `evaluation` reference. The reader `ops_log2_report.py` imports the module and prints only pass flags and failed column names.
- F6. Sentences in notebooks 04 and 05 other than the two edited ones were not re-judged by me one by one. I relied on the live nodes' tables for those (their per-paragraph audits), and spot-checked the two changed sentences, the event totals, the counts and the spend against the files.

## Rulings
- Ruling: counted the new rows per source by mtime windows bounded by the record file times and the start markers, because the row files hold no cell index - the counts equal the expected 1 / 1 / 22 / 79 / 9 and the gap windows are empty - cost if wrong: one row could sit in the neighbouring 04 or 05 window.
- Ruling: judged check 4 as holding although the saved notebooks differ from the OLD executed copies in four markdown cells the nodes of this run did not name - each of the four has a written earlier source (edge-legend notes for 04:50, the previous live-05 notes for 05:15, 20, 44), they are in the pre-edit copies taken at node start, and the new executed copies match - cost if wrong: a stricter reader wanting the old-copy diff to be only 19 and 34 would mark check 4 as failed.
- Ruling: judged check 10 as holding on the transcript timestamps and the diff of the Expected sections, not on file mtimes - the mtimes of the notes and the pre-results copy are later than the rows, so they prove nothing either way - cost if wrong: if the transcript timestamps are not accepted as evidence, check 10 cannot be shown from the files alone.
- Ruling: put the id-spelling rows into the spend and the event table from `P/idspell_root` and did not require them in `Day03_new/outputs/runs` - check 5 compares only the repository folder, and the id-spelling node declared the separate root - cost if wrong: a reader expecting 115 rows in the repository folder finds 112.
- Ruling: used `Day03_new/tests/cost_report.py` functions to price the row-based items rather than writing my own prices - only the repository's prices may be printed - cost if wrong: the row-based USD uses the same input-includes-cache-read convention as the report; a different convention would move it by cents.
- Ruling: took the allowed failure to be exactly the two failing parametrized ids and did not treat `[corpus.py]` (passing) as relevant - the task allows the name `test_rag_lab_copies_are_byte_identical[...]` - cost if wrong: none.

Verify C2: PASS
