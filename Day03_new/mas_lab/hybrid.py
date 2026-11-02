"""완성형 조립. 코드가 경로를 정하고, 판단이 필요한 노드에서만 모델과 Agent를 쓴다."""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from deepagents import create_deep_agent
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from mas_lab.contracts import (FinalAnswer, Route, WorkerResult, WorkerTask, classify_failure, join_results,
                               merge_results, next_action, validate_final)
from mas_lab.desk import Desk
from mas_lab.gate import check_named_payment, gate_answer, refund_decision
from mas_lab.structures import OUTCOME_GUIDE, scope_line, structured_call
from mas_lab.workers import DENY_WRITES, ROLE_TOOLS, allowlist_middleware, checked_worker

ROLES = ("billing", "policy", "outage")
ROLE_GOALS = {"billing": "고객 요청에 관련된 결제 사실을 조회한다. 같은 청구서의 결제와 기본 이용료분을 포함한다.",
              "policy": "고객 요청에 적용되는 환불 규정, SLA 크레딧 구간, 개별 추가 약정의 신청 기한을 원문에서 찾는다.",
              "outage": "고객 요청에 관련된 최근 월의 가용률과 장애 사건을 조회한다."}
FAST_TOOLS = ROLE_TOOLS["policy"] | ROLE_TOOLS["billing"]
MAX_REWRITES = 1


class HybridRoute(Route):  # 범위 밖 판단은 scope_check가 코드로 한다. 모델에게는 그래프가 가는 경로만 고르게 한다.
    path: Literal["fast", "slow"]


class HybridState(TypedDict, total=False):
    question: str
    route: dict
    results: Annotated[dict, merge_results]
    final: dict
    problems: list[str]
    rewrites: int
    retried: bool
    path_taken: list[str]
    task: dict
    approved: bool


