# Ops log repeat (node ops-log-repeat)

Question: with `checked_worker` in place, do Worker results still reach the writer with no evidence references? Observation only; nothing was fixed.

## Scale and cap
- Printed first: "Scale: about 72 model calls (9 hybrid runs on complex-ops-log, about 8 each), cap 80."
- Ran `mas_lab.runner.run_case("hybrid", case, model=make_model(), repeat=i)` for i = 1..9 in one script (`ops_log_run.py`), one after another, from the repository root with `uv run --no-sync`. A 0-call preflight showed the key is set (value never printed).
- Cap rule: stop before a run if the sum of row `model_calls` plus 10 would pass 80. It did not trip: the largest check was before repeat 9 (50 + 10 = 60). No budget was raised (`FIXED_BUDGET` untouched).
- Total: 56 model calls, 155.2 s of run time. `budget["model"]` equals `model_calls` in all 9 rows.
- Files: script `ops_log_run.py`, state `ops_log_runs.json`, console log `ops-log-run.log`, readers `ops_log_report.py`, `ops_log_report2.py`, `ops_log_report3.py` (0 calls; outputs `ops-log-report.out`, `ops-log-report2.out`, `ops-log-report3.out`). The run script does not import `mas_lab.evaluation`; only the readers do, and they print the pass flag and failed column names, never the answer key.

## Rows (9 new row files for this pair, all written by this node)
Columns: repeat, run_id, status, outcome, model calls, seconds, Router path, len(evidence_refs), `worker_checked` events (role: filled/dropped), `validate` events, writer rewrote, budget_exceeded, automatic check (failed columns).

| # | run_id | status | outcome | calls | sec | Router path | refs | worker_checked | validate | rewrote | budget_exceeded | auto check |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 65da339eb6e045b2a7c9646f0c30e21c | ok | answered | 3 | 7.9 | fast | 5 | none (no Worker on fast) | 1, no problems | no | no | pass |
| 2 | 3da387ffd9e343609b5e2e4127ef6a01 | budget_exceeded | None | 9 | 21.7 | slow[outage,policy] | 0 | 1 (outage: 0/0); policy Worker never returned | 0 | no (writer never ran) | yes (search limit 6 reached) | fail (outcome, 필수 사실, 인용 문서, 실행 상태) |
| 3 | 41cf3b5103d642e89aac2b98a03e8af0 | ok | answered | 6 | 18.6 | slow[outage,policy] | 6 | 2 (outage 0/0, policy 0/0) | 1, no problems | no | no | pass |
| 4 | e148c903c1e04886a1100fca76b36d34 | ok | answered | 6 | 15.8 | slow[outage,policy] | 6 | 2 (outage 0/0, policy 0/0) | 1, no problems | no | no | pass |
| 5 | c7b3653c9fa245cdb73c1b265dbc9634 | ok | answered | 6 | 15.5 | slow[outage,policy] | 6 | 2 (outage 0/0, policy filled 17 / dropped 0) | 1, no problems | no | no | fail (인용 문서) |
| 6 | 88029694bab3457f8995b0cfcc1d5761 | ok | answered | 7 | 16.4 | slow[outage,policy] | 6 | 2 (outage 0/0, policy filled 18 / dropped 0) | 1, no problems | no | no | fail (인용 문서) |
| 7 | 8651f08408294378a59fff84a7223377 | ok | answered | 7 | 25.1 | slow[outage,policy] | 2 | 2 (outage 0/0, policy filled 18 / dropped 10) | 1, no problems | no | no | fail (인용 문서) |
| 8 | 0ef56a500fef418d925ce3edf1aa9c34 | ok | answered | 6 | 18.2 | slow[outage,policy] | 5 | 2 (outage 0/0, policy filled 17 / dropped 8) | 1, no problems | no | no | pass |
| 9 | 188d46de36d749788c8637a01fc8e0ef | ok | answered | 6 | 16.0 | slow[outage,policy] | 5 | 2 (outage 0/0, policy 0/0) | 1, no problems | no | no | pass |

Totals for these 9 rows: status ok 8, budget_exceeded 1. Outcome answered 8, none 1, insufficient 0. `evidence_refs` empty in 1 row (row 2, which ended before any answer). Writer rewrote in 0 rows. `validate` events 8, with problems 0. `worker_checked` events 15 in 8 rows. Automatic check passed in 5 of 9 rows.

Router path was `fast` in 1 row (row 1, 3 model calls) and `slow` with roles outage and policy in 8 rows. "Rewrote" means the `writer` span ran more than once; row 1 used the `fast` writer and has no `writer` span.

## What the `worker_checked` events show (the refs finding)
The row stores events, not the raw Worker result. The raw refs are inferred like this: `checked_worker` fills only when the Worker returned facts and no registered ref, so `filled > 0` with `dropped == []` means the raw refs were empty, and `filled > 0` with `dropped != []` means they were all unregistered.

- Worker result arrived with no refs at all and `checked_worker` filled them: 2 rows (rows 5 and 6), both the policy Worker, 17 and 18 refs filled.
- Worker result arrived with only unregistered refs, which were dropped and replaced by fills: 2 rows (rows 7 and 8), both the policy Worker, 10 and 8 refs dropped, 18 and 17 filled. The dropped ids were registered ids with a label in front, for example `runbook 탐지: E-fe73bd71207c`, so they did not match the bare id. This is a neighbouring cause, not "no refs".
- Still empty after the check (`근거 없이 complete입니다.` in `problems`): 0 events.
- Outage Worker: 8 events in 8 rows, 0 filled, 0 dropped. Every fill and every drop came from the policy Worker.
- `worker_checked` `problems` was empty in all 15 events.

