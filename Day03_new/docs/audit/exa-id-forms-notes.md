# exa-id-forms notes (attempt 2)

Scope: `Day03_new/mas_lab/exa.py`, `Day03_new/tests/test_research.py`. No model or EXA call. Nothing written to `Day02_new`, `Day03`, `rag_lab`, `tests/test_layout.py`, the notebooks, the docs or `outputs/`. Scratch work is under `P/exa_id_forms/` (P = this scratchpad's `phase3/`). `DEFAULT_BLOCKED`, `allowed_url` and the domain rules are untouched. Nothing is imported from `gate.py`.

## Why attempt 2

A review found that attempt 1 (`re.ASCII | re.IGNORECASE`) closed the Korean-particle and spelling holes but made `\d` and `\w` ASCII-only, so ids the OLD pattern blocked now passed: `P-７００１ 환불`, `P-٧٠٠١ refund`, `T-１２`, `INV-２０２６`, `INV-가나다` (and `INC-３１１`, which I found while building the table; `AGENTS.md` section 5 item 9 forbids loosening). Attempt 2 drops `re.ASCII` and replaces `\b` with lookarounds that treat only ASCII letters and digits as id-extending. Hangul, `_` and everything else end an id; Unicode `\d` is kept.

## Before and after

Old (before attempt 1; copy in `P/exa_id_forms/exa.before.py`):

```
INTERNAL_PATTERN = re.compile(r"\b(?:P-\d+|INV-[\w-]+|INC-\d+|T-\d+)\b")
```

Attempt 1 (superseded):

```
INTERNAL_PATTERN = re.compile(r"\b(?:P(?:-\d+|\d{4,})|INV-[\w-]+|INC-\d+|T-\d+)\b", re.ASCII | re.IGNORECASE)
```

Attempt 2 (`exa.py:18`, same line number, so no later line citation moved; flags value 34 = IGNORECASE | UNICODE, no ASCII bit):

```
INTERNAL_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:P(?:-\d+|\d{4,})|INV-(?:[A-Za-z0-9-]+|[\w-]+)|INC-\d+|T-\d+)(?![A-Za-z0-9])", re.IGNORECASE)
```

`exa.py:31` (one line, nothing below moved; `grep -c "re.ASCII" mas_lab/exa.py` is 0, the flag is not named anywhere in the file):

```
"""고객 이름과 내부 번호가 든 질의를 호출 전에 막는다. 번호는 대소문자, 하이픈 유무, 전각·아랍 숫자를 가리지 않고 앞뒤에 한글이나 밑줄이 붙어도 막는다. 영문자·숫자가 앞에 붙은 gpt-4 같은 말과 p99 같은 짧은 꼴은 번호가 아니다. 뜻까지 판단하지는 못한다."""
```

Only lines 18 and 31 of `exa.py` differ from `exa.before.py` (`diff` shows exactly those two). The docstring is not a raw string and names no backslash escape.

What each part does and why the new pattern blocks a superset of the old one:
- `(?<![A-Za-z0-9])` / `(?![A-Za-z0-9])` replace `\b`. Where the old `\b` held next to the id, the neighbouring character was a non-word character or the string edge, which is never an ASCII letter or digit, so the lookaround holds too. The reverse is not true: Hangul, `_` and Unicode letters or digits no longer glue to the id. That is the intended tightening (`P-7001을`, `고객P-7001은`, `customer_P-7001`).
- `re.IGNORECASE`: `p-7001`, `inv-2026-03`, `inc-311`, `t-12`.
- Unicode `\d` kept: `P-７００１`, `P-٧٠٠١`, `T-１２`, `INC-３１１` stay blocked.
- `P(?:-\d+|\d{4,})`: hyphen form any digit count (as before); no-hyphen form needs 4+ digits, the gate's floor (`mas_lab/gate.py:13`, not imported). `p99`, `p999`, `p50` stay open.
- `INV-(?:[A-Za-z0-9-]+|[\w-]+)`: ASCII first, so `INV-2026-03번` matches `INV-2026-03` and the error message does not carry the particle. If the first alternative cannot start (`INV-가나다`, `INV-２０２６`) the second keeps the old `[\w-]+` reach. The lookahead after the first alternative always holds (the run stops at a character that is not in the class), so nothing the old pattern matched is lost.

Checked on the four strings the task named (shipped pattern, `findall`):
`INV-2026-03번` gives `['INV-2026-03']`; `INV-가나다` gives `['INV-가나다']`; `INV-２０２６` gives `['INV-２０２６']`; `inv-2026-03` gives `['inv-2026-03']`.

## Old against new, every sample

`P/exa_id_forms/compare_table.py` imports the shipped `INTERNAL_PATTERN` and compares it with the old pattern and the attempt 1 pattern (both copied literally into the script). Output: `P/exa_id_forms/compare_table.txt`. "pass" means the query is allowed through, "blocked" means `assert_public_query` would raise (the three pattern columns only; the `DEFAULT_BLOCKED` words are not applied, so `알파 고객 크레딧 기한` and `베타 SLA` show pass here and are blocked by the word list as before).

| sample | old | attempt 1 | new | new match |
|---|---|---|---|---|
| `P-7001` | blocked | blocked | blocked | ['P-7001'] |
| `P-7001을` | pass | blocked | blocked | ['P-7001'] |
| `p-7001` | pass | blocked | blocked | ['p-7001'] |
| `P7001` | pass | blocked | blocked | ['P7001'] |
| `p7001` | pass | blocked | blocked | ['p7001'] |
| `p7001을` | pass | blocked | blocked | ['p7001'] |
| `INV-2026-03` | blocked | blocked | blocked | ['INV-2026-03'] |
| `inv-2026-03` | pass | blocked | blocked | ['inv-2026-03'] |
| `INV-2026-03번` | blocked | blocked | blocked | ['INV-2026-03'] |
| `INC-311` | blocked | blocked | blocked | ['INC-311'] |
| `inc-311의` | pass | blocked | blocked | ['inc-311'] |
| `T-12` | blocked | blocked | blocked | ['T-12'] |
| `t-12는` | pass | blocked | blocked | ['t-12'] |
| `고객P-7001은 환불` | pass | blocked | blocked | ['P-7001'] |
| `p1000` | pass | blocked | blocked | ['p1000'] |
| `P-７００１ 환불` | blocked | pass (lost) | blocked | ['P-７００１'] |
| `P-٧٠٠١ refund` | blocked | pass (lost) | blocked | ['P-٧٠٠١'] |
| `T-１２` | blocked | pass (lost) | blocked | ['T-１２'] |
| `INV-２０２６` | blocked | pass (lost) | blocked | ['INV-２０２６'] |
| `INV-가나다` | blocked | pass (lost) | blocked | ['INV-가나다'] |
| `customer_P-7001` | pass | pass | blocked | ['P-7001'] |
| `알파 고객 크레딧 기한` | pass | pass | pass |  |
| `P-9002 환불` | blocked | blocked | blocked | ['P-9002'] |
| `INV-2026-08 내역` | blocked | blocked | blocked | ['INV-2026-08'] |
| `베타 SLA` | pass | pass | pass |  |
| `multi-agent orchestration patterns` | pass | pass | pass |  |
| `p99 latency` | pass | pass | pass |  |
| `p50 지연` | pass | pass | pass |  |
| `gpt-4 evaluation` | pass | pass | pass |  |
| `T cell` | pass | pass | pass |  |
| `t-test` | pass | pass | pass |  |
| `inv에 대한 설명` | pass | pass | pass |  |
| `python 3.13` | pass | pass | pass |  |
| `p999 latency` | pass | pass | pass |  |
| `(P-7001)` | blocked | blocked | blocked | ['P-7001'] |
| `P-7001, P-7002` | blocked | blocked | blocked | ['P-7001', 'P-7002'] |
| `고객: P-7001 환불` | blocked | blocked | blocked | ['P-7001'] |
| `Re: INV-2026-03` | blocked | blocked | blocked | ['INV-2026-03'] |
| `INV-2026-03-` | blocked | blocked | blocked | ['INV-2026-03-'] |
| `INV-abc` | blocked | blocked | blocked | ['INV-abc'] |
| `INV-2026- 내역` | blocked | blocked | blocked | ['INV-2026-'] |
| `INV-2026-03번 내역` | blocked | blocked | blocked | ['INV-2026-03'] |
| `INV-2026_03` | blocked | blocked | blocked | ['INV-2026'] |
| `INV-_x` | blocked | blocked | blocked | ['INV-_x'] |
| `P-1` | blocked | blocked | blocked | ['P-1'] |
| `INC-３１１` | blocked | pass (lost) | blocked | ['INC-３１１'] |
| `P-7001٧` | blocked | blocked | blocked | ['P-7001٧'] |
| `INV-2026-03번` | blocked | blocked | blocked | ['INV-2026-03'] |
| `INV-２０２６` | blocked | pass (lost) | blocked | ['INV-２０２６'] |
| `INV-가나다` | blocked | pass (lost) | blocked | ['INV-가나다'] |
| `inv-2026-03번` | pass | blocked | blocked | ['inv-2026-03'] |
| `INV-2026가나다` | blocked | blocked | blocked | ['INV-2026'] |
| `P-7001a` | pass | pass | pass |  |
| `p7001a` | pass | pass | pass |  |
| `p12345` | pass | blocked | blocked | ['p12345'] |
| `T-800 terminator` | blocked | blocked | blocked | ['T-800'] |
| `inv-test` | pass | blocked | blocked | ['inv-test'] |
| `step-1 pre-p-12` | pass | blocked | blocked | ['p-12'] |
| `INV-` | pass | pass | pass |  |
| `INV- 내역` | pass | pass | pass |  |
| `INV--` | pass | pass | blocked | ['INV--'] |
| `P-7001_x` | pass | pass | blocked | ['P-7001'] |
| `_P-7001` | pass | pass | blocked | ['P-7001'] |
| `고객 p-7001을` | pass | blocked | blocked | ['p-7001'] |
| `서P7001` | pass | blocked | blocked | ['P7001'] |
| `T-12번` | pass | blocked | blocked | ['T-12'] |
| `INC-311에서` | pass | blocked | blocked | ['INC-311'] |
| `p-99` | pass | blocked | blocked | ['p-99'] |
| `P99` | pass | pass | pass |  |
| `gpt-4` | pass | pass | pass |  |
| `ap-12` | pass | pass | pass |  |
| `xT-12` | pass | pass | pass |  |
| `paper-12` | pass | pass | pass |  |
| `ΚP-7001` | pass | blocked | blocked | ['P-7001'] |

Samples where old blocked but new passes: []
Samples where old blocked but attempt 1 passed: ['P-７００１ 환불', 'P-٧٠٠١ refund', 'T-１２', 'INV-２０２６', 'INV-가나다', 'INC-３１１', 'INV-２０２６', 'INV-가나다']

superset fuzz: 475254 exhaustive strings (tokens 26, length 1-4) + 1500000 random strings (length 5-14): old-blocked but new-passes = 0 []


So: no sample is blocked by the old pattern and passed by the new one. Attempt 1 lost six distinct strings (the five reproduced plus `INC-３１１`; the script's list shows eight entries because two of them are in the sample list twice). Newly blocked by attempt 2 compared with the old pattern are only the intended ones: other cases, a glued particle or Hangul prefix, `_`, the no-hyphen P form with 4+ digits, and `INV--`.

The fuzz line is exhaustive over every concatenation of up to 4 of 26 tokens (P, p, INV, inv, INC, T, t, hyphen, ASCII/fullwidth/Arabic-Indic digits, letters, `_`, space, Hangul, `(`, `.`, Kelvin sign, long s, `İ`, `ı`, `é`, superscript two) plus 1.5 million random strings of 5 to 14 tokens: zero strings the old pattern blocks and the new one passes.

## Tests (`tests/test_research.py`; `import re` added at line 1, so the test code moved down one line; no document cites a line of this file, checked with grep)

| line | test | cases |
|---|---|---|
| 92 | `test_internal_id_spellings_are_blocked` | the 15 earlier cases plus six new: `P-７００１ 환불`, `P-٧٠٠١ refund`, `T-１２`, `INV-２０２６`, `INV-가나다`, `customer_P-7001` |
| 99 | `test_internal_id_spellings_leave_ordinary_queries_alone` | unchanged: 9 allowed queries (`p99 latency`, `p999 latency`, `p50 지연`, `gpt-4 evaluation`, `T cell`, `t-test`, `inv에 대한 설명`, `python 3.13`, one plain query) |
| 106 | `test_internal_id_spellings_message_names_the_id_without_the_particle` | unchanged: 5 message cases (`P-7001을`, `p7001을`, `INV-2026-03번`, `inc-311의`, `t-12는`) |
| 113-124 | `test_internal_id_spellings_keep_everything_the_old_pattern_blocked` | the superset test: `OLD_INTERNAL_PATTERN` (line 114) is the old pattern copied literally, `OLD_BLOCKED` (line 115) has 22 samples. Each sample is first asserted against the old pattern (so a wrong sample cannot pass quietly), then must raise `ValueError` from the current `assert_public_query`. A future narrowing fails it |

All go through the public `assert_public_query`. No earlier test was deleted, skipped or weakened. `-k internal_id_spellings` selects 57 cases. The old pattern is deliberately not imported from `exa.py` (that would narrow with the code under test).

### Red before green

Against the present attempt 1 code (`re.ASCII` still in `exa.py`), command `../.venv/bin/python -B -m pytest tests/test_research.py -q -p no:cacheprovider -k internal_id_spellings -rf`; full output in `P/exa_id_forms/red_attempt2.txt`:

```
12 failed, 45 passed, 18 deselected in 0.49s
```

12 failed: six in `test_internal_id_spellings_are_blocked` (`P-７００１ 환불`, `P-٧٠٠١ refund`, `T-１２`, `INV-２０２６`, `INV-가나다`, `customer_P-7001`) and six in the superset test (`P-７００１ 환불`, `P-٧٠٠١ refund`, `T-１２`, `INC-３１１`, `INV-２０２６`, `INV-가나다`). Every failure is `Failed: DID NOT RAISE ValueError` at `tests/test_research.py:93` and `:123` (the `pytest.raises` lines), i.e. the requested behaviour, not an import or fixture error. The other 45 selected cases pass before and after (the 29 cases that existed before, plus the 16 of the 22 superset samples that the attempt 1 pattern still blocks).

Green after the fix: `tests/test_research.py` `75 passed`; `-k internal_id_spellings` `57 passed, 18 deselected`.

## Mutation table (attempt 2)

Each row is one change to line 18 in a scratch copy (`P/exa_id_forms/run_mutations2.py` copies `mas_lab`, `rag_lab` and `conftest.py`, `fakes.py`, `test_research.py` to `work2/`, applies the mutation, runs `tests/test_research.py`; output `P/exa_id_forms/mutations_attempt2.txt`; `work2/` is deleted at the end). The real files are never mutated; after the run `exa.py` still has the shipped line (`grep -c "re.ASCII"` gives 0).

| mutation | result | failing tests (first ones; a caught-by test is named when only one) |
|---|---|---|
| none (control) | 75 passed | |
| required: restore `re.ASCII` | 11 failed | `are_blocked[P-７００１ 환불]`, `[P-٧٠٠١ refund]`, `[T-１２]`, `[INV-２０２６]`, `[INV-가나다]` and six `keep_everything_the_old_pattern_blocked` cases |
| required: no `IGNORECASE` | 10 failed | `are_blocked[p-7001]`, `[p7001]`, `[inv-2026-03]`, `[inc-311의]`, `[t-12는]`, `[p1000]`, three message cases |
| required: `\w` in both lookarounds | 11 failed | `are_blocked[P-7001을]`, `[p7001을]`, `[inc-311의]`, `[t-12는]`, `[고객P-7001은 환불]`, `[customer_P-7001]`, five message cases incl. `INV-2026-03번` |
| required: no no-hyphen form (`P-\d+` only) | 5 failed | `are_blocked[P7001]`, `[p7001]`, `[p7001을]`, `[p1000]`, message `[p7001을]` |
| required: no digit floor (`\d+`) | 3 failed | `leave_ordinary_queries_alone[p99 latency]`, `[p50 지연]`, `[p999 latency]` |
| required: drop the `[\w-]+` alternative for `INV-` | 5 failed | `are_blocked[INV-２０２６]`, `[INV-가나다]`, and superset `[INV-_x]`, `[INV-２０２６]`, `[INV-가나다]` |
| required: P form dropped | 22 failed | `test_internal_queries_stay_inside[P-9002 환불]` (an old test) and 21 new cases |
| extra: `\w` in the lookbehind only | 2 failed | `are_blocked[고객P-7001은 환불]`, `[customer_P-7001]` |
| extra: `\w` in the lookahead only | 10 failed | the particle cases and message cases |
| extra: back to `\b` on both sides | 11 failed | same set as `\w` in both |
| extra: `INV-[\w-]+` only (no ASCII-first alternative) | 1 failed | message `[INV-2026-03번 내역]` (the id would be named with the particle) |
| extra: digit floor 3 | 1 failed | `leave_ordinary_queries_alone[p999 latency]` |
| extra: ASCII digits only (`[0-9]` for `\d`) | 7 failed | `are_blocked[P-７００１ 환불]`, `[P-٧٠٠١ refund]`, `[T-１２]` and four superset cases |
| extra: `INC-` dropped | 5 failed | `are_blocked[INC-311]`, `[inc-311의]`, message `[inc-311의]`, two superset cases |
| extra: `T-` dropped | 6 failed | `are_blocked[T-12]`, `[t-12는]`, `[T-１２]`, message `[t-12는]`, two superset cases |

Every required mutation fails at least one test; so does every extra one. The `\w`-in-lookarounds and `re.ASCII` rows fail different tests, so neither is covered only by the other.

### Mutation table of attempt 1 (kept for the record; run against the attempt 1 pattern and the attempt 1 tests, 47 cases)

Each row is one change to line 18 in a scratch copy (`P/exa_id_forms/run_mutations.py` copies `mas_lab`, `rag_lab` and the three test support files to `work/`, applies the mutation, runs `tests/test_research.py`; output in `P/exa_id_forms/mutations.txt`). The real files are never mutated.

| mutation | result | failing tests (first ones) |
|---|---|---|
| none (control) | 47 passed | |
| no IGNORECASE | 10 failed | `are_blocked[p-7001]`, `[p7001]`, `[inv-2026-03]`, `[inc-311의]`, `[t-12는]`, `[p1000]`, three message cases |
| no ASCII | 10 failed | `are_blocked[P-7001을]`, `[p7001을]`, `[inc-311의]`, `[t-12는]`, `[고객P-7001은 환불]`; message cases incl. `INV-2026-03번` (message names `INV-2026-03번`) |
| no no-hyphen form (`P-\d+` only) | 5 failed | `are_blocked[P7001]`, `[p7001]`, `[p7001을]`, `[p1000]`, message `[p7001을]` |
| no digit floor (`\d+`) | 3 failed | `leave_ordinary_queries_alone[p99 latency]`, `[p50 지연]`, `[p999 latency]` |
| digit floor lowered to 3 (`\d{3,}`, extra row) | 1 failed | `leave_ordinary_queries_alone[p999 latency]` |
| P form dropped | 11 failed | `test_internal_queries_stay_inside[P-9002 환불]` (an old test) and ten new cases |

Every required mutation fails at least one test. Note that "no ASCII" does not fail the plain `INV-2026-03번` blocked case (still blocked, but with the particle in the name); only the message test catches that, which is why it exists.

That table did not include a mutation for the Unicode holes, which is why the regression got through.

## Record check (attempt 2)

Notebooks 00 and 06 are not rerun. Script: `P/exa_id_forms/record_check.py` (imports the shipped `INTERNAL_PATTERN`, compares with the old pattern text); output `P/exa_id_forms/record_check.txt`; the attempt 1 output is kept as `record_check_attempt1.txt`, and `diff` of the two is empty (every verdict is the same under the attempt 2 pattern).

A. Code cells (unexecuted notebooks `00-Setup.ipynb`, `06-Lab-Research-Agents.ipynb`): 16 query strings (00: 1, `LangGraph Send API`; 06: 15, cell 3 four, cell 6 three repro queries that are never sent (two are meant to be refused), cell 45 four, cell 47 four). All 722 string literals in the 42 code cells (00: 12 cells, 166 literals; 06: 30 cells, 556 literals) were compared old against new: newly blocked 0. The code cells of the three executed notebooks hold the same string literals as the current ones (differences 0). Cell 6's saved verdict text equals what the shipped code says now for all three rows (`['알파', 'P-9002']`, `['INV-2026-08']`, passes).

B. Saved model-written queries in `outputs/live/` (executed notebooks; the `.json` and `.usage.jsonl` files hold only timing and token counts, 0 query text): 21 unique full queries (06 base 10, 06 exercises 15, 4 in both) and 5 truncated tool-call fragments (2 base, 3 exercises). Newly blocked 0 of 21 and 0 of 5. None of the 21 is blocked by either the old or the new pattern.

LIMIT, stated plainly: the records do not store every model-written query. Parallel and serial runs each made `검색어 수: 6` searches but only their shared ones are printed (5 in the base record, 3 in the exercises record), so the rest of those strings are not stored. The optional and exercise runs in cells 34, 45 and 49 print no queries. The check covers what the records hold, not every query ever sent.

Result: NEWLY BLOCKED COUNT 0, so this check is passed.

## Suite result

- `tests/test_research.py`: `75 passed` (attempt 1: 47).
- Whole `tests/` (`../.venv/bin/python -B -m pytest tests -q -p no:cacheprovider`, output `P/exa_id_forms/suite_attempt2.txt`): `2 failed, 608 passed`. The 2 failures are `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]` and `[evidence.py]`, the expected red the author decided to keep until `Day02_new` settles. Not edited, not a finding. (The pass count also includes tests other nodes added since attempt 1, so it is not comparable with the 579 of attempt 1.)
- `ruff check mas_lab/exa.py tests/test_research.py`: one `I001` on the import block (the long `from mas_lab.research import ...` line), the same finding attempt 1 recorded; `import re` is placed in order and adds none. Left alone.

## Remaining limits (stated so nobody assumes more)

- Not blocked, unchanged from the old pattern: `P-7001a`, `p7001a` (a letter right after the digits); an id glued to the Kelvin sign U+212A, long s U+017F, `İ` or `ı`, e.g. `KP-7001`. Reason: under `re.IGNORECASE` the class `[A-Za-z0-9]` also matches those characters, so the lookarounds count them as id-extending. The old pattern passed the same strings (they are word characters). A scoped `(?-i:[A-Za-z0-9])` inside the lookarounds closes it (I ran it on `P-7001`); I did not ship it because the task asked for the plain ASCII class and the case is not a regression.
- Blocked on the safe side: `p12345`, `T-800 terminator`, `inv-test`, `p-99`, `step-1 pre-p-12`, `INV--` (hyphens only after `INV-`).
- Cosmetic: the error message names `INV-2026-` (trailing hyphen) for `INV-2026- 내역` and `INV-2026` for `INV-2026_03`.
- Meaning is not judged; `inv에 대한 설명` (no hyphen) stays open.

EXA id forms: done
