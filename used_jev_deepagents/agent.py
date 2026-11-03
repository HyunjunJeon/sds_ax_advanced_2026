"""LangGraph ``agent`` 그래프. 라이브 Jev Closed Loop."""

from src.agent.graph import build_agent
from src.observability import instrument_graph

agent = instrument_graph(build_agent(), "agent")
