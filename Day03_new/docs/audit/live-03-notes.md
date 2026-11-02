# Live 03 notes (run dag_mvxjjtgg_181ytn, node live-03, attempt 1)

Work dir <repo>. `uv run --no-sync` only. No 429, no rerun, no code cell edited. No .env content printed.
Announced before each run: base "약 38회" (previous record 38), exercises "약 43회" (previous record 43). Runs were strictly one after the other (base first, then --exercises), both under nohup with `wait_live.py <stem> --seconds 540`.

## Records (both finished true, errors 0, newer than P/run-b-start-marker)

| record | model calls | seconds | input tokens | output tokens | cache_read tokens | switched |
|---|---:|---:|---:|---:|---:|---:|
| 03-Four-Flows (base) | 37 | 110.6 | 83351 | 14999 | 47769 | 0 |
| 03-Four-Flows.exercises | 44 | 135.8 | 111776 | 19149 | 74757 | 1 |
| total | 81 | 246.5 | 195127 | 34148 | 122526 | |

Spend limit 110: used 81 (37 + 44), counted from the two usage.jsonl files (37 and 44 lines).
Previous records (P/live-03-before/): base 38 calls 128.0 s 78924 in / 16872 out; exercises 43 calls 138.5 s 107518 in / 19486 out.

## Per-cell model calls (cell index: base / exercises / announce)
11: 5 / 5 / 5 | 28: 6 / 6 / 12 | 29: 7 / 7 / 12 | 34: 6 / 6 / 6 | 43: 4 / 5 / 6 | 54: 9 / 8 / 15 | 61 (해보기 3): - / 7 / 8
No cell measured above its announce (cells 11 and 34 equal it; 5 and 6 are deterministic counts: one call per role, one call per routed case). No announce was raised and no cell was rerun.
Cell 0 table ranges all hold: 조사→작성→검토 5, 병렬+직렬 13 (12~24), 라우터 6, 루프 4 or 5 (4~6), 조립 9 or 8 (8~15), base total 37 (약 35~56, 2 above the low end), 해보기 3 adds 7 (4~8).

## budget_exceeded rows
None. The string `budget_exceeded` appears in each executed notebook once, as source text of the loop cell's code (stop reason constant), not in any output. Loop stop states were complete / same_failure only. `usage 누락` 0 in every row of cells 30 and 61. FIXED_BUDGET untouched.

## Event kinds
Notebook 03 does not print `desk.trace.events` and does not call run_case. Its only gate call is `gate_answer(..., approved=None, request_id="flows-t1001")` in cell 54 with no `question`, so the gate_skipped path (mas_lab/gate.py:55-59) cannot fire here.
Not seen in either executed notebook (grep count 0 each): gate_skipped, earlier_turn_proposal_ungated, gate_text_appended, worker_checked. Read "not seen" as "not printed in this notebook", not "never emitted": worker_checked is written by run_worker (mas_lab/workers.py:165) in every Worker call here, but the events are not shown.
Observable gate fact: cell 54 outcome needs_approval, 원장 건수 0, 자동 검사 True, 남은 문제 [], 재계획 0 in both runs.