def build_hybrid(desk: Desk, model: BaseChatModel, *, checkpointer=None, force_path: str | None = None,
                 request_id: str = "req"):
    """범위 확인 → Router → Fast 또는 Worker 병렬 → 합성 → 검증 → 게이트 → 승인 → 실행."""
    entities = {d.entity for d in desk.context.retriever.documents.values()} - {desk.scope.entity, "공통"}

    def scope_check(state: HybridState) -> dict:
        outside = sorted(name for name in entities if name in state["question"])
        if not outside:
            return {"path_taken": ["scope"]}
        desk.trace.event("decision", "code", choice="out_of_scope", names=outside)
        final = FinalAnswer(outcome="out_of_scope", text=f"현재 고객 범위({desk.scope.entity}) 밖의 {', '.join(outside)} 계약은 답할 수 없습니다.",
                            uncertainty=[f"범위 밖 이름: {outside}"])
        return {"final": final.model_dump(), "path_taken": ["scope", "out_of_scope"]}

    def router(state: HybridState) -> dict:
        route = structured_call(desk, model, HybridRoute,
            "고객 요청의 경로를 고르세요. fast: 규정 한 곳이나 결제 한 건만 보면 되는 질문. slow: 결제, 규정, 장애 중 둘 이상이 필요한 질문. "
            "roles에는 slow일 때 필요한 조사를 고르세요. billing: 결제 사실. policy: 환불 규정과 SLA 문서. outage: 가용률. 보상이나 크레딧을 물으면 outage와 billing, policy가 모두 필요합니다. "
            f"{scope_line(desk)}\n질문: {state['question']}")
        if force_path:
            route = route.model_copy(update={"path": force_path})
        desk.trace.event("decision", "router", choice=route.path, roles=route.roles, reason=route.reason)
        return {"route": route.model_dump(), "path_taken": [*state["path_taken"], route.path]}

    def _write(state: HybridState, *, tools: list, allowed: frozenset[str], content: str, actor: str) -> dict:
        agent = create_deep_agent(
            model=model, tools=tools, system_prompt=f"고객에게 보낼 답을 씁니다. {scope_line(desk)}\n{OUTCOME_GUIDE}",
            middleware=allowlist_middleware(desk.budget, allowed), permissions=DENY_WRITES,
            response_format=ProviderStrategy(FinalAnswer), name=actor)
        with desk.trace.span(actor, "write"):
            reply = agent.invoke({"messages": [{"role": "user", "content": content}]}, config={"recursion_limit": 40})
        desk.trace.event("final_answer", actor)
        return {"final": reply["structured_response"].model_dump(), "path_taken": [*state["path_taken"], actor]}

    def fast(state: HybridState) -> dict:
        tools = [t for t in desk.tools("all") if t.name in FAST_TOOLS]
        return _write(state, tools=tools, allowed=FAST_TOOLS, content=state["question"], actor="fast")

    def dispatch(state: HybridState) -> list[Send]:
        roles = [r for r in state["route"].get("roles", []) if r in ROLES] or list(ROLES)
        return [Send("worker", {"task": WorkerTask(task_id=r, goal=f"{ROLE_GOALS[r]}\n고객 요청: {state['question']}",
                                                   allowed_tools=sorted(ROLE_TOOLS[r])).model_dump()}) for r in roles]

    def worker(state: HybridState) -> dict:
        task = WorkerTask.model_validate(state["task"])
        return {"results": {task.task_id: checked_worker(task, desk, model).model_dump()}}

    def join(state: HybridState) -> dict:
        return {"path_taken": [*state["path_taken"], "join"]}

    def after_join(state: HybridState):
        """시스템 오류로 실패한 작업만 한 번 다시 돌린다. 완료 결과는 보존한다."""
        required = [k for k in state["results"] if "#" not in k]
        info = join_results({k: WorkerResult.model_validate(v) for k, v in state["results"].items()}, required)
        if info["failed"] and not state.get("retried"):
            desk.trace.event("retry_failed", "code", tasks=info["failed"])
            return [Send("retry", {"task": WorkerTask(task_id=f"{t}#2", goal=state["results"][t].get("error", "") or ROLE_GOALS[t],
                                                      attempt=2, allowed_tools=sorted(ROLE_TOOLS[t])).model_dump(),
                                   "question": state["question"]}) for t in info["failed"]]
        return "writer"

    def retry(state: HybridState) -> dict:
        task = WorkerTask.model_validate(state["task"])
        base = task.task_id.split("#")[0]
        task = task.model_copy(update={"goal": f"{ROLE_GOALS[base]}\n고객 요청: {state['question']}"})
        return {"results": {task.task_id: checked_worker(task, desk, model).model_dump()}, "retried": True}

    def writer(state: HybridState) -> dict:
        facts = {k: {f: v.get(f) for f in ("status", "facts", "evidence_refs", "uncertainty", "error")}
                 for k, v in state.get("results", {}).items()}
        content = (f"고객 요청: {state['question']}\nWorker 결과: {facts}\n앞선 검증 문제: {state.get('problems') or '없음'}\n"
                   "크레딧 금액은 calculate_credit으로 계산하고, 기본 이용료분만 계산 기준에 넣으세요. 실패하거나 누락된 작업은 uncertainty에 쓰세요.")
        return _write(state, tools=desk.tools("writer"), allowed=ROLE_TOOLS["writer"], content=content, actor="writer")

    def validate(state: HybridState) -> dict:
        final = FinalAnswer.model_validate(state["final"])
        problems = validate_final(final, desk.known_refs(), desk.source_text())
        desk.trace.event("validate", "code", problems=problems)
        return {"problems": problems, "rewrites": state.get("rewrites", 0) + (1 if problems else 0)}

    def after_validate(state: HybridState):
        """근거 부족은 재조사, 정책 불가와 통과는 게이트로 간다. Fast에서 부족했으면 Slow로 전환한다."""
        final = FinalAnswer.model_validate(state["final"])
        kind = classify_failure(None, final, state["problems"])
        retries_left = MAX_REWRITES - (state.get("rewrites", 0) - (1 if state["problems"] else 0))
        action = next_action(kind, retries_left=retries_left, budget_left=True)
        came_fast = "fast" in state["path_taken"] and "join" not in state["path_taken"]
        if action == "reinvestigate" and came_fast:
            desk.trace.event("fallback_to_slow", "code", problems=state["problems"], outcome=final.outcome)
            return dispatch(state)
        if action == "reinvestigate" and state["problems"]:
            return "writer"
        return "gate"

    def gate(state: HybridState) -> dict:
        """검사만 한다. 부작용을 interrupt 앞에 두지 않는다. 재개하면 노드가 처음부터 다시 돌기 때문이다."""
        final = check_named_payment(FinalAnswer.model_validate(state["final"]), desk, state["question"])
        return {"final": final.model_dump(), "path_taken": [*state["path_taken"], "gate"]}

    def after_gate(state: HybridState) -> str:
        final = FinalAnswer.model_validate(state["final"])
        if final.proposal is None or final.proposal.action != "refund":
            return END
        return "approve" if refund_decision(final.proposal, desk, state["question"]).decision == "needs_approval" else "execute"

    def approve(state: HybridState) -> dict:
        final = FinalAnswer.model_validate(state["final"])
        waiting = gate_answer(final, desk, approved=None, request_id=request_id, question=state["question"])  # 원장에 닿지 않는다. needs_approval 상태만 만든다.
        answer = interrupt({"proposal": waiting.proposal.model_dump(), "reasons": waiting.uncertainty})
        return {"final": waiting.model_dump(), "approved": bool(answer.get("approved"))}

    def execute(state: HybridState) -> dict:
        settled = gate_answer(FinalAnswer.model_validate(state["final"]), desk, approved=state.get("approved"), request_id=request_id, question=state["question"])
        return {"final": settled.model_dump(), "path_taken": [*state["path_taken"], "execute"]}

    graph = StateGraph(HybridState)
    for name, node in [("scope", scope_check), ("router", router), ("fast", fast), ("worker", worker), ("retry", retry),
                       ("join", join), ("writer", writer), ("validate", validate), ("gate", gate), ("approve", approve),
                       ("execute", execute)]:
        graph.add_node(name, node)
    graph.add_edge(START, "scope")
    graph.add_conditional_edges("scope", lambda s: END if s.get("final") else "router", ["router", END])
    graph.add_conditional_edges("router", lambda s: "fast" if s["route"]["path"] == "fast" else dispatch(s), ["fast", "worker"])
    graph.add_edge("worker", "join")
    graph.add_edge("retry", "join")
    graph.add_conditional_edges("join", after_join, ["retry", "writer"])
    graph.add_edge("fast", "validate")
    graph.add_edge("writer", "validate")
    graph.add_conditional_edges("validate", after_validate, ["writer", "worker", "gate"])
    graph.add_conditional_edges("gate", after_gate, ["approve", "execute", END])
    graph.add_edge("approve", "execute")
    graph.add_edge("execute", END)
    return graph.compile(checkpointer=checkpointer or MemorySaver())

