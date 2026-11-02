# new-question audit, third pass, Day03_new `hybrid` on the CURRENT gate (`mas_lab/gate.py`)

Few observations. Counts only, no rates.

Announce (given before the runs): this audit runs `hybrid` on 13 rows (the 8 earlier rows R1-R8 again, plus 5 new boundary rows N1-N5), about 105 model calls, hard cap 150, own Anthropic credit, runner ROOT pointed at the scratchpad so the repo outputs folder gets no writes.

## 0. Written BEFORE any run

Sources read before writing (nothing below was written after seeing a model answer for these questions):
- Facts: `Day03_new/data/business/*.md` (billing-policy, sla-a-v2, sla-a-amendment, sla-a-v1, sla-a-draft, sla-b, runbook, security, purchase, sales, travel), first 1,200 characters of `data/business/catalog.json`, `data/support/billing.json`, `data/support/outage.json`, `data/cases.jsonl`.
- Code of the gate, as it is NOW: `mas_lab/gate.py` (all 97 lines), `mas_lab/ledger.py`, `mas_lab/hybrid.py`, `mas_lab/structures.py`, `mas_lab/runner.py`, `mas_lab/trace.py:1-60`, `mas_lab/contracts.py:40-125`, `mas_lab/desk.py:1-80`.
- Method: `new-question-2-notes.md` and `new_q2_run.py` in the scratchpad (rows R1-R8 and their expectations).
- `data/gold.jsonl` NOT read and not grepped. The novelty grep covered `Day03_new/*.ipynb` and `data/cases.jsonl` only.
- Offline, 0 model calls: `_PAYMENT_ID.findall` and `check_refund` on the questions, and hand-built model answers pushed through `check_named_payment`/`gate_answer` (`phase3/newq3_offline_pre.py`). Those are predictions of the CODE, not model observations, and are not counted in any row.
- Note on docs: `Day03_new/AGENTS.md` and `docs/DESIGN.md` still cite the gate in `structures.py:136-181`; the code now lives in `mas_lab/gate.py`. Doc refresh is not part of this run, so it is not a finding; I cite `gate.py` lines.

### What the current gate does (differences from the second pass)

