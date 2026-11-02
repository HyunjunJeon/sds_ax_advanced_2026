# Day02_new live audit (rewritten from fresh evidence, 2026-11-01)

Every result below was produced in this rewrite by reading the notebooks and `outputs/live/*.executed.ipynb`, or by running the command named. No earlier node report or earlier version of these notes is used as proof. Gold review and the 60-minute rehearsal remain human tasks and are NOT done (see (j)).

## Weakness by weakness

**(a) 05 바꿔보기 and own-documents 내 것 만들기: PASS.** `05-Production-Agentic-RAG.ipynb` has 5 `# [바꿔보기]` cells (8, 12, 23, 30, 48), each with one named input (`MAX_SEARCHES`, `MENU_ALLOWED`, `SKILL_TO_READ`, `AS_OF`, `START_LINE`); the minimum is 4. Executed cell 8: `2번째에서 멈춤: search 호출 한도를 초과했습니다.` The 내 것 만들기 pair on the student's own documents is cells 62-63 and is about leave policy, not SLA (cell 59-60 is the SLA pair). Executed 62: `적용 문서: ['leave-v2']`, `탈락 문서: ['leave-v1', 'lab-access']`. Executed 63: `status: answered`, `결정적 검증: passed`, `근거 문서: ['leave-v2']`.

**(b) 03 competing Skills and optional summary: PASS.** Cell 19 is a real 4 questions x 2 descriptions x 3 repeats table. Class executed copy: `합계(기대만 읽은 횟수): {'막연': 9, '구체': 12} / 12 회 중`. Optional copy: `{'막연': 8, '구체': 12}`. The vague set moves between runs (Q3 vague 3/3 vs 2/3) and the specific set does not. The optional path is real: `03-optional-copy.json` has `finished` True, `errors` [], 181 model calls, 393.9 s; its cell 46 printed 20 trigger rows and cell 47 printed 6 with/without-Skill rows. `outputs/live/03-optional.summary.md` exists. It is one run, so it shows 1 observation, not a rate.

**(c) 03 validated path after the SLA cell, budgets unchanged, `_LIST_MARKER` no longer blamed: PASS, with a recorded miss in the optional copy.**
- The fix: `rag_lab/answer.py:18` is now `^\s*\d+(?:단계|[.)](?!\d))`, so `99.` of `99.5%` is no longer a list number. `answer.py` is 150 non-blank lines, not more.
- Class executed copy (`outputs/live/03-Agent-Skills.executed.ipynb`): cell 37 ends `상태: error / 검증: failed / 오류: ['인용문에 없는 숫자: 20%', ...]`. That is a sentence linking `20%` to evidence `E-18da…`, which does not hold `20%`, so a genuine rejection and not the decimal bug (`99.0%` and `10%`, `15%` passed). Cell 40 then prints `전: error [...]` and `후: answered / 검증: passed / 오류: []`. This is the validated path.
- Optional copy (`03-optional-copy.executed.ipynb`): the order is reversed. Cell 37 `answered / passed`, cell 40 `후: error / 검증: failed / 오류: ['인용문에 없는 숫자: 20%', ...]`. So over the two live runs the fixed-question cell passed once and failed once. The cell prints no sentences, so I did not determine whether that failure is a genuine link error. Not hidden: the error row is stated here.
- `_LIST_MARKER` is not blamed in the current `03-Agent-Skills.ipynb` cells 38-39: cell 38 explains a wrong evidence link, cell 39 says to re-check whether the same error recurs. The executed copy's markdown is the earlier wording (markdown cells differ from the current notebook, code cells are equal); its cell 39 still says a leading decimal "can give the same false rejection". It is not blamed by name, but it is stale relative to the source.
- Budgets unchanged: `rag_lab/evidence.py:22-27` is 18 tool, 10 model, 3 search, 18 read, 24000 bytes, 180 s.

**(d) 04 hard sets, MRR, hashes, timetable: PASS.** Cell 33 loads `data/cases_hard.jsonl` and `data/cases_hard2.jsonl`; cell 37 prints recall@1,2,3 and MRR@3 per set (executed). `shasum -a 256` this run: cases_hard f70046bc631b6d69647282746fb90456b468d58b1b809efacd93a6f2c20d98e2, gold_hard 0fc6f50a9f32554147c9d8374cf904fa4435c1c2c64266fe05aad141aa943ce2, cases_hard2 38bb099996a4f575cb6d87b3c8c40098d3276bf970d5fc8c95d5f240cde48da1, gold_hard2 19926f25c15e41e337e562b70095b5883fb4af80d85dba528747a435371f2e2a. All four equal the required values. Executed MRR@3: hard bm25 0.962, dense 1.000, hybrid 1.000; hard2 bm25 0.659, dense 0.773, hybrid 0.727. Timetable in cell 0: 5,5,5,4,3,4,4,3,12 for sections 1-9, 직접 해보기 10, 확인 질문 3, 정리 2 (sum 60); the headings in cells 2-49 carry the same minutes. Limit: gold is a draft, 22 questions means one row moves a score by 0.045.

