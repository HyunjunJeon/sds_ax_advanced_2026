"""rows.py: the row table for falsify 7 (the 172 injected rows of falsify 6, every one still applied unchanged after Day03_new/rag_lab was synced with Day02_new/rag_lab, plus sy01 and sy02). Falsify 6 had added n14 to n17, gi01 to gi13, ex01 to ex15, wp01 to wp14 and adapted t11, w02, w08, n01 to n04 where gate.py or workers.py had moved. Each row = a fresh copy + exactly one injected defect (one or more edits to ONE file) + the tests that must fail.

ROWS[id] = dict(label=..., file=<relative to Day03_new>, edits=[(old, new)], nb_edits=[(cell id, old, new)] (edits inside ONE notebook cell's source; file = the notebook),
                expect=[test-name substrings that must be among the failed ids], env={...extra env}, kind="pytest" | "notebook" | "clean", note=...)
Upstream mutation points (gate_dev, refs_dev, budget_dev, gate_id_forms, exa_id_forms, worker_refs_precision) come from row_tables.py, which holds those scripts' own tables, so the strings are theirs.
"""
from __future__ import annotations

import row_tables

H, S, G, R, W = "mas_lab/hybrid.py", "mas_lab/structures.py", "mas_lab/gate.py", "mas_lab/runner.py", "mas_lab/workers.py"
C, L = "mas_lab/contracts.py", "mas_lab/ledger.py"
LINECAP = "test_modules_stay_readable_in_class"
DEAD_PROXY = {"HTTPS_PROXY": "http://127.0.0.1:9", "ALL_PROXY": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9",
              "https_proxy": "http://127.0.0.1:9", "all_proxy": "http://127.0.0.1:9", "http_proxy": "http://127.0.0.1:9"}

ROWS: dict[str, dict] = {}


def add(rid, label, file, edits, expect=(), env=None, kind="pytest", note="", nb_edits=()):
    assert rid not in ROWS, rid
    ROWS[rid] = dict(id=rid, label=label, file=file, edits=list(edits), nb_edits=list(nb_edits), expect=list(expect), env=env or {}, kind=kind, note=note)


ROWS["clean"] = dict(id="clean", label="none (clean copy)", file=None, edits=[], nb_edits=[], expect=[], env={}, kind="clean", note="")

# ---------------------------------------------------------------- rows 1 to 15b (earlier pass; adaptations stated in note)
add("1", "contracts.py merge_results: `if task_id in merged and merged[task_id] != result:` -> `if False:`", C,
    [("if task_id in merged and merged[task_id] != result:", "if False:")], ["test_merge_results_rejects_conflict_and_accepts_same_value"])
add("2a", "contracts.py join_results: `elif result.status != \"complete\":` -> `elif result.status not in (\"complete\", \"failed\"):`", C,
    [('elif result.status != "complete":', 'elif result.status not in ("complete", "failed"):')], ["test_join_results_exposes_missing_failed_and_latest_attempt"])
add("2b", "contracts.py ready: `not buckets[\"failed\"] and not buckets[\"missing\"]` -> `not buckets[\"missing\"]`", C,
    [('"ready": not buckets["failed"] and not buckets["missing"]', '"ready": not buckets["missing"]')], ["test_join_results_is_not_ready_for_a_failure_alone_or_a_missing_task_alone"])
add("2c", "contracts.py ready -> `not buckets[\"failed\"]`", C,
    [('"ready": not buckets["failed"] and not buckets["missing"]', '"ready": not buckets["failed"]')], ["test_join_results_is_not_ready_for_a_failure_alone_or_a_missing_task_alone"])
add("3", "contracts.py trim_payload drops evidence_refs before quotes", C,
    [('    while size() > max_bytes and payload["quotes"]:', '    while size() > max_bytes and payload["evidence_refs"]:\n        dropped.append("근거:" + payload["evidence_refs"].pop())\n    while size() > max_bytes and payload["quotes"]:')],
    ["test_trim_payload_keeps_refs_and_uncertainty_until_the_end"])
add("4", "ledger.py check_refund: `if proposal.amount > APPROVAL_THRESHOLD:` -> `if False:`", L,
    [("if proposal.amount > APPROVAL_THRESHOLD:", "if False:")], ["test_gate_decisions", "test_needs_approval_waits_and_executes_once_when_approved"])
add("5", "ledger.py execute_approved: `(decision.decision == \"needs_approval\" and approved)` -> `(decision.decision == \"needs_approval\")`", L,
    [('(decision.decision == "needs_approval" and approved)', '(decision.decision == "needs_approval")')], ["test_execute_only_when_permitted", "test_needs_approval_waits_and_executes_once_when_approved"])
add("6", "ledger.py PaymentLedger.refund: `record = self.find(idempotency_key)` -> `record = None`", L,
    [("record = self.find(idempotency_key)", "record = None")], ["test_lost_response_duplicates_without_key_and_not_with_key"])
