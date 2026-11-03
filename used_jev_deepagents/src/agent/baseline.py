"""판단이 Jev가 아니라 LLM tool-call인 Deep Agent.

슬롯은 agent와 같고, 팬아웃 대신 패시지마다 한 번 호출한다.
"""

from __future__ import annotations

from deepagents import CompiledSubAgent, create_deep_agent

from src.agent.backend import build_backend
from src.agent.config import Settings, chat_model, load_settings
from src.llm_harness import LlmHarness
from src.middleware.turn_plan import TurnPlanMiddleware
from src.prompts import CHUNK_ANALYST, load_baseline_instructions
from src.retriever import CorpusIndex
from src.tools import build_tools


def build_baseline_agent(
    settings: Settings | None = None,
    index: CorpusIndex | None = None,
    harness: LlmHarness | None = None,
):
    """Agent Chat UI용 LLM 판단 Deep Agent(`baseline`)를 컴파일한다."""
    settings = settings or load_settings()
    if not settings.chat_api_key:
        raise RuntimeError(f"{settings.chat_key_name} is required for the LLM baseline.")
    index = index or CorpusIndex(settings.corpus_dir)
    fast = chat_model(settings, settings.fast_model)
    harness = harness or LlmHarness(settings, model=fast)
    backend = build_backend(settings)
    tools = build_tools(index, harness, backend, settings)
    chunk_analyst = create_deep_agent(
        model=fast,
        system_prompt=CHUNK_ANALYST,
        tools=[],
        name="chunk-analyst",
    )
    return create_deep_agent(
        model=fast,
        tools=tools,
        backend=backend,
        system_prompt=load_baseline_instructions(),
        subagents=[
            CompiledSubAgent(
                name="chunk-analyst",
                description=(
                    "Extract facts from one /retrieved/ file. "
                    "Do not classify support or conflict."
                ),
                runnable=chunk_analyst,
            )
        ],
        middleware=[TurnPlanMiddleware(harness, fast, fast, backend=backend)],
        name="llm-rag",
    )
