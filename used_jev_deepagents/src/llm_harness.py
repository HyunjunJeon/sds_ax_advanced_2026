"""JevHarness와 같은 RAG 결정을 LLM tool-call로 채운다.

슬롯과 코드 정책은 같고, 호출은 패시지마다 한 번이다.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from langchain_core.language_models import BaseChatModel

from src.agent.config import Settings, chat_model
from src.closed_loop import ClosedQuestion
from src.harness import _build_turn_plan, _gated_from_answers, _promote_if_empty
from src.jev import AskResult
from src.llm_judge import (
    bool_noul,
    decide_closed,
    decide_evidence,
    decide_passage,
    decide_reconcile,
    decide_turn,
)
from src.schemas import (
    ClosedLoopResult,
    DecisionTrace,
    EvidenceJudgment,
    GatedPassage,
    Passage,
    ReconcileResult,
    SourcePlan,
    TurnPlan,
)
from src.turn_state import build_turn_state

# LLM은 이산 라벨만 주므로 Jev Score 스케일로 옮긴다.
_COMPLEXITY = {"low": 0.35, "medium": 1.15, "high": 1.75}


class LlmHarness:
    """결정마다 structured LLM tool-call 한 번을 쓰는 판단 엔진."""

    engine = "llm"

    def __init__(
        self,
        settings: Settings,
        model: BaseChatModel | None = None,
    ) -> None:
        self.settings = settings
        self.model = model or chat_model(settings, settings.fast_model)
        self.traces: list[DecisionTrace] = []
        self.last_gated: list[GatedPassage] = []
        self.last_plan: SourcePlan | None = None
        self.last_turn: TurnPlan | None = None
        self.last_reconcile: ReconcileResult | None = None
        self.last_closed: ClosedLoopResult | None = None
        self.last_evidence: list[EvidenceJudgment] = []
        self.last_attachments: list[GatedPassage] = []
        self._plan_key: tuple | None = None

    def reset_traces(self) -> None:
        """실행마다 트레이스와 캐시된 결정을 비운다."""
        self.traces = []
        self.last_gated = []
        self.last_plan = None
        self.last_turn = None
        self.last_reconcile = None
        self.last_closed = None
        self.last_evidence = []
        self.last_attachments = []
        self._plan_key = None

    def plan_turn(
        self,
        question: str,
        *,
        attached: list | None = None,
    ) -> TurnPlan:
        """LLM tool-call 한 번 뒤 Jev와 같은 코드 정책을 얹는다."""
        files = list(attached or [])
        key = (
            question,
            tuple(getattr(item, "filename", "") for item in files),
        )
        if self.last_turn is not None and self._plan_key == key:
            return self.last_turn
        state = build_turn_state(question, self.settings, files)
        decision, trace = decide_turn(self.model, question, state)
        self.traces.append(trace)
        self.last_gated = []
        self.last_reconcile = None
        result = AskResult(
            choices={
                "kind": decision.kind,
                "sources": decision.sources,
                "analysis": decision.analysis,
                "thinking": decision.thinking,
            },
            nouls={
                "need_local": bool_noul(decision.need_local),
                "need_web": bool_noul(decision.need_web),
                "need_fresh_web": bool_noul(decision.need_fresh_web),
                "need_search": bool_noul(decision.need_search),
                "need_attachment": bool_noul(decision.need_attachment),
                "jailbreak": bool_noul(decision.jailbreak),
            },
            scores={"complexity": _COMPLEXITY[decision.complexity]},
            confidence={"kind": 0.70, "sources": 0.70, "analysis": 0.70},
            probabilities={},
            live=False,
            elapsed_ms=trace.elapsed_ms,
        )
        plan = _build_turn_plan(
            question,
            result,
            self.settings,
            attached_present=bool(files),
        )
        plan.reason = f"LLM tool-call {plan.reason}"
        self._plan_key = key
        self.last_turn = plan
        self.last_plan = plan.to_source_plan()
        return plan

    def gate_passages(self, question: str, passages: list[Passage]) -> list[GatedPassage]:
        """패시지마다 LLM tool-call 한 번 (고전 판단 루프)."""
        if not passages:
            return []

        def gate_one(passage: Passage) -> GatedPassage:
            decision, trace = decide_passage(
                self.model,
                question,
                passage.doc_id,
                passage.title,
                passage.text,
            )
            self.traces.append(trace)
            nouls = {
                "is_relevant": bool_noul(decision.is_relevant),
                "contains_answer_evidence": bool_noul(
                    decision.contains_answer_evidence
                ),
                "contradicts_query_premise": bool_noul(
                    decision.contradicts_query_premise
                ),
                "contains_prompt_injection": bool_noul(
                    decision.contains_prompt_injection
                ),
            }
            return _gated_from_answers(passage, nouls, self.settings)

        workers = min(4, len(passages))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            gated = list(pool.map(gate_one, passages))
        _promote_if_empty(gated, self.settings)
        self.last_gated.extend(gated)
        return gated

    def gate_passages_per_item(
        self,
        question: str,
        passages: list[Passage],
    ) -> list[GatedPassage]:
        """별칭. LLM 경로는 이미 패시지마다 tool-call 한 번이다."""
        return self.gate_passages(question, passages)

    def reconcile_sources(self, question: str) -> ReconcileResult | None:
        """이어 붙인 로컬 vs 웹 텍스트에 대한 LLM tool-call."""
        local = [
            item
            for item in self.last_gated
            if item.route != "exclude" and item.passage.source_type != "web"
        ]
        web = [
            item
            for item in self.last_gated
            if item.route != "exclude" and item.passage.source_type == "web"
        ]
        if not local or not web:
            self.last_reconcile = None
            return None
        local_text = "\n\n".join(item.passage.text for item in local)
        web_text = "\n\n".join(item.passage.text for item in web)
        decision, trace = decide_reconcile(self.model, question, local_text, web_text)
        self.traces.append(trace)
        result = ReconcileResult(
            verdict=decision.verdict,
            confidence=0.70,
            web_contradicts_local=bool_noul(decision.web_contradicts_local),
            local_is_authoritative=bool_noul(decision.local_is_authoritative),
            web_is_trustworthy=bool_noul(decision.web_is_trustworthy),
            reason=f"LLM tool-call verdict={decision.verdict}",
        )
        self.last_reconcile = result
        return result

    def ask_closed(
        self,
        state: dict[str, object],
        questions: list[ClosedQuestion],
        *,
        note: str = "",
    ) -> ClosedLoopResult:
        """같은 Closed Loop 슬롯을 채우는 LLM tool-call."""
        spec = "\n".join(
            f"- {item.id} ({item.type}): {item.instructions} criteria={item.criteria}"
            for item in questions
        )
        decision, trace = decide_closed(self.model, state, spec)
        if note:
            trace.note = f"{trace.note}; {note}"
        self.traces.append(trace)
        result = ClosedLoopResult(
            nouls=dict(decision.nouls),
            choices=dict(decision.choices),
            probabilities={},
            scores=dict(decision.scores),
            confidence={},
            elapsed_ms=trace.elapsed_ms,
            live=False,
            reason="LLM tool-call Closed Loop. Apply thresholds in the next action.",
        )
        self.last_closed = result
        return result

    def judge_evidence(
        self,
        question: str,
        text: str,
        *,
        path: str = "",
        source: str = "",
    ) -> EvidenceJudgment:
        """LLM tool-call: supports / conflicts / silent."""
        del source
        decision, trace = decide_evidence(self.model, question, text, path)
        self.traces.append(trace)
        reason = {
            "supports": "이 파일은 질문에 답할 사실을 담고 있다.",
            "conflicts": "이 파일은 질문의 전제와 충돌한다. 숨기지 말 것.",
            "silent": "이 파일은 질문에 침묵한다. 사실로 쓰지 말 것.",
        }[decision.relation]
        result = EvidenceJudgment(
            path=path,
            relation=decision.relation,
            relation_confidence=0.70,
            usable_facts=bool_noul(decision.usable_facts),
            enough_to_answer=bool_noul(decision.enough_to_answer),
            reason=f"LLM tool-call. {reason}",
        )
        self.last_evidence.append(result)
        return result