add("7", "hybrid.py dispatch/worker: one Send carries all tasks, worker loops over them (line count kept)", H,
    [("""        return [Send("worker", {"task": WorkerTask(task_id=r, goal=f"{ROLE_GOALS[r]}\\n고객 요청: {state['question']}",
                                                   allowed_tools=sorted(ROLE_TOOLS[r])).model_dump()}) for r in roles]""",
      """        return [Send("worker", {"task": [WorkerTask(task_id=r, goal=f"{ROLE_GOALS[r]}\\n고객 요청: {state['question']}",
                                                     allowed_tools=sorted(ROLE_TOOLS[r])).model_dump() for r in roles]})]"""),
     ("""        task = WorkerTask.model_validate(state["task"])
        return {"results": {task.task_id: checked_worker(task, desk, model).model_dump()}}""",
      """        tasks = [WorkerTask.model_validate(t) for t in state["task"]]
        return {"results": {t.task_id: checked_worker(t, desk, model).model_dump() for t in tasks}}""")],
    ["test_hybrid_workers_overlap_in_time"], note="ADAPTED: the worker node now calls checked_worker (was run_worker); same two-line shape, line count kept")
add("7b", "research.py build_research_graph: one Send for all subtopics, worker loops", "mas_lab/research.py",
    [("""            sub = SubTopic.model_validate(state["subtopic"])
            return {"findings": {sub.id: _worker_run(sub, {}, client=client, model=model, budget=budget, per_worker=per_worker, inputs=inputs)}}""",
      """            subs_ = [SubTopic.model_validate(s) for s in state["subtopic"]]
            return {"findings": {sub.id: _worker_run(sub, {}, client=client, model=model, budget=budget, per_worker=per_worker, inputs=inputs) for sub in subs_}}"""),
     ('lambda _: [Send("worker", {"subtopic": s.model_dump()}) for s in plan.subtopics]', 'lambda _: [Send("worker", {"subtopic": [s.model_dump() for s in plan.subtopics]})]')],
    ["test_parallel_research_workers_overlap_in_time"])
add("8", "desk.py: `\"billing\": [lookup_payments],` -> `[lookup_payments, *search],`", "mas_lab/desk.py",
    [('"billing": [lookup_payments],', '"billing": [lookup_payments, *search],')], ["test_roles_have_fixed_tools"])
add("9", "desk.py: `lookup_availability(month: str)` -> `(month: str, entity: str = \"\")`", "mas_lab/desk.py",
    [("def lookup_availability(month: str) -> dict:", 'def lookup_availability(month: str, entity: str = "") -> dict:')], ["test_no_tool_lets_the_model_widen_the_scope"])
add("10a", "desk.py: new line `GOLD_ROWS = (ROOT / \"data\" / \"gold.jsonl\").read_text(...)`", "mas_lab/desk.py",
    [("def load_billing(entity: str) -> list[dict]:", 'GOLD_ROWS = (ROOT / "data" / "gold.jsonl").read_text(encoding="utf-8")\n\n\ndef load_billing(entity: str) -> list[dict]:')],
    ["test_only_evaluation_module_touches_the_answer_key"])
add("10b", "rag_lab/settings.py: new line `GOLD_PATH = ROOT / \"data\" / \"gold.jsonl\"`", "rag_lab/settings.py",
    [("def load_settings", 'GOLD_PATH = ROOT / "data" / "gold.jsonl"\n\n\ndef load_settings')], ["test_only_evaluation_module_touches_the_answer_key"])
add("11", "exa.py assert_public_query: `if found:` -> `if False:` (run behind the dead proxy 127.0.0.1:9)", "mas_lab/exa.py",
    [('    if found:\n        raise ValueError(f"내부 정보가 든 질의는 외부로 보내지 않습니다: {found}")', '    if False:\n        raise ValueError(f"내부 정보가 든 질의는 외부로 보내지 않습니다: {found}")')],
    ["test_internal_queries_stay_inside", "test_blocked_query_never_reaches_the_network"], env=DEAD_PROXY)
add("12", "exa.py allowed_url: hostname equality/suffix -> `any(d in url for d in domains)`", "mas_lab/exa.py",
    [('return any(parts.hostname == d or parts.hostname.endswith("." + d) for d in domains)', "return any(d in url for d in domains)")], ["test_allowed_url_rejects_lookalikes"])
add("13", "rag_lab/corpus.py docstring `조각으로` -> `조각으루` (Day02_new copy untouched)", "rag_lab/corpus.py",
    [("조각으로 나눈다", "조각으루 나눈다")], ["test_rag_lab_copies_are_byte_identical"])
add("14", "01-Workflow-vs-Agent.ipynb first code cell gets `model = ScriptedChatModel(steps=[])` (checked by tests/check_notebook.py)", "01-Workflow-vs-Agent.ipynb",
    [], ["check_notebook.py"], kind="notebook")
