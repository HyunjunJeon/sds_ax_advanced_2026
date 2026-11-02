# Stale records notes (node worker-path-check)

Read-only. No model or EXA call, no `.env` opened or printed, `data/gold.jsonl` not read, nothing written outside P.
P = `<P>`
D = `<repo>/Day03_new`

## Verdicts (one per record group)

| record group (end times, 2026-11-01) | module changed after it | can the change alter what the record shows? |
|---|---|---|
| 01, 02, 03 (17:06 17:09 / 17:14 17:17 / 17:24 17:27) vs `workers.py` (19:39) | `checked_worker` rewritten, `_TOKEN` added | **No.** `run_worker` body and `_run_with_messages` are unchanged. `checked_worker` is reached only through `build_hybrid`, and none of these notebooks builds or runs hybrid. |
| 01, 02, 03 vs `gate.py` (19:24) | `_PAYMENT_ID`, `_named_payments` | **No.** The 12 rows written in these windows hold 4 distinct question strings with 0 payment-id tokens of any spelling; 02 and 03 call the gate with an empty question. |
| 06 (01:52, 02:06) vs `exa.py` (20:04) | `INTERNAL_PATTERN`, `assert_public_query` | **Not shown for every query.** 0 newly blocked among everything the record stores, but the record does not store every model-written query. So it could differ for a query that was never saved, and only in one direction: sent then, refused now. Stated plainly, not softened. |
| 00 (00:19) vs `exa.py`, `gate.py`, `workers.py` | `assert_public_query` is reachable (cell 17); `gate.py` and `workers.py` changes are not | **No.** The one query, `LangGraph Send API`, is not blocked by the old or the new pattern. |

## What each record ran with (so "older than" is a fact, not a guess)

Windows come from the cell metadata of the saved executed notebooks (`outputs/live/*.executed.ipynb`, `execution.iopub.execute_input` first cell to `shell.execute_reply` last cell, UTC converted to KST), not from file mtimes.

| executed notebook | first cell | last cell | rows in `outputs/runs` with mtime in the window |
|---|---|---|---|
| 00-Setup | 00:19:49 | 00:19:58 | 0 |
| 01 base | 17:03:40 | 17:06:01 | 6 |
| 01 exercises | 17:06:08 | 17:09:00 | 6 |
| 02 base | 17:12:45 | 17:14:31 | 0 |
| 02 exercises | 17:14:38 | 17:17:22 | 0 |
| 03 base | 17:22:59 | 17:24:49 | 0 |
| 03 exercises | 17:24:58 | 17:27:13 | 0 |
| 06 base | 01:48:47 | 01:52:05 | 10 (not written by 06, see below) |
| 06 exercises | 02:00:15 | 02:06:42 | 0 |

Copies of the code as it was when the records ran:

- `P/clone-src/Day03_new/mas_lab/` is the working tree copied at 17:03 (`P/clean-clone-notes.md` section 1), before notebook 01 started (17:03:40). Compared with the current tree, only `exa.py`, `gate.py` and `workers.py` differ; the other 10 files in `mas_lab` are byte-identical (`cmp`). Its three files: `workers.py` mtime 14:32:37 sha256 `426ebea3620c...`, `gate.py` mtime 16:36:20 sha256 `a559649a4d43...`, `exa.py` mtime 00:06:21 sha256 `12a90aca8a3a...`.
- `P/baseline/Day03_new/mas_lab/` (copied 13:57) holds the files with their original mtimes: `workers.py` 23:55:01, `exa.py` 00:06:21, `contracts.py` 00:04:51, `research.py` 00:06:21, `desk.py`, `ledger.py`, `trace.py`, `view.py` Oct 31 23:5x. These are all older than 00:19, so this is what 00 and 06 ran with for those files. `P/clean/Day03_new/mas_lab/runner.py` (mtime 00:01:15, sha256 `0a621514ad00...`) is the `runner.py` that 00 and 06 ran with.
- Current hashes of the three modules are the same as in `P/c2-code-hashes.txt` (20:27): `gate.py` `16c50d6ee3ecaf2c`, `workers.py` `2fde59e593fb7660`, `exa.py` `c8f238a968aadfaf`. Nothing moved after 20:27, and records 04 (20:28 to 20:32) and 05 (20:38 to 21:06) are newer than all three.

## 1. 01, 02, 03 against `workers.py`

