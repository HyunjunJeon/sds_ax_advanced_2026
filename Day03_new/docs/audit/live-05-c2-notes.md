# Live 05 c2 notes (run dag_mvxqwuxv_oit10v, node live-05, attempt 1)

P = <P>
Work dir <repo>. `uv run --no-sync` only, no uv sync. No .env content or key value printed.
Announced before each run: base "about 145 model calls" (previous record 145), exercises "about 460 model calls" (previous record 460). Spend limit 700.
Runs were strictly one after the other (base, then --exercises), both under nohup. Base finished inside the first `wait_live.py 05-Choosing-Multi-Agent --seconds 540`; exercises needed three waits (RUNNING 133 calls at cell 26, RUNNING at 383 usage lines, then FINISHED). The spend check between waits read 191, 383 and 435 usage lines for the exercises file, with 135 from base: peak 570 of 700.
No 429, no model_error, no rerun, no code cell edited, no announce raised, no mas_lab defect.
Start marker: P/live-05-c2-start-marker. Pre-edit saved notebook: P/live-05-c2-nb-before.ipynb. Old records: P/live-before-c2/ (byte-identical to the live files before this run; verified with cmp).

## Records (both finished true, errors 0, newer than the start marker)

| record | model calls | seconds | input tokens | output tokens | cache_read tokens | switched |
|---|---:|---:|---:|---:|---:|---:|
| 05-Choosing-Multi-Agent (base) | 135 | 394.6 | 498484 | 53211 | 337499 | 0 |
| 05-Choosing-Multi-Agent.exercises | 435 | 1272.2 | 1605783 | 147758 | 1158016 | 4 |
| total | 570 | 1666.8 | 2104267 | 200969 | 1495515 | |

Spend: 570 of 700, counted from the two usage.jsonl files (135 and 435 lines).
Previous records (P/live-before-c2/): base 145 calls 412.2 s 553807 in / 53579 out; exercises 460 calls 1238.1 s 1760800 in / 147281 out.
The exercises run switched RUN_OPTIONAL (cell 1) and the three RUN_EXERCISE cells (48, 50, 52) on. The saved notebook still has no outputs and RUN_OPTIONAL / RUN_EXERCISE False (checked after the edit).
Row files written by the runs in Day03_new/outputs/runs: 101 (22 base + 79 exercises); design_log.json is byte-identical to the pre-run copy (P/live-05-c2-design_log-before.json).

## Per-cell model calls (cell index: base / exercises / announce)
3: 10 / 11 / 20 | 9: 4 / 5 / 8 | 13: 9 / 10 / 20 | 17: 10 / 9 / 20 | 23: 5 / 6 / 12 | 31: 15 / 13 / 30 | 32: 16 / 16 / 24 | 37: 64 / 63 / 100 | 41 (RUN_OPTIONAL): - / 252 / 330 | 42: 2 / 2 / 3 | 48 (해보기 1): - / 30 / 48 | 50 (해보기 2): - / 16 / 24 | 52 (해보기 3): - / 2 / 15
No cell measured above its announce, so no announce was raised and nothing was rerun. `audit_live.py` prints AUDIT OK.
Cell 0 call-scale table holds: base 135 calls (table says 약 120~170회, 5~8분; 6.6 min), RUN_OPTIONAL 252 calls, 700.9 s = 11.7 min (약 220~330회 더, 10~15분), 해보기 30+16+2 = 48 calls, 165 s (합쳐서 20~70회 더).

## Markdown audit
Compared every `**관찰할 것.**` paragraph (cells 7, 11, 15, 20, 25, 29, 34, 44), the problem paragraphs (2, 12, 16, 21, 26, 30, 35, 45), the 해보기 prompts (47, 49, 51, 53), 정리 and 확인 질문 against both new executed notebooks (P/live-05-c2-base-outs.txt, P/live-05-c2-ex-outs.txt). The diff of all 58 cells against P/live-05-c2-nb-before.ipynb shows one changed cell (34).

