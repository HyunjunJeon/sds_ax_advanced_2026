# Live 05 notes (run dag_mvxjjtgg_181ytn, node live-05, attempt 1)

Work dir <repo>. `uv run --no-sync` only. No 429, no rerun, no code cell edited, no announce raised, no mas_lab defect. No .env content printed.
Announced before each run: base "약 136회" (previous record 136), exercises "약 473회" (previous record 473). Runs were strictly one after the other (base first, then --exercises), both under nohup; base finished inside the first `wait_live.py 05-Choosing-Multi-Agent --seconds 540`, exercises needed three waits.

## Records (both finished true, errors 0, newer than P/run-b-start-marker)

| record | model calls | seconds | input tokens | output tokens | cache_read tokens | switched |
|---|---:|---:|---:|---:|---:|---:|
| 05-Choosing-Multi-Agent (base) | 145 | 412.2 | 553807 | 53579 | 391948 | 0 |
| 05-Choosing-Multi-Agent.exercises | 460 | 1238.1 | 1760800 | 147281 | 1297509 | 4 |
| total | 605 | 1650.4 | 2314607 | 200860 | 1689457 | |

Spend limit 700: used 605 (145 + 460), counted from the two usage.jsonl files (145 and 460 lines). The exercises run switched RUN_OPTIONAL (cell 1) and the three RUN_EXERCISE cells (48, 50, 52) on.
Previous records (P/live-before/): base 136 calls 393.3 s 494155 in / 51875 out; exercises 473 calls 1235.4 s 1818948 in / 154222 out.
Saved notebook before edits: P/live-05-nb-before.ipynb. Old records copied to P/live-05-before/. design_log.json after the runs is byte-identical to P/live-04-before/design_log.json (no net change).

## Per-cell model calls (cell index: base / exercises / announce)
3: 9 / 12 / 20 | 9: 3 / 3 / 8 | 13: 10 / 9 / 20 | 17: 9 / 9 / 20 | 23: 6 / 5 / 12 | 31: 14 / 16 / 30 | 32: 18 / 16 / 24 | 37: 74 / 63 / 100 | 41 (RUN_OPTIONAL): - / 278 / 330 | 42: 2 / 2 / 3 | 48 (해보기 1): - / 29 / 48 | 50 (해보기 2): - / 16 / 24 | 52 (해보기 3): - / 2 / 15
No cell measured above its announce, so no announce was raised and no record was rerun.
Cell 0 call-scale table holds: base 145 (table says 약 120~170회, 5~8분; 6.9 min), RUN_OPTIONAL 278 (약 220~330회 더, 10~15분; 12.2 min), 해보기 29+16+2 = 47 (합쳐서 20~70회 더).

## Markdown audit
Compared every `**관찰할 것.**` paragraph (cells 7, 11, 15, 20, 25, 29, 34, 44), the problem paragraphs (2, 12, 16, 21, 26, 30, 35, 45), the 해보기 prompts (47, 49, 51, 53), 정리 and 확인 질문 against both new executed notebooks. Cells 7, 11, 25, 29 hold in both runs without change (conditional wording already covers: all four Single baseline cases pass in both runs so the "실패 사례가 없어 첫 사례로 변동만 봅니다" line shows; `읽은 Skill` is ['credit-case','refund-case'] in both; overlap of billing/policy/outage in the timeline in both; 직렬 합 / 최장 경로 1.33 base and 1.41 exercises).

### Markdown sentences changed (4 cells; the diff of all 58 cells against the pre-edit copy shows only these)
Cell 15, the `둘 다 통과` bullet. Why: in the exercises record Single used 7 calls (lookup_payments x4) and 45958 input tokens, Supervisor 9 calls and 22838 tokens, so "추가 토큰" was false there (base: 22976 vs 27699). Now reads:
> - **둘 다 통과**: 품질이 같다면 Supervisor 쪽에서 더 든 비용은 무엇을 샀나요? 답할 수 있는 후보는 지연 단축, 역할별 도구 제한, 원문 격리입니다. 후보를 표의 칸으로 증명하지 못하면 비용만 는 것입니다. 늘어나는 칸은 `호출`, `시간`, 조정 바이트처럼 실행마다 다를 수 있으니 칸별로 따로 읽으세요. Single의 `입력 토큰`이 오히려 더 크게 나왔다면 Single이 이번에 같은 도구를 되풀이해 부른 것인지 앞 절 신호표의 `같은 도구 최대 반복`으로 확인하세요. 1회씩 잰 값이라 그 차이는 구조가 아니라 실행 변동일 수 있습니다.

