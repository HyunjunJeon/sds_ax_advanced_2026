# Worker refs precision (node worker-refs-precision)

Files changed in the project: `Day03_new/mas_lab/workers.py` and `Day03_new/tests/test_structures.py`. Nothing else. No model or EXA call was made (all tests use the scripted fake model). No `.env` value was read or printed.

## Mode
New behaviour, red before green. Seam: the public `checked_worker(task, desk, model)` and the `worker_checked` trace event, driven through the real `Desk` tools (`lookup_payments`, `lookup_availability`, `search_knowledge`) with the scripted model from `tests/fakes.py`, as the existing `checked_worker` tests do.

## Before (workers.py:147-166, copy kept in `worker_refs_precision/workers.before.py`)
```python
_TOOL_REF = re.compile(r'"(?:fact_ref|evidence_id)"\s*:\s*"([^"\\]+)"')

def checked_worker(task, desk, model):
    """hybrid의 Worker. 등록되지 않은 근거는 빼고, 근거가 빈 결과는 이 Worker 자신의 도구 결과로 채운다.

    desk는 병렬 Worker가 함께 쓰므로 채울 참조는 이 Worker의 메시지에서만 읽는다. 실패 결과는 그대로 돌려준다.
    """
    result, messages = _run_with_messages(task, desk, model, None, None, None)
    if result.status == "failed":
        return result
    known = desk.known_refs()
    kept = [r for r in result.evidence_refs if r in known]
    dropped = list(dict.fromkeys(r for r in result.evidence_refs if r not in known))
    own = dict.fromkeys(r for m in messages if isinstance(m, ToolMessage) for r in _TOOL_REF.findall(m.text))
    filled = list(own) if result.facts and not kept else []
    notes = [f"등록되지 않은 근거를 뺐습니다: {', '.join(dropped)}"] if dropped else []
    checked = result.model_copy(update={"evidence_refs": [*kept, *filled], "uncertainty": [*result.uncertainty, *notes]})
    desk.trace.event("worker_checked", task.task_id, problems=validate_result(checked, known), dropped=dropped, filled=len(filled))
    return checked
```

## After (workers.py:147-171)
```python
_TOOL_REF = re.compile(r'"(?:fact_ref|evidence_id)"\s*:\s*"([^"\\]+)"')
_TOKEN = re.compile(r"[A-Za-z0-9-]+")  # 근거 번호는 ASCII 영문·숫자·하이픈으로 이어진 한 덩이다. 한글 조사나 공백, 쉼표에서 끝난다.

def checked_worker(task, desk, model):
    """hybrid의 Worker. 라벨이 붙은 근거는 등록된 번호만 남기고 번호가 없는 근거는 빼며, 근거가 빈 결과는 이 Worker 자신의 도구 결과로 채운다.

    채울 때는 facts에 적은 번호를 먼저 쓰고 없으면 전부 쓴다. desk는 병렬 Worker가 함께 쓰므로 채울 참조는 이 Worker의 메시지에서만 읽는다. 실패 결과는 그대로 돌려준다.
    """
    result, messages = _run_with_messages(task, desk, model, None, None, None)
    if result.status == "failed":
        return result
    known = desk.known_refs()
    found = {r: [r] if r in known else [t for t in _TOKEN.findall(r) if t in known] for r in result.evidence_refs}
    kept = list(dict.fromkeys(i for ids in found.values() for i in ids))
    dropped = [r for r, ids in found.items() if not ids]
    recovered = len(set(kept) - set(result.evidence_refs))
    own = dict.fromkeys(r for m in messages if isinstance(m, ToolMessage) for r in _TOOL_REF.findall(m.text))
    named = {t for fact in result.facts for t in _TOKEN.findall(fact)}
    filled = ([i for i in own if i in named] or list(own)) if result.facts and not kept else []
    notes = [f"등록되지 않은 근거를 뺐습니다: {', '.join(dropped)}"] if dropped else []
    checked = result.model_copy(update={"evidence_refs": [*kept, *filled], "uncertainty": [*result.uncertainty, *notes]})
    desk.trace.event("worker_checked", task.task_id, problems=validate_result(checked, known), dropped=dropped, filled=len(filled), recovered=recovered)
    return checked
```
Line numbers now: `_TOKEN` 148, `def checked_worker` 151, the `worker_checked` event 169, `return checked` 170.

Non-blank lines of `mas_lab/workers.py`: 146 before, **150 after** (cap in `tests/test_layout.py:22` is 150, unchanged; it passes with zero headroom). The three budget-saving choices: `found` is a dict keyed by ref (dedupes `dropped` for free), `recovered` is one expression, the docstring keeps its three non-blank lines.

