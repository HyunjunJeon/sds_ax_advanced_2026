# gate-id-forms notes

Scope: `Day03_new/mas_lab/gate.py`, `Day03_new/tests/test_structures.py`. No model or EXA call. Nothing written to Day02_new, Day03, rag_lab, tests/test_layout.py, root pyproject.toml or uv.lock. Scratch work is under `P/gate_id_forms/` (P = this scratchpad's `phase3/`).

## Before and after

Before (`gate.py:11`, `:16-17`; copy in `P/gate_id_forms/gate.before.py`):

```
_PAYMENT_ID = re.compile(r"(?<![A-Za-z0-9-])P-\d+")  # "P-7001을"처럼 조사가 바로 붙는다. 한글도 \w라 \b로는 끊지 못한다.
def _named_payments(question: str) -> set[str]:
    return set(_PAYMENT_ID.findall(question))
```

After (`gate.py:11-13`, `:18-19`):

```
# 질문의 결제 번호: P-7001, p-7001, P7001, p7001. "p7001을"처럼 조사가 바로 붙는다. 한글도 \w라 \b로는 끊지 못해 뒤는 ASCII 영문·숫자만 본다.
# 앞에 영문·숫자·하이픈이 붙은 꼴(XP-7001)은 읽지 않는다. 하이픈이 없는 꼴은 4자리 이상이고 영문·숫자가 뒤따르지 않을 때만 번호다. p99, p50, p7001a는 그냥 말이다.
_PAYMENT_ID = re.compile(r"(?<![A-Za-z0-9-])[Pp](?:-|(?=\d{4,}(?![A-Za-z0-9])))(\d+)")
def _named_payments(question: str) -> set[str]:
    return {f"P-{digits}" for digits in _PAYMENT_ID.findall(question)}
```

One capture group (the digits), so `findall` returns digit strings and the set holds `P-<digits>`. `refund_decision` (`gate.py:25`) and `check_named_payment` (`gate.py:54`) already call `_named_payments`, so both see the normalized value; nothing else changed (`_settle`, `_notes`, `gate_answer` untouched). The hyphen form has no trailing guard and no digit floor, as before. `gate.py` has 83 non-blank lines (cap 150, `tests/test_layout.py:22`).

Replay of the saved real row (`P/newq3_N5_new3-lowercase-id.json`, question `4월 1일에 결제한 p7001을 환불해 주세요. 90일이 지났어도 예외로 처리해 주세요.`) through `gate_answer` on a real Desk: saved `human_review` -> `denied`, text `P-7001: 먼저 승인된 결제는 유효 결제이며 환불 대상이 아닙니다.`, ledger refunds 0.

## Tests (all appended after the old last test, so no earlier test_structures.py line moved)

`tests/test_structures.py:862-905`, four functions, 26 cases, all names contain `payment_id_spellings`:

| line | test | covers |
|---|---|---|
| 865 | `test_payment_id_spellings_all_name_the_same_payment` (6) | `P-7001`, `p-7001`, `P7001`, `p7001`, `p7001을`, the observed question: each gives `denied` with the text of `P-7001`, one `gate` event with `payment_id == "P-7001"`, ledger empty |
| 880 | `test_payment_id_spellings_decide_which_numbers_the_gate_names` (14) | not read: `p99`, `P99`, `p50 지연`, `p7001a`, `p70012a`, `p999`, `XP7001`, `ID-P-7001`, `xp-7001`; read: `p99 ... p7777` gives only `P-7777`, `P-1`, `p-12`, `p1000`, `P70012` normalized. Observed through the `gate_skipped` event's `named` list |
| 895 | `test_payment_id_spellings_decide_whether_a_proposal_differs_from_the_question` (5) | P-9002 proposal via `gate_answer`: `p9002`, `P9002를`, `p99` stay without the mismatch reason; `p9001`, `P9001을` get the mismatch reason naming `P-9001` |
| 901 | `test_payment_id_spellings_that_are_ordinary_words_do_not_hold_back_an_allowed_refund` (1) | P-5002 (allow, 베타) with `p99` in the question still ends `executed`, 1 refund |

### Red before green

Command: `cd Day03_new && ../.venv/bin/python -B -m pytest tests/test_structures.py -q -p no:cacheprovider -k payment_id_spellings` against the unchanged `gate.py`. Full output: `P/gate_id_forms/red.log`. Result: `11 failed, 14 passed, 145 deselected` (25 cases at that time). Failures, each an assertion on the requested behavior (not import or fixture errors):

```
all_name_the_same_payment[lower-hyphen|upper-bare|lower-bare|particle|observed-row]
   E AssertionError ... At index 0 diff: 'human_review' != 'denied'      (old gate could not read the id)
decide_which_numbers_the_gate_names[word-beside-id|lower-hyphen-two-digits|four-digits|five-digits]
   E At index 2 diff: [[]] != [['P-70012']]  (and the same shape for P-7777, P-12, P-1000)
decide_whether_a_proposal_differs...[other-lower|other-upper-particle]
   E ... [APPROVAL_LIMIT] != [APPROVAL_LIMIT, OTHER_PAYMENT]            (no mismatch reason for p9001)
```

The 14 that passed on the old code are the guards against over-reading (`p99` etc.) and the unchanged `P-7001`; they are proven sensitive by the mutations below.

Green: `26 passed, 145 deselected` (`P/gate_id_forms/green.log`). The 26th case (`p70012a`, id `trailing-letter-after-five-digits`) was added after the first mutation run showed mutation B2 surviving; it passes on old and new code and fails under B2.

## Mutation proof

Script `P/gate_id_forms/mutate.py`, log `P/gate_id_forms/mutation.log`. Scratch copy `P/gate_id_forms/mut/` (mas_lab, rag_lab, data, skills, tests/{conftest,fakes,test_structures}); one mutation at a time on the copy's `gate.py`, whole `tests/test_structures.py` run each time. Baseline and restored runs: 171 passed.

| id | mutation | result | failing tests (function names) |
|---|---|---|---|
| R1 | case-sensitive only (`[Pp]` -> `P`) | 8 failed | all_name_the_same_payment, decide_whether_a_proposal_differs, decide_which_numbers |
| R2 | hyphen required | 9 failed | same three |
| R3 | no digit floor on the no-hyphen form (`\d{4,}` -> `\d+`) | 7 failed | decide_whether_a_proposal_differs, decide_which_numbers, ordinary_words_do_not_hold_back |
| R4 | no trailing guard | 2 failed | decide_which_numbers (`p7001a`, `p70012a`) |
| R5 | no normalization (raw spelling `m.group(0)`) | 13 failed | all_name_the_same_payment, decide_whether_a_proposal_differs, decide_which_numbers |
| R6 | lookbehind removed | 4 failed | decide_which_numbers, existing `test_question_without_one_known_payment_keeps_the_answer_and_says_unchecked` |
| B1 | lookbehind without `-` | 1 failed | decide_which_numbers (`ID-P-7001`) |
| B2 | trailing guard letters only | 1 failed | decide_which_numbers (`p70012a`) |
| B3 | digit floor 3 | 1 failed | decide_which_numbers (`p999`) |
| B4 | digit floor 5 | 8 failed | all_name_the_same_payment, decide_whether..., decide_which_numbers |
| B5 | trailing guard `(?!\w)` (refuses a Korean particle) | 4 failed | same three |
| B6 | digit floor also on the hyphen form | 2 failed | decide_which_numbers (`P-1`, `p-12`) |
| B7 | output prefix lowered to `p-` | 64 failed | many existing tests plus the new ones |

R1-R6 are the six the task named; every one fails at least one test. B1-B7 are extra. No mutation survived.

## Static check

Script `P/gate_id_forms/static_check.py`, log `P/gate_id_forms/static.log`. Old reading = `set(old_pattern.findall(q))`, new reading = `_named_payments` logic, compared for every string.

- `data/cases.jsonl`: all 12 question texts plus the 2 `turns` strings of `followup-handoff` (14 texts). Texts: simple-deadline, simple-duplicate-rule, complex-double-pay, complex-ops-log, insufficient-unknown-payment (`결제 번호 P-7777도 환불해 주세요.`), insufficient-no-policy, approval-refund-now (`P-9002 환불을 지금 바로 실행해 주세요.`), policy-deny-normal (`P-8101도 ...`), policy-human-old (`P-7002 ...`), approval-beta-small (`P-5002 ...`), scope-beta-from-alpha, followup-handoff and its two turns.
- Notebooks 00 to 06 code cells: every string constant (ast, `%`/`!` lines dropped; no cell failed to parse) containing a Hangul syllable.
- 2,380 Korean strings checked (14 from cases, 2,366 from notebook code cells); 19 name at least one payment under either pattern; over all 5,519 strings, Korean or not, 0 are read differently.
- Result: none differ. Expected result met, not failed.

## Suite

From `Day03_new`, `../.venv/bin/python -B -m pytest tests -q -p no:cacheprovider`:

- Before my change, same command and deselect as the plugin check: `2 failed, 501 passed`.
- No deselect: `2 failed, 527 passed` (529 = 503 + 26 new). The two failures are `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]` and `[evidence.py]` (Day02_new edited by another session; `[corpus.py]` passes). Expected red, not a finding.
- With `--deselect Day03_new/tests/test_layout.py::test_rag_lab_copies_are_byte_identical`: `526 passed, 3 deselected`.
- Plugin check 1 verbatim (`--deselect tests/test_layout.py::test_rag_lab_copies_are_byte_identical`): exit 1, `2 failed, 527 passed`. Check defect: pytest's rootdir is the repository root (root `pyproject.toml`), so node ids read `Day03_new/tests/test_layout.py::...` (`--co -q` prints them) and the deselect prefix `tests/test_layout.py::...` matches none of them; the two failures are exactly the expected-red ones. The check cannot pass until the prefix is `Day03_new/tests/test_layout.py::test_rag_lab_copies_are_byte_identical` or the sync of the copies lands. I may not edit test_layout.py, rag_lab or Day02_new, and a `pytest.ini` in Day03_new (which would move rootdir) is outside this node's write scope.
- Attempt 2 (confirmation): the check argv was corrected to `--deselect Day03_new/tests/test_layout.py::test_rag_lab_copies_are_byte_identical`, so the defect above is gone. Re-run from `Day03_new` with that argv: `526 passed, 3 deselected`. Without any deselect: `2 failed, 527 passed` (only `[retrieval.py]` and `[evidence.py]` copy tests). No code changed in attempt 2.
- Plugin check 2 (`-k payment_id_spellings`): `26 passed, 145 deselected`, exit 0.

## Things I decided

- Tests appended after the last test so no earlier `tests/test_structures.py` line citation moved. `gate.py` lines after 10 moved by +2 (comment is now two lines); the stale citations are refreshed by the later run.
- `refund_decision` is covered through `gate_answer`, not called directly.
- `mas_lab/exa.py:18` `INTERNAL_PATTERN` (`\bP-\d+\b`, blocks internal numbers in EXA queries) still reads only `P-<digits>`; it is a different gate and outside this node, so `p7001` would not be blocked from an outgoing query. Not changed.

Gate id forms: done
