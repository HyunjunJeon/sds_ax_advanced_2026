# Live 04 c2 notes (run dag_mvxqwuxv_oit10v, node live-04, attempt 1)

P = <P>
Work dir <repo>. `uv run --no-sync` only, no uv sync. No .env content or key value printed.
Announced before each run: base "about 34 model calls" (previous record 34), exercises "about 36 model calls" (previous record 36).
Runs were strictly one after the other (base, then --exercises), both under nohup with `wait_live.py <stem> --seconds 540`; each finished inside the first wait.
No 429, no model_error, no rerun, no code cell edited, no announce raised. Start marker: P/live-04-c2-start-marker. Pre-edit saved notebook: P/live-04-c2-nb-before.ipynb.

## Records (both finished true, errors 0, newer than the start marker)

| record | model calls | seconds | input tokens | output tokens | cache_read tokens | switched |
|---|---:|---:|---:|---:|---:|---:|
| 04-Graph-Engineering (base) | 33 | 100.4 | 78655 | 15637 | 42055 | 0 |
| 04-Graph-Engineering.exercises | 36 | 109.0 | 89251 | 16060 | 66335 | 1 |
| total | 69 | 209.4 | 167906 | 31697 | 108390 | |

Spend limit 100: used 69 (33 + 36), counted from the usage.jsonl files (33 and 36 lines).
Previous records (P/live-before-c2/): base 34 calls, 104 s, 84368 in / 16098 out; exercises 36 calls, 104 s, 88995 in / 15912 out.
Files written by the runs: Day03_new/outputs/live/04-Graph-Engineering{,.exercises}.{json,usage.jsonl,executed.ipynb}, plus two row files in outputs/runs
(dc9cdc24d68f477f92e445fb6ce08b0f.json for base cell 52, d160b03b4fdd4c559bf7372843056fab.json for exercises cell 52; runs count 1781 -> 1783).
design_log.json is byte-identical to the pre-run copy (P/live-before-c2/design_log.json).

## Per-cell model calls (cell index: base / exercises / announce)
5: 2 / 2 / 4 | 6: 2 / 2 / 4 | 13: 6 / 6 / 12 | 15: 3 / 3 / 3 | 22: 2 / 2 / 2 | 31: 7 / 7 / 12 | 44: 2 / 2 / 5 | 52: 9 / 10 / 16 | 56 (해보기 1): - / 2 / 4
No cell measured above its announce (cells 15 and 22 equal it: one call per delivery type, and a budget of 2 calls). No announce raised.
Cell 0 call-scale sentence ("기본 실행은 약 31~58회", "해보기 유료 셀을 켜면 2~4회 늘어납니다") holds: base 33, exercises 36 (the 해보기 1 cell added 2).
check_notebook.py ... --minutes 60 prints OK (exit 0). audit_live.py prints AUDIT OK (run after the markdown edit).

## Markdown audit
Compared every `**관찰할 것.**` paragraph (cells 8, 19, 23, 34, 39, 49, 54), the problem paragraphs (12, 30, 40, 50) and the 해보기 prompts (55, 57, 59, 61) against both new executed notebooks.
The cell 19 sentence added by the earlier run (policy with 근거 수 0 -> no 원문 to trim) stays true as written: in these two records policy returned 9 refs, so trim_payload shows 남은 원문 9 -> 0 -> 0 -> 0 and 남은 사실 8 (exercises 9) -> 8 (9) -> 3 -> 0, the order the first sentence says.
No sentence is contradicted by the new outputs. One spelling alignment that predates this rerun (the old records printed `150000` too) was made in cell 19 (below); it is in scope and the meaning is unchanged. The paragraphs are conditional ("나왔다면", "있다면", "수 있습니다") where the model varies:
- Cell 8: 숫자의 출처 for the role prompt row reads `1/5개가 조회 값에 있음. 없는 값: ['10', '25', '99.0', '99.9']` in both ("예를 들어" 10%, 25% case present in the answer). 작업 계약 validate_result: base `문제 없음`, exercises `[등록되지 않은 근거: INC-311]` (the "나왔다면" case). The role prompt row's 근거 수 is now 1 in both (the answer wrote `F-AV-2026-08`); the paragraph does not state it.
- Cell 19: 1줄 요약 row 누락 사실 [15%, 150000, 9월20일], 금지 포함 [], 유효 인용 0 in base (없는 인용 [billing, policy, outage]); exercises 유효 인용 1, 없는 인용 [] (the paragraph says 1줄 요약 "can" cite the key names). Base 사실+근거+불확실성 True, 원문 포함 False with 누락 사실 [9월20일] and 답에 20일 기한 True (the 표기 case); exercises both True. INC-311 in 없는 인용 of the other rows in both, and in the Worker table 검증 문제 of outage in both.
- Cell 23: 허용 5, 거절 4 in both; the thread that is refused differs (the paragraph says it varies); second table billing uncertain, policy budget_exceeded, outage 시작하지 않음; third table model, tool, model.
- Cell 34: fault_injected then join action retry, Worker 구간 has outage and outage#2, billing 1 and policy 1; 도구 lookup_availability 4 vs 3 tool rows in the event table plus the fault row; outage state uncertain (base), exercises outage uncertain with 근거 수 1 and policy complete; timeout_always ends escalate with 2 attempts. First tool row's month after the fault is 2026-09 in both.
- Cell 39: 입력에 outage 언급 False, 예외 없음; join_results rows complete / uncertain / failed / 결과 없음 with respond / reinvestigate / retry / retry; billing, policy 1 run each, outage and outage#2 separate; 같은 키에 다른 결과 raises ValueError.
- Cell 49 (+ ledger cells below): 노드 첫 줄 1 -> 2, interrupt 뒤 0 -> 1, 원장 건수 1 -> 2; approve 2 vs execute 1; 멈춘 곳 ('approve',), 승인 전 원장 0.
- Cell 54: outcome needs_approval, ledger_refunds 0, 검증 사건 [[]] (one list, no rewrite), timeline has one writer line, policy_violations [] in both. 자동 검사 True and 실패 칸 [] in both (the "9월20일 only" case did not occur in the hybrid row; the paragraph is conditional).
- Cells 55-61 prompts: 해보기 1 shows 불확실성 수 2 -> 3 (exercises); 해보기 2 (cell 58) 내 순서 vs trim_payload differ in 남은 사실 0 vs 7 (exercises 0 vs 8); 해보기 3 정책 불가 시도 수 1 -> 2 with the loop; 해보기 4 결과 확인 True vs 알 수 없음.

