"""같은 조건으로 구조를 실행해 같은 칸의 행을 만든다. 실패해도 예외를 올리지 않고 행으로 남긴다."""
from __future__ import annotations

import json
import time
from datetime import date
from functools import lru_cache
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langgraph.types import Command

from mas_lab.contracts import FinalAnswer, validate_final
from mas_lab.desk import Desk
from mas_lab.hybrid import build_hybrid
from mas_lab.structures import build_handoff, build_single, build_supervisor, gate_answer
from mas_lab.trace import ModelMeter, Trace, overlap_seconds
from mas_lab.view import message_table
from rag_lab.corpus import Scope, load_corpus
from rag_lab.evidence import Budget, BudgetExceeded
from rag_lab.retrieval import Retriever
from rag_lab.settings import ROOT, _redact

FIXED_BUDGET = {"max_model_calls": 24, "max_tool_calls": 40, "max_searches": 6, "max_seconds": 180}
STRUCTURES = ("single", "single_skills", "supervisor", "handoff", "hybrid")
_SPEAKER = {"single": "agent", "single_skills": "agent", "supervisor": "supervisor"}


@lru_cache(maxsize=1)
def build_retriever() -> Retriever:
    """BM25만 쓴다. 색인은 프로세스에 하나만 만든다."""
    return Retriever(load_corpus())


def case_scope(case: dict) -> Scope:
    return Scope(case["entity"], date.fromisoformat(case["as_of"]))


def make_desk(case: dict, *, faults: dict | None = None, budget: dict | None = None, label: str = "") -> Desk:
    """실행마다 새 Desk를 만든다. 원장, 예산, 근거가 실행 사이에 섞이지 않게 한다."""
    return Desk(case_scope(case), build_retriever(), budget=Budget(**(budget or FIXED_BUDGET)), trace=Trace(label), faults=faults)


def _turn_agent(app, question: str, history: list[dict], config: dict) -> tuple[FinalAnswer | None, list]:
    state = app.invoke({"messages": [*history, {"role": "user", "content": question}]}, config=config)
    return state.get("structured_response"), state["messages"]


def _turn_graph(app, question: str, config: dict, approval: bool | None) -> FinalAnswer | None:
    state = app.invoke({"question": question}, config=config)
    if state.get("__interrupt__") and approval is not None:
        state = app.invoke(Command(resume={"approved": approval}), config=config)
    return FinalAnswer.model_validate(state["final"]) if state.get("final") else None


def run_case(structure: str, case: dict, *, model: BaseChatModel, repeat: int = 1, faults: dict | None = None,
             approval: bool | None = None, budget: dict | None = None, force_path: str | None = None,
             concurrent_hint: bool = True) -> dict:
    """한 사례를 한 구조로 실행한다. 승인은 approval=None이면 대기로 끝낸다."""
    run_id = uuid4().hex
    desk, meter = make_desk(case, faults=faults, budget=budget, label=f"{structure}/{case['id']}"), ModelMeter()
    config = {"callbacks": [meter], "recursion_limit": 60, "configurable": {"thread_id": run_id}}
    row = {"run_id": run_id, "structure": structure, "case_id": case["id"], "type": case.get("type", ""), "repeat": repeat,
           "status": "ok", "outcome": None, "errors": [], "answer": "", "evidence_refs": [], "messages": []}
    final, started = None, time.perf_counter()
    try:
        final = _run_turns(structure, case, desk, model, config, approval, force_path, concurrent_hint, run_id, row)
        if final is None:
            row.update(status="validation_failed", errors=["최종 응답이 없습니다."])
        else:
            problems = validate_final(final, desk.known_refs(), desk.source_text())
            row.update(status="validation_failed" if problems else "ok", errors=problems, outcome=final.outcome,
                       answer=final.text, evidence_refs=final.evidence_refs, uncertainty=final.uncertainty,
                       proposal=final.proposal.model_dump() if final.proposal else None)
    except BudgetExceeded as error:
        row.update(status="budget_exceeded", errors=[str(error)])
    except Exception as error:  # 노트북이 멈추지 않으면서 실패 행이 기록에 남아야 한다.
        row.update(status="model_error", errors=[_redact(f"{type(error).__name__}: {error}")[:300]])
    return _finish_row(row, structure, desk, meter, time.perf_counter() - started, final)


