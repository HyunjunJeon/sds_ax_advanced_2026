# Replay 4: saved real rows through the current gate (`p7001`/`P7001`/`p-7001` read as P-7001), attempt 2

Offline. No model or EXA call, no `.env` read or printed, nothing written outside `scratchpad/phase3` (P). The answer key was touched only through `mas_lab.evaluation` (`load_gold`, `evaluate_row`) and is not printed. Replay 3 (`replay-3-notes.md`, `replay-results-3.json`) was read and left as it was.

P = `<P>`

## Attempt 2: why every number below was produced again

Attempt 1 of this node (notes kept as `P/replay-4-notes.attempt1.md`, results as `P/replay-results-4.attempt1.json`, N5/R1 as `P/replay4_n5_r1.attempt1.json`) ended `Replay 4: PASS` at 19:52. Upstream nodes changed project files after it: `Day03_new/mas_lab/exa.py` (20:04:21), `Day03_new/tests/test_research.py` (20:04:08) and `Day03_new/04-Graph-Engineering.ipynb` (20:02:39). So the exa hash, the suite totals and the notebook 04 check of attempt 1 are stale on the current tree. This attempt ran from 20:12:27 (start marker `P/replay4a2_start_marker`) and re-ran step 1 to step 5 from scratch with the same scripts (`P/replay_phase3-4.py`, `P/replay4_n5_r1.py`; logs overwritten, attempt-1 copies kept under `*.attempt1.*`).

What the refresh showed against attempt 1:

| item | attempt 1 | attempt 2 |
|---|---|---|
| `gate.py` sha256 prefix (mtime 19:24:45) | 16c50d6ee3ecaf2c | 16c50d6ee3ecaf2c (same) |
| `workers.py` (mtime 19:39:35) | 2fde59e593fb7660 | 2fde59e593fb7660 (same) |
| `exa.py` (mtime 20:04:21) | a19451c9964923f0 | **c8f238a968aadfaf** (changed; not on the replay path) |
| other `mas_lab` files hashed | equal | equal |
| replay rows (422), all fields | - | **0 of 422 rows differ** from `replay-results-4.attempt1.json`; only top-level keys `code_before`, `code_after` differ (the exa hash) |
| replay console output | - | identical except the two lines that print the exa hash |
| N5/R1 console output | - | identical |
| `check_notebook` 7 of 7 | OK | OK |
| suite | 2 failed, 580 passed (582 tests) | **2 failed, 608 passed (610 tests)** |
| `audit_live.py` last line | AUDIT OK | AUDIT OK |
| `outputs/runs` | 1781 / 1781 | 1781 / 1781 |

## What changed since replay 3, and what the replay can and cannot see

| file (`Day03_new/mas_lab/`) | replay 3 | now | changed |
|---|---|---|---|
| `gate.py` | a559649a4d4378fc | 16c50d6ee3ecaf2c | **yes** (`_PAYMENT_ID` reads four spellings, one capture group; `_named_payments` normalizes to `P-<digits>`) |
| `workers.py` | 426ebea3620ce157 | 2fde59e593fb7660 | **yes** (not exercised by a replay: a replay feeds only the final answer) |
| `exa.py`, `research.py`, `view.py` | not hashed in replay 3 | c8f238a968aadfaf, f897e5feac366275, 91b45ed628072ac4 | (hashed now; `exa.py` is not on the replay path) |
| `contracts.py`, `ledger.py`, `evaluation.py`, `structures.py`, `hybrid.py`, `runner.py`, `desk.py`, `trace.py` | equal | equal | no |

Code hashes are identical at the start and the end of the run: True. `gate.py` full sha256 now `16c50d6ee3ecaf2c3895381c4a49beb472b539c32629a38ac3c8fd9378901653` (replay 3: `a559649a4d4378fcb21ee621beaa33a83292b91ecc4b9a282725248a99fb1cc3`).

## Step 1: replay of the saved rows

