"""LangGraph ``baseline`` 그래프. LLM tool-call 판단."""

from src.agent.baseline import build_baseline_agent
from src.observability import instrument_graph

baseline = instrument_graph(build_baseline_agent(), "baseline")