### Markdown sentence changed (cell 34, bullet 3)
Before:
> 전환 뒤 `worker_checked`가 Worker마다 하나씩 보이면 합성 전에 코드가 각 Worker 결과를 거른 기록입니다(등록되지 않은 근거 참조를 뺐는지, 비어 있던 근거 참조를 그 Worker 자신의 도구 결과로 채웠는지).
After:
> 전환 뒤 `worker_checked`가 Worker마다 하나씩 보이면 합성 전에 코드가 각 Worker 결과를 거른 기록입니다. 사건의 `dropped`는 등록된 번호를 찾지 못해 뺀 근거 참조이고, `recovered`는 번호에 설명이 덧붙은 참조에서 등록된 번호만 가려 남긴 수입니다. 등록된 번호는 설명이 붙어 있어도 버리지 않고 남깁니다. `filled`는 사실은 적혔는데 거른 뒤 근거 참조가 하나도 남지 않은 결과를 그 Worker 자신의 도구 결과로 채운 수입니다. 칸의 값은 행의 `events`에서 읽습니다.
Why, checked against `Day03_new/mas_lab/workers.py:151-170`: `found` keeps a ref that is registered as written, otherwise the registered tokens inside it (`:160`); `kept` is those ids, `dropped` the refs with no registered id (`:162`), `recovered = len(set(kept) - set(result.evidence_refs))` (`:163`) so it counts ids that were pulled out of a labelled ref, and `filled` is nonzero only when the result has facts and nothing is left in `kept` (`:166`), so "비어 있던" was too narrow (a result whose refs were all dropped is filled too). The event carries `problems`, `dropped` (list), `filled` (count) and `recovered` (count) (`:169`). The values the new records hold agree: `recovered` is 0 in 42 of 44 events and 12 (base, hybrid complex-ops-log, policy Worker) and 10 (exercises, same case and Worker) in the other two; `dropped` is `['INC-311']` once (base, outage Worker of the forced Fast row); `filled` is 0 in all 44; `problems` is [] in all 44. The notebook prints only the event kinds, hence the last added sentence (the field values are read from `row["events"]`). No count is stated in the prose, so a repeat run that varies does not falsify it.
The `gate_skipped` sentence from the earlier run was checked against `Day03_new/mas_lab/gate.py:54-61` and left unchanged: it fires when the named numbers are not all registered payments (or none are named) and either the answer carries a denied/human_review label or the question mentions 환불; all 10 events seen here are P-7777 (unregistered number, 환불 question) or `named []` with 환불 in the question (cell 52). The answer text stays unchanged and the ledger stays at 0 in each of them.
`check_notebook.py ... --minutes 60` prints OK after the edit.