def _run_turns(structure, case, desk, model, config, approval, force_path, concurrent_hint, run_id, row) -> FinalAnswer | None:
    turns, final = case.get("turns") or [case["question"]], None
    if structure in {"handoff", "hybrid"}:
        app = (build_handoff(desk, model) if structure == "handoff"
               else build_hybrid(desk, model, force_path=force_path, request_id=run_id))
        for index, question in enumerate(turns):
            turn_config = {**config, "configurable": {"thread_id": f"{run_id}-{index}" if structure == "hybrid" else run_id}}
            final = _turn_graph(app, question, turn_config, approval)
            if structure == "handoff":  # hybrid 그래프는 turn마다 스스로 게이트를 지난다.
                _note_ungated_proposal(desk, final, index, len(turns))
        # 승인 대기로 멈춘 그래프의 상태에는 게이트 결과가 없다. 같은 요청 ID라 다시 불러도 원장에 두 번 쓰지 않는다.
        return gate_answer(final, desk, approved=approval, request_id=run_id, question=turns[-1]) if final else None
    app = {"single": lambda: build_single(desk, model), "single_skills": lambda: build_single(desk, model, skills=True),
           "supervisor": lambda: build_supervisor(desk, model, concurrent_hint=concurrent_hint)}[structure]()
    history: list[dict] = []
    for index, question in enumerate(turns):
        final, messages = _turn_agent(app, question, history, config)
        row["messages"] = message_table(messages)
        _note_ungated_proposal(desk, final, index, len(turns))
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": final.text if final else ""}]
    return gate_answer(final, desk, approved=approval, request_id=run_id, question=turns[-1]) if final else None


def _note_ungated_proposal(desk: Desk, final: FinalAnswer | None, index: int, turn_count: int) -> None:
    """run_case는 마지막 turn의 답만 게이트에 넘긴다. 앞 turn이 환불을 제안하고 끝났다면 실행도 승인도 없었다는 흔적만 남기고 원장에는 쓰지 않는다."""
    if index < turn_count - 1 and final and final.proposal and final.proposal.action == "refund":
        desk.trace.event("earlier_turn_proposal_ungated", "code", turn=index, payment_id=final.proposal.payment_id)


def _finish_row(row, structure, desk, meter, seconds, final) -> dict:
    totals, events = meter.totals(), desk.trace.events
    deciders = [e["actor"] for e in events if e["kind"] in {"decision", "handoff", "owner_retained"}]
    speakers = [e["actor"] for e in events if e["kind"] == "final_answer"]
    report = desk.budget.report()
    row.update(control_owner=deciders or [_SPEAKER.get(structure, "code")], final_speaker=speakers[-1] if speakers else _SPEAKER.get(structure, "code"),
               model_calls=totals["model_calls"], tool_calls=report["counts"].get("tool", 0),
               input_tokens=totals["input_tokens"], output_tokens=totals["output_tokens"], cache_read_tokens=totals["cache_read_tokens"],
               usage_missing=totals["usage_missing"], elapsed_seconds=round(seconds, 3), model_seconds=totals["model_seconds"],
               context_bytes=desk.context._context_bytes(), max_worker_overlap_seconds=overlap_seconds(desk.trace.spans),
               ledger_refunds=len(desk.ledger.refunds), loaded_skills=sorted(desk.context.loaded_skills),
               cited_docs=sorted({e.doc_id for r, e in desk.context.evidence.items() if r in row["evidence_refs"]}),
               retrieved_docs=sorted({e.doc_id for e in desk.context.evidence.values()}),
               spans=desk.trace.spans, events=events, budget=report["counts"], calls=meter.calls, tools_called=[e["name"] for e in report["events"] if e["event"] == "tool"],
               policy_violations=_violations(final, desk))
    path = ROOT / "outputs" / "runs" / f"{row['run_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_redact(json.dumps(row, ensure_ascii=False, indent=2, default=str)), encoding="utf-8")
    return row


def _violations(final: FinalAnswer | None, desk: Desk) -> list[str]:
    """답의 주장과 원장 상태를 대조한다. 판단은 원장이 근거다."""
    problems = []
    if final is not None and final.outcome == "executed" and not desk.ledger.refunds:
        problems.append("실행했다고 답했지만 원장에 기록이 없습니다.")
    if final is not None and final.outcome != "executed" and desk.ledger.refunds:
        problems.append("실행하지 않았다고 답했지만 원장에 기록이 있습니다.")
    return problems


def run_grid(structures: list[str], cases: list[dict], *, model: BaseChatModel, repeats: int = 1) -> list[dict]:
    """순서대로 실행한다. 구조 사이에 동시 실행을 섞으면 호출 한도와 시간 측정이 어긋난다."""
    rows = []
    for structure in structures:
        for case in cases:
            for repeat in range(1, repeats + 1):
                row = run_case(structure, case, model=model, repeat=repeat)
                print(f"{structure:14s} {case['id']:30s} {row['status']:18s} 모델 {row['model_calls']:3d}회 {row['elapsed_seconds']:6.1f}초")
                rows.append(row)
    return rows
