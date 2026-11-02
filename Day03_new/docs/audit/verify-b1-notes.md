# Verify B1 (run dag_mvxjjtgg_181ytn, node verify-b1, attempt 1)

P = <P>. Checked 2026-11-01 18:50 to 19:00. Work dir <repo>, `uv run --no-sync`. No notebook run, no model call, no EXA call, no project file written. `.env` values never printed.

## Summary

- The paid rerun's records are real and complete. `audit_live.py` prints AUDIT OK, 937 usage lines are all `claude-sonnet-5-5` with non-null input tokens, 124 new row files (0 deleted), saved notebooks have no outputs and the switches are False.
- Spend: 1,120 model calls and USD 6.85 (lower bound), against the announced about 1,120 / USD 7 and the cap of 1,370. No node reran a record.
- Two things outside the records are red or non-zero, so the verdict is FAIL (reasons below, both external to this run):
  1. Full suite: `2 failed, 501 passed`. The two failures are `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]` and `[evidence.py]`. Another session edited `Day02_new/rag_lab/retrieval.py` (17:24:34) and `evidence.py` (18:00:29) after the preflight; `Day03_new/rag_lab` was not touched. The clean clone at 17:05 had 503 passed on the earlier Day02_new state.
  2. Key scan: 0 hits in `Day03_new/outputs` and in every scratchpad file written after the marker, but 1 file in the scratchpad older than the marker holds both keys: `P/silent_corners/pre/Day03_new/.env` (mtime 10-31 23:47, a pre-run snapshot made by an earlier node). Not produced by this run; not deleted by me (another node's evidence).

## 1. audit_live and the two untouched notebooks

`uv run --no-sync python Day03_new/tests/audit_live.py`, last lines:
```
05-Choosing-Multi-Agent: 모델 145회, 입력 553,807, 출력 53,579, 412초
05-Choosing-Multi-Agent.exercises: 모델 460회, 입력 1,760,800, 출력 147,281, 1238초
06-Lab-Research-Agents: 모델 26회, 입력 134,754, 출력 33,855, 199초
06-Lab-Research-Agents.exercises: 모델 59회, 입력 270,799, 출력 72,381, 388초
AUDIT OK
```
- 00 and 06 not rerun: `outputs/live/00-Setup.*` mtime 00:19:58; `06-Lab-Research-Agents.*` 01:52:05 and 02:06:43; marker `P/run-b-start-marker` is 17:03:00. Their 3 and 85 calls are the old records, not spend of this run.
- Gate import: neither saved notebook names the gate directly. A regex for `gate|structures|check_named_payment|hybrid|runner` over their code cells finds 0 hits in 06 and 1 hit in 00 (cell 16, `from mas_lab.runner import make_desk`). Precisely: 00 loads `mas_lab/gate.py` as a side effect of that import (`runner.py:16` imports `structures`, which imports `gate`), but calls only `make_desk` and a read-only billing Deep Agent; it never calls `gate_answer` or `run_case`. 06 imports `mas_lab.{contracts,exa,research,trace,view,workers}`; none of these imports `gate` (checked the import lines), and it uses only `allowlist_middleware` and `DENY_WRITES` from `workers.py`, whose lines 34-73 are identical to `P/refs_dev/workers.before.py` (the 14:32 edit added `checked_worker`, `_run_with_messages`, `delegation_spans`).
- `audit_live.py:54-55` runs `stale_cells` on every stem whose record has `exercises` false, which includes 00 and 06; it passed, so their saved code equals their executed copy (AUDIT OK).
- Records are on the current code: every `mas_lab/*.py` mtime is before the marker (newest `gate.py` 16:36:20), and the `runner_source` slice printed by 01 cell 35 equals the current `runner.py` slice in both 01 records (3955 characters).

## 2. Spend (cost_report saved at P/cost-report-b1.txt)

Per record, this run versus the record it replaced (`P/live-before`, same `read_rows`/`cost_usd` from `tests/cost_report.py`). USD uses input, output and cache-read prices only.

| record | calls new / old | seconds new / old | USD new / old | input tokens (cache read) new | output new |
|---|---:|---:|---:|---:|---:|
| 01 base | 45 / 40 | 142.5 / 122.6 | 0.2472 / 0.2147 | 187,572 (146,931) | 13,658 |
| 01 exercises | 52 / 50 | 172.6 / 158.9 | 0.2792 / 0.2645 | 224,125 (186,517) | 16,665 |
| 02 base | 33 / 32 | 106.8 / 104.3 | 0.2466 / 0.2354 | 114,568 (69,118) | 14,183 |
| 02 exercises | 51 / 49 | 164.3 / 154.3 | 0.3236 / 0.3431 | 158,291 (110,519) | 20,592 |
| 03 base | 37 / 38 | 110.6 / 128.0 | 0.2307 / 0.2535 | 83,351 (47,769) | 14,999 |
| 03 exercises | 44 / 43 | 135.8 / 138.5 | 0.2805 / 0.2995 | 111,776 (74,757) | 19,149 |
| 04 base | 34 / 36 | 104.2 / 114.8 | 0.2421 / 0.2472 | 84,368 (48,661) | 16,098 |
| 04 exercises | 36 / 38 | 103.8 / 110.6 | 0.2271 / 0.2285 | 88,995 (61,100) | 15,912 |
| 05 base | 145 / 136 | 412.2 / 393.3 | 0.9379 / 0.8747 | 553,807 (391,948) | 53,579 |
| 05 exercises | 460 / 473 | 1238.1 / 1235.4 | 2.6589 / 2.7671 | 1,760,800 (1,297,509) | 147,281 |
| subtotal 01-05 | 937 / 935 | 2690.9 / 2660.6 | 5.6738 / 5.7282 | 3,367,653 (2,434,829) | 332,116 |
| new-question-3 audit (14 rows, `P/newq3_total.json`) | 127 | 288.8 | 0.7668 | 397,930 (255,314) | 43,047 |
| complex-ops-log repeat (9 rows) | 56 | 155.2 | 0.4087 | 197,087 (118,560) | 22,798 |
| clean clone 00-Setup (steps 4 and 5) | 0 | | 0 | 0 | 0 |
| **total of this run** | **1,120** | | **6.85** | | |

- Against the plan: announced about 1,120 calls and USD 7; actual 1,120 and 6.85. Cap 1,370 (sum of node caps 120+110+110+100+700+150+80); 250 calls (18%) unused. Per-node use / cap: 01 97/120, 02 84/110, 03 81/110, 04 70/100, 05 605/700, new-question 127/150, ops-log 56/80.
- Cross-checks: usage lines per record equal the `model_calls` printed by audit_live for all 10 records (45, 52, 33, 51, 37, 44, 34, 36, 145, 460); newq3 row `calls` entries sum to 127 and ops-log to 56, equal to what those nodes report; model name is `claude-sonnet-5-5` in all 937 + 127 + 56 call entries.
- USD is a lower bound: `cost_report.py` has no cache-write price (its own footnote) and the usage lines carry no cache-write field. Cache writes are inside `input_tokens` (installed `langchain_anthropic/chat_models.py:3347-3354` adds `cache_read` and the ephemeral or `cache_creation` write counts to Anthropic's `input_tokens`), so they were priced at the plain input rate and the real bill is at or above 6.85. Size of the gap, my estimate and not from this repository: public Anthropic pricing charges 5-minute cache writes at 1.25 times the input rate, so if every uncached input token (1,153,967 across the three groups) had been a 5-minute write, the surcharge would be about USD 0.58 (ceiling about 7.43). Not verified: whether any call used the 1-hour cache (surcharge 2 times, so a higher ceiling), and what share of uncached tokens were writes. Quote 6.85 as a lower bound, not as the bill.
- Reruns: none. Every live note says "no rerun" (01, 02, 03, 04, 05); there is one log per run (10 logs); the row files outside the ops-log are exactly 115 and fall one-to-one into the 01, 04 and 05 run windows, so a second run of a row-writing notebook would show as extra files (none). 02 and 03 write no rows, so for those two the evidence is the node notes and the continuous mtimes only. The one deliberate repeat is the new-question row N4b (19 calls), already inside the 127. Not visible by any record: a run killed before it saved a usage file, and the overwritten usage of any record that was replaced twice.
- Wall time of the 10 records 44.8 minutes (new) against 44.3 (old).

## 3. Manifest, drift by owner, versions

`grep -v '^#' P/manifest-start.txt | shasum -a 256 -c -`: 209 entries. First run 18:51: 198 OK, 11 FAILED. Rerun 19:02: 196 OK, 13 FAILED, 0 missing (the other session also changed `Day02_new/05-Production-Agentic-RAG.ipynb` 19:01:21 and `06-Lab-DeepAgents-RAG.ipynb` 19:01:56; its `run_live.py` runs for those notebooks were active at 19:02, so the drift list is still growing).
- Root `pyproject.toml` sha256 59dfcfc2...5830c and `uv.lock` e39fee03...3ac4: match (and match the preflight values).
- Day03 (134 manifest entries): 0 differ; 0 files newer than the marker outside `.venv`/`.openviking`.
- Day02_new, owner: another session (a process `Day02_new/tests/run_live.py Day02_new/00-Setup.ipynb` was running at 18:50; the task names Day02_new as other sessions' files). 13 manifest entries differ, the first 11 of them: `00-Setup.ipynb` (18:52:37), `AGENTS.md` (18:04:47), `docs/DESIGN.md` (17:48:23), `rag_lab/agent.py` (17:29:45), `rag_lab/evidence.py` (18:00:29), `rag_lab/retrieval.py` (17:24:34), `rag_lab/settings.py` (17:24:34), `tests/test_rag_lab_api.py`, `test_rag_lab_evidence.py`, `test_rag_lab_retrieval.py`, `test_rag_lab_settings.py`. New since the marker (not in manifest): `rag_lab/{rerank,pipeline,phases,pages}.py`, five new test files, `benchmarks/{measure,make_sample_pdf}.py`, `data/pdf/credit-trend-chart.pdf`, `docs/retrieval_benchmarks.md`, 48 files under `outputs/`. The preflight PASS rule said "Day02_new/rag_lab: all 9 manifest files match; no new file", so this rule no longer holds.
- Day03_new, owner: this run. Newer than the marker outside `outputs/`: only the five notebooks 01-05 (17:11:13, 17:22:00, 17:29:16, 17:41:44, 18:18:58; markdown edits per the node notes, saved code equals the executed copy per audit_live). `mas_lab`, `rag_lab`, `tests`, `data`, `docs` untouched. `outputs/` newer: `live` 30 files, `runs` 124, `baseline/01.json`, `design_log.json`.
- Versions equal `P/versions-before.txt`: python 3.13.14, deepagents 0.7.32, langgraph 1.2.19, langchain-anthropic 1.7.7.
- Effect: `Day03_new/tests/test_layout.py:13-17` requires `Day03_new/rag_lab/{corpus,retrieval,evidence}.py` to be byte-identical to Day02_new's; `diff -q` now reports retrieval.py and evidence.py different (settings.py also differs but is not in that test; `agent.py` exists only in Day02_new). This is the whole reason for the pytest failures. I did not sync the copies: it would change Day03_new's student-facing module and the task says Day02_new is another session's.

## 4. Key scan (script `P/verify_b1_keyscan.py`, output `P/verify-b1-keyscan.out`; counts only)

Needles: 2 secret entries in `Day03_new/.env` (ANTHROPIC_API_KEY, EXA_API_KEY; the empty OPENROUTER entry is skipped), full value and last 12 characters = 4 needles. Scope: `Day03_new/outputs` and P, excluding `clone-src` and `clone-dst`.
- Positive control (a temporary file under P holding the full ANTHROPIC value and the EXA last 12): 7 hits (4 real + 3 control), control file removed.
- `Day03_new/outputs` (1,822 files): 0 hits for all 4 needles.
- P files newer than the marker (1,072 files at the 19:02 rerun, includes the clean-clone logs, `clone-step4-live` and these notes): 0 hits.
- P files older than the marker (21,330 files): 1 file with all 4 needles, `silent_corners/pre/Day03_new/.env` (a copy of the real `.env`, mtime 10-31 23:47, made by an earlier node). Not this run's output. It is a copy of a credential in scratch; clearing it is for the author, I did not touch it.
- Extra scope (Day03_new top-level files and docs, 14 files): 1 file, `.env` itself, as expected.

## 5. Row files and saved notebooks

- `ls Day03_new/outputs/runs | wc -l`: 1781; before 1657 (`P/runs-before-list.txt`); `comm` of the before list against now: 0 names missing, 124 new names, 124 files newer than the marker. Of the 124: 115 from the notebooks (01 base 6, 01 ex 6, 04 base 1, 04 ex 1, 05 base 22, 05 ex 79) and 9 from the ops-log repeat. 0 rows deleted.
- Saved notebooks 00-06: 0 code cells with outputs, 0 with execution_count; switches `RUN_EXERCISE=False` (01 x2, 02 x2, 03, 04, 05 x3, 06 x3) and `RUN_OPTIONAL=False` (05, 06).
- Post-marker rows: 124 files, 696 call entries all `claude-sonnet-5-5`, 0 rows with null input_tokens or `usage_missing` > 0, 0 rows with `model_calls` 0.

## 6. Event counts

Source: row files for run rows (assigned to a record by the record's time window, each row to exactly one record; sums match the live nodes' own counts), and the executed notebook text where noted. `budget_exceeded` = rows whose `status` is `budget_exceeded` (the executed outputs also print that word in tables, so output string counts are higher: 01 3 and 3, 04 14 and 14, 05 2 and 6, identical to the old records). New / old (old = rows in the old records' windows).

| record | rows | budget_exceeded | gate_skipped | earlier_turn_proposal_ungated | gate_text_replaced | gate_text_appended | worker_checked |
|---|---:|---:|---:|---:|---:|---:|---:|
| 01 base | 6 / 6 | 1 / 1 | 1 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 01 exercises | 6 / 6 | 1 / 1 | 1 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 02 base and exercises | no rows | 0 | 0 | 0 | 0 | 0 | 0 (not printed either) |
| 03 base and exercises | no rows | 0 | 0 | 0 | 0 | 0 | 0 (not printed either) |
| 04 base | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 3 / 0 |
| 04 exercises | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 3 / 0 |
| 05 base | 22 / 22 | 1 / 1 | 2 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 11 / 0 |
| 05 exercises | 79 / 79 | 3 / 3 | 8 / 0 | 0 / 0 | 0 / 0 | 10 / 0 | 33 / 0 |
| ops-log repeat | 9 | 1 | 0 | 0 | 0 | 0 | 15 |
| new-question-3 audit (14 rows) | 14 | 2 | 5 | 0 | 4 | 1 | 27 |

- Printed in the executed notebooks: only 05 prints event names (cell 32 `사건 순서` shows `gate_skipped` once and `worker_checked` three times in each of base and exercises). 01 contains the word `earlier_turn_proposal_ungated` once per record only as printed source code of `run_case` (cell 35), not as an event. 01, 02, 03 and 04 print none of the new event names; for 01 and 04 the counts above come from the row files.
- The new kinds `gate_skipped`, `gate_text_appended`, `worker_checked` did not exist in the old records, so old = 0 there is by construction, not a finding. `earlier_turn_proposal_ungated` is 0 in every row because it fires only in multi-turn cases and no notebook row runs one (the new-question N4 rows were two-turn but ended `budget_exceeded` in turn 2).
- The six notebook `budget_exceeded` rows (01: 1 + 1, 05: 1 + 3) are the by-design budget demonstrations and equal the old records. The three others are unplanned: ops-log row 2 and the new-question rows N4 and N4b, all on the search limit of 6.

## Audit for safe-but-wrong output

1. Requested kind: execution records from real model calls. Produced kind: the same. Evidence: 937 lines in `outputs/live/0[1-5]*.usage.jsonl`, 0 with a missing model or null `input_tokens`, one model `claude-sonnet-5-5`; 124 row files with 696 call entries, same model, 0 null input tokens. Model name and token counts come from `ModelMeter` of real calls; none of the rows has `model_calls` 0.
2. New input run again: read executed cell 35 of `outputs/live/01-Workflow-vs-Agent.executed.ipynb`. Its source is `runner_source = inspect.getsource(inspect.getmodule(run_case))` then `print(runner_source[runner_source.index("def run_case"):runner_source.index("def _finish_row")])`; its output begins `def run_case(structure: str, case: dict, *, model: BaseChatModel, repeat: int = 1, faults: dict | None = None,` and equals the present `mas_lab/runner.py` slice (both 01 records: True).
3. Missing data: `audit_live.py:27-28` appends `"{stem}: 실행본({stem}.executed.ipynb)이 없어 셀의 모델 호출을 예고와 비교할 수 없습니다."` when the executed copy is missing, and `test_audit_live.py:85-94` (`test_main_fails_once_per_stem_when_executed_notebook_is_missing`) asserts exactly one `FAIL` line containing `실행본` and `비교할 수 없`, and last stdout line `AUDIT FAIL 1건`. `cost_report.py:82-83` prints "...usage.jsonl이 없습니다." and returns 1 when no usage file exists; a model without a price shows `단가 미확인` and a partial total (`cost_report.py:20`).
4. Check that would fail on wrong behavior: `audit_live.py:37` (`예고 {sum(declared)}회, 실측 {n}회로 예고를 넘습니다`), pinned by `test_audit_live.py:38-44` with cases (8, 9) and (160, 277); `audit_live.py:51` (`저장본의 코드가 실행본과 다릅니다. 다시 실행해야 합니다.`) would fail if a code cell were edited after the run; `audit_live.py:42-43` fails below 90% cells with output. My independent checks that would fail on wrong spend: usage lines per record equal `model_calls` of the record json (10 of 10), and the printed `runner_source` slice equals the current file.
5. Shortfall in items 1-4: none. The red items (pytest, key scan in an older scratch file, Day02_new drift) are outside items 1-4 and are listed in the Summary.

## Suite result

`cd Day03_new && ../.venv/bin/python -B -m pytest tests -q -p no:cacheprovider`: `2 failed, 501 passed in 6.18s` at 18:52 and again `2 failed, 501 passed in 6.20s` at 19:02:40 (same two tests; `cmp` of `rag_lab/retrieval.py` and `evidence.py` shows different, `corpus.py` identical; Day02_new `retrieval.py` mtime 17:24:34, `evidence.py` 18:00:29). `audit_live.py` at 19:02:40: AUDIT OK. Root hashes at 19:02:40 unchanged. The plugin check expects a last line matching `^\d+ passed`, so it cannot match while Day02_new/rag_lab differs from Day03_new/rag_lab.

## Rulings

- Ruling: verdict FAIL although the records are clean - the task ties the verdict to checks 1, 3, 4, 5 and to a green full suite, and the suite is red (2 failed) and the preflight drift rule for `Day02_new/rag_lab` no longer holds - cost if wrong: a reader sees FAIL for a rerun whose records are sound; the body says exactly which parts are sound.
- Ruling: did not sync `Day03_new/rag_lab` with `Day02_new/rag_lab` - it is a student-facing module, Day02_new is another session's and still being written, and this node may not edit project files - cost if wrong: the suite stays red until the author or the other session reconciles the copies.
- Ruling: left `P/silent_corners/pre/Day03_new/.env` in place - it is an earlier node's evidence and the scan scope allows me to report, not clean - cost if wrong: a credential copy stays in `/private/tmp` scratch until the author clears it.
- Ruling: report USD 6.85 as a lower bound with a stated estimate for the gap - the repo logs no cache-write field and the 1.25 times rate is from public pricing, not from this repository - cost if wrong: the docs run quotes a number a few tenths of a dollar low.
- Ruling: for check 1, counted 00's transitive load of `gate.py` through `mas_lab.runner` as not importing the gate - the notebook only calls `make_desk` and never `gate_answer` - cost if wrong: 00's record could be argued stale against the gate, but its three calls use no gate code.
- Ruling: assigned row files to records by time window (end of the executed copy minus the record's seconds minus 20 s, earliest-ending window wins) - rows carry no notebook name - cost if wrong: a row near a window edge could move one record; the totals (115 + 9 = 124) and the live nodes' own counts match, so no row is left over.
- Ruling: took "clean-clone 00 calls" as 0 - `P/clone-step4-live/00-Setup.json` and the clone's own `outputs/live/00-Setup.json` both show `model_calls` 0 and `finished` false at the `require_key`/`require_exa_key` stop - cost if wrong: none seen, no usage file exists in the clone.

## Next (for whoever retries)

No notebook rerun is needed. Reconcile `Day03_new/rag_lab/retrieval.py` and `evidence.py` with `Day02_new/rag_lab/` once the Day02_new session finishes (`Day03_new/tests/test_layout.py:13-17` is the contract), or decide to relax that test, then rerun `cd Day03_new && ../.venv/bin/python -B -m pytest tests -q -p no:cacheprovider` and the manifest recheck. Clear `P/silent_corners/pre/Day03_new/.env`.

Verify B1: FAIL