**(e) 06 back to back with 2 repeats, predictions compared: PASS.** Cell 43 `[전후 ask 번갈아 2회씩]` alternates 전1, 전2, 후1, 후2 per question over 3 questions, change `{'chunker': ('section', 'fixed')}`. Executed: 전 3/3 and 3/3, 후 3/3 and 3/3, `조건 차이(후 합계 - 전 합계): +0`, `예측: 나빠짐 | 실제: 같음 | 일치 여부: 불일치`, plus the line that the table cannot attribute a change to the condition. Model calls per run 10, 10, 9, 10, so the repeat noise is visible.

**(f) 02 and 06 prose substance: PASS.** Markdown characters this run: 02 is 7507, 06 is 7429, floor 7000. The two passages read in the sources earlier teach distinctions (02: the model asks and the application runs; 06: an answer-layer fault versus a scope-layer fault, and why budgets exist), not length. Only passages were read, not every sentence.

**(g) Cache writes, cost, class versus optional: PASS.** Usage logs: every log that has cache reads also has writes (00: 0 reads 3,872 writes; 01: 55,727 / 17,185; 02: 8,034 / 8,250; 03: 397,067 / 26,676; 05: 129,065 / 31,924; 06: 513,562 / 67,749; optional: 892,689 / 61,246; 04: 0 / 0). Writes total 216,902 tokens (class 155,656, optional 61,246), 0 on the 1-hour TTL. Independent recompute, own loop and price table (2.00 / 10.00 / 0.20 / 2.50 per million; uncached = input - read - write): class 00-06 is 224 calls, $1.0709; optional is 181 calls, $0.7864. `python tests/cost_report.py` prints 224 / 428.5 s / 1.0709 and the separate optional row 181 / 393.9 s / 0.7864. `README.md:91-92` and `AGENTS.md:179-180` carry the same numbers, the optional row is outside the class total, and `grep` for 하한/floor/바닥 in both files finds nothing.

**(h) `.deepeval`: PASS, with a caveat.** `git check-ignore -v Day02_new/.deepeval` answers `Day02_new/.gitignore:5:.deepeval/`. When I ran pytest from inside `Day02_new`, an empty `.deepeval/` appeared there (01:34). I removed that empty directory, and the gate-style run from the repo root (`pytest -q Day02_new/tests`, 187 passed) leaves none. So it is gone and ignored; running pytest with cwd `Day02_new` recreates an empty ignored directory.

**(i) Root docs pointers: PASS.** `git diff -U0 -- README.md AGENTS.md CURRICULUM.md`: 0 removed lines mention `Day02/`. Added lines are the `Day02_new` bullet, a table row and a `## Day02_new` section. `CURRICULUM.md` is untracked, so git shows no diff for it; it has the Day02_new pointer at line 11 and still has 5 `Day02/` mentions. The README and AGENTS diffs also hold unrelated earlier uv workspace edits.

**(j) Sheets: PASS.** `docs/gold_review_sheet.md:3` says it is not a human review and every row is `미검수` (37 lines contain it). `docs/rehearsal_sheet.md:5` says nobody has rehearsed, and `:8` says not to mark it complete before rehearsal. Gold review and the 60-minute rehearsal remain human tasks and are not done.

## Live evidence

- `uv run --no-sync pytest -q Day02_new/tests` from the repo root: 187 passed.
- `check_notebook.py`: `OK` for all seven (00 with `--minutes 10`, 01-06 with `--minutes 60`).
- `outputs/live/<stem>.json` for 00-06: `finished` True and `errors` [] for all seven (model calls 2, 24, 18, 82, 2, 24, 72). Executed code cells equal current code cells: True for all seven.
- Residue grep for `ScriptedChatModel|OfflineHashEmbeddings|DAY02_OFFLINE|CONNECTION_CHECK_LABEL|rag_script|live_cell|OPENROUTER|연결 확인` over `rag_lab`, `skills`, `README.md`, `AGENTS.md`, `.env.example`, `*.ipynb`: 0 hits. `rag_lab/__pycache__` holds no `offline` file.
- Module size, non-blank lines: agent 143, answer 150, corpus 107, embeddings 34, evaluation 52, evidence 142, retrieval 99, settings 99; all at most 150.
- `grep -rlE "sk-ant-[A-Za-z0-9_-]{6,}" . --exclude=.env` matched 0 files. `.env` was not read or printed.
- Floors: `tests/check_notebook.py:17` `{"cells": 36, "code": 16, "markdown": 7000}`, `MIN_MARKED_CELLS = 12`, 바꿔보기 minimum 4. The folder is untracked, so there is no git baseline; the values equal the task's.
- Status error rows in the final runs, all of them: 01 cell 28 `ToolMessage status=error` (a made-up tool name, a teaching case); 02 cells 15, 19, 37, 47 (schema validation errors shown on purpose); 03 class cell 37 and cell 40 `전: error` (the genuine link rejection above); 03 optional cell 40 `후: error` (see (c)) and cell 47 three `Skill 없음 상태=error 검증=failed` rows; 05 cell 14 `이 RAG에서 허용하지 않는 도구입니다: delete`, cell 54 `BudgetExceeded: model 호출 한도를 초과했습니다.`; 06 cell 35 the same budget error. The 05 and 06 budget errors are deliberate demonstrations, with the budget left unchanged.

