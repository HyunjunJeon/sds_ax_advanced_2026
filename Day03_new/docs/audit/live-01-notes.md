# Live 01 notes (run dag_mvxjjtgg_181ytn, node live-01, attempt 1)

Work dir <repo>. `uv run --no-sync` only. No 429, no rerun, no code cell edited. No .env content printed.

## Records (both finished true, errors 0, newer than P/run-b-start-marker)

| record | model calls | seconds | input tokens | output tokens | cache_read tokens | switched |
|---|---:|---:|---:|---:|---:|---:|
| 01-Workflow-vs-Agent (base) | 45 | 142.5 | 187572 | 13658 | 146931 | 0 |
| 01-Workflow-vs-Agent.exercises | 52 | 172.6 | 224125 | 16665 | 186517 | 2 |
| total | 97 | 315.1 | 411697 | 30323 | 333448 | |

Spend limit 120: used 97 (45 + 52), counted from the two usage.jsonl files (45 and 52 lines). Announced scale before each run: about 40 and 50 calls (observed 45 and 52).
New outputs/runs records: 12 (6 per run), 1657 before -> 1669 after.

## Per-cell calls (cell index: base / exercises / announce)
5: 1 / 1 / 1 | 9: 2 / 2 / 2 | 11: 2 / 2 / 4 | 17: 7 / 10 / 12 | 23: 5 / 5 / 6 | 27: 3 / 3 / 4 | 32: 3 / 3 / 4 | 36: 20 / 18 / 30 | 39: 2 / 2 / 2 | 44: 0 / 3 / 4 | 48: 0 / 3 / 4
No cell measured above its announce, so no announce was raised and no cell was rerun. Cell 39 equals its announce (2) in both.

Run-to-run spread seen (same code, same question): simple-deadline 9 vs 12 calls, insufficient-no-policy 7 vs 2, adhoc-4 3 vs 6, adhoc-3 4 vs 4, complex-double-pay 4 vs 4 (input tokens 20918 vs 20873; 2절 T-1001 row 20844 vs 20893, same tool order both times).

## budget_exceeded rows (results, FIXED_BUDGET untouched)
- base cell 39: single / complex-double-pay, status budget_exceeded, outcome None, model_calls 2, errors ["model 호출 한도를 초과했습니다."], input_tokens 6843. Intended variant (max_model_calls=2).
- exercises cell 39: same row, input_tokens 7113.
No other budget_exceeded, validation_failed or model_error row. All other Single rows status ok.

## Automatic check outcomes
- base: simple-deadline True, complex-double-pay False (실패 칸 [필수 사실], 누락 사실 [9월20일]; the answer text has "2026-09-20"), insufficient-no-policy True.
- exercises: all three True.
The failed row was kept as is. It is exactly the example the existing 관찰 paragraph names (`9월20일` missing while `2026-09-20` is in the body).

## Event kinds in the 12 new run records (desk.trace.events)
- tool 36, gate 4 (all needs_approval), gate_skipped 2 (adhoc-4 in each run, named=[] because the question names no payment and contains "환불"; Single answered, outcome answered, no policy violation).
- Not seen: earlier_turn_proposal_ungated (only multi-turn followup cases), gate_text_appended.
- worker_checked is emitted by run_worker (workers.py:165) in cell 23 and cell 48, but desk_mixed.trace.events is not printed or saved, so it is not observable in these records.

## Observation prose compared with both executed outputs
Every `**관찰할 것.**` paragraph (cells 4, 6, 13, 16, 20, 26, 29, 34, 40) was read against both records. Branch sentences ("~했다면") that matched the new rows were left. Facts checked: Route roles for T-1001 = [billing, policy] with no outage (both runs); mixed Workflow decisions P-7002 human_review / P-9002 needs_approval, investigate 20.8 / 24.8 s of the node time, verify/fetch/rule 0 calls, 불확실성 mentions the missing availability; refund agent refused P-8101 in both runs (tools lookup_payments x2, ledger 0); proposer returned action none, gate "환불 제안이 아닙니다", ledger 0; tamper table ledger 0 to the end; beta P-5002 allow/True; 4th-request Single used all four tool kinds (base) or five (exercises, +read_evidence).
Side observation, not edited: exercises adhoc-3 answer contains the garbled clause "환불 기한은 지났습니다가 아니라 기한 안에 있습니다". The prose already tells the student to read the answer body.

## Markdown sentences changed (3 cells, markdown only, no rerun needed)
1. Cell 0 (호출 규모), contradicted by cell 24 (no "모델 호출 0회" printed) and cell 25 (prints "모델 호출 0 회"):
   before: `...모델을 부르지 않는 칸은 출력에 "모델 호출 0회"라고 적습니다.`
   after:  `...모델을 새로 부르지 않는 칸은 대부분 출력에 "모델 호출 0회"라고 적고, 앞 셀의 기록만 읽는 3절의 노드 표 칸은 그 기록의 호출 수를 그대로 보여 줍니다.`
2. Cell 10 (Agent Loop intro), contradicted by the cell 11 message table (final AI row has 도구 = agent-loop, the Agent name, not a tool choice):
   before: `표의 `종류`가 `AI`이고 `도구`가 채워진 행이 모델이 다음 행동을 고른 자리입니다.`
   after:  `표의 `종류`가 `AI`이고 `인자`가 채워진 행이 모델이 다음 행동을 고른 자리입니다. 마지막 `AI` 행의 `도구` 칸에 적힌 `agent-loop`는 도구가 아니라 Agent의 이름이고, 그 행은 답을 낸 자리입니다.`
   (tool_steps in cell 19 already keys on 인자, so prose and code now agree.)
3. Cell 21 intro (3절), contradicted by the cell 22 edge table (two rows with 조건부 True):
   before: `` `verify` 뒤에는 조건부 간선을 하나 뒀습니다. ``
   after:  `` `verify` 뒤에는 갈림길 하나를 조건부 간선으로 뒀습니다. 갈 곳이 둘이라 아래 간선 표에서는 `조건부`가 `True`인 행이 두 줄로 보입니다. ``
Backup of the notebook before the edits: P/live-01-nb-before.ipynb. Saved notebook still has no outputs, no execution counts, RUN_EXERCISE False in both switch cells (44, 48).

## Side effects of running the notebook (not edits)
- Day03_new/outputs/baseline/01.json was rewritten by cell 38 in both runs; the file now holds the exercises run's rows (all three auto checks True), because it ran second. The base run's rows (complex-double-pay failed with 필수 사실) are in 01-Workflow-vs-Agent.executed.ipynb and the 12-record run set. Pre-run copy: P/live-01-baseline-before.json.
- Day03_new/outputs/design_log.json rewritten by cell 49.

## Checks
- check_notebook.py Day03_new/01-Workflow-vs-Agent.ipynb --minutes 60: OK, exit 0.
- pytest Day03_new/tests/test_notebook_code.py: 262 passed.
- `runner_source.index` is in 01-Workflow-vs-Agent.executed.ipynb.
- Gate command logic (mtime >= marker, finished, errors empty) reproduced by hand: both records pass.

Live 01: done