### Markdown sentences changed (one cell: 19, the sentence beginning `자동 검사` 표는)
- Before: `금지 포함`에 180,000이 있으면 ... `누락 사실`에 150,000이 있고 금지 표현이 없다면 ...
- After:  `금지 포함`에 `180000`이 있으면 ... `누락 사실`에 `150000`이 있고 금지 표현이 없다면 ...
Reason (a pre-existing mismatch, in scope as a markdown-only fix; the author can accept or reject it): the table prints the gold spelling (`150000` in 누락 사실, e.g. `[15%, 150000, 9월20일]`; `data/gold.jsonl` forbidden entries `180000`), so a reader searching the column for `150,000` or `180,000` finds nothing. Only the number spelling changed; the meaning is the same. Nothing else was changed (diff of all 66 cells against P/live-04-c2-nb-before.ipynb shows only this paragraph). The saved notebook still has no outputs and RUN_EXERCISE = False (the notebook has no RUN_OPTIONAL).

## Ledger cells (base / exercises, identical)
- Cell 41 (interrupt 앞 부작용 재현): 승인 대기 시점 원장 1건, 재개 후 2건 (R-0001, R-0002).
- Cell 44: 멈춘 곳 ('approve',), 승인 전 원장 건수 0. Gate needs_approval (환불액 1,000,000원 초과). Proposal P-9002 1,200,000원, idempotency_key T-1001:P-9002.
- Cell 45: path propose, gate:needs_approval, approve, execute, verify; 실행 횟수 approve 2 vs execute 1; 승인 전 원장 0건, 승인 후 1건 (R-0001).
- Cell 46: approved False -> 원장 0; approved True with amount 1,000,000 -> gate:deny ("제안 금액 1000000가 결제 금액 1200000와 다릅니다"), 원장 0.
- Cell 47: 응답 유실 뒤 키 없이 재시도 2건 (R-0001, R-0002), 키로 재시도 1건 (R-0001).
- Cell 48: ledger.find finds R-0001, no retry, 원장 건수 1.
- Cell 62 (해보기 4): verify True -> 결과 확인 True, 원장 1; verify False -> 결과 확인 "알 수 없음", 원장 1.
- Cell 53: hybrid row ledger_refunds 0 in both. Base hybrid row: model_calls 9, tool_calls 7, input 25196, output 4826, context_bytes 6961, overlap 7.973 s. Exercises: 10 / 8 / 32791 / 4843 / 8224 / 8.53 s.
Approval before 0, after 1, retry 2 versus 1: confirmed.

## budget_exceeded rows (results; FIXED_BUDGET not raised)
Same shape in both records, all by design:
- Cell 21 (no model): 허용 5, 거절 4 BudgetExceeded rows (limit 5, 3 threads x 3 tries).
- Cell 22 (budget 2): billing uncertain, policy `budget_exceeded` ("model 호출 한도를 초과했습니다."), outage "시작하지 않음 (앞 작업에서 예산 소진)"; budget.report() counts model 2, tool 1.
- Cells 25, 27, 60: `budget_exceeded` rows from the injected failure table (no model).
No budget_exceeded row came from a real run of cells 13, 31, 44 or 52 (status ok, outcome needs_approval in the hybrid rows).