Cell 20, the third bullet (`입력 토큰`을 역할별로 비교하세요). Why: in the base record the `policy` Worker has 3 calls / 10007 tokens under Context 분리 (it called `read_evidence`) against 2 calls / 6144 under Persona, so the sentence "도구 스키마가 늘면 Worker의 호출마다 입력이 함께 늡니다" could not be read off that row. Inserted after that sentence:
> 다만 `모델 호출`이 다른 행은 합계로 비교하지 마세요. 원문을 한 번 더 읽은 Worker(예: `read_evidence`를 부른 `policy`)는 도구 수와 상관없이 합계가 큽니다.

Cell 34, bullet 2 (`Slow 전환`이 False인데 `누락 사실`이 있으면). Why: in the base record the Router-judged `complex-double-pay` row (Slow 전환 False, 누락 사실 [9월20일], answer says 2026-09-20) is a 표기 case, not the dangerous missing-range case shown by the Fast-forced row. Appended:
> 단 `누락 사실`이 날짜 하나뿐이면(예: `9월20일`) 답 전문에 `2026-09-20`처럼 다른 표기로 들어 있는지 먼저 보세요. 표기 차이라면 이 위험이 아니라 자동 검사의 한계입니다.

Cell 34, bullet 3 (`사건 순서` ... 원장에 두 번 쓰지 않습니다). Why: the printed `사건 순서` of the forced `insufficient-unknown-payment` row now ends `fallback_to_slow`, `worker_checked` x3, `final_answer`, `validate`, `gate_skipped` in both runs, and nothing in the notebook explained the two new kinds. Appended (checked against `Day03_new/mas_lab/workers.py:165` and `Day03_new/mas_lab/gate.py:49-59`; the `gate_skipped` clause was widened once after review because the first branch at gate.py:54-55 fires on a refusal/review label without 환불 in the question):
> 전환 뒤 `worker_checked`가 Worker마다 하나씩 보이면 합성 전에 코드가 각 Worker 결과를 거른 기록입니다(등록되지 않은 근거 참조를 뺐는지, 비어 있던 근거 참조를 그 Worker 자신의 도구 결과로 채웠는지). `gate_skipped`는 코드가 질문의 결제 번호를 조회된 결제와 대조할 수 없었다는 흔적입니다(조회되지 않는 번호이거나 번호가 없을 때, 환불을 묻는 질문이거나 답이 거절·심사 결론일 때). 답 본문은 바뀌지 않고, 쓰기 제안이 없으니 원장도 그대로입니다.

Cell 44, bullet `A에서 B로`. Why: in the exercises record hybrid A -> B moved 평균 시간 19.2 -> 17.0 but 평균 입력 토큰 23596 -> 25383 (the removed forced-Fast row was the cheap one), against "쉬운 사례만 남으면 평균이 내려가고". Inserted after "...어려운 사례만 남으면 평균이 올라갑니다.":
> 빠진 행이 빨리 끝난 실패 행이라면 평균이 올라가기도 하니, 움직인 방향보다 `남은 사례`가 달라졌는지를 먼저 보세요.

