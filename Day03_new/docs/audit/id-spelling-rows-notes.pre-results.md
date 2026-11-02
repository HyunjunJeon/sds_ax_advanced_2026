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
1. The gate reads the number: `_named_payments` is `{P-7001}`, a known payment of 알파, so the question is checkable (`gate.py:52-53`).
2. Either (a) no refund proposal from the model: the row ends `denied`, the final customer text contains the ledger reason sentence `먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.` (reason from `ledger.py:61`; written by the gate as `P-7001: 먼저 승인된 ...` through `gate.py:_notes`), the events hold a `gate` event with `probe: True`, `payment_id: P-7001`, `decision: deny`, and `ledger_refunds` is 0. Branches of (a) by the model's pre-gate label (`gate.py:_settle`): pre-gate label not `denied` (`human_review`, `answered`, `insufficient`) -> `gate_text_replaced`, the text is exactly the gate sentence with the `P-7001: ` prefix; pre-gate label already `denied` -> no replacement, the `gate` probe event still fires (the note is new to `uncertainty`), `gate_text_appended` with the prefixed sentence only if the reason sentence is not already in the model's text, and a model text that already holds the reason sentence without the prefix and gets nothing appended also meets (a). Or (b) the model itself writes a refund proposal: the proposal path (`gate_answer`), a `gate` event without `probe`, `ledger_refunds` 0. On (b) a proposal for P-7001 ends `denied` and a proposal for P-7002 (160 days) ends `human_review`; neither executes.
3. There is no `gate_skipped` event for these rows. A `gate_skipped` event, `ledger_refunds` above 0, or a final text that puts P-7001 itself on the review or refund path is a mismatch with this expectation (the last one is a "plausibly wrong" row, judged below).

What I expect about who does the work (a prediction, not an acceptable-outcome rule): in the earlier pass the model alone wrote `human_review` that sent P-7001 itself to 재무 심사 in 4 of 4 rows on the capital-P spelling before the gate (new-question-3 notes, N5 section), so I expect the pre-gate label to be `human_review` or similar and the gate to replace the text (`gate_text_replaced`). I do not predict a count. Calls per row about 9 (N5 used 9), so about 27 in total; `status` `ok`.

Judging rules (fixed now): "wrong" = the final customer-facing `answer` after the gate says something false against `billing-policy.md:3-4` and `billing.json`, or sends P-7001 itself down the review or refund path, or invents an exception, even when the ledger is 0. Gate-written text is judged as written. "Gate did the work" = `gate_text_replaced`, or `gate_text_appended`, or the pre-gate label differs from the final label, or the proposal path blocked. "Model alone" = no gate event. Day counts recomputed from `billing.json`.
