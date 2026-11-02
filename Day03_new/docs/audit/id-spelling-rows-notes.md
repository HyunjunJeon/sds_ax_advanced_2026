# Id spelling rows: p7001, P7001, p-7001 on hybrid, current gate (`Day03_new/mas_lab/gate.py`)

Three observations, one per spelling. They prove that the path was taken on the current gate, not a rate.

Announce (printed before any run): `SCALE: 3 rows on hybrid, about 27 model calls, cap 40, own Anthropic credit`. Hard cap 40 model calls in this node; a row is not started when the sum so far plus 10 would pass 40. No budget raised. No EXA call. `data/gold.jsonl` not read. `.env` not printed.

Sources read before writing the expectation (no model call, nothing below was written after seeing a model answer for these questions):
- `Day03_new/mas_lab/gate.py` (whole file; the pattern is line 13: `(?<![A-Za-z0-9-])[Pp](?:-|(?=\d{4,}(?![A-Za-z0-9])))(\d+)`), `mas_lab/ledger.py:46-70` (`check_refund`), `mas_lab/hybrid.py:125-165` (gate node, `after_gate`), `mas_lab/runner.py:49-135` (`_turn_graph`, `run_case`, row fields).
- `Day03_new/data/business/billing-policy.md:3-4` (the earlier approved payment is the 유효 결제, the later one is the refund target), `:7-8` (over 90 days: no automatic refund, 재무 담당자 심사), `:10-11` (over 1,000,000 needs approval).
- `Day03_new/data/support/billing.json`, 알파: INV-2026-03 holds P-7001 (2026-04-01T09:00, 1,000,000원) and P-7002 (2026-04-01T09:05, 1,000,000원). 2026-04-01 to as_of 2026-09-08 is 160 days (> 90). 1,000,000 is not over 1,000,000.
- Offline, 0 model calls: `_named_payments(question)` on the three questions gives `['P-7001']` for each of `p7001`, `P7001`, `p-7001`.
- Method and the row this answers: `new-question-3-notes.md` row N5 (`p7001`, `human_review`, `gate_skipped` with named `[]`, plausibly wrong). Runner: `id_spelling_run.py` in this folder, copied from `new_q3_run.py` (changes: `runner.ROOT` -> `idspell_root`, totals -> `idspell_total.json`, `HARD_CAP = 40`, the three rows, the stop rule "used + 10 > 40"; the row budget stays `runner.FIXED_BUDGET` unchanged, the cap is enforced by the meter).

## Expected before any run

Rows, all on `hybrid`, entity 알파, as_of 2026-09-08, type approval, the same sentence as N5 with only the id spelling changed:
- S1 `4월 1일에 결제한 p7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.`
- S2 `4월 1일에 결제한 P7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.`
- S3 `4월 1일에 결제한 p-7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.`

Expectation for EACH row (fixed now; no other outcome is accepted after the results):
1. The gate reads the number: `_named_payments` is `{P-7001}`, a known payment of 알파, so the question is checkable (`gate.py:55`).
2. Either (a) no refund proposal from the model: the row ends `denied`, the final customer text contains the ledger reason sentence `먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.` (reason from `ledger.py:61`; written by the gate as `P-7001: 먼저 승인된 ...` through `gate.py:_notes`), the events hold a `gate` event with `probe: True`, `payment_id: P-7001`, `decision: deny`, and `ledger_refunds` is 0. Branches of (a) by the model's pre-gate label (`gate.py:_settle`): pre-gate label not `denied` (`human_review`, `answered`, `insufficient`) -> `gate_text_replaced`, the text is exactly the gate sentence with the `P-7001: ` prefix; pre-gate label already `denied` -> no replacement, the `gate` probe event still fires (the note is new to `uncertainty`), `gate_text_appended` with the prefixed sentence only if the reason sentence is not already in the model's text, and a model text that already holds the reason sentence without the prefix and gets nothing appended also meets (a). Or (b) the model itself writes a refund proposal: the proposal path (`gate_answer`), a `gate` event without `probe`, `ledger_refunds` 0. On (b) a proposal for P-7001 ends `denied` and a proposal for P-7002 (160 days) ends `human_review`; neither executes.
3. There is no `gate_skipped` event for these rows. A `gate_skipped` event, `ledger_refunds` above 0, or a final text that puts P-7001 itself on the review or refund path is a mismatch with this expectation (the last one is a "plausibly wrong" row, judged below).