## Decisions on points the task left open (each is a Ruling in the report)
- `recovered` = number of kept ids the Worker never wrote as a ref of its own (`len(set(kept) - set(result.evidence_refs))`). A labelled ref that repeats an id already kept exactly adds 0; two labelled refs naming the same id add 1.
- A ref that is exactly registered is kept first (`[r] if r in known`), then tokens are tried. For every id the desk registers today the token path alone would give the same answer; the exact check is for a registered id with a character outside the token set (test below), where tokens alone would keep only its prefix.
- The facts-first fill keeps the order of `own` (tool-result order), not the order in which facts name the ids.
- A ref with one registered id and one unregistered token (`E-x, INC-311`) is rescued and the unregistered part is not named in the note (item 3 names only refs with no registered id).
- `_TOKEN` stops at `_`, `.`, `:` as well as Hangul, as the task said (letters, digits, hyphens only): `F-P-9001_b` is a token `F-P-9001` plus `b`.

## Tests added (24 cases, 12 test functions + 1 helper, all in `tests/test_structures.py`, lines 620-722; 103 lines added, 0 removed)
Helper `run_billing_worker` (:620) and table `LABELLED` (:627).
- `test_checked_worker_labelled_ref_keeps_the_registered_ids` (8 cases): label-prefix, particle-suffix, comma-pair, first-seen-order, mixed-with-exact, dedupe-exact-wins, dedupe-labelled-twice, exact-refs-recover-nothing. Each asserts refs, no note, dropped [], filled 0, `recovered`.
- `test_checked_worker_labelled_ref_matches_whole_tokens_only` (3): `결제 F-P-90012`, `XF-P-9001`, `F-P-9001-2` are not `F-P-9001`.
- `test_checked_worker_labelled_ref_keeps_an_exactly_registered_id_whatever_its_characters`: registers `F-P-9001_b` through the public `desk.fact_refs`.
- `test_checked_worker_labelled_ref_drops_a_longer_id_next_to_a_kept_one`
- `test_checked_worker_labelled_ref_without_a_registered_id_is_dropped_and_named` (`INC-311 장애` named, `runbook` not named).
- `test_checked_worker_labelled_ref_rescue_blocks_the_fill_even_when_facts_name_another_id`
- `test_checked_worker_labelled_ref_keeps_a_searched_evidence_id`: real `E-<12 hex>` from a real `search_knowledge` call, ref written as `runbook 탐지: E-…`, six ids registered, one kept, no fill.
- `test_checked_worker_fill_prefers_ids_named_in_facts` (2): one id before a Korean particle; own order not facts order.
- `test_checked_worker_fill_falls_back_to_all_own_ids_when_none_is_named_in_facts` (3): names nothing, longer id only (`F-P-90012`), unregistered id only (`INC-311`).
- `test_checked_worker_named_in_facts_ignores_ids_another_worker_registered` (2): an earlier outage Worker registered `F-AV-2026-08` on the same desk; facts naming it are not adopted.
- `test_checked_worker_named_in_facts_is_not_used_when_a_ref_was_kept`

### Existing tests edited
None. The existing `checked_worker` tests compare single event keys (`actor`, `problems`, `dropped`, `filled`), not the whole event, so the new `recovered` key outdated nothing. No test was deleted, skipped or weakened (`diff` of the file: 103 lines added, 0 removed). `tests/test_layout.py` and `Day03_new/rag_lab` were not touched.

## Red (old code, 22 of 24 fail; run in the scratch copy with `workers.before.py`)
Command (from `worker_refs_precision/Day03_new`): `.venv/bin/python -B -m pytest tests/test_structures.py -q -p no:cacheprovider -k 'labelled_ref or named_in_facts' --tb=line -rf` -> `22 failed, 2 passed, 171 deselected`. Failure list in `worker_refs_precision/red-24.txt`; the first run on the real tree (23 tests then) is `worker_refs_precision/red.txt` (`21 failed, 2 passed`). Typical messages:
```
AssertionError: assert (['F-P-9001', 'F-P-9002'], ...) == (['F-P-9001'], [])        # label-prefix: the old code dropped the labelled ref and filled both ids
AssertionError: assert ['F-P-9001', 'F-P-9002'] == ['F-P-9001']                     # rescue blocks the fill
AssertionError: assert (6 > 1 and ['E-ba32cdb66...7a6af68a6a76'] == ['E-24ccfa7ed1c5']  # real search: filled all six ids
AssertionError: assert ['F-P-9001', 'F-P-9002'] == ['F-P-9002']                     # facts name one id
KeyError: 'recovered'                                                                # event has no recovered key (exact-refs, fallback cases)
```
The 2 that pass on the old code are guards: `named_in_facts_ignores_ids_another_worker_registered[only-the-other-id]` (old code fills every own id, which is also the expected answer) and `named_in_facts_is_not_used_when_a_ref_was_kept`. Their sensitivity is shown by mutations M4 and M15 below. 12 of the 22 reds are `AssertionError`s on `evidence_refs` (wrong ids kept or filled); the other 10 fail on `KeyError: 'recovered'` (the key does not exist yet). No import error, no fixture error.