### 1a. The before-copy exists and the diff

The before-copy exists: `P/worker_refs_precision/workers.before.py` (9895 bytes, copied 19:38:33). Also `workers.after.py` (10486 bytes, 19:40:29) and a full tree copy under `P/worker_refs_precision/Day03_new/` (its `mas_lab/workers.py` is the current file; I did not open its `.env`). `cmp`: `workers.after.py` == current `D/mas_lab/workers.py`; `workers.before.py` == `P/clone-src/Day03_new/mas_lab/workers.py`, the 17:03 copy that 01, 02 and 03 ran against. So the before-copy is the code the records ran with, not a later one.

`diff workers.before.py D/mas_lab/workers.py` gives 16 changed lines (`<` and `>` lines) in 6 hunks of the normal diff format, all inside `checked_worker` (`D/mas_lab/workers.py:151-170`) plus one new line:

- added `_TOKEN = re.compile(r"[A-Za-z0-9-]+")` at `workers.py:148`
- docstring lines 152 and 154 reworded
- lines 160-163: `kept` and `dropped` now come from `found` (labelled refs such as an id inside text are reduced to the registered ids in them), and a new `recovered` count
- lines 165-166: when `kept` is empty, `filled` prefers the ids named in `facts` (`named`) and falls back to all of the worker's own ids
- line 169: the `worker_checked` trace event gets `recovered=`

AST comparison of top-level definitions (before-copy against current): changed `['checked_worker']`, added `['_TOKEN']`, removed `[]`. Every other function is byte-equal as a definition: `contract_prompt`, `allowlist_middleware`, `TrackedSkillsBackend`, `_role_tools`, `make_worker`, `_run_with_messages` (`:118`), `run_worker` (`:141`), `subagent_spec`, `delegation_spans`.

**The body of `run_worker` did not change.** The diff has no hunk in lines 141-146. (Against the older 23:55:01 version in `P/baseline`, `run_worker` was refactored at 14:32:37 into a call to `_run_with_messages(...)[0]` with the same failed results; that is older than the 17:03 copy, so 01, 02 and 03 already ran with it. 00 and 06 do not call `run_worker`; see sections 3 and 4.)

### 1b. `checked_worker` has one caller

`grep -n checked_worker D/mas_lab/*.py`: definition `workers.py:151`, import `hybrid.py:18`, calls `hybrid.py:90` (the `worker` node) and `hybrid.py:110` (the `retry` node). Confirmed, no other call site. A text search over `*.py`, `*.ipynb`, `*.md` in `D` outside `outputs/` and `tests/test_*.py` finds nothing else; the other hits are the 32 lines in `tests/test_structures.py`. No notebook has `checked_worker` in a code cell. `build_hybrid` is `hybrid.py:45`; `runner.py:84-86` builds it only when `structure == "hybrid"`.

### 1c. Which notebooks' code cells reach `build_hybrid`, `run_case('hybrid', ...)` or `checked_worker`

Read with `json` and `ast` over every code cell (Call nodes and imports), not grep on prose. Cell numbers are 0-based `cells[i]`.

| notebook | `build_hybrid` | `run_case("hybrid", ...)` | `checked_worker` | what it does instead |
|---|---|---|---|---|
| 00-Setup | no | no | no | `make_desk` (cells[16]); `ExaClient.search` (cells[17]) |
| 01-Workflow-vs-Agent | no (not imported) | no: `run_case("single", ...)` cells[17] and cells[39]; `run_grid(["single"], ...)` cells[36] | no | `run_worker` cells[22]. `from mas_lab.hybrid import ROLE_GOALS` only (cells[1]) |
| 02-Agent-Architecture | no | no (no `run_case`) | no | `build_single`, `build_supervisor`, `build_handoff` from `structures`; `run_worker` cells[50]; `gate_answer` cells[5] and cells[35] |
| 03-Four-Flows | no | no (no `run_case`) | no | `run_worker` cells[27] and cells[53]; `gate_answer` cells[54]. `from mas_lab.hybrid import ROLE_GOALS, ROLES` only (cells[1]) |
| 06-Lab-Research-Agents | no | no | no | `run_research`, `assert_public_query` |

