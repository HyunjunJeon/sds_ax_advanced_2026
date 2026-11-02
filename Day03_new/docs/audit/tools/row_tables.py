"""row_tables.py: the mutation points that rows.py turns into rows g01-g34, w01-w21, b01-b11, gi01-gi13, ex01-ex15 and wp01-wp14.

Each block is the table of one earlier mutation script, copied text for text (the strings are those scripts' own). Only the name of each table was made unique,
and the shared constants G, H, W are defined once below. The scripts themselves lived in a scratch folder that is not kept; all paths in the tables are relative to Day03_new.
"""
G, H, W = "mas_lab/gate.py", "mas_lab/hybrid.py", "mas_lab/workers.py"

# ---- gate_dev: rows g01 to g34
GATE_DEV = [
    ("M01 환불 단어 조건 제거", G, 'not (claims_a_block or "환불" in question)', "False"),
    ("M02 모르는 번호를 빼고 아는 번호만 탐침", G, 'checkable, claims_a_block = bool(named) and named <= payments.keys(), final.outcome in _BLOCKED.values()', 'named &= payments.keys()\n    checkable, claims_a_block = bool(named), final.outcome in _BLOCKED.values()'),
    ("M03 다른 레이블도 gate_skipped", G, 'if not checkable and claims_a_block:', 'if not checkable:'),
    ("M04 out_of_scope 제외 제거", G, 'if final.outcome == "out_of_scope" or (final.proposal', 'if (final.proposal'),
    ("M05 탐침 금액 0", G, 'amount=payments[payment_id]["amount"]', 'amount=0'),
    ("M06 하나만 deny여도 denied", G, '"denied" if decisions == {"deny"} else "human_review"', '"denied" if "deny" in decisions else "human_review"'),
    ("M07 실행 안 함 문장 제거", G, 'notes.append(_NOT_EXECUTED)', 'pass'),
    ("M08 번호 역순 탐침", G, 'for payment_id in sorted(named)}', 'for payment_id in sorted(named, reverse=True)}'),
    ("M09 탐침이 원장에 쓴다", G, '    decisions = {decision.decision for decision in probes.values()}', '    decisions = {decision.decision for decision in probes.values()}\n    for pid, d in probes.items():\n        execute_approved(Proposal(action="refund", payment_id=pid, amount=payments[pid]["amount"]), d, desk.ledger)'),
    ("M10 탐침이 제안을 만든다", G, '    # 탐침은 모두', '    final = final.model_copy(update={"proposal": Proposal(action="refund", payment_id=sorted(named)[0])})\n    # 탐침은 모두'),
    ("M11 번호 접두 제거", G, 'return [f"{payment_id or \'결제 번호 없음\'}: {reason}" for reason in decision.reasons]', 'return list(decision.reasons)'),
    ("M12 번호 없는 제안 접두 그대로", G, "{payment_id or '결제 번호 없음'}", "{payment_id}"),
    ("M13 묵은 불확실성 유지", G, '"text": " ".join(notes), "uncertainty": notes, ', '"text": " ".join(notes), '),
    ("M14 action none 제안 유지", G, '"proposal": final.proposal if final.proposal and final.proposal.action == "refund" else None', '"proposal": final.proposal'),
    ("M15 거절된 환불 제안 삭제", G, '"proposal": final.proposal if final.proposal and final.proposal.action == "refund" else None', '"proposal": None'),
    ("M16 dropped_uncertainty 빈 값", G, 'dropped_uncertainty=[line for line in final.uncertainty if line not in notes]', 'dropped_uncertainty=[]'),
    ("M17 교체 문장 출처 미등록", G, 'desk._register(f"F-GATE-{outcome}", update["text"])', 'pass'),
    ("M18 덧붙인 문장 출처 미등록", G, 'desk._register(f"F-GATE-{outcome}", appended)', 'pass'),
    ("M19 모델 문장까지 출처 등록", G, 'desk._register(f"F-GATE-{outcome}", appended)', 'desk._register(f"F-GATE-{outcome}", update["text"])'),
    ("M20 이미 있는 이유도 덧붙임", G, 'if note.rpartition(": ")[2] not in final.text]', 'if note not in final.text]'),
    ("M21 레이블 같으면 덧붙이지 않음", G, 'not in final.text] if blocked else []', 'not in final.text] if False else []'),
    ("M22 allow도 덧붙임", G, 'not in final.text] if blocked else []', 'not in final.text]'),
    ("M23 덧붙임 사건 없음", G, 'desk.trace.event("gate_text_appended", "code", appended=missing)', 'pass'),
    ("M24 레이블 바뀌어도 교체 안 함", G, 'if blocked and outcome != final.outcome:', 'if False:'),
    ("M25 불확실성 중복 제거 없음", G, 'fresh = [note for note in notes if note not in final.uncertainty]', 'fresh = list(notes)'),
    ("M26 gate_answer가 대조를 건너뜀", G, 'decision = refund_decision(proposal, desk, question)', 'decision = check_refund(proposal, desk.payments(), desk.scope.as_of)'),
    ("M27 불일치면 deny도 승인 대기", G, 'if not named or proposal.payment_id in named or decision.decision in _BLOCKED:', 'if not named or proposal.payment_id in named:'),
    ("M28 불일치 대조 제거", G, 'if not named or proposal.payment_id in named or decision.decision in _BLOCKED:', 'if True:'),
    ("M29 번호 없어도 대조", G, 'if not named or proposal.payment_id in named', 'if proposal.payment_id in named'),
    ("M30 이유 문장 추가 없음", G, 'reasons=[*decision.reasons, reason]', 'reasons=decision.reasons'),
    ("M31 after_gate 대조 제거", H, 'refund_decision(final.proposal, desk, state["question"])', 'refund_decision(final.proposal, desk, "")'),
    ("M32 approve에 question 없음", H, 'approved=None, request_id=request_id, question=state["question"])', 'approved=None, request_id=request_id)'),
    ("M33 execute에 question 없음", H, 'approved=state.get("approved"), request_id=request_id, question=state["question"])', 'approved=state.get("approved"), request_id=request_id)'),
    ("M34 gate 노드 검사 제거", H, 'final = check_named_payment(FinalAnswer.model_validate(state["final"]), desk, state["question"])', 'final = FinalAnswer.model_validate(state["final"])'),
]

