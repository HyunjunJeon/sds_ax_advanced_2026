# Sync copy notes (node sync-copy, 2026-11-02)

P = <P>

## What was done
- Saved the before state first: `P/sync-before/rag_lab/` (corpus, evidence, retrieval, settings, __init__), `P/sync-before/test_layout.py`, `P/sync-before/rag_lab-hashes.txt`.
- Copied `Day02_new/rag_lab/{corpus,retrieval,evidence,pipeline}.py` to `Day03_new/rag_lab/` with `cp`. `corpus.py` was already identical (its bytes did not change); `retrieval.py` and `evidence.py` were replaced; `pipeline.py` is new in Day03_new.
- `Day03_new/rag_lab/settings.py` untouched (sha256 d72fe2f6...acc4 before and after). No other module copied: `pipeline.py` imports only `rag_lab.corpus` and `rag_lab.retrieval` (Day02_new/rag_lab/pipeline.py:12-13); `evidence.py` imports `rag_lab.corpus`, `rag_lab.pipeline`, `rag_lab.retrieval` (Day02_new/rag_lab/evidence.py:13-15).
- `Day03_new/tests/test_layout.py:13`: parametrize list now `["corpus.py", "retrieval.py", "evidence.py", "pipeline.py"]`. The only changed line (diff against P/sync-before/test_layout.py is that one line; the line number did not move).

## Proof 1: tests
`cd Day03_new && ../.venv/bin/python -B -m pytest tests -q -p no:cacheprovider`
-> `611 passed in 6.18s`, 0 failed, 0 skipped, 0 deselected. All four `test_rag_lab_copies_are_byte_identical` cells (corpus, retrieval, evidence, pipeline) pass. Before the sync the suite had 610 tests with `2 failed, 608 passed` (Day03_new/AGENTS.md headnote); the one added parametrize cell makes 611.

Byte identity: `cmp Day02_new/rag_lab/$f.py Day03_new/rag_lab/$f.py` for corpus, retrieval, evidence, pipeline -> all four identical, exit 0.

## Proof 2: notebooks and audit
`.venv/bin/python -B Day03_new/tests/check_notebook.py <nb> --minutes N` (exit codes read from the command itself):
- 00-Setup.ipynb --minutes 10: `OK`, exit 0
- 01-Workflow-vs-Agent.ipynb --minutes 60: `OK`, exit 0
- 02-Agent-Architecture.ipynb --minutes 60: `OK`, exit 0
- 03-Four-Flows.ipynb --minutes 60: `OK`, exit 0
- 04-Graph-Engineering.ipynb --minutes 60: `OK`, exit 0
- 05-Choosing-Multi-Agent.ipynb --minutes 60: `OK`, exit 0
- 06-Lab-Research-Agents.ipynb --minutes 60: `OK`, exit 0

`.venv/bin/python -B Day03_new/tests/audit_live.py` -> last line `AUDIT OK`.

## Proof 3: equivalence on the real tree (no model, no EXA, no .env, no gold)
`.venv/bin/python -B P/sync_probe2.py Day03_new P/s2-after-sync.jsonl` ->
`Day03_new {'part1': 720, 'part2': 720, 'part3': 720, 'excluded2': 0, 'excluded3': 2689}`
Compared with the pre-sync baseline `P/s2-old.jsonl` (both 2280 lines; part order identical):

| part | what | rows old / new | identical | differing |
|---|---|---|---|---|
| 1 | one fresh context per query, limits 3/6/10 | 720 / 720 | 720 | 0 |
| 2 | one context, real byte limit 24000 (`Budget.max_context_bytes`, rag_lab/evidence.py:28) | 780 / 780 (720 searches + 60 event summaries) | 780 | 0 |
| 3 | limit 3000, forces the overflow path | 780 / 780 | 707 | 73 (result 67, context_bytes 67, events 6) |

Parts 1 and 2 are identical (1500 rows, 0 differences) -> required result met. Part 3 differs as allowed, on the overflow path: the new `_admit` (evidence.py:118) hands the ranked candidates to `fit_context` (pipeline.py:83), which drops from the lowest rank until the sum fits; the old code checked `_register` item by item. Of the 67 part-3 search rows whose result differs, status changed found->context_budget in 4 and context_budget->found in 4; the status stayed and the evidence count changed in 12 (7 fewer, 5 more); the status and count stayed in 47 (the other 6 differing lines are events summaries). The reasons for the 47 were not analysed. The limit 3000 itself held in both (max `context_bytes` 3000 old and new). part 3 is not claimed to be equal.