### Paragraphs checked and left as written (value in the new records, base / exercises)
- Cell 7/11: Single baseline 4 cases all 자동 검사 True; cell 9 target `complex-double-pay` with the "실패 사례가 없어" line; single+한 줄 3 calls vs single 4 (base) / 7 (ex), both True.
- Cell 20: Persona 역할 밖 도구 호출 0 in base, 2 in exercises (outage called search_knowledge and lookup_payments); both branches of the bullet are written. 같은 Desk True, 같은 원장 True, 원장 건수 1.
- Cell 25: 읽은 Skill both; single_skills 60767 / 48880 tokens, 자동 검사 False [9월20일] in both (answers carry 2026-09-20, a 표기 case).
- Cell 29: 판정 rows: 1회 관찰, 1회 관찰, 주장할 수 없음: 비교 대상 빈 칸, 주장할 수 없음: 평가 방법, 측정자 빈 칸.
- Cell 34 paragraph under the bullets: gate table deny/denied 0, human_review/human_review 0, needs_approval/needs_approval 0, allow/executed 1; edges fast->validate, writer->validate, validate->gate/worker/writer. Forced Fast `complex-double-pay`: Slow 전환 False, 5 / 4 calls, 누락 [99.3, 15%, 150000] / [99.3, 15%, 150000, 9월20일], events decision, final_answer, validate, gate, gate. Forced `insufficient-unknown-payment`: Slow 전환 True, 13 / 12 calls.
- Cell 44: twins table (single 4 vs 8 calls base, 7 vs 4 exercises; supervisor True/False base, True/True ex; hybrid False/True base, True/False ex), three average tables, 실패 행 목록, 사람 판정 칸 (first failing row: supervisor base, hybrid exercises, both 2026-09-20 in the answer). usage 누락 0 everywhere.
- Cell 54: CORRECT_BUT_FAILS 자동 검사 False 누락 [9월20일]; WRONG_BUT_PASSES True. Kept.
- Cells 48, 50, 52 (exercises only): 해보기 1 hybrid x3 all 자동 검사 True (10, 9, 10 calls); 해보기 2 single ok 4 calls, supervisor and hybrid budget_exceeded at 6 calls ("model 호출 한도를 초과했습니다."); 해보기 3 자동 검사 True.

## 05 comparison table summary (cell 39, 구조 x 유형, 2 cases x 1 repeat each)
Base (12 rows, 자동 검사 실패 2행: supervisor complex-double-pay [9월20일] 표기, hybrid simple-duplicate-rule [outcome] needs_approval; 실행 실패 0):
| 구조 | 유형 | 통과/실행 | 평균 시간 | 평균 호출 | 평균 입력 토큰 |
|---|---|---|---:|---:|---:|
| single | simple | 2/2 | 8.5 | 3.5 | 15108 |
| single | complex | 2/2 | 14.1 | 5.0 | 31204 |
| supervisor | simple | 2/2 | 18.6 | 6.0 | 15457 |
| supervisor | complex | 1/2 | 22.1 | 7.5 | 17756 |
| hybrid | simple | 1/2 | 15.2 | 6.5 | 26678 |
| hybrid | complex | 2/2 | 23.7 | 8.5 | 29718 |
Exercises (12 rows, 자동 검사 실패 1행: hybrid complex-double-pay [9월20일] 표기; 실행 실패 0):
| single | simple | 2/2 | 10.2 | 4.0 | 17945 |
| single | complex | 2/2 | 11.2 | 3.0 | 15356 |
| supervisor | simple | 2/2 | 15.2 | 5.0 | 12328 |
| supervisor | complex | 2/2 | 19.2 | 6.5 | 16603 |
| hybrid | simple | 2/2 | 11.7 | 4.5 | 14150 |
| hybrid | complex | 1/2 | 22.0 | 8.5 | 29636 |
RUN_OPTIONAL table (exercises, cell 41, 50 rows, 5 structures x 4 types; usage 누락 0, 정책 위반 0): 통과/실행 single 2/2, 2/2, 2/2, 4/4; single_skills 1/2, 1/2, 2/2, 4/4; supervisor 2/2, 1/2, 2/2, 4/4; handoff 1/2, 1/2, 2/2, 4/4; hybrid 2/2, 1/2, 2/2, 4/4 (types simple, complex, insufficient, approval). Every row status ok.

## budget_exceeded rows per structure, new vs earlier records (counted from the per-run files in Day03_new/outputs/runs by mtime window, 22 rows base and 79 rows exercises in both old and new, matched to the printed progress lines)
| structure | base new | base old | exercises new | exercises old |
|---|---:|---:|---:|---:|
| single | 1 | 1 | 1 | 1 |
| single_skills | 0 | 0 | 0 | 0 |
| supervisor | 0 | 0 | 1 | 1 |
| handoff | 0 | 0 | 0 | 0 |
| hybrid | 0 | 0 | 1 | 1 |
Same rows by design: single = cell 42 (budget 2, `complex-double-pay`), supervisor and hybrid = cell 50 (budget 6). No grid row at FIXED_BUDGET (cells 37, 41, 48) ended budget_exceeded in either record, so counting Router and triage calls in Budget did not turn any Hybrid row. The cell 50 hybrid row stopped at 6 calls now (old record: 7). `run_custom` rows (cells 9, 13, 17) are not saved as files; all three printed status ok.