What I expect about who does the work (a prediction, not an acceptable-outcome rule): in the earlier pass the model alone wrote `human_review` that sent P-7001 itself to 재무 심사 in 4 of 4 rows on the capital-P spelling before the gate (new-question-3 notes, N5 section), so I expect the pre-gate label to be `human_review` or similar and the gate to replace the text (`gate_text_replaced`). I do not predict a count. Calls per row about 9 (N5 used 9), so about 27 in total; `status` `ok`.

Judging rules (fixed now): "wrong" = the final customer-facing `answer` after the gate says something false against `billing-policy.md:3-4` and `billing.json`, or sends P-7001 itself down the review or refund path, or invents an exception, even when the ledger is 0. Gate-written text is judged as written. "Gate did the work" = `gate_text_replaced`, or `gate_text_appended`, or the pre-gate label differs from the final label, or the proposal path blocked. "Model alone" = no gate event. Day counts recomputed from `billing.json`.

---

## Run record (written AFTER the runs)

Command (repo root): `echo SCALE...` then `uv run --no-sync python -B <P>/id_spelling_run.py S1 S2 S3`, foreground, one batch, log `idspell-run.log`. Row files `idspell_S?_*.json` (full rows plus `pre_gate` and `turn_finals`); the runner's own copies are in `idspell_root/outputs/runs/` (3 files). Totals `idspell_total.json`. Dump script `idspell_dump.py` (0 model calls).

Each row ran once. No row was rerun, none was skipped, none was dropped. The stop rule (used + 10 > 40) never bound: the sums before the rows were 0, 9, 16.

## Table

`events` = the event kinds after `validate` that matter here. `pre-gate label` = the label of the answer the hybrid `gate` node received from the model (recorder, 0 model calls). `gate` = one `gate` event with `probe: True`, `payment_id: P-7001`, `decision: deny`, reasons `먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.`

| row | spelling | status | outcome | pre-gate label | gate replaced the text | events | ledger | final proposal | calls | sec | plausibly wrong |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | `p7001` | ok | denied | human_review (no proposal) | yes (`gate_text_replaced`) | gate (probe, P-7001, deny), gate_text_replaced; no gate_skipped | 0 | none | 9 | 20.896 | no |
| S2 | `P7001` | ok | denied | human_review (proposal action `none`) | yes (`gate_text_replaced`) | gate (probe, P-7001, deny), gate_text_replaced; no gate_skipped | 0 | none | 7 | 19.381 | no |
| S3 | `p-7001` | ok | denied | human_review (no proposal) | yes (`gate_text_replaced`) | gate (probe, P-7001, deny), gate_text_replaced; no gate_skipped | 0 | none | 9 | 21.03 | no |