add("15a", "hybrid.py: Router schema `HybridRoute` -> `Route` in the structured call", H,
    [("route = structured_call(desk, model, HybridRoute,", "route = structured_call(desk, model, Route,")],
    ["test_hybrid_router_offers_only_the_paths_the_graph_routes"], note="ADAPTED: the call moved into structured_call(desk, model, <schema>, ...); same schema swap")
add("15b", "hybrid.py: `path: Literal[\"fast\", \"slow\"]` -> `Literal[\"fast\", \"slow\", \"out_of_scope\"]`", H,
    [('    path: Literal["fast", "slow"]', '    path: Literal["fast", "slow", "out_of_scope"]')], ["test_hybrid_router_offers_only_the_paths_the_graph_routes"])

# ---------------------------------------------------------------- rows 16 to 23b (earlier M1 to M8b; the gate code now lives in gate.py)
add("16", "gate.py check_named_payment: probe never runs (`if not (claims_a_block or \"환불\" in question):` -> `if True:`)  [earlier M1]", G,
    [('    if not (claims_a_block or "환불" in question):', "    if True:")], ["test_first_payment_without_proposal_is_denied_by_the_code_gate"],
    note="ADAPTED (falsify 5): the single probe became a probe per named payment inside check_named_payment, and this run moved the `not checkable` exits into two branches above, so the early return that skips every probe is now the guard `if not (claims_a_block or 환불)`; same defect, line-neutral")
add("17", "gate.py check_named_payment: every probe also goes to execute_approved(..., approved=True)  [earlier M2]", G,
    [('    decisions = {decision.decision for decision in probes.values()}',
      '    decisions = {decision.decision for decision in probes.values()}\n    for pid, d in probes.items():\n        execute_approved(Proposal(action="refund", payment_id=pid, amount=payments[pid]["amount"]), d, desk.ledger, approved=True)')],
    ["test_refundable_payment_without_proposal_is_reviewed_and_never_written"], note="ADAPTED: written for the per-payment probes; gate.py has room under the line cap")
add("18", "gate.py check_named_payment: payment ids read from final.text instead of the question  [earlier M3]", G,
    [("desk.payments()}, _named_payments(question)", "desk.payments()}, _named_payments(final.text)")], ["test_payment_is_read_from_the_question_not_the_answer_text"],
    note="ADAPTED: the extraction moved into _named_payments(question); the injection swaps its argument at the no-proposal call site")
add("19", "gate.py _settle: replaced text keeps the model text (`\"text\": \" \".join(notes)` -> `\"text\": final.text`)  [earlier M4]", G,
    [('"text": " ".join(notes), "uncertainty": notes', '"text": final.text, "uncertainty": notes')], ["test_first_payment_without_proposal_is_denied_by_the_code_gate"],
    note="ADAPTED: the line moved from structures.py to gate.py and is now a dict entry in `update |= {...}`; same defect")
add("20", "gate.py _settle: idempotency dropped (`fresh = list(notes)`, `if True:`)  [earlier M5]", G,
    [("fresh = [note for note in notes if note not in final.uncertainty]\n    if fresh or outcome != final.outcome:", "fresh = list(notes)\n    if True:")], ["test_checking_twice_adds_nothing"],
    note="ADAPTED: file moved from structures.py to gate.py; injection text unchanged")
add("21", "gate.py check_named_payment: `answered` also counts as a label the code blocked (claims_a_block widened)  [earlier M6]", G,
    [("final.outcome in _BLOCKED.values()", 'final.outcome in {*_BLOCKED.values(), "answered"}')], ["test_other_outcomes_naming_a_payment_are_untouched"],
    note="ADAPTED: behavior deliberately changed. A refund question under `answered` is now overruled; the surviving invariant is that a question without the word 환불 leaves other labels untouched. The widening acts on `answered` without that word")
add("22", "hybrid.py gate node: check_named_payment call removed  [earlier M7]", H,
    [('final = check_named_payment(FinalAnswer.model_validate(state["final"]), desk, state["question"])', 'final = FinalAnswer.model_validate(state["final"])')],
    ["test_hybrid_graph_alone_checks_the_named_payment"])
add("23a", "runner.py graph path: `question=turns[-1]` removed  [earlier M8a]", R,
    [("request_id=run_id, question=turns[-1]) if final else None\n    app =", "request_id=run_id) if final else None\n    app =")],
    ["test_hybrid_run_ends_denied_with_one_probe_and_no_unchecked_note", "test_handoff_run_checks_the_named_payment"])
add("23b", "runner.py agent path: `question=turns[-1]` removed  [earlier M8b]", R,
    [("request_id=run_id, question=turns[-1]) if final else None\n\n\ndef _note_ungated_proposal", "request_id=run_id) if final else None\n\n\ndef _note_ungated_proposal")],
    ["test_first_payment_without_proposal_is_denied_by_the_code_gate", "test_run_checks_the_question_of_the_last_turn"],
    note="ADAPTED (falsify 5): the anchor after the agent path's `return gate_answer(...)` was `def _finish`; this run inserted `_note_ungated_proposal` between them, so the anchor is now `def _note_ungated_proposal`; same removal")