- Script: `P/replay_phase3-4.py` (copy of `replay_phase3-3.py`, built by `P/patch_replay4.py` with asserted one-match replacements). Command from the repo root: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python P/replay_phase3-4.py`; console `P/replay-run-4.out`, rows `P/replay-results-4.json`, stderr empty (0 bytes), exit 0.
- Needed adaptation: the gate's new `_PAYMENT_ID` has a capture group, so `findall` now returns digits; the script's `named` ids come from `gate._named_payments`. Without that the independent probe check would have compared `7001` with `P-7001`.
- Real row = a call with model `claude-sonnet-5-5` and non-null `input_tokens` (same `is_real`). Per replayable row: rebuild `FinalAnswer` from the saved fields, fresh `Desk` from `runner.make_desk(case)`, `check_named_payment(final, desk, last_turn_question)`, score the saved and the gated row with `evaluate_row`; then call again on the same desk, on a fresh desk, and through `gate_answer` with no proposal.

### Population

| bucket | replay 3 | now | added |
|---|---|---|---|
| files in `outputs/runs` | 1657 | **1781** | 124 |
| real rows | 608 | **732** | 124 (all real; fake rows 1049 then and now) |
| real, case not in `data/cases.jsonl` (`adhoc-3` 7, `adhoc-4` 7, `my-refund-window` 7) | 16 | 21 | 5 |
| real, known case, no final answer (`budget_exceeded`) | 33 | 40 | 7 |
| real, known case, saved a refund proposal (`executed` 31, `needs_approval` 218) | 209 | 249 | 40 |
| real, known case, no refund proposal: **replayed** | 350 | **422** | 72 |

21 + 40 + 249 + 422 = 732 = real rows. 5 + 7 + 40 + 72 = 124 = added real rows. Replayed by saved label: `answered` 246, `denied` 31, `human_review` 30, `insufficient` 101, `out_of_scope` 14. 27 of them saved a proposal with action `none`. Replayable rows with a saved ledger write: 0.

Files that existed at replay 3 are byte-identical: those 1657 files (mtime not after `replay-results-3.json`) fold to `f39d71755dccab5699c9f7b9215db294fb1dc32744e27f9ef6e8f4cc25bccd61`, equal to replay 3's all-files hash; the 608 real ones among them fold to `851669f09bcd0695277ff05c53e01d8351b9a66e778c973b545f16655e76c234`, equal to replay 3's real-rows hash. Hashes now: all 1781 `aaaba62498522ca2dd743e406b4335cd51aedf4d23cd0ad4c6ccdd32d2b7f915`, real 732 `db465f4becb3bd032be16288a7a9477574f8a7a50ec9ddb402db4eafde4ca1cc`; identical before and after the run; added 0, removed 0, modified 0, real files changed 0. These two hashes are the same as in attempt 1, so nothing in `outputs/runs` moved between the attempts.

### Rows common to replay 3 (350 run_ids)

| measure | replay 3 | now, same 350 rows |
|---|---|---|
| rows only in replay 3 | - | **0** |
| outcome flips | 0 | **0** |
| text replaced | 0 | **0** |
| text appended | 51 | 51 |
| rows with trace-only `gate_skipped` | 50 | 50 |
| ledger writes (first call, second call, public path) | 0 | **0** |
| automatic check pass, before gate / after gate | 342 / 342 | **342 / 342** |
| case-and-structure cells whose pass count fell | - | none |
| rows that differ in the listed keys (outcome, text, added uncertainty, check result, failing columns, replaced/appended, status) | - | **0** |
| rows that differ in any field (event counts and payloads, ledger counts, idempotence flags included) | - | **0** (fields that differ: none) |

The 8 common rows that fail the automatic check fail the same columns before and after, as in replay 3 (differing: 0): `complex-ops-log`/hybrid 60b46e02, 68d77eab, a18125f8, ac61151f, b1ad7245, f1daa341 on `outcome` + `인용 문서`; `insufficient-unknown-payment`/single 96f82600 on `실행 상태`; `complex-double-pay`/handoff e4f4f193 on `outcome` + `필수 사실` + `금지 표현`. Nothing moved on the saved real rows: the gate change is invisible on them.

### Rows new since replay 3 (72 replayed)

| measure | value |
|---|---|
| outcome flips | 0 |
| text replaced | 0 |
| text appended | 0 |
| ledger writes | 0 |
| automatic check pass before / after | 68 / 68 of 72 |
| rows with trace-only `gate_skipped` on replay | 9 (all `insufficient-unknown-payment`, label `insufficient`) |

These rows were already gated by the current code, and replaying them adds nothing: the 10 new `denied`/`human_review` rows (`policy-deny-normal` 5, `policy-human-old` 5) saved one `gate` and one `gate_text_appended` event each (read from the saved rows), and the replay appends 0 more; the 9 new `insufficient-unknown-payment` rows saved one `gate_skipped` each and the replay emits exactly one on its fresh desk, answer unchanged. The script prints a `NEW ROW WITH CHANGE` line for any flip, replacement, append, ledger write, pass change or status change, and printed none.

Not good news, listed in full and not explained away: 4 of the 72 new rows fail the automatic check, all `complex-ops-log` / `hybrid` on column `인용 문서` (run_ids `56948295017a4ea8b689c3cfb5e4454d`, `8651f08408294378a59fff84a7223377`, `88029694bab3457f8995b0cfcc1d5761`, `c7b3653c9fa245cdb73c1b265dbc9634`). They fail the same column before and after the gate (the gate neither caused nor fixed them); they are the model's own citations, which a replay cannot touch.

### Totals, all 422 replayed rows

Rows 422, flips 0, text replaced 0, text appended 51, `gate_skipped` rows 59 (50 + 9), ledger writes 0, automatic check pass 410 before and 410 after (342 + 68). Total fails 12 (8 common + 4 new), same columns before and after (rows whose failing columns differ: 0). Verdict flag from the script: `ok` True (ledger_bad [], no case, case-and-structure cell or row fell).

### Spelling scan of the questions the replay used

120 id-like tokens in the 422 questions with the wide scan `(?<![A-Za-z0-9-])[Pp]-?\d+`; all 120 are the old `P-<digits>` form, none is `p7001`, `P7001`, `p-7001` or a word like `p99`. So the new spellings cannot move any saved row, and the identical result above is expected. The scan is not vacuous: it finds `p7001`, `p-7001` and `P7001` in test strings (controls below).

### Other checks (all rows)

- Ledger writes after `check_named_payment`: 0; after a second call on the same desk: 0; after the public `gate_answer` path: 0.
- Second call on the same desk adds nothing: True. Gated answer fed to a fresh desk adds nothing: True. `gate_answer` with no proposal equals `check_named_payment`: True. `gate_text_replaced`/`gate_text_appended` events agree with the string comparison of old and new text: True (text classes by string: same 371, appended 51, replaced 0).
- Probe decisions in the trace equal `check_refund` called directly for each named id (ids from `_named_payments`): false on 0 rows. Unsourced appended amounts: 0 rows. New validation problems: 0 rows. Status changed: 0 rows.
- `gate_skipped` rows equal the independently derived set (59 observed, 59 expected, missing [], extra []); one event per desk also after the second call; answer, outcome, text, uncertainty, proposal unchanged; no other gate event on those rows.
- Negative controls, each must come out False and did: gate that writes the ledger False, gate that empties the text and relabels `denied` False; for the `gate_skipped` check: edits the answer False, never emits False, emits twice False.
- Controls for the new comparison, each must be True and is: a gate that ruins the text makes `compare_with_first` list differing rows (60 rows) True; the spelling scan sees `p7001` True, `p-7001` True, `P7001` True.
- Synthetic relabel probe, not part of the verdict (61 saved `denied`/`human_review` texts relabeled `answered`, `insufficient`, `needs_approval`, `executed`, 244 variants): `policy-deny-normal` -> `denied` 31 rows per label, `policy-human-old` -> `human_review` 30 rows per label, text replaced every time, ledger 0.
- Synthetic spelling sweep, not part of the verdict (the question of each of those 61 rows written as `P-N`, `p-N`, `PN`, `pN`, `pN을`, saved text labelled `answered`): all five spellings give the same outcome, text and uncertainty as `P-N` on all 61 rows (`denied` 31, `human_review` 30), ledger 0.

## Step 2: row N5 (`p7001`) through the current `gate_answer`

Script `P/replay4_n5_r1.py`, console `P/replay4_n5_r1.out`, data `P/replay4_n5_r1.json`. Input: the `pre_gate` recorder value of `P/newq3_N5_new3-lowercase-id.json` (the model's own `FinalAnswer`: outcome `human_review`, no proposal, text beginning "요청하신 결제는 P-7001(청구서 INV-2026-03 ...") and its recorded question `4월 1일에 결제한 p7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.` (asserted equal to the case question). Desk: `runner.make_desk(case)` with the case dict of `new_q3_run.py` (`case()` helper at line 64, N5 at line 83, R1 at line 70: entity 알파, as_of 2026-09-08; checked against that file in this attempt). Call: `gate_answer(final, desk, approved=None, request_id=<saved run_id>, question=<recorded question>)`.

Observed:

- **outcome `denied`**, **ledger 0**, proposal None.
- text: `P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.`
- uncertainty: `['P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.']`
- `gate` events (2 gate-family events): `{"kind": "gate", "actor": "code", "probe": true, "payment_id": "P-7001", "decision": "deny", "reasons": ["먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다."]}` and `gate_text_replaced` (`replaced` = the first 80 characters of the model text; `dropped_uncertainty` = the model's five uncertainty lines, all replaced).
- `gate_text_replaced`: 1 event, as expected for a text the gate replaced. No `gate_skipped`.
- The real hybrid path (the node's `check_named_payment`, then the runner's `gate_answer` on its result) gives the same: `denied`, same text, same uncertainty, ledger 0, events `['gate', 'gate_text_replaced']`.
- The saved row, produced by the gate before the change: outcome `human_review`, the model's text kept, events `['gate_skipped']`, ledger 0. That is the one wrong row; it is now corrected.
- Control, same input through the gate as it was before the change (`P/gate_id_forms/gate.before.py`): N5 gives `human_review`, text equal to the model's, events `['gate_skipped']`, ledger 0 (the wrong reading, reproduced); R1 gives `denied`. So the check is sensitive to the fix.

## Step 3: row R1 (`P-7001`) and the comparison

R1 (`P/newq3_R1_new-deny-p7001.json`): question `4월 1일에 결제한 P-7001을 환불해 주세요. ...`, model answer `human_review`, no proposal. Through the current `gate_answer`: **`denied`**, ledger 0, text `P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.`, events `gate` + `gate_text_replaced`.

| compared N5 vs R1 | result |
|---|---|
| outcome equal | True (`denied` both) |
| customer-visible text equal | True (character for character) |
| uncertainty equal | True |
| `gate` probe event equal in every field | True |
| gate event kinds equal | True (`gate`, `gate_text_replaced`) |
| R1's saved text (old gate) equals N5's text now | True |
| `gate_text_replaced` equal in every field | **False**, fields that differ: `replaced`, `dropped_uncertainty` |
| model text equal | False |

The last two rows differ because the two model samples wrote different text and different uncertainty lines, and that event carries the model's own text. They are inputs, not gate behavior; the customer-visible result does not depend on them.

## Step 4: notebooks, suite, audit

`check_notebook.py` from the repo root (log `P/replay4_check_notebook.log`, all exit 0, each printed `OK`): `00-Setup` (`--minutes 10`), `01-Workflow-vs-Agent`, `02-Agent-Architecture`, `03-Four-Flows`, `04-Graph-Engineering` (changed in markdown at 20:02 by `edge-legend-note`, so this is the first check of the final version), `05-Choosing-Multi-Agent`, `06-Lab-Research-Agents` (each `--minutes 60`). Seven of seven OK.

Suite from `Day03_new`, `../.venv/bin/python -B -m pytest tests -q -p no:cacheprovider` (log `P/replay4_pytest.log`): **2 failed, 608 passed** in 6.59 s (610 tests; attempt 1 had 582 because `tests/test_research.py` has gained cases since). The 608 equals the count `exa-id-forms` reported. Failing ids (pytest prints them relative to `Day03_new`; their full ids are `Day03_new/tests/test_layout.py::...`):

- `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]`
- `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[evidence.py]`

Both are the allowed expected red (`rag_lab` copies against Day02_new, edited by another session; `[corpus.py]` passes). No other failure.

`audit_live.py` from the repo root (log `P/replay4_audit_live.log`, exit 0, 14 lines): last line `AUDIT OK`. Notebooks 01 and 04 changed only in markdown, and the audit still passes.

## Step 5: `outputs/runs` count

Before (taken before the replay read anything, 20:12:27): **1781** (`P/replay4a2_runs_count_before.txt`; attempt 1 had 1781 too). After the replay, N5/R1, notebooks, suite and audit: **1781** (`P/replay4a2_runs_count_after.txt`). Also checked inside the replay by file hash: added 0, removed 0, modified 0. It did not shrink.

No project file changed during this node: `find Day03_new -newer P/replay4a2_start_marker -type f -not -path "*/outputs/*"` finds nothing, and `find Day03_new/outputs -newer P/replay4a2_start_marker -type f` finds nothing. The three upstream edits (exa.py 20:04:21, test_research.py 20:04:08, 04 notebook 20:02:39) are all older than the marker (20:12:27), so they were made by upstream nodes, not here.

## Limits

1. 249 real known-case rows saved a refund proposal and cannot be replayed (they saved only the gated outcome, not the model's answer before the gate); 40 have no final answer; 21 belong to cases not in `cases.jsonl`. The proposal path (`refund_decision` with the mismatch reason) has no real input here; it is covered by `tests/test_structures.py` (`payment_id_spellings` tests).
2. No saved real question uses a new spelling (120 of 120 id tokens are `P-<digits>`), so the replay can show "no regression" but cannot show the correction on a real row except through N5, which was recorded for exactly that purpose. The spelling sweep above rewrites real questions in memory; it is synthetic.
3. A replay feeds the gate only the final answer. It cannot show Worker references (`workers.py` changed), budgets, spans or the EXA query boundary (`exa.py` changed); the unit tests and the paid rerun cover those.
4. The automatic check is string containment (`mas_lab/evaluation.py`). An unchanged pass count means the gate added no forbidden wording and kept every required fact; it does not prove the text is right.
5. The "files that existed at replay 3" set is picked by mtime not after `replay-results-3.json`; the hash equality with replay 3 (both the 1657 and the 608) is what proves it is the same set and unchanged.
6. N5 is one recorded model sample; a different sample would write different text, but the gate's reading of the question (`p7001` is P-7001) does not depend on the model text.

## Verdict criteria

- step 1: 422 replayed, partition adds up (21 + 40 + 249 + 422 = 732): True
- step 1: rows only in replay 3: 0; common rows differing in any field: 0; flips 0, replaced 0, ledger 0 on all 422 rows and on all three paths: True
- step 1: automatic check pass 342 -> 342 on the common rows, 68 -> 68 on the new rows, no cell fell: True
- step 1: replaying rows already gated by the current code adds nothing (new rows: appended 0, replaced 0, flips 0): True
- step 1: `outputs/runs` files at replay 3 byte-identical (1657 and 608 hashes equal replay 3's); added/removed/modified during the run 0: True
- step 1: negative controls fail as they must (ledger writer, text ruiner, three `gate_skipped` controls, comparison control): True
- step 1: attempt 2 rows equal attempt 1 rows (0 of 422 differ): True
- step 2: N5 `denied`, text is the ledger sentence about P-7001, ledger 0: True
- step 3: R1 `denied` with the same customer-visible text as N5: True
- step 4: seven notebooks OK: True; suite failures only the two allowed `test_layout` ids: True; `audit_live.py` last line `AUDIT OK`: True
- step 5: 1781 before, 1781 after: True

Replay 4: PASS