### Paragraphs checked and left as written (value in the new records, base / exercises)
- Cells 7, 11: base Single baseline 4 cases all 자동 검사 True, so cell 9 prints "실패 사례가 없어 첫 사례로 변동만 봅니다" (the third bullet of cell 11 applies); exercises complex-double-pay False [9월20일] (the answer carries 2026-09-20, a 표기 case) and the one-line patch row is True with fewer tool calls (lookup_availability 3 -> 1, read_evidence added) and `장애 다음 달 20일(2026-09-20)` in the answer (first bullet of cell 11 applies).
- Cell 15: base Single True 29581 tokens 5 calls vs Supervisor True 23574 / 9 (the "Single의 입력 토큰이 더 크게" branch; Single 같은 도구 최대 반복 = 2); exercises Single False [9월20일] 37775 / 6 vs Supervisor True 27499 / 10 (the first bullet, with its "표현 차이였다면 품질 차이가 아닙니다" check, applies).
- Cell 20: Persona 역할 밖 도구 호출 0 in both. Persona vs Context 분리 input: billing 3226 vs 1950 (base), 3156 vs 1914 (ex); outage 2792 vs 1578, 2790 vs 1591; policy rows differ in model calls (base Persona 3 calls incl. read_evidence x2 vs 2; exercises Context 분리 3 calls incl. read_evidence vs Persona 2), which is the case the earlier-added sentence covers in both directions. 같은 Desk True, 같은 원장 True, 원장 건수 1.
- Cell 25: 읽은 Skill ['credit-case','refund-case'] in both; first-call input 5678 vs 2410; single_skills 48902 tokens, False [9월20일] (base) and 61531, True (ex).
- Cell 29: 판정 rows: 1회 관찰, 1회 관찰, 주장할 수 없음: 비교 대상 빈 칸, 주장할 수 없음: 평가 방법, 측정자 빈 칸. Timeline overlaps billing/outage/policy; 직렬 합 / 최장 경로 1.46 (base), 1.38 (ex).
- Cell 34: forced Fast complex-double-pay: Slow 전환 False, 4 calls, 자동 검사 False, 누락 [99.3, 15%, 150000, 9월20일], events decision, final_answer, validate, gate, gate (both records) against 11 / 9 calls for the Router-judged row; forced insufficient-unknown-payment: Slow 전환 True, 12 calls, events end `fallback_to_slow`, worker_checked x3, final_answer, validate, gate_skipped; gate table deny/denied 0, human_review/human_review 0, needs_approval/needs_approval 0, allow/executed 1; edges fast->validate, writer->validate, validate->gate/worker/writer.
- Cell 44: base twins single 5 vs 4 calls (True / False), supervisor 9 vs 10 (True / True), hybrid 11 vs 9 (True / True); exercises single 6 vs 4 (False / False), supervisor 10 vs 9, hybrid 9 vs 9. Averages: 평균 0 -> A time and input tokens fall for single and hybrid in both records (single 11.3 -> 9.7 s, 15324 -> 13162 tokens base; 11.5 -> 9.9, 15336 -> 12595 ex; hybrid 24.6 -> 21.1, 30528 -> 24309 base; 23.8 -> 20.5, 25550 -> 20985 ex); A -> B single's 남은 사례 shrink to [complex-ops-log] and hybrid returns to the 평균 0 values (time and tokens rise), both written in the paragraph. 실패 행 목록: 3 rows each (single ok [9월20일], single budget_exceeded, hybrid forced Fast with 인용 문서 in 실패 칸). usage 누락 0.
- Cell 54: CORRECT_BUT_FAILS False [9월20일]; WRONG_BUT_PASSES True. Cells 48, 50, 52 (exercises only): 해보기 1 hybrid x3 = 10, 11, 9 calls with 자동 검사 False [9월20일], True, True (the prompt states no values and says one run does not make a statistic); 해보기 2 single ok 4 calls, supervisor and hybrid budget_exceeded at 6 calls ("model 호출 한도를 초과했습니다."); 해보기 3 자동 검사 True.

## Comparison tables

Cell 39 grid summary (2 cases x 1 repeat each; 통과/실행), this run vs previous record (P/live-before-c2):
| 구조 | 유형 | base this | base prev | ex this | ex prev |
|---|---|---:|---:|---:|---:|
| single | simple | 2/2 | 2/2 | 2/2 | 2/2 |
| single | complex | 1/2 | 2/2 | 1/2 | 2/2 |
| supervisor | simple | 2/2 | 2/2 | 2/2 | 2/2 |
| supervisor | complex | 2/2 | 1/2 | 2/2 | 2/2 |
| hybrid | simple | 2/2 | 1/2 | 2/2 | 2/2 |
| hybrid | complex | 2/2 | 2/2 | 2/2 | 1/2 |
실행 실패 0 in all four; usage 누락 0; 정책 위반 0. Average rows this run (time s / calls / input tokens), base: single 8.2 / 3.5 / 14562 and 11.3 / 3.0 / 15324; supervisor 19.4 / 5.0 / 11924 and 19.4 / 8.0 / 21790; hybrid 11.3 / 4.0 / 11776 and 24.6 / 8.5 / 30528. Exercises: single 12.2 / 4.5 / 20800 and 11.5 / 3.0 / 15336; supervisor 18.4 / 5.0 / 12643 and 21.7 / 6.5 / 16771; hybrid 12.4 / 4.5 / 14078 and 23.8 / 8.0 / 25550. These are single observations; no cause or rate is stated.
The single complex failure in both records is the 표기 case (answer says 2026-09-20, 누락 [9월20일]). Previous grid failures: base supervisor complex-double-pay ([9월20일], a 표기 case) and base hybrid simple-duplicate-rule ([outcome], needs_approval); exercises hybrid complex-double-pay ([9월20일]). In the previous cell 41 the hybrid complex failure was complex-ops-log with only `인용 문서` (runbook, security).