# ---------------------------------------------------------------- new rows named in the task (one injection per behavior)
add("t01", "gate.py refund_decision: a mismatched allow keeps `allow` (not raised to needs_approval)", G,
    [('return GateDecision(decision="needs_approval", reasons=[*decision.reasons, reason])', "return GateDecision(decision=decision.decision, reasons=[*decision.reasons, reason])")],
    ["test_refund_decision_compares_the_proposal_with_the_named_payment", "test_proposal_for_another_payment_waits_for_approval"])
add("t02", "gate.py check_named_payment: only the first named payment is probed (`sorted(named)` -> `sorted(named)[:1]`)", G,
    [("for payment_id in sorted(named)}", "for payment_id in sorted(named)[:1]}")], ["test_two_named_payments"])
add("t03", "gate.py check_named_payment: one deny among several probes gives `denied` (`decisions == {\"deny\"}` -> `\"deny\" in decisions`)", G,
    [('"denied" if decisions == {"deny"} else "human_review"', '"denied" if "deny" in decisions else "human_review"')], ["test_two_named_payments"])
add("t04", "gate.py _settle: the appended code reason removed (`if blocked else []` -> `if False else []`)", G,
    [("not in final.text] if blocked else []", "not in final.text] if False else []")], ["test_same_label_with_a_wrong_reason_gets_the_code_reason_appended"])
add("t05", "gate.py check_named_payment: the 환불 word no longer triggers a check (`claims_a_block or \"환불\" in question` -> `claims_a_block`)", G,
    [('not (claims_a_block or "환불" in question)', "not claims_a_block")], ["test_refund_question_under_another_label_is_overruled"])
add("t06", "gate.py _settle: stale model uncertainty kept on a replaced answer (`\"uncertainty\": notes,` removed)", G,
    [('"uncertainty": notes, ', "")], ["test_overrule_drops_stale_model_lines_and_a_none_action_proposal"])
add("t07", "gate.py _settle: an action-none proposal is kept on a replaced answer", G,
    [('"proposal": final.proposal if final.proposal and final.proposal.action == "refund" else None', '"proposal": final.proposal')],
    ["test_overrule_drops_stale_model_lines_and_a_none_action_proposal"])
add("t08", "gate.py _notes: payment id dropped from the replaced text (`return list(decision.reasons)`)", G,
    [("""return [f"{payment_id or '결제 번호 없음'}: {reason}" for reason in decision.reasons]""", "return list(decision.reasons)")],
    ["test_first_payment_without_proposal_is_denied_by_the_code_gate"])
add("t09", "gate.py check_named_payment: execute_approved called from a probe (no approval argument)", G,
    [('    decisions = {decision.decision for decision in probes.values()}',
      '    decisions = {decision.decision for decision in probes.values()}\n    for pid, d in probes.items():\n        execute_approved(Proposal(action="refund", payment_id=pid, amount=payments[pid]["amount"]), d, desk.ledger)')],
    ["test_two_named_payments_with_one_allow_are_reviewed_and_never_written"])
add("t10", "workers.py checked_worker: fills empty refs from the shared desk (`desk.fact_refs`) instead of the Worker's own messages", W,
    [("own = dict.fromkeys(r for m in messages if isinstance(m, ToolMessage) for r in _TOOL_REF.findall(m.text))", "own = dict.fromkeys(desk.fact_refs)")],
    ["test_parallel_workers_do_not_get_each_others_refs"])
add("t11", "workers.py checked_worker: unregistered refs kept (`kept = list(result.evidence_refs)`)", W,
    [("kept = list(dict.fromkeys(i for ids in found.values() for i in ids))", "kept = list(result.evidence_refs)")], ["test_checked_worker_drops_unregistered_refs_and_names_them"],
    note="ADAPTED (falsify 6): old `kept = [r for r in result.evidence_refs if r in known]` is gone (a labelled ref is now recovered token by token through `found`); the same defect is now the `kept = list(dict.fromkeys(...))` line replaced by `kept = list(result.evidence_refs)`")
add("t12", "hybrid.py router: model call bypasses structured_call, so the Budget no longer counts it (line-neutral)", H,
    [("route = structured_call(desk, model, HybridRoute,", 'route = model.with_structured_output(HybridRoute, method="json_schema").invoke(')],
    ["test_router_and_triage_calls_count_against_the_model_budget"])
add("t13", "structures.py handoff triage: model call bypasses structured_call, so the Budget no longer counts it", S,
    [("route = structured_call(desk, model, Route,", 'route = model.with_structured_output(Route, method="json_schema").invoke(')],
    ["test_router_and_triage_calls_count_against_the_model_budget"])