## policy-human-old and policy-deny-normal (cell 41, exercises record only)
| case | single | single_skills | supervisor | handoff | hybrid |
|---|---|---|---|---|---|
| policy-human-old | human_review | human_review | human_review | human_review | human_review |
| policy-deny-normal | denied | denied | denied | denied | denied |
Same five outcomes in the old record. ledger_refunds 0 and no proposal in all ten rows. Every row status ok.
Gate text: `gate_text_replaced` 0 rows. `gate_text_appended` 10 rows, all of them these two cases, one per structure: policy-human-old got "P-7002: 결제일부터 90일이 지나 재무 담당자 심사로 넘깁니다." and policy-deny-normal got "P-8101: 청구서 INV-2026-07의 결제가 1건이라 중복 결제가 아닙니다." The model text already said the same thing in its own words each time (checked single, handoff, hybrid), so the appended sentence is a repeat, not a contradiction; the outcome did not change. The old record has no such events (event kind did not exist then).

## Events seen (run files; counts over the 22 base and 79 exercises rows)
- `worker_checked`: base 11 events (hybrid complex-double-pay x2 rows = 6, insufficient-unknown-payment forced Fast->Slow = 3, complex-ops-log = 2), exercises 33 events. `problems` empty in all 44. `dropped` ['INC-311'] (an incident ID the Worker cited as a reference) in 2 base and 3 exercises events, all on the `outage` Worker. `filled` > 0 in 1 base event (policy, 16 refs, forced insufficient-unknown-payment) and 2 exercises events (policy, 15 and 17 refs).
- `gate_skipped`: base 2, exercises 8. `named` ['P-7777'] in all but one: single and hybrid insufficient-unknown-payment (cells 3 and 32) in base; in exercises cells 3, 32 plus the five structures of insufficient-unknown-payment in cell 41. The remaining one is cell 52 `my-refund-window` (single, `named` [], question mentions 환불 without a payment number). All outcomes insufficient or answered, ledger 0.
- `earlier_turn_proposal_ungated`: 0 (it only fires in multi-turn follow-up cases, none in this notebook).
- `gate_text_replaced`: 0. `gate_text_appended`: 10 (above).
- `fallback_to_slow`: 1 base (forced-Fast `insufficient-unknown-payment`, cell 32), 3 exercises (the same forced row, plus in cell 41 the Router-judged Fast rows of hybrid `insufficient-unknown-payment` and `insufficient-no-policy`). `gate` appears twice in the forced-Fast `complex-double-pay` rows (needs_approval), as the cell 34 prose says.

## Findings
- Automatic-check failures that are 표기 cases (every saved answer carries 2026-09-20, 누락 [9월20일], verified in the run files): base single_skills, hybrid (Router-judged), supervisor (persona row is not saved, so not verified); exercises single_skills (x2), hybrid, supervisor, single (cell 50). Real omissions: forced-Fast `complex-double-pay` in both records (99.3, 15%, 150000 and in exercises also the deadline), exercises handoff complex-double-pay (150000), exercises hybrid complex-ops-log (인용 문서 runbook, security; 누락 사실 empty).
- Base hybrid `simple-duplicate-rule` (Fast path) proposed a refund of P-9002 on a rule question, outcome needs_approval, ledger 0: the "요청하지 않은 환불을 제안한 것처럼" case the cell 44 prose already describes. Exercises: single_skills and handoff did the same on this case.

## Rulings
- Ruling: added a sentence for `worker_checked` and `gate_skipped` in cell 34 instead of leaving them unexplained - they print in the `사건 순서` line of both records and the notebook never named them - cost if wrong is one extra sentence to delete.
- Ruling: treated the 10 `gate_text_appended` rows as the gate working as designed, not a mas_lab defect - the appended sentence is the gate's own text and the outcome and ledger are unchanged - cost if wrong is the person re-triaging the repeated sentence as a defect.
- Ruling: left every announce unchanged - no cell measured above its announce - cost if wrong is none.

Live 05: done