Cell 41 RUN_OPTIONAL table (exercises, 50 rows, 5 structures x 4 types; 통과/실행; usage 누락 0, 정책 위반 0, every row status ok):
| 구조 | simple | complex | insufficient | approval | previous (simple, complex, insufficient, approval) |
|---|---:|---:|---:|---:|---|
| single | 2/2 | 2/2 | 2/2 | 4/4 | same |
| single_skills | 1/2 | 1/2 | 2/2 | 4/4 | same |
| supervisor | 2/2 | 2/2 | 2/2 | 4/4 | 2/2, 1/2, 2/2, 4/4 |
| handoff | 1/2 | 1/2 | 2/2 | 4/4 | same |
| hybrid | 1/2 | 2/2 | 2/2 | 4/4 | 2/2, 1/2, 2/2, 4/4 |
Failed rows in cell 41 this run: single_skills simple-duplicate-rule [outcome] needs_approval, single_skills complex-double-pay [9월20일], handoff simple-duplicate-rule [outcome] needs_approval, handoff complex-double-pay [150000], hybrid simple-duplicate-rule [outcome] needs_approval. policy-human-old and policy-deny-normal: human_review and denied in all five structures, ledger 0, no proposal.

Per structure x type pass counts over all run-file rows (grid plus the single rows of cells 3, 31, 32, 42 and the rows of 41, 48, 50; `my-refund-window` has no gold row and is not counted; from P/live-05-c2-analysis.txt):
- base this: single simple 2/2, complex 3/5, insufficient 1/1, scope 1/1; single_skills complex 0/1; supervisor simple 2/2, complex 2/2; hybrid simple 3/3, complex 3/4, insufficient 1/1. Previous: single complex 4/5; supervisor complex 1/2; hybrid simple 2/3, complex 2/4; the rest equal.
- ex this: single simple 4/4, complex 5/8, insufficient 3/3, approval 4/4, scope 1/1; single_skills simple 1/2, complex 2/3, insufficient 2/2, approval 4/4; supervisor simple 4/4, complex 4/5, insufficient 2/2, approval 4/4; handoff simple 1/2, complex 1/2, insufficient 2/2, approval 4/4; hybrid simple 4/5, complex 7/10, insufficient 3/3, approval 4/4. Previous: single complex 6/8; single_skills complex 1/3; supervisor complex 3/5; hybrid simple 5/5, complex 6/10; the rest equal.

## hybrid `인용 문서` column
- Grid rows (cell 38, 8 hybrid rows over both records) and the cell 41 hybrid rows: no `인용 문서` in 실패 칸 in either record this run. In the previous exercises record hybrid complex-ops-log had `인용 문서` [runbook, security] (answered); that shape did not recur (the hybrid complex-ops-log rows this run pass: base 8 calls, exercises 7 / 6 calls).
- `인용 문서` appears in 실패 칸 for: the forced-Fast complex-double-pay row (both records, 누락 문서 [sla-a-v2, sla-a-amendment]; previous: exercises only) and the budget_exceeded rows (cells 42, 50). Counts over run files: hybrid rows with `인용 문서`: base 1 of 8 (prev 0 of 8), exercises 2 of 22 (prev 3 of 22). Single observations; no cause or rate stated.
- The hybrid complex-ops-log policy Worker events changed shape: previous records held `filled` 16 / 17 / 15 (policy Worker, forced insufficient-unknown-payment and complex-ops-log, complex-double-pay) and no `recovered` field; this run holds `filled` 0 everywhere and `recovered` 12 (base) / 10 (exercises) on the complex-ops-log policy Worker. The row ended `ok`, `answered`, 자동 검사 True, `problems` [] in both. The `recovered` field did not exist in the previous event, so the two are not comparable column by column. The shape is what `Day03_new/mas_lab/workers.py:160-166` produces when a Worker writes a registered id together with a label: the id is kept and counted in `recovered`, `kept` is not empty, so `filled` stays 0. The row does not store the Worker's raw `evidence_refs`, so that the 12 and 10 were labelled refs is a reading of the code, not something the record shows; the old code's behaviour was not re-read here.