## Proof 4: outputs/runs
`find Day03_new/outputs/runs -type f | wc -l` -> 1893 before the copy, 1893 after the tests/check_notebook/audit/probe. (The repository-root `outputs/runs` does not exist; the 1893 files are in `Day03_new/outputs/runs`.)

## Proof 5: names the new code could break
- Test suite (proof 1) is green, so no mas_lab or tests name was broken.
- `grep -rn multi_query Day03_new --include='*.py' --include='*.ipynb'` (outputs excluded): 0 hits. `rerank_by_overlap`: 0 hits.
- RetrievalContext's removed `_register`: 0 call sites on a RetrievalContext. The remaining `_register` hits are other classes' methods: `Desk._register` (mas_lab/desk.py:59, called at desk.py:83,95,104 and mas_lab/gate.py:89,96) and `ExaClient._register` (mas_lab/exa.py:64,72), plus test names containing "registered" and the audit mutation table (docs/audit/tools/row_tables.py:26-28, which targets Desk._register in gate.py).
- `RetrievalContext._context_bytes` lost its `*extra` parameter; the only outside caller `mas_lab/runner.py:120` calls it with no arguments.
- Imports of rag_lab names in mas_lab/tests/notebooks: `Budget`, `BudgetExceeded`, `RetrievalContext`, `make_search_tools`, `Retriever`, `content_terms`, `tokenize`, `Scope`, `load_corpus`, `load_cases`, ... all still exist (tests green).

## New line numbers in the synced files
rag_lab/evidence.py: `BudgetExceeded` 18, `Budget` 23, `consume` 42 (`Budget.consume`), `RetrievalContext` 106, `make_search_tools` 173.
rag_lab/retrieval.py: `Retriever` 126.
Other moved or new names: `Budget.max_decision_calls` 30 (new field), `_listed_bytes` 69, `RetrievalContext._context_bytes` 115, `RetrievalContext._admit` 118 (replaces `_register`).
Old numbers (from AGENTS.md 4장): BudgetExceeded 17, Budget 22, consume 40, RetrievalContext 104, make_search_tools 162, Retriever 101.

## Proof 6: new hash baseline
`P/sync-code-hashes.txt`: 38 lines, `shasum -a 256` of every .py in Day03_new/mas_lab, Day03_new/rag_lab, Day03_new/tests (excluding __pycache__) plus `pyproject.toml` and `uv.lock` (paths from the repository root).
Against the previous baseline `P/c2-code-hashes.txt` (37 lines) exactly these differ: `Day03_new/rag_lab/evidence.py`, `Day03_new/rag_lab/retrieval.py` (changed), `Day03_new/rag_lab/pipeline.py` (new), `Day03_new/tests/test_layout.py` (changed). Every mas_lab file, `rag_lab/settings.py`, `rag_lab/corpus.py`, `rag_lab/__init__.py`, the other tests, `pyproject.toml` and `uv.lock` are byte-equal to the c2 baseline.

## Timestamps and part-3 precision (for the doc nodes)
- Sync time: rag_lab/corpus.py, retrieval.py, evidence.py, pipeline.py all have mtime 2026-11-02 09:13:10; tests/test_layout.py 2026-11-02 09:13:12. The execution records (outputs/live, outputs/runs) predate this sync.
- corpus.py bytes are unchanged (sha256 1deabc44...b110b9 in both c2-code-hashes.txt and sync-code-hashes.txt); only its mtime was refreshed by the `cp`. Use the hash files, not mtimes, for "what changed".
- Part 3: of the 67 differing search rows, 45 have an identical evidence-id list (the evidence returned is the same; the difference is in other result fields and context_bytes, which carry state from earlier searches in the same seed); 22 have a different id list. Root cause of the 22 is not analysed (the task allows part 3 to differ).

## Scope kept
Written: Day03_new/rag_lab/{evidence,retrieval,pipeline}.py (corpus.py rewritten with identical bytes), Day03_new/tests/test_layout.py (one line), and files under P. No model call, no EXA call, no .env read, no commit; Day02_new, Day03, Day07_new, root files, mas_lab, notebooks, rag_lab/settings.py unchanged.

Sync copy: PASS
