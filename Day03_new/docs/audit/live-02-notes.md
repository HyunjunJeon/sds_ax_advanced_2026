# Live 02 notes (run dag_mvxjjtgg_181ytn, node live-02, attempt 1)

Work dir <repo>. `uv run --no-sync` only. No 429, no rerun, no code cell edited. No .env content printed.
Announced before each run: base "about 32 calls", exercises "about 49 calls".

## Records (both finished true, errors 0, newer than P/run-b-start-marker)

| record | model calls | seconds | input tokens | output tokens | cache_read tokens | switched |
|---|---:|---:|---:|---:|---:|---:|
| 02-Agent-Architecture (base) | 33 | 106.8 | 114568 | 14183 | 69118 | 0 |
| 02-Agent-Architecture.exercises | 51 | 164.3 | 158291 | 20592 | 110519 | 2 |
| total | 84 | 271.1 | 272859 | 34775 | 179637 | |

Spend limit 110: used 84 (33 + 51), counted from the two usage.jsonl files (33 and 51 lines).
Previous records (P/live-02-before/): base 32 calls 104.3 s, exercises 49 calls 154.3 s.

## Per-cell calls (cell index: base / exercises / announce)
9: 5 / 4 / 12 | 15: 9 / 9 / 14 | 20: 10 / 9 / 14 | 32: 6 / 8 / 12 | 34: 3 / 3 / 8 | 48 (해보기 1): - / 10 / 14 | 50 (해보기 2): - / 8 / 12
No cell measured above its announce, so no announce was raised and no cell was rerun. The closest cell to its announce is cell 20 base, 10 of 14 (4 below); every other cell is at least 5 below (cell 34: 3 of 8).
Exercise extra calls: 10 + 8 = 18, inside the cell-0 range "약 14~26회 더". Base 33 is inside "약 25~60회".

## budget_exceeded rows
None. The text budget_exceeded appears in neither executed notebook; `실행 오류` was 없음 in every paid cell and the 검증 문제 column was [] in every row. FIXED_BUDGET untouched.

## Supervisor Worker spans seen (Manager = build_supervisor, cell 15/17)
Base, mas_lab spans (delegation_spans, seconds since the run start): outage 4.386-7.924, billing 4.371-10.841, policy 4.397-14.376. Overlap 6.455 s, one parent message with 3 task calls (billing, policy, outage). Recorder bars: billing 6.47 s, outage 3.54 s, policy 9.98 s.
Exercises, mas_lab spans: billing 3.990-10.632, outage 4.008-12.989, policy 4.000-15.136. Overlap 8.989 s, 3 task calls in one message.
Cell 20 (지침 없음), per-Worker bars: base billing 5.92 / outage 3.74 / policy 12.58, overlap 5.903, delegation [billing, policy, outage] in one message [3]; exercises billing 6.81 / outage 3.85 / policy 8.67, overlap 6.793, [3].
Exercise 1 (설명 모호): delegation [billing, policy] -> [outage], messages [2, 1], overlap 8.510 s, 10 calls, no general-purpose delegation (예산 밖 호출 0).
Worker 안 도구 (cell 18) base: billing 1 tool / 5 refs, policy 3 tools / 15 refs, outage 2 tools / 4 refs; exercises: 1 / 5, 2 / 12, 2 / 2. No Worker-only tool in the parent conversation.

## Event kinds
Notebook 02 does not save a run record (Day03_new/outputs/runs stayed 1669 files), and it prints only the CONTROL kinds of the Handoff trace.
Seen in the printed tables: handoff (turn 1: triage -> billing, billing -> technical, both runs), final_answer (technical), owner_retained (turn 2: technical -> technical, both runs).
Not seen in any output: gate_skipped, earlier_turn_proposal_ungated, gate_text_appended, worker_checked. Why: cell 35 calls gate_answer per turn without a `question`, so the gate_skipped path (gate.py:55-59) cannot fire; handoff_turn drives the graph itself, not run_case, and earlier_turn_proposal_ungated is written only by run_case (runner.py:106-108); worker_checked is written by run_worker (workers.py:165) in exercise 2 (cell 50) but desk.trace.events is not printed there.
Followup-handoff turn check (indirect, from the table in cell 35): turn 1 담당자 outcome answered -> 게이트 뒤 needs_approval (a proposal was carried through the owners); turn 2 answered -> answered in BOTH runs, 원장 건수 0. The previous record had turn 2 answered -> needs_approval. So turn 2 starts with no proposal, as the triage `"proposal": None` (structures.py:100) says. The event itself is covered offline by Day03_new/tests/test_structures.py:776-859.

