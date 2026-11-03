"""LangGraph 서버와 CLI가 쓰는 Deep Agent 팩토리.

라이브 Jev가 있어야 라우팅과 Auto Mode가 돈다.
chunk-analyst는 사실만 베끼고 관계 판단은 하지 않는다.
"""

from __future__ import annotations

from deepagents import CompiledSubAgent, create_deep_agent

from src.agent.backend import build_backend
from src.agent.config import Settings, chat_model, load_settings
from src.harness import JevHarness
from src.middleware import build_middleware
from src.prompts import CHUNK_ANALYST, load_instructions
from src.retriever import CorpusIndex
from src.tools import build_tools


def build_agent(
    settings: Settings | None = None,
    index: CorpusIndex | None = None,
    harness: JevHarness | None = None,
):
    """Agent Chat UI용 Jev 하네스 Deep Agent를 컴파일한다."""
    settings = settings or load_settings()
    if not settings.jev_live:
        raise RuntimeError("TYPESAFE_API_KEY is required for live Jev routing and Auto Mode.")
    index = index or CorpusIndex(settings.corpus_dir)
    harness = harness or JevHarness(settings)
    backend = build_backend(settings)
    tools = build_tools(index, harness, backend, settings)
    fast = chat_model(settings, settings.fast_model)
    powerful = chat_model(settings, settings.powerful_model)
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
        skills=["/skills/"],
        system_prompt=load_instructions(),
        subagents=[
            CompiledSubAgent(
                name="chunk-analyst",
                description=(
                    "Extract facts from one /retrieved/ file. "
                    "Do not classify support or conflict — Jev judge_evidence does that."
                ),
                runnable=chunk_analyst,
            )
        ],
        middleware=build_middleware(fast, powerful, harness, backend),
        name="jev-sample-rag",
    )