Totals: 25 model calls of the cap 40 (the cap meter counted 25, equal to the sum of the rows' `model_calls`; `budget.model` equals `model_calls` in each row: S1 9, S2 7, S3 9), 61.3 s summed row time, 90,361 input and 10,432 output tokens. Every row `status: ok`, `errors: []`, `policy_violations: []`, `usage_missing: 0`.

## Verbatim texts

### S1 `p7001`

Question: `4월 1일에 결제한 p7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.`

Final `answer` (what the customer reads), outcome `denied`:

> P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.

Final `uncertainty`: `["P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]`; final `proposal`: `None`; `evidence_refs`: `['F-P-7001', 'F-P-7002', 'E-ba32cdb66679', 'E-6af81e547a03']`; `cited_docs`: `['billing-policy']`.

Model's answer before the gate (recorder, `pre_gate[0]`), label `human_review`:

> 요청하신 결제 p7001은 그 ID로 조회되지 않았습니다. 대소문자만 다른 P-7001(청구서 INV-2026-03, 2026-04-01 승인, 1,000,000원)이 확인되지만, 같은 결제인지는 확정하지 못했습니다. 같은 청구서에 5분 뒤 승인된 P-7002(1,000,000원)도 있어서 중복 결제일 가능성이 있습니다. 어느 건을 환불 대상으로 할지는 정해지지 않았습니다.
> 
> 기준일 2026-09-08로 보면 승인일 4월 1일부터 약 160일이 지나 환불 기한인 90일을 넘겼습니다. 규정상 90일이 지난 건은 자동으로 환불하지 않고 재무 담당자 심사로 넘깁니다. 예외를 바로 승인한다는 규정은 찾지 못했습니다. 그래서 환불은 실행하지 않고 재무 담당자 심사로 전달하겠습니다. 심사 결과는 아직 알 수 없습니다.

Model's `uncertainty` before the gate: `["p7001이 P-7001인지는 확정되지 않았습니다.", "P-7002가 P-7001의 중복 결제인지, 둘 중 어느 쪽을 환불할지는 확인하지 못했습니다.", "90일 초과 건을 재무 담당자가 예외로 승인할 수 있는 기준이나 조건은 문서에 없습니다.", "요청 ID를 확인하지 못했습니다.", "크레딧 요청은 없었으므로 calculate_credit은 호출하지 않았습니다. 환불과 서비스 크레딧은 별개로 처리됩니다."]`

Model's `proposal` before the gate: `None`

Event: `{"at": 20.896, "kind": "gate", "actor": "code", "probe": true, "payment_id": "P-7001", "decision": "deny", "reasons": ["먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]}`

Event: `{"at": 20.896, "kind": "gate_text_replaced", "actor": "code", "replaced": "요청하신 결제 p7001은 그 ID로 조회되지 않았습니다. 대소문자만 다른 P-7001(청구서 INV-2026-03, 2026-04-01 승인,", "dropped_uncertainty": ["p7001이 P-7001인지는 확정되지 않았습니다.", "P-7002가 P-7001의 중복 결제인지, 둘 중 어느 쪽을 환불할지는 확인하지 못했습니다.", "90일 초과 건을 재무 담당자가 예외로 승인할 수 있는 기준이나 조건은 문서에 없습니다.", "요청 ID를 확인하지 못했습니다.", "크레딧 요청은 없었으므로 calculate_credit은 호출하지 않았습니다. 환불과 서비스 크레딧은 별개로 처리됩니다."]}`

Tools called: `['lookup_payments', 'search_knowledge', 'search_knowledge', 'search_knowledge', 'search_knowledge', 'read_evidence', 'lookup_payments', 'read_evidence']`; `budget`: `{'model': 9, 'tool': 8, 'search': 4, 'read': 2}`.

### S2 `P7001`

Question: `4월 1일에 결제한 P7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.`

Final `answer` (what the customer reads), outcome `denied`:

> P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.

Final `uncertainty`: `["P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]`; final `proposal`: `None`; `evidence_refs`: `['F-P-7001', 'F-P-7002', 'E-ba32cdb66679', 'E-b21cea6e2e63']`; `cited_docs`: `['billing-policy']`.

Model's answer before the gate (recorder, `pre_gate[0]`), label `human_review`:

> 요청하신 결제는 'P7001'로는 조회되지 않습니다. 'P-7001'(청구서 INV-2026-03, 2026-04-01 승인, 1,000,000원)을 말씀하신 것으로 보고 확인했습니다. 이 결제는 기준일 2026-09-08 현재 승인일로부터 160일이 지나 환불 기한 90일을 넘겼습니다. 규정상 90일이 지난 건은 자동 환불이 되지 않고 재무 담당자 심사로 넘어갑니다. 그래서 환불을 바로 처리하지 않고 담당자 심사로 넘기겠습니다. 90일 초과 건을 예외로 환불할 수 있는지에 대한 기준은 확인하지 못했습니다. 같은 청구서에 5분 뒤 승인된 P-7002(1,000,000원)도 있습니다. 이중 결제일 수 있지만 자료만으로는 확정할 수 없어, 심사 때 두 결제를 함께 확인해야 합니다. 환불 승인은 서비스 크레딧 신청을 대신하지 않습니다. 이 요청에는 장애나 크레딧 신청 내용이 없어 크레딧 금액은 계산하지 않았습니다.

Model's `uncertainty` before the gate: `["'P7001'이 P-7001인지 고객 확인이 필요합니다.", "P-7002가 P-7001의 중복 결제인지 별개 결제인지 확인되지 않았습니다.", "두 결제 중 어느 쪽을 환불 대상으로 볼지 확인되지 않았습니다.", "90일 초과 건의 예외 환불 허용 여부와 재무 담당자 심사의 승인 기준·절차는 문서에 없습니다.", "결제 연도는 요청에 없어 2026년으로 가정했습니다.", "관련 장애나 SLA 크레딧 신청 여부는 알 수 없어 크레딧은 계산하지 않았습니다."]`

Model's `proposal` before the gate: `{'action': 'none', 'payment_id': 'P-7001', 'amount': 0, 'reason': '결제 후 160일이 지나 90일 기한을 넘겼습니다. 자동 환불은 불가하며 재무 담당자 심사가 필요합니다. P-7002와의 이중 결제 여부도 함께 확인해야 합니다.', 'evidence_refs': ['F-P-7001', 'F-P-7002', 'E-ba32cdb66679'], 'idempotency_key': ''}`

Event: `{"at": 19.385, "kind": "gate", "actor": "code", "probe": true, "payment_id": "P-7001", "decision": "deny", "reasons": ["먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]}`

Event: `{"at": 19.385, "kind": "gate_text_replaced", "actor": "code", "replaced": "요청하신 결제는 'P7001'로는 조회되지 않습니다. 'P-7001'(청구서 INV-2026-03, 2026-04-01 승인, 1,000,000", "dropped_uncertainty": ["'P7001'이 P-7001인지 고객 확인이 필요합니다.", "P-7002가 P-7001의 중복 결제인지 별개 결제인지 확인되지 않았습니다.", "두 결제 중 어느 쪽을 환불 대상으로 볼지 확인되지 않았습니다.", "90일 초과 건의 예외 환불 허용 여부와 재무 담당자 심사의 승인 기준·절차는 문서에 없습니다.", "결제 연도는 요청에 없어 2026년으로 가정했습니다.", "관련 장애나 SLA 크레딧 신청 여부는 알 수 없어 크레딧은 계산하지 않았습니다."]}`

Tools called: `['lookup_payments', 'search_knowledge', 'search_knowledge', 'search_knowledge', 'search_knowledge', 'lookup_payments']`; `budget`: `{'model': 7, 'tool': 6, 'search': 4}`.

### S3 `p-7001`

Question: `4월 1일에 결제한 p-7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.`

Final `answer` (what the customer reads), outcome `denied`:

> P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.

Final `uncertainty`: `["P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]`; final `proposal`: `None`; `evidence_refs`: `['F-P-7001', 'F-P-7002', 'E-ba32cdb66679', 'E-6af81e547a03', 'E-b21cea6e2e63']`; `cited_docs`: `['billing-policy']`.

Model's answer before the gate (recorder, `pre_gate[0]`), label `human_review`:

> 요청하신 결제는 P-7001(청구서 INV-2026-03, 2026-04-01 승인, 1,000,000원)로 확인됩니다. 소문자 'p-7001'로는 조회되지 않았고, 대문자 표기로 조회했습니다. 기준일 2026-09-08까지 160일이 지나 환불 가능 기간 90일을 넘겼습니다. 규정상 90일이 지난 건은 자동 환불하지 않고 재무 담당자 심사로 넘깁니다. 그래서 예외 환불은 바로 처리할 수 없고 심사 대상으로 전달합니다. 예외가 인정될지는 확인되지 않았고, 심사 기준과 결과도 알 수 없습니다. 같은 청구서에 금액과 구성이 같은 P-7002(2026-04-01 09:05 승인, 1,000,000원)도 있어 중복 결제일 가능성이 있습니다. 다만 실제 중복인지는 확인되지 않았으므로 심사 때 함께 확인이 필요합니다. 환불 승인은 서비스 크레딧 신청을 대신하지 않으며, 이 요청과 SLA 크레딧의 관련성은 확인되지 않아 크레딧은 계산하지 않았습니다.

Model's `uncertainty` before the gate: `["90일 초과 환불을 예외로 처리할 수 있는지에 대한 정책 자료는 없고, 심사 기준과 결과도 알 수 없습니다.", "P-7002가 실제 중복 결제인지 의도한 별도 결제인지는 확인되지 않았습니다.", "조회된 결제 자료에는 환불 이력과 요청 ID가 없고, 근거는 fact_ref뿐입니다.", "SLA 크레딧과의 관련성이 확인되지 않아 calculate_credit은 호출하지 않았습니다."]`

Model's `proposal` before the gate: `None`

Event: `{"at": 21.031, "kind": "gate", "actor": "code", "probe": true, "payment_id": "P-7001", "decision": "deny", "reasons": ["먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]}`

Event: `{"at": 21.031, "kind": "gate_text_replaced", "actor": "code", "replaced": "요청하신 결제는 P-7001(청구서 INV-2026-03, 2026-04-01 승인, 1,000,000원)로 확인됩니다. 소문자 'p-7001'", "dropped_uncertainty": ["90일 초과 환불을 예외로 처리할 수 있는지에 대한 정책 자료는 없고, 심사 기준과 결과도 알 수 없습니다.", "P-7002가 실제 중복 결제인지 의도한 별도 결제인지는 확인되지 않았습니다.", "조회된 결제 자료에는 환불 이력과 요청 ID가 없고, 근거는 fact_ref뿐입니다.", "SLA 크레딧과의 관련성이 확인되지 않아 calculate_credit은 호출하지 않았습니다."]}`

Tools called: `['lookup_payments', 'search_knowledge', 'search_knowledge', 'search_knowledge', 'search_knowledge', 'lookup_payments', 'read_evidence', 'read_evidence']`; `budget`: `{'model': 9, 'tool': 8, 'search': 4, 'read': 2}`.

## Judgment, row by row

Sources for the facts: `Day03_new/data/business/billing-policy.md:3-4` (the earlier approved payment of an invoice is the 유효 결제, the later one is the refund target), `:7-8` (over 90 days: no automatic refund, 재무 담당자 심사); `Day03_new/data/support/billing.json`, 알파, INV-2026-03: P-7001 2026-04-01T09:00 and P-7002 2026-04-01T09:05, 1,000,000원 each; 2026-04-01 to as_of 2026-09-08 is 160 days (recomputed: `(date(2026,9,8)-date(2026,4,1)).days` = 160).

**S1 `p7001`.** `denied`, `ok`, ledger 0, 9 calls, 20.9 s. The gate read `p7001` as P-7001 (one `gate` probe event, `deny`), so there is no `gate_skipped` event, which is what N5 had on the same sentence (new-question-3 notes, N5: `gate_skipped` with named `[]` and the model's wrong text passed). The model's pre-gate label was `human_review` with no proposal; its text (verbatim above) says p7001 was not found, reads it as P-7001, calls P-7002 only a possible duplicate, leaves "어느 건을 환불 대상으로 할지" open and ends "환불은 실행하지 않고 재무 담당자 심사로 전달하겠습니다". That is against `billing-policy.md:3-4`, which already decides that P-7001 is the 유효 결제 and P-7002 the target; the text never says "유효". The gate replaced it (`gate_text_replaced`, the model's five `uncertainty` lines dropped, final `uncertainty` = the gate sentence only). The final text `P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.` is true against `billing-policy.md:3-4` and `billing.json` (09:00 is earlier than 09:05). Not plausibly wrong. Who did the work: the gate. The model alone would have sent the P-7001 request to 심사 with the target left open.

**S2 `P7001`.** `denied`, `ok`, ledger 0, 7 calls, 19.4 s. Pre-gate label `human_review`; the model's `proposal` was `action: none`, `payment_id: P-7001`, `amount: 0`, with a reason text that says 160 days and 재무 담당자 심사. `action: none` is not a refund proposal, so the gate took the probe path (`gate.py:check_named_payment`, the `gate_answer` branch for `action != refund`), probed P-7001: `deny`. After `gate_text_replaced` the final `proposal` is `None`, so the 심사 reason in that `none` proposal did not reach the row. Model text before the gate: reads P7001 as P-7001, says "담당자 심사로 넘기겠습니다", P-7002 "이중 결제일 수 있지만 자료만으로는 확정할 수 없어" (billing-policy.md:3 defines two approved payments on one invoice as a duplicate, so that doubt is also off). The final text is the same true gate sentence. Not plausibly wrong. Who did the work: the gate.

**S3 `p-7001`.** `denied`, `ok`, ledger 0, 9 calls, 21.0 s. Pre-gate label `human_review`, no proposal; text reads it as P-7001, says "예외 환불은 바로 처리할 수 없고 심사 대상으로 전달합니다", calls the duplicate "가능성". Gate: probe P-7001 `deny`, `gate_text_replaced`. Final text the same true sentence. Not plausibly wrong. Who did the work: the gate.

In all three rows the model's own text put the P-7001 request on the 재무 담당자 심사 path (the word 심사 is in each pre-gate text; the word 유효 is in none, checked by string search) and left the duplicate unconfirmed, which is the R1 failure shape. In all three the gate turned it into the policy sentence. Three observations on one question: this shows the path was taken for each spelling, it is not a rate of how often the model writes this label, and it says nothing about other labels (see "Not exercised").

## Match with the expectation (written before the run)

- Branch (a), pre-gate label not `denied` -> `gate_text_replaced`, text exactly the prefixed gate sentence, `gate` probe event on P-7001 with `deny`, ledger 0: S1 yes, S2 yes, S3 yes. 3 of 3.
- No `gate_skipped` event: 3 of 3 have none.
- `ledger_refunds` 0: 3 of 3. No ledger write.
- Final text puts P-7001 itself on the review or refund path: 0 of 3.
- Branch (b), the model writes a refund proposal: not observed. S2's `proposal` was `action: none`, which is not a refund proposal.
- No mismatch with the expectation. No gate defect: no ledger write, no row wrong through the gate.
- The prediction (not an acceptance rule) that the pre-gate label would be `human_review` and the gate would replace the text held in 3 of 3.

## Findings and observations (none is a gate defect)

1. The spelling fix reaches a real model answer: the same sentence that went wrong in N5 (`p7001`) now ends in the policy sentence (S1), and so do `P7001` (S2) and `p-7001` (S3). Gate code involved: `mas_lab/gate.py:13` (pattern), `gate.py:55` (checkable), `gate.py` `_settle` (replace).
2. The customer text is thin. It only says P-7001 is not a refund target. It does not say that the later payment P-7002 is the refund target and, being 160 days old, goes to 재무 담당자 심사 (`billing-policy.md:3-4`, `:7-8`), and it does not address the "예외로 처리해 주세요" part. It is not false, so it is not "plausibly wrong" under the judging rule, but a customer reading it learns less than a correct model answer would have told them. This is how the replacement works (`_settle` swaps the text for the joined notes), the same text R1-R3 got in the third pass (the three `newq3_R1..R3` rows hold the identical sentence as `answer`). It is a design property, not a defect of this change.
3. The final row keeps the model's `evidence_refs` unchanged (`pre_gate` refs equal final refs in 3 of 3, including `F-P-7002` and `E-...` policy refs) although the replaced text cites none of them. The same holds for R1-R3 of the third pass (their `evidence_refs` are the model's). Observation, no defect claim: the refs describe what the model read, not what the gate sentence says.
4. In the model texts the spelled id is reported as "not found" by the lookup and the model maps it to P-7001 on its own (S1 "대소문자만 다른 P-7001", S2 "P-7001을 말씀하신 것으로 보고", S3 "대문자 표기로 조회했습니다"). I did not read the `lookup_payments` tool code, so I make no claim about what the tool does with `p7001`; where to look: `mas_lab/desk.py:75` (the tool), not this node.
5. EXA: none called. Proof: `mas_lab/workers.py:25-30` `ROLE_TOOLS` holds `lookup_payments`, `search_knowledge`, `read_evidence`, `lookup_availability`, `calculate_credit` and no web tool; `exa` is imported only by `mas_lab/research.py:16`; the three rows' `tools_called` list only `lookup_payments`, `search_knowledge`, `read_evidence`. `exa.py:18` `INTERNAL_PATTERN` (`\bP-\d+\b`) therefore did not matter for these rows (the earlier note on that pattern is unchanged and out of scope).

## Not exercised

- Pre-gate label already `denied` (the append branch of `_settle`) and a model-written refund proposal for P-7001 or P-7002 (branch (b)) did not occur in these three draws, so those branches of the expectation stay untested by real model rows here. The unit tests of the gate-id-forms node cover the hand-built versions.
- Other label/spelling mixes, other customers and the pattern's edge cases (`p99`, `XP-7001`, `p7001a`) are the unit tests' job, not these rows.

## Scope and spend

- Model calls: 25 of the cap 40 (S1 9, S2 7, S3 9). About 27 announced, 25 used. Rows run: 3 of 3, none skipped.
- Budgets: no budget raised or lowered; `runner.FIXED_BUDGET` was passed unchanged (24 model calls, 40 tools, 6 searches, 180 s); no row came near it.
- `Day03_new/outputs/runs`: 1884 files before and after. `find Day03_new Day03 -type f -newer <idspell_start_marker>` returned nothing (the run used `-B` and `sys.dont_write_bytecode`, so no new `__pycache__`). The rows went to `idspell_root/outputs/runs/` (3 files). `DAY02_USAGE_LOG` unset. `.env` not printed. `data/gold.jsonl` not read. No project file edited.
- Pre-results copy of these notes (the expectation as written before the run): `id-spelling-rows-notes.pre-results.md`.

## Decisions I made (rulings)

- Ruling: kept `runner.FIXED_BUDGET` unchanged for the rows instead of the old `min(24, left - 1)` lowering - a lowered per-row budget could end a row `budget_exceeded` for a cap reason and hide the gate path; the meter enforces the cap of 40 anyway - cost if wrong: a row that would have needed more than the remaining calls fails as `model_error` at the cap instead of `budget_exceeded` (did not happen).
- Ruling: amended the expectation text once, before the run, to cover the pre-gate `denied` branch (the reason sentence without the prefix, or an appended prefixed sentence) - the gate's `_settle` has that branch and the first draft was stricter than the task's own expectation - cost if wrong: none in the results, since all three rows took the replace branch.
- Ruling: judged the rows "not plausibly wrong" although the customer text is thin (finding 2) - the sentence is true against `billing-policy.md:3-4` and `billing.json`, and the judging rule fixed before the run counts only false or wrong-path text - cost if wrong: a reviewer who counts thin answers would mark 3 of 3 differently.
- Ruling: did not read `desk.py`'s `lookup_payments` to explain why the model reports the id as "not found" - outside the task (judge the final texts, gate vs model) - cost if wrong: finding 4 stays a pointer.

Id spelling rows: done
