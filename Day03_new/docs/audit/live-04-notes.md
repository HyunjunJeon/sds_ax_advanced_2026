# Live 04 notes (run dag_mvxjjtgg_181ytn, node live-04, attempt 1)

Work dir <repo>. `uv run --no-sync` only. No 429, no rerun, no code cell edited, no announce raised. No .env content printed.
Announced before each run: base "약 36회" (previous record 36), exercises "약 38회" (previous record 38). Runs were strictly one after the other (base first, then --exercises), both under nohup with `wait_live.py <stem> --seconds 540`; each finished inside the first wait.

## Records (both finished true, errors 0, newer than P/run-b-start-marker)

| record | model calls | seconds | input tokens | output tokens | cache_read tokens | switched |
|---|---:|---:|---:|---:|---:|---:|
| 04-Graph-Engineering (base) | 34 | 104.2 | 84368 | 16098 | 48661 | 0 |
| 04-Graph-Engineering.exercises | 36 | 103.8 | 88995 | 15912 | 61100 | 1 |
| total | 70 | 207.9 | 173363 | 32010 | 109761 | |

Spend limit 100: used 70 (34 + 36), counted from the two usage.jsonl files (34 and 36 lines).
Previous records (P/live-04-before/): base 36 calls 114.8 s 96937 in / 17512 out; exercises 38 calls 110.6 s 105408 in / 16598 out.
Saved notebook P/live-04-nb-before.ipynb is the pre-edit copy. design_log.json is byte-identical to the pre-run copy (P/live-04-before/design_log.json).

## Per-cell model calls (cell index: base / exercises / announce)
5: 2 / 2 / 4 | 6: 2 / 2 / 4 | 13: 6 / 7 / 12 | 15: 3 / 3 / 3 | 22: 2 / 2 / 2 | 31: 7 / 7 / 12 | 44: 2 / 2 / 5 | 52: 10 / 9 / 16 | 56 (해보기 1): - / 2 / 4
No cell measured above its announce (cells 15 and 22 equal it: one call per delivery type, and a budget of 2 calls). No announce raised, no cell rerun.
Cell 0 call-scale sentence ("기본 실행은 약 31~58회", "해보기 유료 셀을 켜면 2~4회 늘어납니다") holds: base 34, exercises add 2.

## Markdown audit
Compared every `**관찰할 것.**` paragraph (cells 8, 19, 23, 34, 39, 49, 54), the problem paragraphs (12, 30, 40, 50), and the 해보기 prompts (55, 57, 59, 61) against both new executed notebooks. All hold except one sentence in cell 19.

Cause: in the base record the policy Worker returned status `complete` with 근거 수 0 (검증 문제 "근거 없이 complete입니다."). So `trim_payload` had no 원문 and no 근거 참조 to cut: cell 17 shows 남은 원문 0 and 남은 근거 참조 0 in all four rows, 남은 사실 10 -> 4 -> 1 -> 0. The sentence "`남은 원문`이 먼저 줄고 `남은 사실`이 뒤에 줄어듭니다" could not be seen. The exercises record had policy 근거 수 10, and showed 원문 10 -> 1 -> 0 -> 0 as the sentence says.

### Markdown sentences changed (one cell: 19, paragraph beginning `trim_payload` 표에서는)
Added after "근거 참조와 불확실성은 끝까지 유지합니다.":
> 이 순서는 `policy` Worker가 근거 참조를 돌려줬을 때만 보입니다. Worker 표에서 `policy`의 `근거 수`가 0이면 줄일 원문과 근거 참조가 처음부터 없습니다. `complete`였다면 `검증 문제`에 `근거 없이 complete입니다.`도 함께 나옵니다. 그 실행에서는 `남은 원문`과 `남은 근거 참조`가 모든 행에서 0이고 `남은 사실`만 줄어드니, 원문이 먼저 빠지는 순서를 이 표로 확인했다고 적지 마세요.
Nothing else was changed (diff of all 66 cells against the pre-edit copy shows only this paragraph).