Plain answer: yes, the direct cause was observed again. In 2 of 9 rows (2 of the 8 rows that ran Workers) the policy Worker's result had no refs when `checked_worker` received it. In both rows `checked_worker` filled the refs, so the writer received non-empty refs, `validate` raised nothing, there was no rewrite, and the outcome was `answered` with 6 final refs. In 2 more rows the policy Worker's refs were all unregistered and were also replaced by fills. Counting both kinds, `filled > 0` in 4 of 9 rows.

Limits of this reading: a Worker that returned empty refs and empty facts leaves no trace in the row, because `checked_worker` does not fill without facts. The writer's prompt is not stored, so "the writer received refs" is inferred from the post-check result, not read from the prompt.

## Comparison with the existing real rows of this pair
"Real" means a row with a call to claude-sonnet-5-5 with input tokens recorded (same test as `followup_rows.py`); 0 fake rows exist for this pair. Split by file mtime against `run-b-start-marker` (17:03). My 9 rows are excluded from both groups and are identified by run_id from `ops_log_runs.json`, not by mtime.

| group | rows | status | outcome | refs empty | writer rewrote | `answered` without refs flagged by validate | worker_checked events | budget_exceeded |
|---|---|---|---|---|---|---|---|---|
| before marker (mtime 00:27 to 10:23) | 20 | ok 20 | answered 14, insufficient 6 | 6 | 6 | 6 | 0 | 0 |
| after marker, not mine | 3 | ok 3 | answered 3 | 0 | 0 | 0 | 6 events in 3 rows (1 policy fill of 17, dropped 0) | 0 |
| after marker, mine | 9 | ok 8, budget_exceeded 1 | answered 8, none 1 | 1 (the budget_exceeded row) | 0 | 0 | 15 events in 8 rows (4 policy fills) | 1 |

- The 3 after-marker rows that are not mine were written by other nodes' notebook runs at 17:49, 17:55 and 18:06 (run ids starting `bd1311ed`, `e2496889`, `56948295`); none falls inside my run window. Together with mine, 12 rows ran after the marker: `insufficient` 0, `budget_exceeded` 1, fills in 5 rows (3 raw-empty, 2 all-unregistered).
- The 20 before rows all predate the 14:32 edit of `mas_lab/workers.py` and `mas_lab/hybrid.py`, so none can contain a `worker_checked` event. For them the only visible trace of the chain is: `evidence_refs` empty, a `validate` event with `근거 없이 answered입니다.`, a second writer run, then `insufficient`. All 6 `insufficient` rows show exactly that trace. They are the same 6 rows in every one of those counts. Whether each began with empty Worker refs cannot be read from them, only inferred; every one of the 6 had Workers (3 with the older Router label `out_of_scope` and three Workers, 3 `slow`).
- Router label in the before group: `out_of_scope` 7 rows (3 insufficient), `slow` 12 rows (3 insufficient), `fast` 1 row (0 insufficient). In the after-marker rows: `slow` 11, `fast` 1.
- The before group mixes several code versions (the 7 `out_of_scope` rows ran an older Router). It is a count of what was saved, not a controlled comparison. Counts only; nine rows cannot support a rate.

## Other things seen, not explained
- Citations after a fill: in 4 of the 5 post-marker rows with `filled > 0` (rows 5, 6, 7 and one not-mine row) the writer cited only `billing-policy` and `travel` documents, and the automatic check failed on `인용 문서`. The fifth (row 8) cited `runbook` and `security` and passed. In the 6 post-marker `ok` rows with no fill the check passed in all 6. The answers in rows 5 to 7 contained the required facts (`필수 사실` passed). This is a correlation in small counts; the cause was not tested. A fill adopts every `fact_ref` and `evidence_id` in the Worker's own tool results (17 or 18 ids, from a search that returns several documents), so `answered` stays legal even when the cited documents are not the ones the question needs. `worker-refs-notes.md` already listed citation precision as unmeasured.
- Row 2 ended `budget_exceeded` on the search limit (budget counts: 9 model, 12 tool, 6 search, 3 read; message `search 호출 한도를 초과했습니다.`). It is the only one of the 32 hybrid rows for this case (20 before, 3 after, 9 mine) whose search count reached 6; the other saved rows used at most 5. The cause is the policy Worker searching more than the fixed limit allows; it was not raised and was not investigated further.
- Row 1 took the `fast` path (3 calls) and passed; no Worker ran, so it says nothing about refs.

## Rulings
- Ran from the repository root. The preflight showed `require_key()` passes from there because `rag_lab.settings` reads `ROOT/.env`, not the working directory.
- Rows are told apart by run_id (state file), not by mtime, because other nodes also write rows to `Day03_new/outputs/runs`. The verify count reconciles: 9 new row files for this pair since my start marker, all 9 mine, 9 files added to the folder in total.
- "Arrived with no refs" is inferred from `filled > 0 and dropped == []` in `worker_checked`, since row files hold no raw Worker result.
- The cap used the sum of row `model_calls` as written in the task; it equals `budget["model"]` in all 9 rows, so both readings agree.

Ops log repeat: done