## Green
`-k 'labelled_ref or named_in_facts'` on the real tree: `24 passed, 171 deselected`. The 15 existing `checked_worker`, `run_worker`, hybrid writer/retry and parallel-worker tests (`-k '(checked_worker or run_worker or hybrid_writer or hybrid_retry or parallel_workers) and not labelled_ref and not named_in_facts and not fill_prefers and not fill_falls_back'`): 15 passed with the new code, unedited.

## Mutation proof (scratch copy `worker_refs_precision/Day03_new`, script `worker_refs_precision/mutate.py`, raw output `mutation.out`)
One mutation at a time on `workers.after.py`, full `tests/test_structures.py` (195 tests) run each time; the copy was restored and compared byte for byte at the end.

| # | Mutation | Result | First failing tests |
|---|---|---|---|
| M1 | substring match instead of whole token (`k in r`) | 5 failed | `matches_whole_tokens_only` x3, `drops_a_longer_id_next_to_a_kept_one`, `first-seen-order` (sorted order) |
| M2 | token charset includes Hangul | 3 failed | `particle-suffix`, `dedupe-exact-wins`, `fill_prefers_ids_named_in_facts[one-id-before-a-particle]` |
| M3 | recovery removed | 10 failed | all `labelled_ref_keeps_the_registered_ids` label/particle/comma/order/mixed/dedupe cases, rescue test, searched evidence id |
| M4 | adopt ids from `known` instead of `own` | 2 failed | `named_in_facts_ignores_ids_another_worker_registered` x2 |
| M5 | fill ignores facts | 2 failed | `fill_prefers...[one-id-before-a-particle]`, `ignores_ids_another_worker_registered[other-id-and-own-id]` |
| M6 | fallback removed | 15 failed | `fills_empty_refs...` x2, `fills_the_evidence_ids_a_search_returned`, `whole_tokens_only` x3, `falls_back...` x3, and more |
| M7 | `recovered` always 0 | 9 failed | label-prefix, particle-suffix, comma-pair, first-seen-order, mixed-with-exact, dedupe-labelled-twice, ... |
| M8 | dedupe removed | 2 failed | `dedupe-exact-wins`, `dedupe-labelled-twice` |
| M9 | note names rescued refs as dropped | 8 failed | all rescue cases (dropped is no longer `[]`) |
| M10 | `recovered = len(kept)` | 5 failed | `mixed-with-exact`, `dedupe-exact-wins`, `exact-refs-recover-nothing`, ... |
| M11 | fill still runs when only a labelled ref was rescued | 8 failed | label-prefix, particle-suffix, comma-pair, ... |
| M12 | exact-first check removed (tokens only) | 1 failed | `keeps_an_exactly_registered_id_whatever_its_characters` |
| M13 | facts matched by substring | 1 failed | `falls_back...[longer-id-only]` |
| M14 | facts tokens include Hangul | 1 failed | `fill_prefers...[one-id-before-a-particle]` |
| M15 | fill even when something was kept (`not kept` removed) | 15 failed | `named_in_facts_is_not_used_when_a_ref_was_kept`, `drops_unregistered_refs...[some-unregistered]`, label cases |

All 15 mutations are caught; M1-M9 are the nine the task listed.

## Suite
From `Day03_new`:
- With the deselect (`../.venv/bin/python -B -m pytest tests -q -p no:cacheprovider --deselect Day03_new/tests/test_layout.py::test_rag_lab_copies_are_byte_identical`): **579 passed, 3 deselected**.
- Without it: **580 passed, 2 failed**. The two failures are `tests/test_layout.py::test_rag_lab_copies_are_byte_identical[retrieval.py]` and `[evidence.py]` (the author's expected red; the third parameter, `corpus.py`, passes). Nothing else fails.
- The total (582) is higher than the 529 the previous node reported because sibling nodes running in parallel added tests; my share is 24.
- `test_layout.py::test_modules_stay_readable_in_class` passes with workers.py at 150 non-blank lines.

## Not covered / limits
- Replay of saved real rows is another node's job; this node's code was checked only against scripted models and a real search tool. In the real incident the refs were `runbook 탐지: E-fe73bd71207c`; the searched-evidence test uses that shape.
- A ref with an id glued to a letter or digit on either side (`XF-P-9001`) or followed by `_` is read by the token rule only; `F-P-9001_b` is covered only because it is registered exactly. An unregistered id with an underscore suffix that starts with a registered id (`F-P-9001_x`) is rescued as `F-P-9001`.
- Whether the writer cites the right documents after this change is not measured here; the earlier correlation (4 of 5 filled rows failing `인용 문서`) is still only a correlation.

Worker refs precision: done