## budget_exceeded rows per structure (results; FIXED_BUDGET not raised)
| structure | base this | base prev | exercises this | exercises prev |
|---|---:|---:|---:|---:|
| single | 1 | 1 | 1 | 1 |
| single_skills | 0 | 0 | 0 | 0 |
| supervisor | 0 | 0 | 1 | 1 |
| handoff | 0 | 0 | 0 | 0 |
| hybrid | 0 | 0 | 1 | 1 |
Same rows by design: single = cell 42 (budget 2, complex-double-pay, 2 calls), supervisor and hybrid = cell 50 (budget 6, both stopped at 6 calls). No grid row at FIXED_BUDGET (cells 37, 41, 48) ended budget_exceeded. `run_custom` rows (cells 9, 13, 17) are not saved as files; all printed status ok.

## Events (run files; 22 base rows and 79 exercises rows)
| event | base | exercises |
|---|---:|---:|
| gate_skipped | 2 | 8 |
| gate_text_appended | 0 | 10 |
| gate_text_replaced | 0 | 0 |
| earlier_turn_proposal_ungated | 0 | 0 |
| worker_checked | 11 | 33 |
| worker_checked total dropped | 1 (['INC-311'], outage Worker, forced Fast insufficient-unknown-payment) | 0 |
| worker_checked total filled | 0 | 0 |
| worker_checked total recovered | 12 (1 event) | 10 (1 event) |
| worker_checked problems non-empty | 0 | 0 |
| fallback_to_slow | 1 | 3 |
Previous records, same counts: gate_skipped 2 / 8, gate_text_appended 0 / 10, worker_checked 11 / 33 with dropped 2 / 3 events (all `INC-311`), filled 16 / 32 (1 / 2 events), no recovered field.
- gate_skipped: `named` ['P-7777'] in base cells 3 and 32; exercises cells 3, 32 and the five structures of insufficient-unknown-payment in cell 41; the eighth is cell 52 `my-refund-window` (single, `named` [], 환불 in the question). Outcomes insufficient or answered, ledger 0.
- gate_text_appended: 10 rows, all in cell 41, policy-human-old ("P-7002: 결제일부터 90일이 지나 재무 담당자 심사로 넘깁니다.") and policy-deny-normal ("P-8101: 청구서 INV-2026-07의 결제가 1건이라 중복 결제가 아닙니다.") once per structure; outcome and ledger unchanged (human_review / denied, 0), same as the previous record.
- fallback_to_slow: base 1 (cell 32 forced insufficient-unknown-payment); exercises 3 (the same, plus hybrid insufficient-unknown-payment and insufficient-no-policy in cell 41).
- earlier_turn_proposal_ungated fires only in multi-turn follow-up cases; this notebook has none.
Details per row: P/live-05-c2-events.txt; counting script P/live-05-c2-analyze.py.

## Rulings
- Ruling: rewrote the `filled` clause of the cell 34 `worker_checked` sentence ("비어 있던 근거 참조" became "사실은 적혔는데 거른 뒤 근거 참조가 하나도 남지 않은 결과") together with adding `recovered` - the code fills when `kept` is empty and the result has facts, which includes a result whose refs were all dropped - cost if wrong is one sentence to restore.
- Ruling: named the event fields `dropped`, `recovered`, `filled` and added "칸의 값은 행의 `events`에서 읽습니다" - the notebook prints only event kinds, so a student cannot see the values otherwise; no counts are written into the prose - cost if wrong is one sentence to delete.
- Ruling: left every other observation paragraph unrewritten although values moved (single complex 2/2 -> 1/2, hybrid failures moved between rows, `filled` 16/17/15 -> 0 with `recovered` 12/10) - every affected sentence is conditional and the new tables match one of its branches - cost if wrong is a reviewer wanting concrete numbers in the prose.
- Ruling: treated the `recovered` 12 and 10 on the hybrid complex-ops-log policy Worker as recorded values, not a `mas_lab` defect - the rows ended `ok`, `answered`, 자동 검사 True, `problems` [] - cost if wrong is the person re-triaging it.
- Ruling: did not raise any announce - no cell measured above it (closest: cell 42, 2 of 3) - cost if wrong is none.
- Ruling: counted the run-file rows with an mtime split between the base record's finish time and the start marker (22 + 79 = 101 files, equal to the expected row counts) - the run files carry no cell index - cost if wrong is a mislabelled row in the per-structure counts.

Live 05: done