# ---- refs_dev: rows w01 to w21
IMPORT = "from mas_lab.workers import DENY_WRITES, ROLE_TOOLS, allowlist_middleware, checked_worker\n"
OWN = "own = dict.fromkeys(r for m in messages if isinstance(m, ToolMessage) for r in _TOOL_REF.findall(m.text))"
REFS_DEV = [
    ("failed result is checked too", W, [('    if result.status == "failed":\n        return result\n', "")]),
    ("keeps unregistered refs", W, [("kept = [r for r in result.evidence_refs if r in known]", "kept = list(result.evidence_refs)")]),
    ("known snapshot empty", W, [("known = desk.known_refs()", "known = set()")]),
    ("dropped refs not named", W, [("notes = [f\"등록되지 않은 근거를 뺐습니다: {', '.join(dropped)}\"] if dropped else []", "notes = []")]),
    ("fills from the shared desk", W, [(OWN, "own = dict.fromkeys(desk.fact_refs)")]),
    ("fills even without facts", W, [("if result.facts and not kept", "if not kept")]),
    ("fills even when refs were kept", W, [("if result.facts and not kept", "if result.facts")]),
    ("never fills", W, [("filled = list(own) if result.facts and not kept else []", "filled = []")]),
    ("problems not computed", W, [("problems=validate_result(checked, known)", "problems=[]")]),
    ("filled count wrong", W, [("filled=len(filled)", "filled=0")]),
    ("no dedupe of own refs", W, [(OWN.replace("dict.fromkeys(", "list(", 1), None)]),
    ("regex fact_ref only", W, [("(?:fact_ref|evidence_id)", "(?:fact_ref)")]),
    ("regex evidence_id only", W, [("(?:fact_ref|evidence_id)", "(?:evidence_id)")]),
    ("reads refs from every message", W, [("for m in messages if isinstance(m, ToolMessage) for r in", "for m in messages for r in")]),
    ("model's own uncertainty overwritten", W, [('"uncertainty": [*result.uncertainty, *notes]', '"uncertainty": [*notes]')]),
    ("BudgetExceeded becomes a failed result", W, [("        except BudgetExceeded:\n            raise\n",
        "        except BudgetExceeded as error:\n            return WorkerResult(**base, status=\"failed\", error=type(error).__name__), []\n")]),
    ("run_worker filters", W, [("    return _run_with_messages(task, desk, model, role, prompt, config)[0]", "    return checked_worker(task, desk, model)")]),
    ("event kind renamed", W, [('"worker_checked"', '"worker_check"')]),
    ("event actor not the task id", W, [('"worker_checked", task.task_id', '"worker_checked", "worker"')]),
    ("hybrid worker node uses run_worker", H, [(IMPORT, IMPORT.replace("checked_worker", "checked_worker, run_worker")),
        ('        return {"results": {task.task_id: checked_worker(task, desk, model).model_dump()}}\n',
         '        return {"results": {task.task_id: run_worker(task, desk, model).model_dump()}}\n')]),
    ("hybrid retry node uses run_worker", H, [(IMPORT, IMPORT.replace("checked_worker", "checked_worker, run_worker")),
        ('checked_worker(task, desk, model).model_dump()}, "retried": True}', 'run_worker(task, desk, model).model_dump()}, "retried": True}')]),
]