## Observation prose compared with both executed outputs
Read against both records: every `**관찰할 것.**` paragraph (cells 5, 13, 26, 31, 37, 45, 55) and the surrounding prose that cites outputs (cells 18, 22, 41, 50, 56, 58, 60, 62, 65, 66). Branch sentences ("~했다면") that match the rows were left. Facts checked:
- cell 5: 선행 작업 3 for credit, 묶음 2 has three tasks, both rejected plans have `json으로 직렬화됨 = True`.
- cell 13: 자료 바이트 2425 vs 조사 메모 바이트 2050 (base) / 2105 (exercises), so the memo is shorter; `메모 없음` writer wrote '확인 필요' with a note to the author; reviewer first line 반려 in both runs of both records, with detail items beyond what a customer answer needs.
- cell 26: Send 함께 credit 0 with 입력 {} and no error; merge_results re-delivery passes, conflict ValueError; 최장 경로 병렬 실측 1.010 / 1.007 vs 계산 1.0.
- cell 31: plan_hash 7f41517672b9 identical in both rows; 직렬 겹침 0.000; 병렬 합산 24.59 / 24.44 s far above 전체 9.409 / 8.836 s; 모델 호출 6 vs 7 and 입력 토큰 15212 vs 22740 (base) / 15212 vs 23626 (exercises), i.e. the rows differ and the prose already says not to read it as a concurrency effect; no `complete` row with 근거 수 0 (policy complete 11/11 in serial, 8/9 in exercises parallel); 필수 사실 5/6 with 누락 사실 [150000] in all four rows, which is the single missing amount the prose explains.
- cell 37: 모델 라우터 6/6 in both runs (the "전부 일치했다면" branch); 규칙 경로 for complex-ops-log is fast (기대 slow) and for simple-duplicate-rule is slow (기대 fast); Fast 강제 누락 사실 six items; 복구 간선 simple-deadline fast, complex-double-pay fast -> check_kinds -> slow.
- cell 45: base 기본 누락 [크레딧 비율, 계산 기준] -> [] with 근거 1 -> 3 and 입력 토큰 777 -> 1199; 답 없는 항목 추가 same_failure after 2 attempts, first attempt 근거 1 with 누락 [법인카드 포인트 보상] only, so 크레딧 비율 and 계산 기준 were not listed and the last draft says the values are not in the evidence ("SLA v2.0을 그대로 따른다고만") - the paragraph's last-but-one bullet branch occurred. Exercises run: variant same_failure after 3 attempts, 근거 수 5 and 입력 토큰 1410 in attempts 2 and 3 (the "근거 수가 앞 시도와 같다면" branch occurred), last draft has concrete 10%/15%/20%.
- cell 55: plan first, aggregate after the Workers, writer span starts after the last Worker span ends; 겹침 8.316 / 7.683 s > 0; 재계획 0;남은 문제 []; outcome needs_approval with 원장 건수 0; 자동 검사 True.
- cell 50: Supervisor and Hierarchical rows have equal 조건부 간선 3 and 순환 True and differ only in 병렬 (False vs True, 겹침 0.000 vs 0.105).
- Deterministic cells (3, 4, 7, 8, 16, 17, 20, 21, 23, 24, 25, 33, 35, 36, 39, 40, 48, 49, 52, 59, 63) match across base, exercises and the previous base record except for timing digits (cells 17, 20, 21, 23, 49, 52 differ in the third decimal or in the bar layout; cell 59 differs by up to 14 ms in 이득: 0.115 / 0.101 / 0.109 s, 이득 비율 0.16 / 0.14 / 0.15). Every sentence that cites them (병렬 겹침 > 0, 직렬 겹침 0, 실측 slightly above 계산, 이득 positive) holds in all three.

## Markdown sentences changed (1 cell, markdown only, no rerun needed)
1. Cell 0 (호출 규모). Cells 1, 10, 12, 19, 27, 30, 42, 44, 47, 51, 53, 61 and 64 do not print "모델 호출 0회" in either record (22 of the 35 code cells with no model call print it), so "이런 셀은 출력에 `모델 호출 0회`를 적습니다." was visibly false. It was false in the previous records too and is the same wording defect that live-02 corrected in notebook 02.
  before: `...일반 함수 노드로 돌립니다. 이런 셀은 출력에 \`모델 호출 0회\`를 적습니다.`
  after:  `...일반 함수 노드로 돌립니다. 이런 셀은 대부분 출력에 \`모델 호출 0회\`를 적습니다. 준비 셀, 그래프를 만들거나 그리기만 하는 셀, 앞 실행의 기록을 표로 읽기만 하는 셀은 이 문구가 없어도 모델을 부르지 않습니다.`
The three categories in the new sentence do not list every non-printing cell (cell 27 prints only a plan_hash line, cell 61 prints 실행하지 않았습니다 when the switch is off, cell 64 writes design_log.json); the sentence does not claim a complete list and the preceding "대부분" keeps it true. Chosen on purpose over a longer enumeration that would go stale.
Backup of the notebook before the edit: P/live-03-nb-before.ipynb. The saved notebook still has no outputs and no execution counts; RUN_EXERCISE = False (cell 61 switch cell); this notebook has no RUN_OPTIONAL. No code cell was edited (source diff against the backup shows one changed line, in cell 0).

## Seen, not edited
- Cell 54 final answer in the exercises run adds a paragraph about INV-2026-03 (P-7001/P-7002, 1,000,000원 each) and says it is unconfirmed whether it is part of the request; the base run's answer does not. Nothing in the prose depends on the answer text, and 자동 검사 was True with 누락 사실 [] in both.
- Cell 63 (해보기 4) shows 그대로 -> same_failure at 4 attempts while cell 40 shows 2; cell 63 sets `MY_SAME_LIMIT = 4` while cell 40 calls `run_scenarios(max_attempts=5, same_limit=2)`, and the exercise prose asks the student to change it.

## Side effects of running the notebook (not edits)
- Day03_new/outputs/design_log.json rewritten by cell 64 in both runs; its content is identical to the copy taken before (P/live-03-before/design_log.json).
- Day03_new/outputs/runs stayed at 1669 entries. No change to outputs/baseline, mas_lab, rag_lab, tests, docs or data/gold.jsonl by this node.

## Checks
- check_notebook.py Day03_new/03-Four-Flows.ipynb --minutes 60: OK, exit 0.
- pytest Day03_new/tests/test_notebook_code.py: 262 passed.
- The plugin gate command reproduced by hand: both records newer than P/run-b-start-marker, finished true, errors empty (exit 0).

Live 03: done