add("t14", "structures.py build_supervisor: `, *delegation_spans(desk.trace)]` -> `]` (no worker span per delegated task)", S,
    [(", *delegation_spans(desk.trace)]", "]")], ["test_supervisor_run_records_a_worker_span_per_delegated_task_and_they_overlap"])
add("t15", "tests/conftest.py runs_in_tmp: `monkeypatch.setattr(\"mas_lab.runner.ROOT\", tmp_path)` -> `pass` (rows go to the copy's outputs/runs)", "tests/conftest.py",
    [('monkeypatch.setattr("mas_lab.runner.ROOT", tmp_path)', "pass")], ["test_a_run_writes_its_row_under_tmp_and_not_into_the_saved_runs"],
    note="CHECK: files written in the COPY's Day03_new/outputs/runs must be > 0 here and 0 in every row whose redirect is intact")
add("t16", "structures.py handoff resume: `\"proposal\": None` removed from the new-turn update (followup-handoff fix reverted)", S,
    [('"handoffs": 0, "notes": "", "proposal": None}', '"handoffs": 0, "notes": ""}')],
    ["test_new_customer_turn_is_not_relabelled_by_the_refund_proposed_in_the_earlier_turn"])


# ---------------------------------------------------------------- extra rows: every upstream mutation point (read from the upstream scripts)
for label, rel, old, new in row_tables.GATE_DEV:
    num = label.split()[0][1:]
    add(f"g{num}", f"gate_dev {label}  [{rel}: {old.strip()[:60]!r} -> {new.strip()[:60]!r}]".replace("\n", " "), rel, [(old, new)])

OWN = row_tables.OWN
for i, (label, rel, edits) in enumerate(row_tables.REFS_DEV, 1):
    fixed = [((o if n is not None else OWN), (n if n is not None else o)) for o, n in edits]
    add(f"w{i:02d}", f"refs_dev {label}", rel, fixed)

for i, (label, rel, old, new) in enumerate(row_tables.BUDGET_DEV, 1):
    edits = [(old, new)]
    if label == "span serialized by a lock":
        edits = [("import re\n", "import re\nimport threading\n"), ("ROLE_TOOLS: dict", "LOCK = threading.Lock()\nROLE_TOOLS: dict"), (old, new)]
    add(f"b{i:02d}", f"budget_dev {label}", rel, edits)

# followup-handoff: the carry inside one turn (the fix must keep it)
add("f01", "structures.py handoff: the proposal carried within one turn dropped (`\"proposal\": carried` -> `\"proposal\": None`)", S,
    [('"handoffs": state.get("handoffs", 0) + 1, "proposal": carried,', '"handoffs": state.get("handoffs", 0) + 1, "proposal": None,')],
    ["test_handoff_inside_one_turn_keeps_the_proposal_for_the_owner_who_answers"])
add("f02", "structures.py owner_node: the turn-1 proposal is the fallback for a turn that has none (`state.get(\"proposal\")` fallback removed)", S,
    [('else state.get("proposal")', "else None")], ["test_handoff_inside_one_turn_keeps_the_proposal_for_the_owner_who_answers"])


# ---------------------------------------------------------------- n01 to n13: silent corners A and B, notebook import and source-slice guard (the changes made before falsify 5)
# An `expect` entry "a&&b" means ONE failed test id must contain both parts (function name and the injected parameter text).
def matches(entry: str, test_id: str) -> bool:
    return all(part in test_id for part in entry.split("&&"))


GATE_SKIP = '            desk.trace.event("gate_skipped", "code", named=unchecked)'
GATE_GUARD = 'if "환불" in question and not any(event["kind"] == "gate_skipped" and event["named"] == unchecked for event in desk.trace.events):'
add("n01", "gate.py check_named_payment: the gate_skipped event of the non-blocking branch is not recorded (`desk.trace.event(\"gate_skipped\", ...)` -> `pass`)", G,
    [(GATE_SKIP, "            pass")],
    ["test_refund_question_without_only_known_payments_leaves_other_labels_silent", "test_hybrid_run_records_one_gate_skipped_for_an_unchecked_refund_question",
     "test_gate_skipped_event_leaves_the_row_as_the_model_wrote_it"])
add("n02", "gate.py check_named_payment: that event on every call, not once per desk (dedupe `and not any(event[\"kind\"] == \"gate_skipped\" ...)` removed)", G,
    [(GATE_GUARD, 'if "환불" in question:')],
    ["test_second_call_on_an_unchecked_refund_question_adds_no_second_event", "test_hybrid_run_records_one_gate_skipped_for_an_unchecked_refund_question"])
add("n03", "gate.py check_named_payment: that event also for a question without 환불 (`\"환불\" in question and` removed)", G,
    [(GATE_GUARD, 'if not any(event["kind"] == "gate_skipped" and event["named"] == unchecked for event in desk.trace.events):')],
    ["test_question_without_refund_leaves_no_event_even_when_the_code_could_not_check_it"])
