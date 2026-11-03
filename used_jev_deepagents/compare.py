"""Jev vs LLM tool-call 스코어보드를 찍는 LangGraph 어시스턴트."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from src.compare_run import compare_one, render_markdown
from src.observability import instrument_graph
from src.quality import CASES


class CompareState(TypedDict):
    """compare 어시스턴트의 채팅 상태."""

    messages: Annotated[list[AnyMessage], add_messages]


def _latest_question(state: CompareState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            content = message.content
            if isinstance(content, str) and content.strip():
                return content.strip()
    return CASES[1].question


def compare_node(state: CompareState) -> dict:
    """두 판단 엔진을 돌리고 마크다운 표로 답한다."""
    question = _latest_question(state)
    # 한 질문이 아니라 골드 스위트 전체를 표로 보고 싶을 때.
    if question in {"비교", "compare", "suite", "전체"}:
        from src.compare_run import render_suite, run_suite

        return {"messages": [AIMessage(content=render_suite(run_suite()))]}
    report = compare_one(question)
    return {"messages": [AIMessage(content=render_markdown(report))]}


_graph = StateGraph(CompareState)
_graph.add_node("compare", compare_node)
_graph.add_edge(START, "compare")
_graph.add_edge("compare", END)
compare = instrument_graph(_graph.compile(), "compare")
