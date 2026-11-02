# Ops log repeat 2 (node ops-log-repeat-2)

Question: with the current `checked_worker` (labelled refs recovered, empty refs filled with named ids first), what did each Worker really return, and how do these nine `hybrid` rows on `complex-ops-log` compare with the previous nine? Observation only; nothing was fixed and no project file was edited.

Nine rows on one day support no rate and no cause. Every count below is a count of what was saved in these rows. Read none of them as a frequency.

## Scale and cap
- Printed first by the script: "Scale: about 60 model calls (9 hybrid runs on complex-ops-log), cap 80."
- Ran `runner.run_case("hybrid", case, model=make_model(), repeat=i)` for i = 1..9, one after another, from the repository root with `uv run --no-sync` (`ops_log_run2.py`, a copy of `ops_log_run.py`).
- Total spent: 55 model calls (sum of row `model_calls`; equals `budget["model"]` in all 9 rows), 142.1 s of run time, 0 EXA calls. The 0-call probe and the readers made no model call.
- Cap rule (stop before a run if the sum of row `model_calls` plus 10 would pass 80) did not trip: the largest check was before repeat 9 (49 + 10 = 59). No budget was raised. Every row is kept; no row failed.
- Recorder: the script wraps `mas_lab.workers._run_with_messages` (in the script only). Each raw `WorkerResult` is appended to `ops_log2_raw.jsonl` with repeat, task id, `status`, `facts`, `evidence_refs`, the number of tool-result ids and the ids themselves, and the return value is passed through unchanged (a 0-call probe with a scripted model showed the wrapped `checked_worker` still returned the gate's result). Lines are passed through `_redact` and carry a `ts`. A patch guard stopped the run if a slow row wrote fewer than 2 raw lines; it never fired (slow rows wrote 2, fast rows 0, as expected).
- The run script does not import `mas_lab.evaluation`. Only the separate reader `ops_log2_report.py` does, and it prints the pass flag and the failed column names, never the answer key.
- Reconciliation: 9 files were added to `Day03_new/outputs/runs` between the pre-run list and the end, all 9 are mine by run_id (`ops_log2_runs.json`), none removed. Nothing else under `Day03_new` changed during the window. Files under `Day02_new` changed in the same window; they belong to another session and are not mine.

## Rows
Columns: n = repeat; run id; status; outcome; model calls; seconds; Router path; final `evidence_refs`; `worker_checked` events as role (dropped / filled / recovered); writer rewrote; `budget_exceeded`; automatic check (failed columns); cited documents.

| n | run_id | status | outcome | calls | sec | Router path | final refs | worker_checked (dropped/filled/recovered) | rewrote | budget_exceeded | auto check | cited documents |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | a9ec803b139a4220a70a3a7a02246962 | ok | answered | 6 | 16.4 | slow[outage,policy] | 6 | outage 0/0/0; policy 0/0/0 | no | no | pass | billing-policy, runbook, security |
| 2 | 31702a3e44494ac1a9a8913b946529bc | ok | answered | 3 | 8.0 | fast | 6 | none (no Worker on fast) | no | no | pass | runbook, security |
| 3 | 2f9d9c7c40154d0896327b63a124805a | ok | answered | 6 | 14.1 | slow[outage,policy] | 5 | outage 0/0/0; policy 0/0/0 | no | no | pass | runbook, security |
| 4 | 6ad767df44ff4d338c22dc967004e294 | ok | answered | 8 | 20.1 | slow[outage,policy] | 7 | outage 0/0/0; policy 0/0/12 | no | no | pass | runbook, security |
| 5 | b71bfde8d80247a1bca8b24b276f45da | ok | answered | 3 | 7.6 | fast | 5 | none (no Worker on fast) | no | no | pass | runbook, security |
| 6 | d9c4b67c4cc145d1ac6c3818a653baa1 | ok | answered | 6 | 15.5 | slow[outage,policy] | 6 | outage 0/0/0; policy 0/17/0 | no | no | fail (인용 문서) | billing-policy, travel |
| 7 | 950835a3ac6744e0a45ae190b86b8059 | ok | answered | 10 | 23.4 | slow[outage,policy] | 6 | outage 0/0/0; policy 0/0/12 | no | no | pass | runbook, security |
| 8 | 737b7a1f47524bfba8a48fa52a8edd2c | ok | answered | 7 | 20.4 | slow[outage,policy] | 5 | outage 0/0/0; policy 0/0/0 | no | no | pass | runbook, security |
| 9 | 33d1df617e384936a0e272bbc7d62f61 | ok | answered | 6 | 16.7 | slow[outage,policy] | 6 | outage 0/0/0; policy 0/0/0 | no | no | pass | billing-policy, runbook, security |

Totals: status ok 9; outcome answered 9; `validate` events 9 (one per row), problems 0; writer rewrote in 0 rows; `budget_exceeded` in 0 rows; final refs empty in 0 rows; automatic check passed in 8 of 9 (the one failure is `인용 문서` in row 6). Router path: `fast` 2 rows (2 and 5, 3 model calls each, no Worker), `slow` 7 rows. `worker_checked` events: 14 (7 rows x outage and policy), all with `problems` empty. All 9 rows retrieved the same six documents (billing-policy, purchase, runbook, sales, security, travel).

Budget counts worth one line: rows 7 and 8 reached 6 `search` calls (row 7 also 3 `read_evidence`) and ended `ok`; none exceeded a limit. The earlier nine had one row (row 2) end `budget_exceeded` on the search limit.

## Raw Worker results (14 recorded, 0 raised)
Source: `ops_log2_raw.jsonl`. Raw refs are what the Worker returned before `checked_worker` touched them. "Own ids" are the `fact_ref` and `evidence_id` values found in the Worker's own tool results (the same regex `checked_worker` uses). The last column is the `worker_checked` event of the same row and task (dropped / filled / recovered).

| n | Worker | status | facts | raw refs | raw ref kind | own ids | event d/f/r |
|---|---|---|---|---|---|---|---|
| 1 | outage | uncertain | 2 | 0 | - | 0 | 0/0/0 |
| 1 | policy | uncertain | 8 | 8 | bare registered | 17 | 0/0/0 |
| 3 | outage | uncertain | 2 | 0 | - | 0 | 0/0/0 |
| 3 | policy | uncertain | 8 | 8 | bare registered | 17 | 0/0/0 |
| 4 | outage | uncertain | 2 | 0 | - | 0 | 0/0/0 |
| 4 | policy | uncertain | 7 | 12 | labelled | 19 | 0/0/12 |
| 6 | outage | uncertain | 2 | 0 | - | 0 | 0/0/0 |
| 6 | policy | uncertain | 10 | 0 | - | 17 | 0/17/0 |
| 7 | outage | uncertain | 2 | 0 | - | 0 | 0/0/0 |
| 7 | policy | uncertain | 7 | 12 | labelled | 20 | 0/0/12 |
| 8 | outage | uncertain | 0 | 0 | - | 0 | 0/0/0 |
| 8 | policy | uncertain | 10 | 9 | bare registered | 17 | 0/0/0 |
| 9 | outage | uncertain | 2 | 0 | - | 0 | 0/0/0 |
| 9 | policy | uncertain | 9 | 7 | bare registered | 17 | 0/0/0 |

Recomputing dropped, filled and recovered from each raw line (facts, refs, own ids, record-time registration) matched the row's `worker_checked` event in 14 of 14 results. "Registered" here means known to the desk at record time, a few microseconds before `checked_worker` read it; the event is the authority on what the gate did, the raw line on what the Worker returned.

All 14 raw results had `status: uncertain`; none was `complete`. Raw refs in total: 56 (32 bare registered, 24 labelled, 0 unregistered).

## A. Raw results with empty refs
- Empty `evidence_refs`: **8 of 14** raw results (7 outage, 1 policy).
- Facts naming one of the Worker's own ids: **0 of 8**. (Across all 7 policy results, 0 had an own id written inside any fact string, including the 4 that returned bare refs.)
- Fell back to all own ids: **1 of 8** (row 6 policy: 10 facts, none naming an id, so all 17 own ids were filled).
- The other **7 of 8** are the outage Workers: their tool results held no `fact_ref` or `evidence_id` (own ids 0), so there was nothing to fill and they stayed empty. Six of them wrote 2 facts saying the lookup returned `not_found`; row 8's outage Worker wrote 0 facts. Their `problems` stayed empty; the only empty-refs check in `validate_result` is for status `complete` (`Day03_new/mas_lab/contracts.py:81`), and all 14 statuses were `uncertain`. I did not read the `lookup_availability` tool code, so why its result carries no ids is a pointer, not a finding (`Day03_new/mas_lab/desk.py`).

Facts strings, quoted as saved:
- r1 outage: "2026-09월 가용률·장애 조회 결과는 not_found였습니다."
- r7 outage: "2026-08월 가용률·장애 조회 결과: not_found (자료 없음)"
- r6 policy: "검색 서비스 타임아웃이 증가하면 upstream 지연, 연결 풀 포화, 인덱스 상태 순서로 확인한다. 이 절차는 검색 API의 5분 오류율이 5%를 초과하면 담당자를 호출한다는 탐지 기준과 같은 문서에 있다."
- r6 policy: "운영 접근 로그는 90일 보관한 뒤 삭제한다."
- r6 policy: "예외: 보안 사고 조사 대상으로 별도 보존 명령이 내려진 로그는 조사 종료 승인까지 보존한다."

The "named ids first" branch of the fix was never taken in these nine rows (0 named). The only fill used the all-own-ids branch, 17 ids.

## B. Raw results with labelled refs
- Labelled refs (a registered id inside a longer string): **2 of 14** raw results, both policy Workers (rows 4 and 7), 12 labelled refs each, **24** in total.
- Ids kept by the recovery: **24** (`recovered` 12 and 12), one registered id per labelled ref. Refs still dropped: **0**. Unregistered refs in any result: **0**.
- Real strings, raw ref to kept id:
  - r4: `runbook:E-fe73bd71207c` to `E-fe73bd71207c`; `runbook:E-09fef7763fe2` to `E-09fef7763fe2`; `runbook:E-a489dd52ddb1` to `E-a489dd52ddb1`
  - r7: `runbook 탐지: E-fe73bd71207c` to `E-fe73bd71207c`; `runbook 전문: E-09fef7763fe2` to `E-09fef7763fe2`; `runbook 롤백 조건: E-a489dd52ddb1` to `E-a489dd52ddb1`
- Both rows ended `answered`, 7 and 6 final refs, rewrote no, cited runbook and security, automatic check passed. In the earlier nine rows (code before the recovery), the same shape (`runbook 탐지: E-...`, a label in front of a registered id) was dropped and replaced by fills of 18 and 17 ids (earlier rows 7 and 8).

## Comparison with the previous nine rows
Previous nine: rows in `ops-log-notes.md`, ids in `ops_log_runs.json`, re-read with the same reader logic (the counts match that file). For the previous nine, raw refs were not recorded: "refs empty" there is the final `evidence_refs` of the row, and the raw cause was inferred from `filled` and `dropped`.

| | previous nine | these nine |
|---|---|---|
| status | ok 8, budget_exceeded 1 | ok 9 |
| outcome | answered 8, none 1 | answered 9 |
| Router path | fast 1, slow 8 | fast 2, slow 7 |
| final refs empty | 1 row (the budget_exceeded row) | 0 rows |
| raw Worker results with empty refs | not recorded (inferred: 2 policy results) | 8 of 14 recorded (7 outage with no own ids, 1 policy) |
| fills (events with filled > 0) | 4, in rows 5 to 8, all policy | 1, row 6, policy |
| ids filled per fill | 17, 18, 18, 17 | 17 |
| refs dropped as unregistered | 2 events (10 and 8 refs dropped, rows 7 and 8) | 0 |
| labelled refs recovered | not available in that code | 2 results, 24 ids |
| `인용 문서` failures | 4 rows (rows 2, 5, 6, 7; row 2 is the budget_exceeded row with no answer, so 3 on answered rows) | 1 row (row 6) |
| automatic check passed | 5 of 9 | 8 of 9 |
| model calls / seconds | 56 / 155.2 | 55 / 142.1 |

Slow-path rows only: previous 8 slow rows had 4 fills and 4 `인용 문서` failures; these 7 slow rows had 1 fill and 1 failure. Counting all 18 rows together, 5 rows had a fill and 4 of those 5 failed `인용 문서`; of the 13 rows without a fill, 1 failed `인용 문서` (the budget_exceeded row, which cited nothing), and 0 of the 12 answered rows without a fill did.

## 인용 문서 failures after this fix
The failure remains: 1 of 9 rows, row 6, and it is the one row with a fill. What the raw file shows for that row, and no more:
- The policy Worker returned empty refs with 10 facts; none of the facts contained one of its 17 own ids; the gate filled all 17 in tool-result order.
- The writer's 6 final refs were the first 6 of those 17 ids (positions 0 to 5 in tool-result order). The cited documents were billing-policy and travel; the automatic check failed `인용 문서` and passed every other column.
- In the 6 slow rows without a fill, the final refs sat at positions 2, 8, 9 and 12 to 14 of the Worker's own list, plus positions 11, 17 and 18 in rows 4 and 7 (the two rows whose Worker returned labelled refs and whose own list held 19 and 20 ids); those rows cited runbook and security, rows 1 and 9 also billing-policy, and all passed.
- All 9 rows retrieved the same six documents, so retrieval does not separate the failing row from the passing ones.
- Not tested: why the writer's refs follow the fill order, and whether a different fill would change the cited documents. A grep of `hybrid.py` for slices on refs found none, but the writer was not traced.

## Limits
- 9 rows, one day, one case: no rate and no cause. The 2 `fast` rows ran no Worker, so the Worker-level counts rest on 7 slow rows and 14 raw results.
- The named-first fill branch has no real-data evidence either way; its fact style (no ids inside facts) in these 7 policy results would not trigger it.
- The writer's prompt is not stored; "the writer received refs" is read from the post-check result and the final refs.

## Rulings
- Ruling: kept the two fast-path rows in the nine and did not re-run them - the task says keep every row and run exactly nine - cost if wrong: fewer Worker results (14, not 18) under the counts.
- Ruling: reported the 7 outage results with empty refs as a third bucket ("no own ids, nothing to fill") instead of forcing them into "named" or "fell back" - their own ids were 0, so neither branch can apply - cost if wrong: someone adding 8 to the fallback count would overstate it.
- Ruling: the 0-call probe `ops_log2_probe.py` borrowed the scripted-model helpers of `tests/test_structures.py`, whose import line pulls in the module `mas_lab.evaluation` (`tests/test_structures.py:15`) - `load_gold()` is called only inside test bodies (lines 124 and 883), so `gold.jsonl` was not read, and the probe made no model call and printed no gold content; the run script itself does not import `mas_lab.evaluation` - cost if wrong: a reviewer who counts any import of that module as a breach would flag the probe, not the run.
- Ruling: also recorded the tool-result id list and per-ref registered tokens in the raw file, beyond the asked fields - the counts need them to be recomputed - cost if wrong: a larger raw file only.
- Ruling: counted `인용 문서` failures in the previous nine as 4 rows (2, 5, 6, 7) because row 2's failed columns include it, while the earlier notes' text names only rows 5, 6 and 7 - cost if wrong: the earlier "3" and this "4" read as a disagreement; both are in the table.

## Files (all in the scratchpad `phase3`)
`ops_log_run2.py`, `ops_log2_raw.jsonl`, `ops_log2_runs.json`, `ops-log2-run.log`, `ops_log2_report.py`, `ops-log2-report.out`, `ops_log2_probe.py` (0-call recorder probe), `ops_log2_runs_before.txt`, `ops_log2_runs_after.txt`, `ops_log2_start_marker`. Rows: `Day03_new/outputs/runs/<run_id>.json`.

Ops log repeat 2: done