add("n04", "gate.py check_named_payment: that branch also appends `_UNCHECKED` to the answer's uncertainty (`return final` -> `return final.model_copy(update={\"uncertainty\": [*final.uncertainty, _UNCHECKED]})`)", G,
    [(GATE_SKIP + "\n        return final\n", GATE_SKIP + '\n        return final.model_copy(update={"uncertainty": [*final.uncertainty, _UNCHECKED]})\n')],
    ["test_refund_question_without_only_known_payments_leaves_other_labels_silent", "test_gate_skipped_event_leaves_the_row_as_the_model_wrote_it"])
add("n05", "runner.py _run_turns: earlier_turn_proposal_ungated not recorded in the handoff loop (`_note_ungated_proposal(...)` -> `pass`)", R,
    [('            if structure == "handoff":  # hybrid 그래프는 turn마다 스스로 게이트를 지난다.\n                _note_ungated_proposal(desk, final, index, len(turns))',
      '            if structure == "handoff":  # hybrid 그래프는 turn마다 스스로 게이트를 지난다.\n                pass')],
    ["test_handoff_records_the_refund_proposal_of_an_earlier_turn_that_no_gate_saw", "test_ungated_event_leaves_the_row_as_the_owner_wrote_it"])
add("n06", "runner.py _run_turns: not recorded in the single, single_skills and supervisor loop (`_note_ungated_proposal(...)` -> `pass`)", R,
    [('        row["messages"] = message_table(messages)\n        _note_ungated_proposal(desk, final, index, len(turns))', '        row["messages"] = message_table(messages)\n        pass')],
    ["test_agent_loop_records_the_refund_proposal_of_an_earlier_turn&&single]", "test_agent_loop_records_the_refund_proposal_of_an_earlier_turn&&single_skills", "test_agent_loop_records_the_refund_proposal_of_an_earlier_turn&&supervisor"])
add("n07", "runner.py _note_ungated_proposal: also recorded for the last turn (`index < turn_count - 1` -> `index < turn_count`)", R,
    [("if index < turn_count - 1 and final", "if index < turn_count and final")],
    ["test_last_turn_proposal_goes_through_the_gate_and_leaves_no_ungated_event"])
add("n08", "runner.py _run_turns: also recorded for hybrid (`if structure == \"handoff\":` -> `if True:`)", R,
    [('            if structure == "handoff":  # hybrid 그래프는 turn마다 스스로 게이트를 지난다.', "            if True:  # hybrid 그래프는 turn마다 스스로 게이트를 지난다.")],
    ["test_hybrid_gates_every_turn_in_its_graph_and_gets_no_ungated_event"])
add("n09", "runner.py _note_ungated_proposal: recorded for a proposal whose action is none (`and final.proposal.action == \"refund\"` removed)", R,
    [('final and final.proposal and final.proposal.action == "refund":', "final and final.proposal:")],
    ["test_turn_without_a_refund_proposal_leaves_no_ungated_event"])
add("n10", "02-Agent-Architecture.ipynb cell cd44b5d8: the source slice regains the end marker (`source.index(\"def gate_answer\")`; the function now lives in gate.py)", "02-Agent-Architecture.ipynb", [],
    ["test_source_slice_marker_exists_in_source&&source.index('def gate_answer')"],
    nb_edits=[("cd44b5d8", 'print(source[source.index("OWNER_TOOLS ="):])', 'print(source[source.index("OWNER_TOOLS ="):source.index("def gate_answer")])')])
add("n11", "05-Choosing-Multi-Agent.ipynb cell e545d437: imports a name that mas_lab.hybrid does not have (`from mas_lab.hybrid import build_hybrid, no_such_helper`)", "05-Choosing-Multi-Agent.ipynb", [],
    ["test_notebook_import_resolves&&no_such_helper"],
    nb_edits=[("e545d437", "from mas_lab.hybrid import build_hybrid\n", "from mas_lab.hybrid import build_hybrid, no_such_helper\n")])
add("n12", "06-Lab-Research-Agents.ipynb cell a5f89ff5: graph_source slice marker not in the source (`\"    if chained:\"` -> `\"    if chained_no_such:\"`)", "06-Lab-Research-Agents.ipynb", [],
    ["test_source_slice_marker_exists_in_source&&graph_source.index('    if chained_no_such:')"],
    nb_edits=[("a5f89ff5", 'graph_source.index("    if chained:")', 'graph_source.index("    if chained_no_such:")')])