## Observation prose compared with both executed outputs
Every `**관찰할 것.**` paragraph (cells 12, 19, 22, 24, 29, 36, 42, 46) and the 직접 해보기 prose (cells 47, 49, 51, 53) was read against both records. Branch sentences ("~했다면") that match the new rows were left. Facts checked:
- cell 12: 도구 결과 is the largest bar (base 7,022, exercises 6,575); 입력 토큰 2,410 -> 7,394 (base) / 2,410 -> 7,089 (exercises).
- cell 19: task 수 3, 겹침 > 0, Worker 전용 도구 없음, 근거 참조 수 all > 0.
- cell 22: 메시지당 task 수 [3] in both rows of both runs; the "지침을 뺐는데도 한꺼번에 위임했다면" branch is the one that occurred; time columns differ (24.3/27.4 base, 27.3/26.1 exercises) and the prose already says not to read the difference as a parallel effect.
- cell 24: 예산 밖 모델 호출 0 in row 1, 6 in row 2 (both runs); general-purpose appears in the task description (True) but was not delegated to, which the prose's "없었다면 이번 1회는 쓰지 않은 것" branch covers.
- cell 29: GraphRecursionError at 8 nodes; limit table 0/1/3 -> needs_clarification, paths as stated.
- cell 36: 크레딧 계산 기준 = 계산 도구 호출 없음 in both runs (third bullet); 메모에 '기본 이용료' 언급 False, 메모에 1,000,000 있음 True. The 1,000,000 in the memo is INV-2026-03 P-7001/P-7002, exactly the case the bullet warns about. 턴 2 owner_retained; 턴 2 검색 1, 원문 읽기 0; 원장 건수 0; the gate-after-outcome sentences hold (see above).
- cell 46: Single/Manager 크레딧 계산 기준 "1,000,000 x 15% (기본 이용료분과 일치)", Handoff "계산 도구 호출 없음": the "값이 다르다면" branch occurred. 최종 응답 주체 of Handoff is technical, not the first control owner.
- cell 42: deterministic skeleton output unchanged (policy#1:실패 then policy#2:완료, 순환 True, 6 vs 5 steps).
- cells 47/49: 해보기 2 model calls 2 vs 2 and tool calls 1 vs 1 (facts True raised input tokens 3104 -> 4106 for billing): the "줄지 않았다면 도구를 다시 부른 것" branch occurred.

## Markdown sentences changed (2 cells, markdown only, no rerun needed)
1. Cell 0 (호출 규모). Cell 1 (setup, key_status line) and cell 10 (call table of the Single run) print no "모델 호출 0회" in either record, so the sentence "나머지 셀은 ... 출력에 '모델 호출 0회'를 적습니다" was visibly false. (It was false in the previous records too.)
  before: `...나머지 셀은 일반 함수로 돌아가며 출력에 "모델 호출 0회"를 적습니다.`
  after:  `...나머지 셀은 일반 함수로 돌아가며 대부분 출력에 "모델 호출 0회"를 적습니다. 준비 셀과 앞 실행의 호출표를 읽기만 하는 셀은 이 문구가 없어도 모델을 부르지 않습니다.`
2. Cell 47 (해보기 1), found by dumping cell 48's output in full: the prose named columns the cell does not print. Cell 48 prints the 위임 순서 and 메시지당 task 수 columns plus one line "실제 모델 호출: N | 예산이 센 호출: N"; there is no `예산 밖 모델 호출` column (cell 24's table has that one) and no `Worker 안의 도구` column (only cell 18's `안에서 부른 도구 수`, computed from manager["rec"].tool_results).
  before: `` `위임 순서`, `예산 밖 모델 호출`, `Worker 안의 도구`가 어떻게 달라지는지 보세요. `general-purpose`로 위임했다면 예산 칸이 어떻게 되는지도 보세요. ``
  after:  `` 표의 `위임 순서`와 `메시지당 task 수`가 어떻게 달라지는지 보세요. 표 아래 한 줄의 `실제 모델 호출`과 `예산이 센 호출`의 차이가 예산 밖 모델 호출입니다. `general-purpose`로 위임했다면 이 차이가 어떻게 되는지도 보세요. Worker 안에서 부른 도구는 이 셀이 출력하지 않습니다. 보고 싶다면 `vague["rec"].tool_results`를 3절의 `안에서 부른 도구 수` 표처럼 읽는 칸을 직접 더하세요. ``
  The column names in the other exercise paragraphs (cells 49, 51, 53) and in every 관찰할 것 paragraph were then checked against the printed tables; they all exist.
Backup of the notebook before the edits: P/live-02-nb-before.ipynb. The saved notebook still has no outputs and no execution counts; RUN_EXERCISE = False in both switch cells (48, 50); this notebook has no RUN_OPTIONAL.

## Seen, not edited
- Cell 36 third bullet: `답의 금액` is [1,200,000원] (the invoice payment, not a credit) in the Handoff row of both runs. The bullet says "크레딧 금액이 없다면", which is true, but a reader may take 1,200,000원 for a credit amount. It is not contradicted, and the same value was in the previous record, so it was left.
- Exercises Manager row 답의 금액 contains 200,000원 (the 사용량 초과분) and the 설명 모호 row contains 1,000,000원 twice; the 검증 문제 column is [] there.

## Side effects of running the notebook (not edits)
- Day03_new/outputs/design_log.json rewritten by cell 55 in both runs (the exercises run wrote it last).
- No change to outputs/baseline, outputs/runs, mas_lab, rag_lab, tests, docs or data/gold.jsonl.

## Checks
- check_notebook.py Day03_new/02-Agent-Architecture.ipynb --minutes 60: OK, exit 0.
- pytest Day03_new/tests/test_notebook_code.py: 262 passed.
- The plugin gate command reproduced by hand: both records newer than the marker, finished true, errors empty (exit 0). `OWNER_TOOLS =` is in 02-Agent-Architecture.executed.ipynb.

Live 02: done
