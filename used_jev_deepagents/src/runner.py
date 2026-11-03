"""질문 하나를 Jev 하네스와 Deep Agent로 돌린다."""

from __future__ import annotations

from langchain.messages import HumanMessage

from src.agent.config import Settings, load_settings
from src.agent.graph import build_agent
from src.harness import JevHarness
from src.retriever import CorpusIndex
from src.schemas import RunResult


class RagDemo:
    """상태 있는 데모: 색인 하나, 하네스 하나, 질문마다 Deep Agent."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.index = CorpusIndex(self.settings.corpus_dir)
        self.harness = JevHarness(self.settings)

    def preview(self, question: str) -> RunResult:
        """빠른 훑어보기용으로 Jev 하네스만 돌린다 (라우트 + 게이트)."""
        self.harness.reset_traces()
        turn = self.harness.plan_turn(question)
        gated = []
        if turn.allow_search and turn.allowed_local:
            hits = self.index.search(question, k=self.settings.retrieve_k)
            gated = self.harness.gate_passages(question, hits)
        return RunResult(
            question=question,
            answer="",
            query_route=turn.to_query_route(),
            gated=gated,
            grounding=None,
            citations=[],
            tool_risks=[],
            traces=list(self.harness.traces),
            jev_live=self.settings.jev_live,
            source_plan=turn.to_source_plan(),
            turn_plan=turn,
        )

    def ask(self, question: str, *, publish: bool = False) -> RunResult:
        """분류하고 에이전트로 검색한 뒤, 답을 Jev로 채점한다."""
        self.harness.reset_traces()
        turn = self.harness.plan_turn(question)
        agent = build_agent(self.settings, self.index, self.harness)
        prompt = question
        if publish:
            prompt += "\n\n답변을 마친 뒤 publish_answer로 게시하세요."
        events: list[dict] = []
        result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        messages = result.get("messages", [])
        answer = _final_text(messages)
        gated = list(self.harness.last_gated)
        grounding = None
        citations = []
        if answer:
            grounding = self.harness.check_grounding(question, answer, gated)
            citations = self.harness.check_citations(answer, gated)
        return RunResult(
            question=question,
            answer=answer,
            query_route=turn.to_query_route(),
            gated=gated,
            grounding=grounding,
            citations=citations,
            tool_risks=list(self.harness.last_risks),
            traces=list(self.harness.traces),
            jev_live=self.settings.jev_live,
            events=events,
            source_plan=self.harness.last_plan,
            turn_plan=self.harness.last_turn,
            reconcile=self.harness.last_reconcile,
        )


def _final_text(messages: list) -> str:
    for message in reversed(messages):
        text = getattr(message, "text", None)
        if text:
            return text
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            role = getattr(message, "type", "")
            if role in {"ai", "assistant"}:
                return content
    return ""