So **none of 00, 01, 02, 03, 06 calls any of the three**. Importing `mas_lab.hybrid` (01, 03) or `mas_lab.runner` (00, 01, 02, 03) imports `workers.py` and runs only its definitions; it does not run `checked_worker`. The notebooks that do build hybrid are 04 (cells[3], [51]) and 05 (cells[1], [33]), which are newer than `workers.py`.

Searches made through `run_worker` in 01, 02, 03 use the unchanged `run_worker`/`_run_with_messages`, `contract_prompt`, `allowlist_middleware` and `make_worker`.

**Verdict:** the saved 01, 02, 03 records cannot differ because of `workers.py`.

Korean sentence for the documents:
01·02·03 기록은 workers.py 수정 앞 기록이며, 수정된 것은 `checked_worker`(`Day03_new/mas_lab/workers.py:151`)와 새 `_TOKEN`(`workers.py:148`)뿐이고 `run_worker`(`workers.py:141`)와 `_run_with_messages`(`workers.py:118`)의 본문은 그대로이며, `checked_worker`는 `Day03_new/mas_lab/hybrid.py:90`과 `hybrid.py:110`에서만 불리는데 이 세 노트북의 코드 셀은 `build_hybrid`도 `run_case("hybrid", ...)`도 `checked_worker`도 부르지 않아 기록이 달라지지 않습니다.

## 2. 01, 02, 03 against `gate.py`: the payment-id spelling

### 2a. The only behaviour change

`diff P/gate_id_forms/gate.before.py D/mas_lab/gate.py`: `_PAYMENT_ID` (`gate.py:13`) went from `(?<![A-Za-z0-9-])P-\d+` to `(?<![A-Za-z0-9-])[Pp](?:-|(?=\d{4,}(?![A-Za-z0-9])))(\d+)`, and `_named_payments` (`gate.py:18-19`) now returns `{f"P-{digits}" ...}`. AST: changed `['_PAYMENT_ID', '_named_payments']`, nothing added or removed, against both `gate.before.py` and `P/clone-src/.../gate.py` (same sha256 `a559649a4d43...`, mtime 16:36:20, so it is the gate that 01, 02, 03 ran with). The pattern is read only inside `_named_payments`, which is called from `refund_decision` (`gate.py:25`) and `check_named_payment` (`gate.py:54`), always on the question. `_named_payments("")` is the empty set under both patterns.

### 2b. The line from `replay-4-notes.md`

`P/replay-4-notes.md:97` (section "Spelling scan of the questions the replay used"): "120 id-like tokens in the 422 questions with the wide scan `(?<![A-Za-z0-9-])[Pp]-?\d+`; all 120 are the old `P-<digits>` form, none is `p7001`, `P7001`, `p-7001` or a word like `p99`. So the new spellings cannot move any saved row, and the identical result above is expected."
And `P/replay-4-notes.md:93`: "Rows 422, flips 0, text replaced 0, text appended 51, `gate_skipped` rows 59 (50 + 9), ledger writes 0, automatic check pass 410 before and 410 after (342 + 68)."

### 2c. My own count for the 01, 02, 03 windows

The replay set (422 rows) is every real row in `outputs/runs`, known case, no saved refund proposal. It covers only part of the 01 rows, so I counted from the saved rows themselves.

- Rows written in the six windows: **12**, all from 01 (6 base, 6 exercises). 02 and 03 wrote **0** rows: their code cells have no `run_case` or `run_grid` call.
- Question strings: 12 rows, 12 question strings, **4 distinct** (`서비스 크레딧 신청 기한은 언제까지인가요?`, `결제가 두 번 됐어요. 취소하고 보상안도 함께 확인해 주세요.` (used for both `adhoc-3` and `complex-double-pay`), `법인카드 포인트로 보상받는 규정이 있나요?`, `지난달 장애 때문에 환불도 되나요?`). Source: the Human message saved in the row's `messages` for 10 rows; the 2 `budget_exceeded` rows (`3c8dd61a`, `33f9832c`) saved no messages, so their question is the `complex-double-pay` entry in `data/cases.jsonl`, and it is the same string as the others. The saved Human text equals the case text for all 10 (no truncation).
- Scan with the wide pattern `(?<![A-Za-z0-9-])[Pp]-?\d+` and the looser `[Pp]-?\d+` anywhere: **0 tokens in 12 of 12 strings**. So the number using a spelling other than `P-<digits>` is **0**; the number using `P-<digits>` is also 0. None of the four strings has a Latin letter or a digit.
- Which of the 12 the replay covered: 4 replayed (`simple-deadline` x2, `insufficient-no-policy` x2). 8 were outside the 422: `adhoc-3` x2 and `adhoc-4` x2 (case not in `cases.jsonl`), `complex-double-pay` `needs_approval` x2 (saved a refund proposal), `complex-double-pay` `budget_exceeded` x2 (no final answer). The 4 with refund proposals go through `refund_decision`, which also reads `_named_payments(question)`; their question has no id, so `named` is empty under both patterns and `refund_decision` returns the `check_refund` decision unchanged (`gate.py:25-26`).
- 02 and 03: `gate_answer(final, desk, request_id=...)` is called without `question` (02 cells[5] and cells[35], 03 cells[54]); the default is `""` (`gate.py:32`), so the pattern has no input.