add("n13", "04-Graph-Engineering.ipynb cell aaa85b65: a new `.index(` slice on an unmapped variable (`hybrid_text.index(\"def build_hybrid\")`)", "04-Graph-Engineering.ipynb", [],
    ["test_source_slice_marker_exists_in_source&&hybrid_text.index('def build_hybrid')"],
    nb_edits=[("aaa85b65", "print(inspect.getsource(build_hybrid))\n", 'hybrid_text = inspect.getsource(build_hybrid)\nprint(hybrid_text[hybrid_text.index("def build_hybrid"):])\n')])


# ---------------------------------------------------------------- falsify 6: rows whose old text moved are adapted here (same behaviour, new text); every adapted row carries an ADAPTED (falsify 6) note
def adapt(rid: str, note: str, edits=None, label=None) -> None:
    row = ROWS[rid]
    if edits is not None:
        row["edits"] = list(edits)
    if label is not None:
        row["label"] = label
    row["note"] = (row["note"] + " " if row["note"] else "") + note


NEW_W2 = ("kept = list(dict.fromkeys(i for ids in found.values() for i in ids))", "kept = list(result.evidence_refs)")
adapt("w02", "ADAPTED (falsify 6): old text `kept = [r for r in result.evidence_refs if r in known]` is gone (labelled refs are recovered token by token through `found`); the same defect is now the `kept = list(dict.fromkeys(...))` line replaced by `kept = list(result.evidence_refs)`", edits=[NEW_W2])
NEW_W8 = ("filled = ([i for i in own if i in named] or list(own)) if result.facts and not kept else []", "filled = []")
adapt("w08", "ADAPTED (falsify 6): old text `filled = list(own) if result.facts and not kept else []` is gone (the fill now prefers the ids the facts name); the same defect is now that line replaced by `filled = []`", edits=[NEW_W8])
for _rid in ("n01", "n02", "n03", "n04"):
    adapt(_rid, "ADAPTED (falsify 6): the non-blocking branch of check_named_payment now writes `desk.trace.event(\"gate_skipped\", \"code\", named=unchecked)` and its dedupe also compares the sorted number list (`event[\"named\"] == unchecked`); the injection works on those new lines")

# ---------------------------------------------------------------- n14 to n17: the blocked-label branch of check_named_payment and the per-set dedupe (gate.py changed after falsify 5)
add("n14", "gate.py check_named_payment: the dedupe of the gate_skipped event ignores the number list (`and event[\"named\"] == unchecked` removed), so an earlier event for another list hides this one", G,
    [(GATE_GUARD, 'if "환불" in question and not any(event["kind"] == "gate_skipped" for event in desk.trace.events):')],
    ["test_later_turn_naming_another_unchecked_set_leaves_its_own_event"])
BLOCKED_BRANCH = '        return _settle(final, desk, final.outcome, [_UNCHECKED], blocked=False, events=[("gate_skipped", {"named": sorted(named)})])'
add("n15", "gate.py check_named_payment: a blocking label the code could not check records no gate_skipped event (`events=[(\"gate_skipped\", ...)]` -> `events=[]`)", G,
    [(BLOCKED_BRANCH, BLOCKED_BRANCH.replace('events=[("gate_skipped", {"named": sorted(named)})]', "events=[]"))],
    ["test_event_from_a_blocked_label_counts_only_for_the_same_set"])
add("n16", "gate.py check_named_payment: a blocking label the code could not check gets its answer text changed (`blocked=False` -> `blocked=True`, so the _UNCHECKED sentence is appended to the model text)", G,
    [(BLOCKED_BRANCH, BLOCKED_BRANCH.replace("blocked=False", "blocked=True"))],
    ["test_event_from_a_blocked_label_counts_only_for_the_same_set"])
add("n17", "gate.py check_named_payment: a blocking label the code could not check says nothing (`[_UNCHECKED]` -> `[]`: no note, no event)", G,
    [(BLOCKED_BRANCH, BLOCKED_BRANCH.replace("[_UNCHECKED]", "[]"))],
    ["test_event_from_a_blocked_label_counts_only_for_the_same_set"])

# ---------------------------------------------------------------- gi01 to gi13: the gate's payment-number pattern (mutation list row_tables.GATE_ID_FORMS)
ALL_SAME = "test_payment_id_spellings_all_name_the_same_payment"
WHICH = "test_payment_id_spellings_decide_which_numbers_the_gate_names"
ORDINARY = "test_payment_id_spellings_that_are_ordinary_words_do_not_hold_back_an_allowed_refund"
GI_EXPECT = {"R1": [ALL_SAME], "R2": [ALL_SAME], "R3": [WHICH, ORDINARY], "R4": [WHICH], "R5": [ALL_SAME], "R6": [WHICH], "B1": [WHICH], "B2": [WHICH], "B3": [WHICH],
             "B4": [ALL_SAME], "B5": [ALL_SAME], "B6": [WHICH], "B7": [ALL_SAME]}
for _i, (_label, _old, _new) in enumerate(row_tables.GATE_ID_FORMS, 1):
    add(f"gi{_i:02d}", f"gate.py payment-number pattern/normalisation, {_label}  [phase3/gate_id_forms]", G, [(_old, _new)], GI_EXPECT[_label.split()[0]])