# ---- budget_dev: rows b01 to b11
BUDGET_DEV = [
    ("drop consume in structured_call", "mas_lab/structures.py", '    desk.budget.consume("model")\n', ""),
    ("hybrid router bypasses structured_call", "mas_lab/hybrid.py", "route = structured_call(desk, model, HybridRoute,", 'route = model.with_structured_output(HybridRoute, method="json_schema").invoke('),
    ("handoff triage bypasses structured_call", "mas_lab/structures.py", "route = structured_call(desk, model, Route,", 'route = model.with_structured_output(Route, method="json_schema").invoke('),
    ("supervisor without delegation_spans", "mas_lab/structures.py", ", *delegation_spans(desk.trace)]", "]"),
    ("span kind is not worker", "mas_lab/workers.py", '"subagent_type", "task"), "worker")', '"subagent_type", "task"), "work")'),
    ("span wraps every tool", "mas_lab/workers.py", 'if request.tool_call["name"] != "task":', 'if False:'),
    ("span serialized by a lock", "mas_lab/workers.py", "with trace.span(", "with LOCK, trace.span("),
    ("span key is required", "mas_lab/workers.py", '.get("subagent_type", "task")', '["subagent_type"]'),
    ("span opens after the task ends", "mas_lab/workers.py", "        with trace.span(request.tool_call[\"args\"].get(\"subagent_type\", \"task\"), \"worker\"):\n            return handler(request)",
     "        reply = handler(request)\n        with trace.span(request.tool_call[\"args\"].get(\"subagent_type\", \"task\"), \"worker\"):\n            return reply"),
    ("conftest fixture removed", "tests/conftest.py", "@pytest.fixture(autouse=True)", "@pytest.fixture"),
    ("conftest rebinds settings ROOT too", "tests/conftest.py", 'monkeypatch.setattr("mas_lab.runner.ROOT", tmp_path)', 'monkeypatch.setattr("mas_lab.runner.ROOT", tmp_path)\n    monkeypatch.setattr("rag_lab.settings.ROOT", tmp_path)\n    monkeypatch.setattr("mas_lab.desk.ROOT", tmp_path)'),
]

# ---- gate_id_forms: rows gi01 to gi13
PATTERN = r'(?<![A-Za-z0-9-])[Pp](?:-|(?=\d{4,}(?![A-Za-z0-9])))(\d+)'
NORMALIZE = 'return {f"P-{digits}" for digits in _PAYMENT_ID.findall(question)}'
GATE_ID_FORMS = [
    ("R1 case-sensitive only", PATTERN, PATTERN.replace("[Pp]", "P")),
    ("R2 hyphen required", PATTERN, PATTERN.replace("(?:-|(?=\\d{4,}(?![A-Za-z0-9])))", "-")),
    ("R3 no digit floor on the no-hyphen form", PATTERN, PATTERN.replace("\\d{4,}", "\\d+")),
    ("R4 no trailing guard", PATTERN, PATTERN.replace("(?![A-Za-z0-9])", "")),
    ("R5 no normalization (raw spelling)", NORMALIZE, "return {m.group(0) for m in _PAYMENT_ID.finditer(question)}"),
    ("R6 lookbehind removed", PATTERN, PATTERN.replace("(?<![A-Za-z0-9-])", "")),
    ("B1 lookbehind without the hyphen", PATTERN, PATTERN.replace("(?<![A-Za-z0-9-])", "(?<![A-Za-z0-9])")),
    ("B2 trailing guard letters only", PATTERN, PATTERN.replace("(?![A-Za-z0-9])", "(?![A-Za-z])")),
    ("B3 digit floor 3", PATTERN, PATTERN.replace("\\d{4,}", "\\d{3,}")),
    ("B4 digit floor 5", PATTERN, PATTERN.replace("\\d{4,}", "\\d{5,}")),
    ("B5 trailing guard is \\w (refuses a Korean particle)", PATTERN, PATTERN.replace("(?![A-Za-z0-9])", "(?!\\w)")),
    ("B6 digit floor also on the hyphen form", PATTERN, PATTERN.replace("(?:-|", "(?:-(?=\\d{4,})|")),
    ("B7 uppercase output prefix lowered", NORMALIZE, 'return {f"p-{digits}" for digits in _PAYMENT_ID.findall(question)}'),
]