The saved questions in the records therefore have no spelling the old gate read differently from the new gate. Reasoning, not just the replay: the gate is a pure function of (final answer, desk, question), the question string has no payment-id token of any spelling, and `_named_payments` returns the same empty set both before and after.

Korean sentence for the documents:
01·02·03 기록은 gate.py 수정 앞 기록이며, 수정된 것은 결제 번호 철자 패턴 `_PAYMENT_ID`(`Day03_new/mas_lab/gate.py:13`)와 그것을 쓰는 `_named_payments`(`gate.py:18`)뿐인데, 이 구간에 쓰인 행 12개의 질문 문자열 4종에는 어떤 철자의 결제 번호도 없고 02·03은 질문 없이 `gate_answer`를 불러(`gate.py:32`) 패턴이 읽을 입력이 없으며, 저장된 질문 120개가 모두 `P-<숫자>`였고 422행에서 뒤집힌 행이 0이었다는 `P/replay-4-notes.md:97`·`:93`과도 맞아 기록이 달라지지 않습니다.

## 3. 06 (and the exa part of 00) against `exa.py`

### 3a. The change

`diff P/exa_id_forms/exa.before.py D/mas_lab/exa.py`: `INTERNAL_PATTERN` (`exa.py:18`) from `\b(?:P-\d+|INV-[\w-]+|INC-\d+|T-\d+)\b` to `(?<![A-Za-z0-9])(?:P(?:-\d+|\d{4,})|INV-(?:[A-Za-z0-9-]+|[\w-]+)|INC-\d+|T-\d+)(?![A-Za-z0-9])` with `re.IGNORECASE`, plus the docstring of `assert_public_query` (`exa.py:30-32`). `DEFAULT_BLOCKED` (`exa.py:19`) is unchanged. `exa.before.py` has sha256 `12a90aca8a3a...`, the same as the file in the 17:03 copy and in `P/baseline` (mtime 00:06:21), so it is the code that 00 (00:19) and 06 (01:52, 02:06) ran with. `assert_public_query` is called from `ExaClient.search` (`exa.py:49`), so every EXA search goes through it. `make_exa_tool` (`exa.py:81`) and the rest are unchanged.

### 3b. The record check, quoted

`P/exa_id_forms/record_check.txt` (and `P/exa-id-forms-notes.md:208-214`, section "Record check (attempt 2)"):

- "00-Setup.ipynb: code cells 12, string literals 166, query strings 1, newly blocked among all literals 0"
- "06-Lab-Research-Agents.ipynb: code cells 30, string literals 556, query strings 15, newly blocked among all literals 0"
- notes line 208: "16 query strings (00: 1, `LangGraph Send API`; 06: 15, cell 3 four, cell 6 three repro queries that are never sent (two are meant to be refused), cell 45 four, cell 47 four). All 722 string literals in the 42 code cells ... were compared old against new: newly blocked 0."
- notes line 210: "21 unique full queries (06 base 10, 06 exercises 15, 4 in both) and 5 truncated tool-call fragments (2 base, 3 exercises). Newly blocked 0 of 21 and 0 of 5. None of the 21 is blocked by either the old or the new pattern."
- record_check.txt end: "NEWLY BLOCKED COUNT: 0"; notes line 214: "Result: NEWLY BLOCKED COUNT 0, so this check is passed."

Its stated limit (notes line 212), verbatim: "LIMIT, stated plainly: the records do not store every model-written query. Parallel and serial runs each made `검색어 수: 6` searches but only their shared ones are printed (5 in the base record, 3 in the exercises record), so the rest of those strings are not stored. The optional and exercise runs in cells 34, 45 and 49 print no queries. The check covers what the records hold, not every query ever sent."