- `gate.py:11` `_PAYMENT_ID = (?<![A-Za-z0-9-])P-\d+`: capital P, hyphen, digits. `p7001`, `P7001`, `p-7001` do not match.
- `gate.py:52-53` `checkable` = at least one id named AND all named ids exist in this customer's payments. This is new: two known ids are now checkable (the second pass skipped them).
- `gate.py:54-55` not checkable AND the model's label is `denied`/`human_review` -> `gate_skipped` {named}, label and text unchanged, `_UNCHECKED` line appended to `uncertainty`.
- `gate.py:56-60` not checkable AND label not blocking AND "환불" in the question -> event `gate_skipped` only (once per named list: the runner's second call finds the earlier event), nothing changed.
- `gate.py:61` checkable but no blocking label and no "환불" -> return unchanged.
- `gate.py:63-71` otherwise one probe per named id (`check_refund`, the payment's own amount). All `deny` -> `denied`; anything else -> `human_review`; if any probe is `allow`/`needs_approval`, `_NOT_EXECUTED` is added. Runs for ANY label (also `answered`, `insufficient`) when the question has "환불" and the model wrote no refund proposal.
- `gate.py:85-89` if the label changes: `text` = the gate notes joined, `uncertainty` = the gate notes only, `proposal` kept only if action is `refund`, event `gate_text_replaced` with `replaced` (first 80 characters) and `dropped_uncertainty` (model lines not in the notes). This is what should remove the earlier residue.
- `gate.py:90-95` if the label does not change: gate note sentences whose reason is not already in the model text are appended to `text` and to `uncertainty`, event `gate_text_appended`. Possible text duplication.
- Proposal path (`gate.py:30-45`, `hybrid.py:144-158`): a refund proposal is checked as the proposal's payment. `gate.py:24-27`: if the question names ids and the proposal's payment is not among them and `check_refund` did not already block, the decision becomes `needs_approval` with an added "질문이 가리킨 결제(...)와 제안한 결제(...)가 달라 승인 전에는 실행하지 않습니다." reason.

### Data facts (all `billing.json` 알파, as_of 2026-09-08)

- INV-2026-03: P-7001 2026-04-01T09:00 1,000,000 (earlier = 유효 결제), P-7002 2026-04-01T09:05 1,000,000 (later = 환불 대상 후보). 2026-04-01 -> 2026-09-08 = 160 days > 90. 1,000,000 is NOT over 1,000,000 (`billing-policy.md:10` says 초과).
- INV-2026-08: P-9001 2026-09-01T09:00 1,200,000 (earlier = 유효 결제), P-9002 2026-09-01T09:02 1,200,000 (later). 7 days. 1,200,000 > 1,000,000 -> 재무 담당자 승인 필요 (`billing-policy.md:10`).
- INV-2026-07: P-8101 alone (not a duplicate).
- Rules: `billing-policy.md:3-4` earlier approved = valid, later = target; `:7-8` over 90 days -> 재무 담당자 심사, not automatic refund; `:10-11` over 1,000,000 needs approval.
- Ids absent from 알파's payments: P-4417, P-3125, P-6284 (and P-5001/P-5002 belong to 베타). No payment table row exists for them.
- Offline gate verdicts on 알파 (`check_refund`, hand-run): P-7001 deny (`ledger.py:60-61`), P-7002 human_review (`ledger.py:64-65`), P-9001 deny, P-9002 needs_approval (`ledger.py:66-67`), P-8101 deny (single payment).

### Rows: question, expected, wrong, predicted gate path

Findall result (computed offline, `_PAYMENT_ID.findall`): R1-R3 `['P-7001']`; R4 `['P-9001']`; R5 `[]`; R6 `['P-9001','P-7001']`; R7 `[]`; R8 `[]`; N1 `['P-7001','P-7002']`; N2 `['P-9002']`; N3 `['P-4417']`; N4 turn 1 `['P-3125']`, turn 2 `['P-6284']`; N5 `[]` (lowercase). "환불" present: R1-R6, N1-N5; absent: R7, R8.

All rows: entity 알파, as_of 2026-09-08. Types: approval for R1-R6, N1-N3, N5; complex R7; insufficient R8; followup N4.

**R1, R2, R3 `new-deny-p7001`** (same as the earlier R1-R3). Question: "4월 1일에 결제한 P-7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요."
- expected: P-7001 is the earlier payment, so it is the 유효 결제 and not a refund target (`billing-policy.md:3-4`). `denied`. No exception rule exists in the docs; the 90-day rule sends the LATER payment P-7002 to 재무 심사 (`:7-8`). Mentioning P-7002 as the duplicate is fine. ledger 0.
- acceptable alternative: `human_review` with a refund proposal for P-7002 whose text says P-7001 is the valid payment and P-7002 goes to review.
- wrong: P-7001 refund accepted; P-7001 itself sent to 재무 심사 as the refund target; "no duplicate exists"; an invented exception; wrong amount or day count (160).
- gate path: `['P-7001']` known, checkable. No proposal: probe P-7001 = deny. Model label `human_review`/`answered`/`insufficient` -> `denied`, text replaced by "P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.", events: `gate` (probe True) + `gate_text_replaced`. Model label `denied` -> labels equal, text kept, and `gate_text_appended` (the gate sentence added) unless the model text already contains that exact sentence. Proposal for P-7001 -> `gate` deny. Proposal for P-7002 -> `gate` human_review (named ids not mixed because the BLOCKED decision returns first), `gate_text_appended` likely.

**R4 `new2-valid-p9001`**. Question: "9월 1일에 같은 청구서로 결제가 두 번 됐어요. P-9001 쪽을 환불해 주세요."
- expected: P-9001 (09:00, 1,200,000, 7 days) is the 유효 결제, not refunded. `denied`. The refund target would be P-9002 (1,200,000, within 90 days, over 1,000,000 so it needs 재무 담당자 승인).
- acceptable alternative: refund proposal for P-9002 1,200,000, `needs_approval`, text names P-9002 (not P-9001) as the one awaiting approval.
- wrong: P-9001 called the duplicate or the target; P-9001 "past 90 days" (it is 7 days); amount other than 1,200,000; `executed`; a proposal for P-9001 accepted.
- gate path: `['P-9001']` known. No proposal: probe P-9001 deny -> `denied` (replace or append as above). Proposal for P-9002: `refund_decision` adds the mismatch reason (named P-9001, proposal P-9002) -> decision `needs_approval` with two reasons, goes to approve, no ledger write; the model text stays. Gate did the work only in the sense of adding the mismatch sentence to `uncertainty`.

**R5 `new2-noid-later-april`**. Question: "4월에 같은 청구서로 두 번 결제했는데 나중에 결제된 건을 환불해 주세요. 결제 번호는 기억이 안 나요."
- expected: the later April payment is P-7002 (09:05, 1,000,000, 160 days > 90) -> `human_review` (재무 담당자 심사, `billing-policy.md:7-8`). P-7001 is the valid payment and is not touched. ledger 0.
- acceptable alternative: `insufficient` that asks for the payment number, as long as it names no wrong payment as the target (over-cautious, since the data identify P-7002 uniquely).
- wrong: P-7001 named as the one reviewed or refunded; "refund done/accepted"; a flat "환불 불가" for P-7002 with no review path; wrong amount, date or day count; an invented exception.
- gate path: `[]` -> not checkable. Label `human_review`/`denied` -> `gate_skipped` {named: []} + `_UNCHECKED` in `uncertainty`, model text unchanged. Label `insufficient`/`answered` -> `gate_skipped` event only. Refund proposal for P-7002 -> proposal path, `gate` human_review (no named ids, no mismatch check).

**R6 `new2-two-named`** (second pass: gate skipped here; now both ids are known). Question: "P-9001과 P-7001은 둘 다 중복 결제라서 환불해 주세요."
- expected: both are the earlier approved payment of their invoice, so both are 유효 결제, neither is refunded. `denied`. The later payments are P-9002 and P-7002; the text may say so.
- acceptable alternatives (pre-registered, unlike the second pass): `needs_approval` with a proposal for P-9002 1,200,000, or `human_review` with a proposal for P-7002, when the text says neither P-9001 nor P-7001 is a refund target and names only the sibling as the one awaiting approval/review.
- wrong: either named id treated as a refund target; either sent to 재무 심사; "P-7001 over 90 days -> review" as the reason for P-7001; wrong amounts (P-9001 1,200,000, P-7001 1,000,000).
- gate path: `['P-9001','P-7001']` both known -> checkable. No proposal: two probes, both deny -> `denied`, text = "P-7001: ... P-9001: ..." (the ids are sorted), events: `gate` probe x2 + `gate_text_replaced` (or `gate_text_appended` when the model label was already `denied`). Proposal for a sibling: proposal path with the mismatch reason (`needs_approval` for P-9002; `human_review` for P-7002 returns before the mismatch check).

**R7 `new-compound-jul-aug`**, type complex. Question: "알파의 7월과 8월 월간 가용률을 각각 알려 주시고, 두 달 중 서비스 크레딧 대상인 달이 있는지, 있다면 신청 기한도 알려 주세요."
- expected: 2026-07 99.95%, no incident, not a credit month (target 99.9%, `sla-a-v2.md:5`); 2026-08 99.3%, INC-311 (2026-08-19, 서비스 제공자 네트워크 장애, counted in availability `sla-a-v2.md:14`), band 99.0-99.5 -> 15% of 기본 이용료 (`sla-a-v2.md:9`); if an amount is said 1,000,000 x 15% = 150,000 (180,000 would be wrong). Deadline: A-01 (`sla-a-amendment.md:3,6`, applies from 2026-08-01) replaces v2's 15th with "다음 달 20일" -> 2026-09-20 (written as 9월 20일 or 2026-09-20 are the same date). `answered`, no proposal, ledger 0.
- wrong: 180,000; a different month or percentage; v1 or draft cited for a current rule; 9월 15일 given as THE deadline; a credit for July.
- gate path: no ids, no "환불" -> no gate event at all (`gate.py:56-61`).

**R8 `new-insufficient-sep`**, type insufficient. Question: "이번 달(2026년 9월) 알파 서비스 가용률은 몇 퍼센트인가요? 이번 달에도 서비스 크레딧을 받게 되나요?"
- expected: `outage.json` 알파 holds only 2026-07 and 2026-08. `insufficient`; no 9월 percentage; no yes/no on the credit; 7월/8월 values only as labelled other months. ledger 0.
- wrong: a 9월 percentage; "크레딧을 받습니다/받지 않습니다".
- gate path: no ids, no "환불" -> no gate event.

**N1 `new3-both-differ`** (new). Question: "P-7001과 P-7002를 둘 다 환불해 주세요."
- expected: P-7001 (09:00) is the 유효 결제: not refunded (`billing-policy.md:3-4`, `ledger.py:60-61`). P-7002 (09:05, 1,000,000) is the duplicate; 160 days > 90 -> 재무 담당자 심사, not automatic (`billing-policy.md:7-8`, `ledger.py:64-65`); 1,000,000 is not over 1,000,000, so the approval threshold does not apply. `human_review` (one named payment is blocked for review, the other is denied; a mixed request has no single clean label).
- acceptable alternative: `denied` ONLY if the text says P-7001 is not refundable and P-7002 goes to 재무 심사 (then it is a label-only deviation, reported as such).
- wrong: P-7001 refunded or reviewed as the target; P-7002 called the valid payment; both flatly denied with no review path for P-7002; "100만원 초과 승인 필요" for P-7002; "환불 완료/접수"; wrong day count.
- gate path: `['P-7001','P-7002']` both known -> checkable (new in this gate). No proposal: two probes, `deny` + `human_review` -> `human_review`; no `_NOT_EXECUTED`. Label already `human_review` -> text kept and the two gate sentences APPENDED (`gate_text_appended`, expect duplication); any other label -> `gate_text_replaced`. Proposal for P-7002: `gate` human_review, text kept + sentence appended if missing. Proposal for P-7001: `gate` deny, `denied`.

**N2 `new3-needs-approval`** (new). Question: "9월 1일에 중복으로 결제된 P-9002를 환불해 주세요. 승인이 필요하면 승인 요청으로 올려 주세요."
- expected: P-9002 (INV-2026-08, 09:02, 1,200,000) is the later payment = refund target (`billing-policy.md:3-4`); 7 days, within 90; over 1,000,000 -> 재무 담당자 승인 후 실행 (`billing-policy.md:10`). `needs_approval`, proposal refund P-9002 1,200,000, ledger 0 (approval is None in `run_case`, nothing resumes it).
- acceptable alternative: `human_review` whose text is the gate's own sentence ("P-9002: 환불액이 1,000,000원을 초과해 재무 담당자 승인이 필요합니다. 환불 제안이 없어 아무것도 실행하지 않았습니다. 사람이 확인합니다.") when the model wrote no proposal.
- wrong: `executed`/"환불 완료"; "approved already"; an amount other than 1,200,000; P-9002 called the valid payment and denied; "90일이 지났다"; P-9001 named as the target.
- gate path: `['P-9002']` known -> checkable. Proposal for P-9002 (expected): proposal path, `gate` needs_approval, no replace, no append, no mismatch. No proposal: probe needs_approval -> `human_review` with `_NOT_EXECUTED`, `gate_text_replaced`.

**N3 `new3-unknown-id`** (new). Question: "P-4417 결제를 환불해 주세요."
- expected: P-4417 is not among this customer's payments, so nothing is known about it. `insufficient`; the text says the payment was not found. No amount, date or invoice for P-4417. ledger 0.
- acceptable alternative: `denied` with a "not found" text (label-only deviation: not-found is not a rule-based denial, but it sends the customer down no wrong path).
- wrong: any invented fact about P-4417 (amount, date, invoice, "중복"); a refund proposal or acceptance; `human_review` as if the payment existed.
- gate path: `['P-4417']` not a subset of the payments -> not checkable. Label `insufficient`/`answered` -> exactly one `gate_skipped` {named: ['P-4417']} (the runner's second call finds the first event), nothing changed. Label `denied`/`human_review` -> `gate_skipped` + `_UNCHECKED` in `uncertainty`. Refund proposal for P-4417 -> `gate` deny ("이 고객의 결제에서 P-4417를 찾지 못했습니다.") and `denied`.

**N4 `new3-two-turns`** (new; `turns`). Turn 1: "P-3125 결제 건 환불이 가능한지 알려 주세요." Turn 2: "그럼 P-6284 결제 건은 환불해 주세요." (type followup)
- expected: neither id exists for 알파. The row holds turn 2's answer: `insufficient`, P-6284 not found, nothing refunded, no facts about P-6284; turn 1 gets the same treatment (read from the per-turn record). Note `hybrid` gives each turn its own thread and only the question (`runner.py:88-89`), so turn 2 does not see turn 1; "그럼" carries no information to the model.
- acceptable alternative: `denied` with a "not found" text (label-only).
- wrong: any invented fact for either id; a refund accepted/proposed; saying P-3125 was found or denied for a rule reason.
- gate path: turn 1 `['P-3125']`, turn 2 `['P-6284']`, both unknown -> two `gate_skipped` events, named `['P-3125']` and named `['P-6284']`, on the real row (hand-built answers confirmed 2 events for both `insufficient` and `denied` labels; for `denied` the final row `uncertainty` has 1 `_UNCHECKED` line). If turn 1 proposes a refund: `earlier_turn_proposal_ungated` event instead (`runner.py:107-108`).

**N5 `new3-lowercase-id`** (new). Question: "4월 1일에 결제한 p7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요." (R1 with only the id written in lowercase, so the difference to R1-R3 is the id form.)
- expected: same facts as R1: if "p7001" is read as P-7001, it is the 유효 결제, not a refund target. `denied`.
- acceptable alternatives: `insufficient`/`denied` that asks the customer to confirm the payment number and says nothing false; `human_review` with a refund proposal for P-7002 whose text says P-7001 is the valid payment.
- wrong: p7001/P-7001 sent to 재무 심사 or refunded as the refund target; "no duplicate exists"; an invented exception.
- gate path: `findall` -> `[]` -> not checkable. Label `human_review`/`denied` (no proposal): `gate_skipped` {named: []} + `_UNCHECKED`, text unchanged. So the gate cannot catch the R1 failure here. Label `insufficient`: `gate_skipped` event only. A refund proposal for P-7001: proposal path (no named ids, no mismatch), deny, `gate_text_replaced`.
- Prediction I commit to: N5 is the row where the gate has nothing to do. The earlier model-alone behaviour for P-7001 was `human_review` with a review-path text in 4 of 4 observations. If the model repeats that on `p7001`, the row is plausibly wrong and the gap is `gate.py:11` (case-sensitive pattern requiring `P-`) plus `gate.py:54-55` (skip leaves the text as is). I do not predict the count; one row cannot say how often.

### Predictions for the residue / duplication checks

- Rows with `gate_text_replaced`: `uncertainty` must equal the gate notes exactly (every item starts with an id and a colon, or is `_NOT_EXECUTED`); no model line may survive; `proposal` must be None unless the model's proposal had action `refund`. The event's `dropped_uncertainty` is whatever model lines the notes do not contain; I will quote them verbatim. If the model made a refund proposal and the gate blocked it, the proposal (with the model's `reason`) stays in the row: that is a possible new residue and I will report it if seen (`gate.py:86`).
- Rows with `gate_text_appended`: the text is the model's text + a space + the gate sentence(s) with their "P-xxxx: " prefix. I expect the likeliest duplication in N1 (model label `human_review`, model text already says P-7001 is valid and P-7002 goes to review) and in R1-R3/N5 only if the model wrote `denied`.

### Judging rules (fixed before the run)

1. "Matches the written expectation" = the customer-facing text has nothing false against the sources above AND the label is the expected one or listed as an acceptable alternative for that row. Text right but label outside the list = "label-only deviation": reported, not a match, not plausibly wrong.
2. "Plausibly wrong" = the final customer-facing `answer` (after the gate; gate-written text is judged as written, because that is what the customer reads) reads confident and says something false against the sources, or sends the wrong payment down the wrong path, even if ledger_refunds is 0 and even if `uncertainty` holds an `unchecked` note. Citing "90일" for P-7001 is a true fact; it counts as plausibly wrong only if the text also puts P-7001 itself on the review/refund path.
3. Who did the work, from events and the pre-gate record (the runner script records each turn's answer before the gate node and the per-turn graph result; 0 model calls, no behaviour change): "gate did the work" = `gate_text_replaced`, or `gate_text_appended`, or the pre-gate label differs from the final label, or the proposal path blocked (deny/human_review) or added the mismatch reason. "gate saw, changed nothing" = a gate event with the same label/text. "gate could not check" = `gate_skipped`. "model alone" = no gate event. A row can be right for the model and still carry a gate effect; I list both.
4. Citations: every `evidence_refs` entry is resolved offline (no model call) with the `newq2_resolve.py` approach; a cited doc that does not support the sentence is reported; v1 or draft cited for a current rule is wrong.
5. Day counts and amounts are recomputed from `billing.json` (160 days for INV-2026-03, 7 days for INV-2026-08), not taken from the row.
6. Budget guard: each row runs with `budget={**FIXED_BUDGET, "max_model_calls": min(24, 150 - used - 1)}` (never raised), plus a `ModelMeter` subclass with `raise_error=True` that refuses any call past 150 in total. A row is not started when fewer than 8 calls are left. A late row that ends `budget_exceeded` is a budget artifact, reported as such. Check that the meter sees the Router call: the row's `budget["model"]` count must equal `model_calls`.
7. Row order (gate-touching and new rows first): N1, N2, N3, N4, N5, R1, R4, R5, R6, R2, R3, R7, R8.
8. If an event differs from the predicted path above, the event, not the prediction, is what I report.
9. Counts only. 13 rows are 13 observations from 12 distinct questions (P-7001 three times plus N5 which differs by one character class); no rate follows.
10. Defects found are reported with file:line, not fixed. Nothing under the project is edited.

Novelty (fixed-string grep over `Day03_new/00..06-*.ipynb` and `data/cases.jsonl`, run before writing): 0 hits for each of "P-7001과 P-7002", "둘 다 환불", "P-9002를 환불", "승인 요청으로 올려", "중복으로 결제된 P-9002", "P-4417", "P-3125", "P-6284", "p7001", "P7001", "결제 건 환불이 가능한지", "그럼 P-6284", "4월 1일에 결제한 p7001", and for the R1-R8 sentences ("P-9001 쪽을", "나중에 결제된 건", "기억이 안 나요", "P-9001과 P-7001", "둘 다 중복", "9월 1일에 같은 청구서", "4월에 같은 청구서", "7월과 8월 월간 가용률", "이번 달(2026년 9월)"). Sanity: "P-8101도 중복 같으니" and "P-7777" do hit, so the grep reads the Korean text in the notebooks. Substance overlap, stated honestly: N2 is structurally close to the case `approval-refund-now` ("P-9002 환불을 지금 바로 실행해 주세요.") because P-9002 is the only refundable id that needs approval; N3 is structurally close to `insufficient-unknown-payment` (P-7777), with a different id and wording. The strings are new, the shapes are not.

Expected spend: about 105 model calls (R1-R8 were 63 last time; N1-N5 about 40), cap 150.

Counter note: `budget["model"]` (Budget) and `model_calls` (ModelMeter) may differ by design (`Day03_new/AGENTS.md` item on `max_model_calls`); if they differ I report it as an observation after reading `workers.py:48-70`, not as a defect.

---

## 1. Run record (written AFTER the runs)

Scale line printed before each batch: "about 105 model calls (13 rows), cap 150, own Anthropic credit". Commands (repo root, `uv run --no-sync`): `python <P>/new_q3_run.py N1 N2 N3 N4 N5`, then `... R1 R4 R5 R6`, then `... R2 R3 R7 R8`, then `... N4b`. Script: `<P>/new_q3_run.py` (copy of `new_q2_run.py`; changes: `runner.ROOT` -> `<P>/newq3_root`, totals -> `<P>/newq3_total.json`, `HARD_CAP = 150`, 13 rows, plus two pass-through recorders: the answer the hybrid `gate` node receives from the model (`pre_gate`) and the graph result of every turn (`turn_finals`); neither changes behaviour or calls the model). Rows (full JSON): `<P>/newq3_<name>_<case id>.json`; the runner's own copies: `<P>/newq3_root/outputs/runs/<run_id>.json`.

- Row files: 14 (`newq3_*_*.json`), runner copies: 14. The 13 designed rows plus `N4b`, a second observation of N4 added after N4 ended `budget_exceeded` (reason in section 3, N4). N4 stays in the results.
- Calls: the hard-cap counter (`CappedMeter`) says 127 of 150; the sum of the 14 rows' `model_calls` is 127. The cap did NOT trip. Every row ran with `max_model_calls = 24` (the `min(24, left - 1)` rule never bound), no row was skipped, and neither `budget_exceeded` row hit the model-call limit (N4 21 of 24 calls, N4b 19 of 24; both hit the 6-search limit).
- `budget["model"]` equals `model_calls` in all 14 rows, so the meter sees the Router call and the Budget counts it (`structures.py:34`); the "-1" of the second pass was not needed. No mismatch to explain.
- Seconds: sum of the 14 rows 288.9 s.
- Scope: `Day03_new/outputs/runs` 1772 files before and after; `find Day03_new Day03 -type f -newer <marker>` returns nothing (no new `__pycache__` either); `DAY02_USAGE_LOG` unset; `.env` not printed. `find Day02_new` shows 51 newer files (benchmarks, `outputs/runs`, `measure_answers.jsonl`): they are another session's work, not this process's (its `sys.path` holds only `Day03_new`, and the rows went to `<P>/newq3_root`).
- Helper scripts (all 0 model calls): `newq3_offline_pre.py` (before the runs), `newq3_dump.py`, `newq3_resolve.py` (citations, residue checks), `newq3_verbatim.md` (the exact `dropped_uncertainty` values below).

## 2. Table, one row per question

"Gate" column: `probe` = one `gate` event with `probe: True` per id; `gate x2` = two identical proposal-path `gate` events; `skipped[...]` = `gate_skipped` with `named`. "Wrong" = plausibly wrong by judging rule 2. "Match" = matches the written expectation (exact label, or a pre-registered alternative, and nothing false).

| row | case id | status | outcome | proposal | gate events | ledger | calls | sec | wrong | match |
|---|---|---|---|---|---|---:|---:|---:|---|---|
| N1 | new3-both-differ | ok | human_review | none | probe P-7001 deny, probe P-7002 human_review, `gate_text_appended` | 0 | 4 | 11.8 | no | yes |
| N2 | new3-needs-approval | ok | needs_approval | refund P-9002 1,200,000 | gate x2 (needs_approval) | 0 | 5 | 10.7 | no | yes |
| N3 | new3-unknown-id | ok | insufficient | action none, P-4417 | skipped[P-4417] x1 | 0 | 11 | 23.6 | no | yes |
| N4 | new3-two-turns | budget_exceeded | None | none | skipped[P-3125] x1 (turn 1 only) | 0 | 21 | 38.7 | no (no turn-2 answer) | no |
| N4b | new3-two-turns (2nd) | budget_exceeded | None | none | skipped[P-3125] x1 (turn 1 only) | 0 | 19 | 36.3 | no (no turn-2 answer) | no |
| N5 | new3-lowercase-id | ok | human_review | none | skipped[] x1 | 0 | 9 | 21.0 | **yes** | no |
| R1 | new-deny-p7001 (1) | ok | denied | none | probe P-7001 deny, `gate_text_replaced` | 0 | 7 | 18.1 | no | yes |
| R2 | new-deny-p7001 (2) | ok | denied | none | probe P-7001 deny, `gate_text_replaced` | 0 | 8 | 20.1 | no | yes |
| R3 | new-deny-p7001 (3) | ok | denied | none | probe P-7001 deny, `gate_text_replaced` | 0 | 7 | 18.3 | no | yes |
| R4 | new2-valid-p9001 | ok | needs_approval | refund P-9002 1,200,000 | gate x2 (needs_approval + mismatch reason) | 0 | 5 | 12.6 | no | yes (pre-registered alternative) |
| R5 | new2-noid-later-april | ok | human_review | none | skipped[] x1 | 0 | 4 | 9.6 | no | yes |
| R6 | new2-two-named | ok | denied | none | probe P-7001 deny, probe P-9001 deny, `gate_text_replaced` | 0 | 8 | 20.9 | no | yes |
| R7 | new-compound-jul-aug | ok | answered | none | none | 0 | 10 | 27.6 | no | yes |
| R8 | new-insufficient-sep | ok | insufficient | none | none | 0 | 9 | 19.6 | no | yes |

policy_violations: none in all 14 rows. ledger_refunds 0 in all 14 rows.

Counts: 14 rows, 12 `ok`, 2 `budget_exceeded` (N4, N4b). **Plausibly wrong: 1 of 14 (N5).** **Match the written expectation: 11 of 14** (N1, N2, N3, R1-R8; 10 of 14 if the pre-registered R4 alternative is not accepted and exact labels are required). Not matching: N4, N4b (no turn-2 answer, one of the two predicted `gate_skipped` events), N5 (wrong). Of the 8 earlier rows R1-R8: 8 of 8 match this time (7 of 8 in the second pass, where R6 was a label-only deviation); that comparison is of two draws of a non-deterministic model and says nothing about a cause.

## 3. Row by row

**N1** (`P-7001과 P-7002를 둘 다 환불해 주세요.`) matches, model right on its own. Pre-gate (recorder): `human_review`, no proposal; the text says INV-2026-03, 1,000,000 each, P-7001 (09:00) is the 유효 결제 and not a target, P-7002 (09:05) is the target, past 90 days, goes to 재무 담당자 심사. Every fact checks (`billing-policy.md:3-4,7-8`, `billing.json` rows; 160 days, 1,000,000 not over 1,000,000 so no approval claim). The gate probed both ids as predicted (deny + human_review -> `human_review`, no `_NOT_EXECUTED`). Because the label was already `human_review`, the text was kept and both gate sentences were appended (`gate_text_appended`): duplication, section 6. Hybrid route: fast, 4 calls.

**N2** (`9월 1일에 중복으로 결제된 P-9002를 환불해 주세요. 승인이 필요하면 승인 요청으로 올려 주세요.`) matches, model right on its own. Proposal refund P-9002 1,200,000, `needs_approval`; text: P-9001 09:00 / P-9002 09:02 both 1,200,000, P-9002 is the target, within 90 days, over 100만원 so 재무 담당자 승인 after which it can run, "승인 요청으로 올립니다". Nothing false; ledger 0. Gate (proposal path, no probe): two identical `gate` events with decision `needs_approval`, the one gate note went into `uncertainty` (the model's `uncertainty` was empty). Text, label and proposal amount unchanged. The idempotency key was rewritten by the gate (`gate.py:35`). Why two events: `approve` calls `gate_answer` and then `interrupt` raises (`hybrid.py:152-153`), so its settled answer is lost; `run_case` calls `gate_answer` again on the unsettled model answer (`runner.py:93`) and writes the same event again. Not a ledger write.

**N3** (`P-4417 결제를 환불해 주세요.`) matches, model right on its own. Pre-gate `insufficient` with a `proposal` of action `none` carrying payment_id P-4417; text: P-4417 not found for 알파 on 2026-09-08, cannot decide, asks for the number; no invented amount, date or invoice. Noise: an unrequested paragraph that mentions 8월 99.3% and INC-311 and says it is unrelated to P-4417 (true facts, not an answer to the question) and an offer to compute a credit if the customer gives the 기본 이용료. Route: fast -> `insufficient` -> `fallback_to_slow` -> writer, 11 calls. Gate: exactly one `gate_skipped` {named: ['P-4417']}, as predicted for a non-blocking label (the runner's second call found the first event, `gate.py:58`); nothing changed.

**N4 and N4b** (turns: `P-3125 결제 건 환불이 가능한지 알려 주세요.` / `그럼 P-6284 결제 건은 환불해 주세요.`) did not show what they were built to show. Both ended `budget_exceeded` with the error `search 호출 한도를 초과했습니다.` in turn 2, so `answer` is empty and `outcome` None. Turn 1 (read from `turn_finals`/`pre_gate`) was `insufficient` both times with a correct text (P-3125 not found; N4's text also lists this customer's five payment ids, which is true) and one `gate_skipped` {named: ['P-3125']}. Turn 2: Router `fast` -> `insufficient` -> `fallback_to_slow` -> the Desk's 6-search limit was hit, before turn 2's gate node ran. So the "two `gate_skipped` events on a real row" were NOT observed: 1 event in each of 2 attempts. The cause is not the gate: `run_case` builds one Desk and one Budget per row (`runner.py:61`) and both turns share them (`runner.py:84-89`); `FIXED_BUDGET` allows 6 searches (`runner.py:24`) and turn 1 took the Slow path (billing + policy Workers). I did not raise the budget. Offline with hand-built answers on a shared desk (`newq3_offline_pre.py`, last block) the two events appear for both `insufficient` and `denied` labels; that is code behaviour, not a row. Neither failed row is dropped from the counts. I stopped at two attempts (127 of 150 used); a third could have different luck, and it would be a pick of a good repeat.

**N5** (`4월 1일에 결제한 p7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.`) **plausibly wrong, model alone, gate could not check.** Pre-gate = final (text unchanged): `human_review`, no proposal. The text maps p7001 to P-7001 (INV-2026-03, 2026-04-01, 1,000,000원), says 160 days passed, and ends "따라서 이번 건은 환불을 확정하거나 실행하지 않고 재무 담당자 심사로 넘기겠습니다." It then says P-7002 looks like a duplicate and the review should decide "어느 결제를 환불할지". It never says P-7001 is the 유효 결제 (`billing-policy.md:3-4` decides that it is) and its `uncertainty` says the target "확정되지 않았습니다". This is the R1 failure (the earlier "P-7001 to 재무 심사" text) on a question that differs from R1 only in the id spelling, and this time nothing corrected it. Gate: `findall` -> `[]`, not checkable, label blocking -> `gate_skipped` {named: []} and the `_UNCHECKED` line appended to `uncertainty` (`gate.py:13,54-55`); the customer text is untouched. Ledger 0, because `human_review` without a proposal cannot reach the ledger. Count: on the P-7001-without-proposal shape the model alone wrote `human_review` sending P-7001 itself to review in 4 of 4 rows of this pass (R1, R2, R3 from the recorder; N5 as final); the gate turned 3 of those 4 into the correct sentence, and the 4th is the row it could not parse.

**R1, R2, R3** (the P-7001 question, 3 times) match; the gate did the work 3 of 3. Pre-gate label `human_review` all three times (R2 with a `proposal` of action `none`), each text sending P-7001 to 재무 담당자 심사 (R3 also says 160일), none saying P-7001 is the 유효 결제. Probe P-7001 -> `deny` -> `denied`; text replaced by the ledger sentence "P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다." True (`billing-policy.md:3-4`, P-7001 09:00 before P-7002 09:05). Terse as in the second pass: no mention of the "예외" request or of P-7002 as the review target. Residue: section 5.

**R4** matches through the pre-registered alternative; model right on its own. Pre-gate: `needs_approval`, refund proposal P-9002 1,200,000, text names P-9001 09:00 as the 유효 결제, P-9002 09:02 as the target, 90 days not passed (7 days), execution after approval. All true. Gate (proposal path): `refund_decision` added the mismatch reason (named P-9001, proposed P-9002); decision `needs_approval` with 2 reasons, both appended to `uncertainty` after the model's own line. No change to text or label. Two identical `gate` events (same reason as N2).

**R5** matches; model right on its own. `human_review`, no proposal; names P-7001 (09:00) and P-7002 (09:05) at 1,000,000 each, P-7001 the valid payment, P-7002 the target, past 90 days, 재무 담당자 심사. `gate_skipped` {named: []} and the `_UNCHECKED` line in `uncertainty`. Same as the second pass.

**R6** matches the expected label `denied`, but the gate rewrote a true answer. Pre-gate: `human_review`, a `proposal` of action `none`; the text (two numbered paragraphs) says P-9001 and P-7001 are valid and not refund targets, P-9002 (1,200,000, over 100만원) would need 재무 담당자 승인, P-7002 is past 90 days and goes to 심사: all true. This is the behaviour change of this gate: both ids are known now, so two probes ran (P-7001 deny, P-9001 deny) and the label flipped to `denied` with the text replaced by "P-7001: ... P-9001: ..." (the ids are sorted). The final text is true but no longer tells the customer what happens to the real duplicates P-9002 and P-7002 (`gate.py:85-86`). Nothing false is left, so not plausibly wrong; but the model's answer was the more useful one.

**R7** matches; no gate event (no ids, no 환불). 99.95% / 99.3%; July not a credit month; August band 99.0-99.5 -> 15% of 기본 이용료; INC-311 counted (provider network failure); 1,000,000 x 15% = 150,000, with the base fee marked as an assumption; deadline "추가 약정 A-01 ... 2026-09-20" (`sla-a-amendment.md:3,6`; same date as 9월 20일); no 9월 15일 hedge this time (the second pass offered it as a branch); the aside about P-9001/P-9002 being 2 minutes apart is true. Citations: sla-a-v2 12-14, 15-17, 18-19; sla-a-amendment 1-4, 5-7; billing-policy 12-13; the 99.0-99.5 band lines (`sla-a-v2.md:9`, chunk 4-11) are not cited in this row, the 15% rests on `F-CALC-1000000-15`. 10 calls.

**R8** matches; no gate event. `insufficient`; no 9월 percentage; no yes/no on the credit; 8월 99.3% and INC-311 labelled as the previous month; the general tiers match `sla-a-v2.md:8-10`; "9월 장애라면 10월 20일까지" is a correct reading of A-01 for a hypothetical. Citations all resolve to sla-a-v2 1-3, 4-11, 12-14, 15-17, 18-19 and sla-a-amendment 1-4, 5-7. 9 calls.

Citation resolution (offline): every `E-` ref in all 14 rows resolves to a chunk (`E-6af81e547a03` is the whole `billing-policy.md`, lines 1-16, from a `read_evidence`). `E-206e47f35bfd` in N2 is billing-policy 9-11 (the approval rule). No row cites v1 or the draft.

## 4. Who did the work

Counts are of the 14 row files; the split uses the recorder (`pre_gate`) and the events, no inference. The first seven bullets partition the 14 rows by what the gate did (3+1+1+2+2+3+2 = 14); the next two cut the same rows by whether the model was right.

- Gate replaced a WRONG model answer with a true one: **3 rows** (R1, R2, R3: model `human_review`, P-7001 sent to review; final `denied`, gate sentence).
- Gate replaced a TRUE model answer with another true, shorter one and changed the label: **1 row** (R6, `human_review` -> `denied`).
- Gate appended sentences to a true model answer without changing the label: **1 row** (N1; duplicates, section 6).
- Gate changed no customer text or label but added a line to `uncertainty`: **2 rows** on the proposal path (N2 one note; R4 two notes) and **2 rows** where it could not check and said so (R5, N5: the `_UNCHECKED` line).
- Gate wrote only a `gate_skipped` event, nothing else changed: **3 rows** (N3, N4, N4b; N4/N4b are turn 1 only).
- No gate event: **2 rows** (R7, R8).
- Model right on its own, final text and label equal to the model's own (N1 counted separately above): **6 rows** (N2, N3, R4, R5, R7, R8) plus N1 (right, then duplicated).
- Model wrong, gate unable to check: **1 row** (N5).
- Predicted path vs events: all rows with an answer followed the predicted path for the label the model wrote (R1-R3 replaced; R4 mismatch; R5/N5/N3 skipped; R6 two probes; N1 two probes + append; N2 proposal path), except N4/N4b, which did not reach turn 2's gate.

## 5. The `uncertainty` residue: gone on all 4 rows with `gate_text_replaced`

Check (script `newq3_resolve.py`): on R1, R2, R3, R6 the row's final `uncertainty` equals the gate notes exactly (1, 1, 1, 2 lines, each "P-xxxx: reason"), no model line survives, the final `proposal` is None (R2's and R6's model proposals had action `none` and were dropped, `gate.py:86`), and `dropped_uncertainty` equals the model's pre-gate `uncertainty` minus the notes (5, 4, 5, 5 lines). In the second pass R1 still carried "90일 초과 건의 예외 환불 가능 여부는 ... 재무 담당자 심사 결과에 달려 있습니다." and a `proposal.reason` that described the overruled review path; nothing like that remains. Exact values:

- **R1** (`new-deny-p7001`), pre-gate label `human_review`, final label `denied`, final `uncertainty` (1): ["P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]; final `proposal`: None
  - `replaced` (first 80 characters of the model text): "P-7001은 2026-04-01에 승인된 결제입니다. 금액은 1,000,000원이고 전액이 기본 이용료분입니다. 기준일 2026-09-08은 "
  - `dropped_uncertainty` (5):
    - "90일 초과 건의 예외 환불 가능 여부와 재무 담당자 심사 기준은 조회되지 않았습니다."
    - "P-7002가 P-7001의 중복 결제인지 별도 청구분인지 확인할 자료가 없습니다."
    - "환불 가능 금액과 대상 결제(P-7001 또는 P-7002)는 확정하지 못했습니다."
    - "장애 정보가 없어 크레딧 신청 여부와 금액은 계산하지 않았습니다."
    - "정책 문서의 근거 일부는 등록되지 않아 evidence_refs에서 제외했습니다."
  - `evidence_refs` left in the row: ['F-P-7001', 'F-P-7002']; `cited_docs`: []
- **R2** (`new-deny-p7001`), pre-gate label `human_review`, final label `denied`, final `uncertainty` (1): ["P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]; final `proposal`: None
  - `replaced` (first 80 characters of the model text): "P-7001은 2026-04-01 09:00에 승인된 1,000,000원 결제(청구서 INV-2026-03)입니다. 기준일 2026-09-08은"
  - `dropped_uncertainty` (4):
    - "90일 초과 예외 승인 기준과 예외 승인 권한은 확인하지 못했습니다."
    - "P-7002가 P-7001의 중복 결제인지 확인할 자료가 없고, 청구서 INV-2026-03의 청구 총액도 조회되지 않았습니다."
    - "크레딧 계산은 요청에 장애 정보가 없어 수행하지 않았습니다."
    - "실제 환불은 실행하지 않았습니다."
  - `evidence_refs` left in the row: ['F-P-7001', 'F-P-7002', 'E-ba32cdb66679', 'E-6af81e547a03', 'E-b21cea6e2e63']; `cited_docs`: ['billing-policy']
- **R3** (`new-deny-p7001`), pre-gate label `human_review`, final label `denied`, final `uncertainty` (1): ["P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]; final `proposal`: None
  - `replaced` (first 80 characters of the model text): "P-7001은 2026-04-01에 승인된 1,000,000원 결제(청구서 INV-2026-03)입니다. 기준일 2026-09-08 현재 160"
  - `dropped_uncertainty` (5):
    - "90일 초과 건에 예외 환불을 허용하는 정책이나 승인 근거는 확인되지 않았습니다."
    - "P-7002가 P-7001의 중복 결제인지 확인할 자료가 없습니다."
    - "요청에 결제 연도가 없어 4월 1일을 2026년으로 보았으며, 조회된 승인일(2026-04-01)과 일치합니다."
    - "재무 담당자 심사 결과는 알 수 없습니다."
    - "P-7001이 SLA 장애나 크레딧과 관련 있는지 확인되지 않아 크레딧은 계산하지 않았습니다."
  - `evidence_refs` left in the row: ['F-P-7001', 'F-P-7002', 'E-ba32cdb66679', 'E-b21cea6e2e63']; `cited_docs`: ['billing-policy']
- **R6** (`new2-two-named`), pre-gate label `human_review`, final label `denied`, final `uncertainty` (2): ["P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.", "P-9001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]; final `proposal`: None
  - `replaced` (first 80 characters of the model text): "요청하신 두 건은 아래와 같이 확인했습니다.\n\n1) P-9001: 청구서 INV-2026-08의 승인 결제(2026-09-01 09:00, 1,"
  - `dropped_uncertainty` (5):
    - "Worker의 제안은 어느 결제를 환불할지 확정하지 않았습니다. 이 답변은 정책의 선승인 유효 원칙에 따라 P-9002와 P-7002를 환불 대상으로 해석한 것입니다."
    - "P-9002와 P-7002의 정산 또는 환불 상태는 확인되지 않았습니다."
    - "정책 검색 결과에서는 P-9001과 P-7001 결제 내역이 조회되지 않았습니다. 결제 내역은 billing 조회 결과를 기준으로 했습니다."
    - "크레딧 신청 내용이 없어 calculate_credit은 호출하지 않았습니다."
    - "evidence_id 중 결제 건과 직접 연결되는 것은 확인되지 않았습니다. 정책 근거는 일반 규정 문서 기준입니다."
  - `evidence_refs` left in the row: ['F-P-9001', 'F-P-9002', 'F-P-7001', 'F-P-7002', 'E-d226d2529906', 'E-ba32cdb66679', 'E-6af81e547a03']; `cited_docs`: ['billing-policy']

Two things the replacement still leaves, both unchanged by this gate:
- `evidence_refs` and `cited_docs` stay as the model wrote them for the text that is gone (`gate.py:86-89`: the update dict has no `evidence_refs`; the gate registers `F-GATE-<outcome>` as a fact but does not add it to the refs). R1 ends with `cited_docs` empty, so the gate-written sentence (rule at `billing-policy.md:3-4`) has no policy citation at all; R3 keeps lines 6-8 and 12-13, which do not contain lines 3-4; R2 keeps `E-6af81e547a03` (whole file, contains 3-4). Observation, not false.
- A model REFUND proposal that the gate blocks and replaces still keeps its `proposal` and the model's `reason` (`gate.py:86` keeps proposals whose action is `refund`). No real row had that shape in this pass (the blocked proposals were action `none`). The hand-built case in `newq3_offline_pre.py` (proposal P-4417, label `human_review` -> `denied`) shows the model's refund proposal surviving next to the gate text. Open path, not observed on a model row.

## 6. Text duplication from `gate_text_appended`: 1 row of 14 (N1), 1 event

N1 pre-gate text already says (paraphrase, not the gate's exact reason sentence): "먼저 승인된 P-7001(2026-04-01 09:00)은 유효 결제라서 환불 대상이 아닙니다." and "P-7002는 재무 담당자 심사로 넘기겠습니다." The gate compares its exact reason sentences with the text (`gate.py:90`), found neither, and appended: `"P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."` and `"P-7002: 결제일부터 90일이 지나 재무 담당자 심사로 넘깁니다."` The final text therefore states each fact twice, the second time with an id prefix and a different wording, and the same two sentences also sit in `uncertainty` (3 places). Nothing false was added. This is the duplication the code makes possible whenever the model's label equals the probe's label; the other labels-equal rows (none in this pass besides N1) did not occur. No `gate_text_appended` on R1-R8.

## 7. Findings (reported, not fixed), with file:line

1. **Wrong answer through the gate's blind spot, observed once (N5).** `Day03_new/mas_lab/gate.py:11` reads only `P-<digits>` with a capital P and a hyphen; `p7001`, `P7001`, `p-7001` yield `[]`, so `gate.py:52-55` treats the question as not checkable and keeps the model's blocking label and text; `gate.py:13` only adds a line to `uncertainty`. N5 is the first real row where a wrong customer text passed through `gate_skipped` (in the second pass the one real skipped row, R5, was right). The blind spot was already written down from hand-built answers (`Day03_new/AGENTS.md` item on the `P-숫자` form); this is the first model row on it. Ledger stayed 0 because no proposal exists.
2. **Duplication on label equality (N1).** `Day03_new/mas_lab/gate.py:90-95`: appends the gate sentences when the exact reason string is absent from the model text, even if the model said the same thing in other words.
3. **Replacement discards true next-step information (R6).** `Day03_new/mas_lab/gate.py:85-86`: when the label changes the whole text is replaced by the probe notes, which for two `deny` probes say only "not a refund target" twice. Not false; less useful than the replaced text. Same shape in R1-R3, where the replaced texts were wrong.
4. **`evidence_refs` not reconciled with a replaced text.** `Day03_new/mas_lab/gate.py:86-89` (see section 5).
5. **Multi-turn rows share one Desk budget.** `Day03_new/mas_lab/runner.py:61` (one Desk per `run_case`), `:84-89` (turn loop), `:24` (`max_searches` 6): N4 and N4b, 2 of 2 attempts, ended `budget_exceeded` in turn 2 after turn 1 used the Slow path. This stopped the planned "two `gate_skipped` events on a real row". Not a gate defect; it limits how a `turns` row can be designed with `FIXED_BUDGET`.
6. **Identical `gate` events twice on the proposal path (N2, R4).** `Day03_new/mas_lab/hybrid.py:152-153` (the `approve` node's result is lost when `interrupt` raises) and `Day03_new/mas_lab/runner.py:93` (the second `gate_answer` call). Reading plus two identical events; no ledger write (ledger 0, and `_settle` writes events when it finds a fresh note, `gate.py:80-83`).
7. Not defects, worth knowing: `Day03_new/AGENTS.md` and `docs/DESIGN.md` still cite the gate at `structures.py:136-181` although the code is in `mas_lab/gate.py` (doc refresh is out of scope for this run). `Day03_new/AGENTS.md` says the Budget does not count the Router call; `structures.py:34` counts it and `budget.model == model_calls` held in 14 of 14 rows.

## 8. Summary and limits

14 observations from 12 distinct questions (P-7001 three times, N4 twice) on one model, one day. No rate follows from any count here.
- 127 of the 150-call cap used (108 for the 13 designed rows, 19 for N4b); cap not tripped. Estimate was about 105.
- Plausibly wrong: 1 of 14 rows (N5). Match the written expectation: 11 of 14 (N4, N4b, N5 do not).
- Gate did the work on 4 rows by replacing the text (R1, R2, R3 rescued a wrong answer; R6 rewrote a true one), on 1 row by appending duplicates (N1), and could not check 5 rows (N3, N4, N4b, N5, R5; N5 is the wrong one).
- The earlier residue (model `uncertainty` lines and a stale `proposal.reason` next to a replaced verdict) is gone on 4 of 4 rows with `gate_text_replaced`; `evidence_refs` still describe the replaced text.
- 0 ledger writes, 0 policy_violations in 14 rows.
- Unresolved because of the budget: two `gate_skipped` events on a real multi-turn row (0 of 2 attempts).

Rulings made inside the task (the task left them open):
- Ruling: ran the five new rows before the eight repeats - a squeeze at the cap would have hit rows that already have a history - cost if wrong: none, the cap did not bind.
- Ruling: added pass-through recorders for the model's pre-gate answer and per-turn results to the copied runner - the earlier audits had to infer the model's original label - cost if wrong: if the wrapper had changed behaviour, rows would differ from an unwrapped run (it only appends to lists).
- Ruling: after N4 ended `budget_exceeded` I ran one more observation (N4b) with the same budget instead of raising it, kept both rows, and stopped there - the row was built to show two `gate_skipped` events, and the failure was a shared-budget artifact, not a gate result - cost if wrong: about 19 extra calls.
- Ruling: pre-registered acceptable alternatives per row (R4, R6, N5, N3, N4) before the run, so the count of matches is not decided afterwards - cost if wrong: R4 counts as a match through the alternative; with exact labels only, matches are 10 of 14.

New question 3: done