### Paragraphs checked and left as written (value in the new records)
- Cell 8: role row 숫자의 출처 "1/5개가 조회 값에 있음. 없는 값: 10, 25, 99.0, 99.9" (the "예를 들어" case) in both; contract row validate_result "등록되지 않은 근거: INC-311" in both.
- Cell 19: 1줄 요약 row 누락 사실 [15%, 150000, 9월20일] in both; base 없는 인용 [billing, policy, outage], exercises []; base 자동 검사 False/False/False, exercises False/True/False; 사실+근거+불확실성 row has 누락 `9월20일` with 답에 20일 기한 True in base (the 표기 case).
- Cell 23: 허용 5, 거절 4, no 누적 model above 5; second table billing uncertain, policy budget_exceeded, outage 시작하지 않음.
- Cell 34: events show fault_injected then join action retry; Worker 구간 has outage and outage#2; billing and policy 1 each; lookup_availability 4 started vs 3 tool events; outage state uncertain; first `tool` row's month in the event table was 2026-08 in base and 2026-09 in exercises (the faulted call's own month is not shown); timeout_always ends escalate (2 attempts).
- Cell 39: 입력에 outage 언급 False, 예외 없음; join_results rows failed / uncertain / 결과 없음 with retry / reinvestigate / retry; billing, policy 1 run each, outage and outage#2 separate; 같은 키에 다른 결과 raises ValueError.
- Cell 49 and the ledger cells: see below.
- Cell 54: outcome needs_approval, ledger_refunds 0, 검증 사건 [[]] (one list, no rewrite), timeline writer one line. Base 실패 칸 [필수 사실] with 누락 [9월20일] and the answer saying 2026-09-20 (the sentence's exact case); exercises 자동 검사 True. policy_violations [] in both.

## Ledger cells (base / exercises, identical)
- Cell 41 (interrupt 앞 부작용 재현): 승인 대기 시점 원장 1건, 재개 후 2건 (R-0001, R-0002).
- Cell 44: 멈춘 곳 ('approve',), 승인 전 원장 건수 0. Gate needs_approval (환불액 1,000,000원 초과). Proposal P-9002 1,200,000원.
- Cell 45: path propose, gate:needs_approval, approve, execute, verify; 실행 횟수 approve 2 vs execute 1; 승인 전 원장 0건, 승인 후 1건.
- Cell 46: approved False -> 원장 0; approved True with amount 1,000,000 -> gate:deny ("제안 금액 1000000가 결제 금액 1200000와 다릅니다"), 원장 0.
- Cell 47: 응답 유실 뒤 키 없이 재시도 2건 (R-0001, R-0002), 키로 재시도 1건 (R-0001).
- Cell 48: ledger.find finds R-0001, no retry, 원장 건수 1.
- Cell 62 (해보기 4): verify True -> 결과 확인 True, 원장 1; verify False -> 결과 확인 "알 수 없음", 원장 1.
- Cell 60 (해보기 3): 정책 불가 시도 수 1 (original) vs 2 with RETRIES=3; 계속 거절 4 attempts ending stop_with_reason.
- Cell 53: hybrid_row ledger_refunds 0 in both. Base hybrid 10 model calls / 8 tool calls / 32160 in tokens; exercises 9 / 7 / 25022.

## budget_exceeded rows (results, FIXED_BUDGET not raised)
By design in both records, same shape each time:
- Cell 21 (no model): 허용 5, 거절 4 BudgetExceeded rows (limit 5, 3 threads x 3 tries).
- Cell 22 (budget 2): billing uncertain, policy `budget_exceeded` ("model 호출 한도를 초과했습니다."), outage "시작하지 않음 (앞 작업에서 예산 소진)"; budget.report() counts model 2, tool 1.
- Cells 25, 27, 60: `budget_exceeded` rows from the injected failure table (no model).
No `budget_exceeded` row came from a real run of cells 13, 31, 44 or 52 (all status ok / outcome needs_approval).

## New event kinds
`gate_skipped`, `earlier_turn_proposal_ungated`, `gate_text_appended`, `worker_checked`, `gate_text_replaced`: 0 occurrences in either executed notebook. Notebook 04 prints the event table only for the fault run (cell 32) and `검증 사건` for the hybrid row, neither of which showed them. Read "not seen" as "not printed in this notebook".

## Other observations (not prose changes)
- Base cell 13: policy Worker status `complete` with 0 근거 and 검증 문제 "근거 없이 complete입니다." (the third row of the 3절 failure table, happening live). Exercises: policy uncertain, 10 근거.
- Base cell 15: all three 누락 문서 columns list [billing-policy, sla-a-v2, sla-a-amendment] because of the 0-ref policy payload; exercises show [] for rows 2 and 3.

## Rulings
- Ruling: treated the base record's policy `complete` with 0 근거 as model variation, not a mas_lab defect - the notebook (cell 11 row 3, cell 39) and Day03_new/AGENTS.md 7장 already name this gap (Worker results reach the writer without `validate_result`; "참조가 비는 이유는 확인된 원인이 없다") - cost if wrong is the person re-triaging it as a code bug.
- Ruling: qualified the cell 19 trim_payload paragraph instead of rewriting its first sentence, keyed on `근거 수` 0 alone (not on status complete) - it must survive a repeat where policy is `uncertain` with 0 refs - cost if wrong is one extra sentence to review.
- Ruling: left cells 15 and 22 at announce 3 and 2 with zero margin - both counts are deterministic (one call per delivery type, budget of 2) - cost if wrong is a rerun if a later model change adds a call.
- Ruling: left design_log.json as the exercises run's write - byte-identical to the pre-run copy - cost if wrong is none.

Live 04: done
