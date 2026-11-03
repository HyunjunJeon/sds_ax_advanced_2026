"""Jev 기반 LangChain 미들웨어. 턴 팬아웃과 게시 게이트."""

from langchain_core.language_models import BaseChatModel
from langchain_typesafe.experimental.middleware import AutoModeMiddleware

from src.harness import JevHarness
from src.middleware.turn_plan import TurnPlanMiddleware


def build_middleware(
    fast: BaseChatModel,
    powerful: BaseChatModel,
    harness: JevHarness,
    backend: object | None = None,
) -> list:
    """턴을 팬아웃하고 모델을 고정한 뒤, 게시를 라이브 Jev로 게이트한다."""
    return [
        TurnPlanMiddleware(harness, fast, powerful, backend=backend),
        AutoModeMiddleware(tools=["publish_answer"]),
    ]