# ---------------------------------------------------------------- ex01 to ex15: the EXA internal-id pattern (mutation list row_tables.EXA_ID_FORMS)
_BLOCKED = "test_internal_id_spellings_are_blocked"
_PARTICLE = "test_internal_id_spellings_message_names_the_id_without_the_particle"
_ORDINARY = "test_internal_id_spellings_leave_ordinary_queries_alone"
_OLD = "test_internal_id_spellings_keep_everything_the_old_pattern_blocked"
EX_EXPECT = [[_BLOCKED], [_BLOCKED], [_BLOCKED], [_BLOCKED], [_ORDINARY], [_OLD], ["test_internal_queries_stay_inside"], [_BLOCKED + "&&customer_P-7001"], [_PARTICLE],
             [_BLOCKED], [_PARTICLE], [_ORDINARY], [_BLOCKED], [_BLOCKED + "&&INC-311"], [_BLOCKED + "&&T-12"]]
_ex_mut = [(n, l) for n, l in row_tables.EXA_ID_FORMS if not n.startswith("none")]
assert len(_ex_mut) == len(EX_EXPECT) == 15
for _i, ((_name, _line), _expect) in enumerate(zip(_ex_mut, EX_EXPECT), 1):
    add(f"ex{_i:02d}", f"exa.py INTERNAL_PATTERN, {_name}  [phase3/exa_id_forms; run behind the dead proxy 127.0.0.1:9]", "mas_lab/exa.py", [(row_tables.GOOD, _line)], _expect, env=DEAD_PROXY)

# ---------------------------------------------------------------- wp01 to wp14: the labelled-reference recovery and the named-first fill (mutation list row_tables.WORKER_REFS)
_LAB = "test_checked_worker_labelled_ref_keeps_the_registered_ids"
WP_EXPECT = {"M1": ["test_checked_worker_labelled_ref_matches_whole_tokens_only"], "M2": [_LAB + "&&particle-suffix"], "M3": [_LAB + "&&label-prefix"],
             "M4": ["test_checked_worker_named_in_facts_ignores_ids_another_worker_registered"], "M5": ["test_checked_worker_fill_prefers_ids_named_in_facts"],
             "M6": ["test_checked_worker_fills_the_evidence_ids_a_search_returned"], "M7": [_LAB + "&&label-prefix"], "M8": [_LAB + "&&dedupe-exact-wins"],
             "M9": [_LAB + "&&label-prefix"], "M10": [_LAB + "&&exact-refs-recover-nothing"],
             "M11": ["test_checked_worker_labelled_ref_rescue_blocks_the_fill_even_when_facts_name_another_id"],
             "M12": ["test_checked_worker_labelled_ref_keeps_an_exactly_registered_id_whatever_its_characters"],
             "M13": ["test_checked_worker_fill_falls_back_to_all_own_ids_when_none_is_named_in_facts&&longer-id-only"],
             "M14": ["test_checked_worker_fill_prefers_ids_named_in_facts&&one-id-before-a-particle"]}
for _i, (_name, _old, _new) in enumerate(row_tables.WORKER_REFS, 1):
    add(f"wp{_i:02d}", f"workers.py checked_worker, {_name}  [phase3/worker_refs_precision]", W, [(_old, _new)], WP_EXPECT[_name.split()[0]])

# every row that injects into exa.py runs behind the dead proxy (a defect there could let a test query reach api.exa.ai with the fixture's fake key)
ROWS["12"]["env"] = dict(DEAD_PROXY)
ROWS["12"]["note"] = "run behind the dead proxy 127.0.0.1:9 (falsify 6; falsify 5 ran this row without it)"

# the copy test has one cell per synced file (corpus.py, retrieval.py, evidence.py, pipeline.py); each row must fail its own cell, so row 13 names the corpus.py cell
ROWS["13"]["expect"] = ["test_rag_lab_copies_are_byte_identical&&corpus.py"]

# ---------------------------------------------------------------- sy01, sy02: ONE byte changed inside a comment of a synced file (no behaviour changes); the Day02_new copy stays untouched, so only the copy test can see it
add("sy01", "rag_lab/pipeline.py comment `str.format` -> `str.fornat` (one byte; Day02_new copy untouched)", "rag_lab/pipeline.py",
    [("있어 str.format을 쓸 수 없다", "있어 str.fornat을 쓸 수 없다")], ["test_rag_lab_copies_are_byte_identical&&pipeline.py"])
add("sy02", "rag_lab/evidence.py comment `1회가 1이다` -> `1회가 2이다` (one byte; Day02_new copy untouched)", "rag_lab/evidence.py",
    [("judge 호출 1회가 1이다.", "judge 호출 1회가 2이다.")], ["test_rag_lab_copies_are_byte_identical&&evidence.py"])