# ---- exa_id_forms: rows ex01 to ex15 (the first entry is the control and is not a row)
GOOD = r'INTERNAL_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:P(?:-\d+|\d{4,})|INV-(?:[A-Za-z0-9-]+|[\w-]+)|INC-\d+|T-\d+)(?![A-Za-z0-9])", re.IGNORECASE)'
LB, LA = r"(?<![A-Za-z0-9])", r"(?![A-Za-z0-9])"
EXA_ID_FORMS = [
    ("none (control)", GOOD),
    ("REQUIRED restore re.ASCII", GOOD.replace(", re.IGNORECASE)", ", re.ASCII | re.IGNORECASE)")),
    ("REQUIRED no IGNORECASE", GOOD.replace(", re.IGNORECASE)", ")")),
    ("REQUIRED \\w in both lookarounds", GOOD.replace(LB, r"(?<!\w)").replace(LA, r"(?!\w)")),
    ("REQUIRED no no-hyphen form (P-\\d+ only)", GOOD.replace(r"P(?:-\d+|\d{4,})", r"P-\d+")),
    ("REQUIRED no digit floor (\\d+)", GOOD.replace(r"\d{4,}", r"\d+")),
    ("REQUIRED drop the [\\w-]+ alternative for INV-", GOOD.replace(r"INV-(?:[A-Za-z0-9-]+|[\w-]+)", r"INV-[A-Za-z0-9-]+")),
    ("REQUIRED P form dropped", GOOD.replace(r"P(?:-\d+|\d{4,})|", "")),
    ("extra: \\w in the lookbehind only", GOOD.replace(LB, r"(?<!\w)")),
    ("extra: \\w in the lookahead only", GOOD.replace(LA, r"(?!\w)")),
    ("extra: back to \\b on both sides", GOOD.replace(LB, r"\b").replace(LA, r"\b")),
    ("extra: INV- without the ASCII-first alternative ([\\w-]+ only)", GOOD.replace(r"INV-(?:[A-Za-z0-9-]+|[\w-]+)", r"INV-[\w-]+")),
    ("extra: digit floor 3 (\\d{3,})", GOOD.replace(r"\d{4,}", r"\d{3,}")),
    ("extra: ASCII digits only ([0-9] for \\d)", GOOD.replace(r"\d", "[0-9]")),
    ("extra: INC- dropped", GOOD.replace(r"|INC-\d+", "")),
    ("extra: T- dropped", GOOD.replace(r"|T-\d+", "")),
]

# ---- worker_refs_precision: rows wp01 to wp14
FOUND = "    found = {r: [r] if r in known else [t for t in _TOKEN.findall(r) if t in known] for r in result.evidence_refs}\n"
FILLED = "    filled = ([i for i in own if i in named] or list(own)) if result.facts and not kept else []\n"
WORKER_REFS = [
    ("M1 substring match instead of whole token", FOUND, "    found = {r: [r] if r in known else sorted(k for k in known if k in r) for r in result.evidence_refs}\n"),
    ("M2 token includes Hangul", '_TOKEN = re.compile(r"[A-Za-z0-9-]+")', '_TOKEN = re.compile(r"[A-Za-z0-9가-힣-]+")'),
    ("M3 recovery removed", FOUND, "    found = {r: [r] if r in known else [] for r in result.evidence_refs}\n"),
    ("M4 adopt ids from known instead of own", FILLED, "    filled = ([i for i in sorted(known) if i in named] or list(own)) if result.facts and not kept else []\n"),
    ("M5 fill ignores facts", FILLED, "    filled = list(own) if result.facts and not kept else []\n"),
    ("M6 fallback removed", FILLED, "    filled = [i for i in own if i in named] if result.facts and not kept else []\n"),
    ("M7 recovered always 0", "recovered=recovered)", "recovered=0)"),
    ("M8 dedupe removed", "    kept = list(dict.fromkeys(i for ids in found.values() for i in ids))\n", "    kept = [i for ids in found.values() for i in ids]\n"),
    ("M9 note names rescued refs as dropped", "    dropped = [r for r, ids in found.items() if not ids]\n", "    dropped = [r for r, ids in found.items() if ids != [r]]\n"),
    ("M10 recovered counts every kept id", "    recovered = len(set(kept) - set(result.evidence_refs))\n", "    recovered = len(kept)\n"),
    ("M11 fill still runs when a labelled ref was rescued", "if result.facts and not kept else []", "if result.facts and not any(r in known for r in result.evidence_refs) else []"),
    ("M12 exact-first check removed (tokens only)", FOUND, "    found = {r: [t for t in _TOKEN.findall(r) if t in known] for r in result.evidence_refs}\n"),
    ("M13 facts matched by substring", "    named = {t for fact in result.facts for t in _TOKEN.findall(fact)}\n", "    named = {i for i in own for fact in result.facts if i in fact}\n"),
    ("M14 facts tokens include Hangul", "    named = {t for fact in result.facts for t in _TOKEN.findall(fact)}\n", "    named = {t for fact in result.facts for t in re.findall(r'[A-Za-z0-9가-힣-]+', fact)}\n"),
]