### 3c. My own repeat (independent of that script)

I extracted both patterns from `exa.before.py` and the current `exa.py` with `ast` (no import) and compared them. String constants in the code cells of `00-Setup.ipynb` (166) and `06-Lab-Research-Agents.ipynb` (556), and of the three executed notebooks (same counts, 166 / 556 / 556): the verdict differs old against new in **0** of the 722 distinct-cell literals of the two source notebooks and in 0 of the literals of the executed copies. Over the whole saved output text of the executed notebooks, the new pattern finds an id the old one does not in exactly one place: the design-log line `T-1001은 중복 결제와 환불 대상 ...` printed by 06 cell 38 (`read_design_log()`), in the base and the exercises record. That is a displayed log, not a search query (06 passes `assert_public_query` only for the strings in cells 3 and 6 and for what the model writes into `web_search`). It is also the intended new block (an id followed by a Korean particle), so I list it as "would be refused if a model copied it into a query; no saved query contains it".

### 3d. What 06 can and cannot show

06 reaches the changed code only through `assert_public_query` (cells[3], [6] directly; every `run_research` search through `ExaClient.search`, `exa.py:49`). The rest of its import closure is unchanged: `research.py` (mtime 00:06:21), `contracts.py`, `trace.py`, `view.py`, `workers.allowlist_middleware` and `workers.DENY_WRITES` (equal as definitions between the 23:55:01 version and now), `rag_lab/*` (unchanged since 00:06:51). It never calls `run_worker`, `gate_answer`, `check_named_payment`, `build_hybrid` or `run_case`.

**It could differ.** Everything the record stores passes. A model-written query that the record did not store, for example one containing `p7001` or `P-9002을`, would have been sent in the record and would be refused now. The record gives no sign of such a query, but it cannot rule it out for the searches whose strings were not printed. The documents must say "the stored queries" and not "all queries".

The direction of any difference is one-way: a query that went out then and is refused now. Nothing the old pattern refused passes now. Evidence: `P/exa-id-forms-notes.md:134` ("no sample is blocked by the old pattern and passed by the new one"), and my own check of 400000 random strings built from id fragments, Hangul, digits, `_`, `-`: old blocks and new passes in **0**, new blocks and old passes in 30214 (the intended new blocks). That is a test, not a proof, but the two patterns read the same way: the new look-around only asks for no ASCII letter or digit next to the id, which is weaker than `\b`, and the new pattern is case-insensitive.

Rows in `outputs/runs` that fall in 06's base window (10 rows, 01:49:52 to 01:52:03: `single_skills`, `hybrid` x4, `single` x4, `supervisor`) were not written by 06, because 06 has no `run_case` call; another process was running then. They are not part of the 06 record.

Korean sentence for the documents:
06은 exa.py 수정 앞 기록이며, 기록에 남은 코드 셀 질의 문자열 16개와 모델이 쓴 질의 21개와 조각 5개 가운데 새 `INTERNAL_PATTERN`(`Day03_new/mas_lab/exa.py:18`)이 새로 막는 것은 0개이지만, `P/exa_id_forms/record_check.txt`의 한계대로 기록이 모델이 쓴 질의를 전부 저장하지는 않아(병렬·직렬 실행은 6회 검색 중 공유한 일부만 출력) 저장되지 않은 질의는 `assert_public_query`(`exa.py:30`)가 다르게 판정했을지 확인할 수 없고, 달라질 수 있는 방향은 기록 당시 나간 질의가 지금은 막히는 쪽뿐이며 옛 패턴이 막던 것이 지금 통과하는 경우는 없습니다.

## 4. 00 against all three

00 (00:19:49 to 00:19:58) has 12 code cells. Imports from the three modules and calls:

- cells[5]: `rag_lab.settings` (`key_status`, `make_model`, `require_exa_key`, `require_key`), `mas_lab.view.show_table`. No call into `gate`, `workers` or `exa`.
- cells[16]: `mas_lab.runner.make_desk`, `ModelMeter`, `message_table`, `create_deep_agent` with `desk.tools("billing")`. `make_desk` (`runner.py`) builds `Desk(...)`, `Budget(**FIXED_BUDGET)`, `Trace`. `desk.py`, `rag_lab/*` and `FIXED_BUDGET` are unchanged. 00 does not call `run_worker`, `checked_worker`, `gate_answer`, `check_named_payment`.
- cells[17]: `ExaClient(max_searches=1, ...).search("LangGraph Send API")`. This is the only changed function it reaches: `ExaClient.search` -> `assert_public_query` (`exa.py:49`, `exa.py:30`). The query is not blocked by the old pattern or the new one (`record_check.txt` section A, "cell 17 old=False new=False  LangGraph Send API"; my repeat agrees), so the search goes out exactly as it did.

`gate.py` did not exist as a file at 00:19 (the gate was in `structures.py`); 00 imports `mas_lab.runner`, which imports `structures` and `hybrid`, but only defines their functions. The `runner.py` that 00 ran with (`P/clean/Day03_new/mas_lab/runner.py`, 00:01:15) differs from the current one only in `_run_turns` and the new `_note_ungated_proposal` (`diff` + AST: changed `['_run_turns']`, added `['_note_ungated_proposal']`); `make_desk`, `build_retriever`, `case_scope` and `FIXED_BUDGET` are equal. `_run_turns` is called from `run_case`, which 00 does not call.

**Verdict:** the saved 00 record cannot differ because of `gate.py`, `workers.py` or `exa.py`.

Korean sentence for the documents:
00은 gate.py·workers.py·exa.py 수정 앞 기록이며, 코드 셀이 닿는 수정 함수는 `ExaClient.search`(`Day03_new/mas_lab/exa.py:49`)가 부르는 `assert_public_query`(`exa.py:30`) 하나뿐이고 그 질의 `LangGraph Send API`는 옛 패턴도 새 `INTERNAL_PATTERN`(`exa.py:18`)도 막지 않으며, `make_desk`(`Day03_new/mas_lab/runner.py`)만 부르므로 `gate.py`의 `_PAYMENT_ID`(`gate.py:13`)와 `workers.py`의 `checked_worker`(`workers.py:151`)에는 닿지 않아 기록이 달라지지 않습니다.

## 5. Things the premise did not list (for the documents' wording)

- 00 and 06 are older than more files than the three modules named. Mtimes of the files changed after 02:06 (the end of 06): `hybrid.py` 02:50:34 (copies exist), then 09:28:29 and 14:32:37; `runner.py` 09:28:29 and 15:40:14; `structures.py` 09:28:57, 14:32:37 and 14:44:48; `workers.py` 14:32:37 (adds `delegation_spans`, `_run_with_messages`, `checked_worker`; `run_worker` body moved into `_run_with_messages`); `gate.py` is absent from the 13:57 baseline (the gate code lived in `structures.py` there) and present in the 17:03 copy with mtime 16:36:20. I checked each against what 00 and 06 call: none of them is reached (sections 3d and 4). The earliest copy of `hybrid.py` in P has mtime 02:50:34, so the version that existed at 00:19 and 02:06 is not in P; it does not matter because neither notebook builds hybrid. A document sentence that says "only gate.py, workers.py and exa.py changed after 00 and 06" would be false; the true sentence is "none of the later changes is reached by these notebooks".
- 01, 02, 03 (17:06 to 17:27) were run after the 14:32 to 16:36 changes, so only the three late edits (19:24, 19:39, 20:04) matter for them.
- A run of `run_worker` in 01, 02, 03 uses the code that existed then. The `checked_worker` rewrite (19:39) is invisible to them because hybrid was never run.

## Not proved

- The 17:03 copy is a copy, not a log of the file at every second. I rely on the mtimes (`workers.py` 14:32:37, `gate.py` 16:36:20, both before 17:03; the current mtimes 19:39:35 and 19:24:45 are later) and on `workers.before.py` (19:38:33) being byte-equal to the 17:03 copy. A change and restore between 17:03 and 19:38 that left the same bytes would be invisible and would not matter.
- Window membership of rows is by file mtime inside the executed-notebook window (+2 s at the end). Rows written by another process in the same minutes would be counted; none appeared in the 01 windows (all 12 are `single` rows of the 01 cases), and 02 and 03 windows had 0.
- 06: unstored model-written queries, as stated in section 3d.
- The 06 base window contains 10 rows by another process (section 3d). I did not look at which process wrote them.

Stale records: done