## Falsification

Both in `mktemp` copies of `Day02_new` (without `.env` and `outputs`), deleted afterwards.
- Old list marker restored (`[.)](?!\d)` to `[.)]`): `1 failed, 1 passed`; `FAILED tests/test_rag_lab_answer.py::test_leading_decimal_is_not_a_list_marker` with `assert ['인용문에 없는 숫자: 5%'] == []`.
- Cache write parsing zeroed (`_cache_writes` returns 0): `3 failed, 184 passed`; `test_usage_log_appends_tokens_without_content`, `test_usage_log_records_five_minute_writes_from_real_shape`, `test_usage_log_records_one_hour_part_without_double_counting` failed.

## Audit for safe-but-wrong output

1. Requested and produced kinds: requested a validator fix with a test, cache writes from the real usage shape with pricing, all seven notebooks plus the 03 optional path re-run live, class and optional totals apart, docs without floor wording. Produced: all of those exist (7 executed copies, 8 usage logs, optional copy and summary, cost table in README and AGENTS). The one kind that is not clean is the 03 optional copy ending in a validation error in cell 40.
2. A 99.5%-style check with a value no notebook used (`97.3%`, absent from every notebook and `data/business`), one command on `_unsupported_numbers`: quote holds it gives `unsupported= []`; quote lacks it gives `unsupported= ['97.3%']`.
3. Blank input, 05 cell 60 with `MY_QUESTION = ""`: `안내: 앞 셀의 MY_QUESTION, MY_ENTITY, MY_AS_OF를 채운 뒤 실행하세요.`
4. The check that would have failed had the behavior been wrong: `test_leading_decimal_is_not_a_list_marker` (failed above with `['인용문에 없는 숫자: 5%']`) and the three usage-log tests. The 03 cell-40 path has no test, because it depends on a live model; only the executed record covers it, and that record is split 1 pass, 1 fail.
5. Shortfall: none against the assigned items. Open limits: the optional-copy cell 40 error, the stale markdown in the executed 03 copies, and the draft gold. Rehearsal and gold review remain human tasks.

## Correction and follow-up (2026-11-01, after this audit)

- **(c) was wrong about the cause.** `E-18da…` does hold `20%`. Run records show the rejected sentence is the one about amendment A-01, linked only to amendment evidence that has no `20%`. The rejection is still valid, but cells 38-39 are rewritten with this cause.
- **Repeat measure with one attempt:** the cell 37 question passed 6 of 6 and the cell 40 question 4 of 6. With both earlier runs and the later re-run, cell 37 is 7 of 9; cell 40 is 5 of 8. All failures in the repeat measure are numbers from another document in a sentence that does not link that document.
- **Cell 40 now re-asks the cell 37 question with `max_attempts=2`:** changing the question did not address a link fault. Validator and budgets are unchanged. With retry on, 14 runs over the two questions all passed; 5 of them passed only after a rejected first answer.
- **Fresh-reader review, then fixes:** a first-time read of all 313 cells gave 15 findings. Fixes went into 01-06. Open: 03 cell 34 and 04's missing 오인 example. Later done in 06: a free layer-practice table on hand-made records (cells 40-41), and a comparison that measures on the 36 hard questions with `mode: dense` as the default change (cell 45: missed rows 8 to 4 in retrieval, `ask` unchanged at 3/3, one run).
- **00-06 records on the final code:** 01-06 re-run live; 227 class calls, $1.1512. The cost lines above record the earlier run.
- **Known differences from executed copies:** 06 markdown cell 43 has one added sentence; `03-optional-copy` predates these edits.
- **05 with all five changed values:** a copy ran to the end with 0 cell errors. This was one run in a scratch folder, and its outputs are not in `outputs/live`.

## Correction (2026-11-01)

- Verification runs of the live notebooks repeated paid calls during the 2026-11-01 lesson run. The cost lines above therefore understate what was spent in total.
- The exact spend for those reruns cannot be recovered: `run_live.py` overwrites `outputs/live/*.usage.jsonl`, so only the last run of each notebook remains.
- The review pass alone made about 110 calls. The current per-notebook values (class total 236 calls, $1.2583) are in `tests/cost_report.py` output and in README and AGENTS; the same notebook varies between runs (05 was seen at 30 and 34 calls).

Live audit: PASS