## worker_checked events (read from the row files, not printed by the notebook)
Row file dc9cdc24d68f477f92e445fb6ce08b0f.json (base cell 52, hybrid, status ok, 12 events: tool 4, worker_checked 3, gate 2, decision 1, final_answer 1, validate 1):
- outage: problems [], dropped [], filled 0, recovered 0 (at 9.477)
- billing: problems [], dropped [], filled 0, recovered 0 (at 10.163)
- policy: problems [], dropped [], filled 0, recovered 9 (at 13.244)
- validate: problems []
Row file d160b03b4fdd4c559bf7372843056fab.json (exercises cell 52, hybrid, status ok, same 12-event shape):
- outage: problems [], dropped [], filled 0, recovered 0 (at 8.866)
- billing: problems [], dropped [], filled 0, recovered 0 (at 10.584)
- policy: problems [], dropped [], filled 0, recovered 0 (at 13.317)
- validate: problems []
Other new event kinds (`gate_skipped`, `earlier_turn_proposal_ungated`, `gate_text_appended`, `gate_text_replaced`): 0 in both row files. Notebook 04 prints neither these nor worker_checked, so no saved sentence mentions them.
What the three values mean (`Day03_new/mas_lab/workers.py:151-169`, `checked_worker`): `dropped` = labelled refs the model wrote that resolve to no registered id (removed, a note goes to uncertainty); `recovered` = registered ids the code pulled out of labelled ref strings that were not bare ids (`kept` minus the strings the model gave literally, line 163); `filled` = refs added from the Worker's own tool messages when the model returned no usable ref (line 166). So base policy `recovered 9, filled 0` means: the model wrote 9 ref strings that contained registered ids inside other text, and the code extracted them; it did not come from an empty ref list. Exercises policy `recovered 0` means the model wrote bare ids. This is the only place the changed `workers.py` visibly acted in these two records. It is one observation each; whether it connects to the open item in `Day03_new/AGENTS.md` 7장 about refs coming back empty or labelled is not shown by these two rows.
Note on cell 13 vs cell 52: cells 6, 13, 22 and 31 call plain `run_worker` (checked by grep of the notebook code cells; cell 52 calls `build_hybrid`, whose worker node calls `checked_worker`, `hybrid.py` worker). So cell 13 shows the unfiltered Worker result (outage `[등록되지 않은 근거: INC-311]` in both records) while the hybrid row's `checked_worker` showed problems [] for outage. They are separate model runs and different code paths.
Observation, not a finding: exercises cell 16 shows the 1줄 요약 row with 유효 인용 1 although its payload carries 0 refs (cell 14 shows 0); the writer produced a ref that exists in the case registry. The cell 19 prose is conditional ("수 있습니다") and holds. One observation only.

## Differences from the previous records (P/live-before-c2/, P/live-04-notes.md), none needing prose
- Base cell 13: policy is now `uncertain` with 9 근거 (before: `complete` with 0 근거 and 검증 문제 "근거 없이 complete입니다."); outage now has the INC-311 problem (before: policy had the problem). Cell 16 therefore shows `누락 문서` [] for rows 2-3 and 유효 인용 13 / 14 (before: all three docs missing in every row, 유효 인용 0 / 5 / 5), and cell 17 shows 남은 원문 9 -> 0 -> 0 -> 0 (before 0 in every row). The sentence the earlier run added to cell 19 still holds as a conditional.
- Base cell 52: 9 model calls / 7 tool calls (before 10 / 8); the answer now carries the credit (150,000원, 15%, 9월 20일) and 자동 검사 True (before False with 필수 사실 [9월20일] because of the 2026-09-20 spelling).
- Cell 58 (해보기 2): 내 순서 남은 원문 8 with 남은 사실 0, trim_payload 남은 사실 7 (before 내 순서 남은 사실 5 and 남은 원문 0, trim_payload 남은 사실 4).

## Rulings
- Ruling: changed `180,000` and `150,000` to `180000` and `150000` in the cell 19 sentence as a spelling alignment that predates this rerun (the old records printed `150000` too, so the new output does not contradict the old sentence) - the 누락 사실 and 금지 포함 columns print the gold spelling, so the comma form can never be found in them, and the task allows markdown-only fixes - cost if wrong: one sentence to restore, no behavior change.
- Ruling: did not rewrite any other observation paragraph although the values moved (policy complete -> uncertain, INC-311 problem moved between rows) - every affected sentence is conditional and the new tables match one of its branches - cost if wrong: a reviewer wanting concrete numbers in the prose.
- Ruling: left cells 15 and 22 at announce 3 and 2 with zero margin - both counts are deterministic (one call per delivery type, a budget of 2) and they measured exactly 3 and 2 again - cost if wrong: a rerun if a model change adds a call.
- Ruling: treated the hybrid row's policy `recovered 9` as a recorded value, not a defect - `worker_checked` is the designed event for refs that were filled from tool calls, and the row ended ok with problems [] - cost if wrong: none for this node.

Live 04: done
