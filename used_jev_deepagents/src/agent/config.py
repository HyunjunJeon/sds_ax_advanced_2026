"""프로젝트 설정. 채팅은 Anthropic 또는 OpenRouter, 판단은 TypeSafe Jev.

채팅 공급자는 `.env`의 `LLM_PROVIDER`로 고른다(`anthropic` 기본, `openrouter`).
게이트·그라운딩 임계값은 여기에 두고 프롬프트에 넣지 않는다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openrouter import ChatOpenRouter

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_PROVIDER = "anthropic"
# 공급자별 (fast, powerful) 모델. 턴 계획이 둘 중 하나를 고른다.
CHAT_MODELS: dict[str, tuple[str, str]] = {
    # Anthropic 직접 호출은 Haiku 5.5 한 모델로 fast·powerful을 모두 맡는다.
    "anthropic": ("claude-haiku-5-5", "claude-haiku-5-5"),
    "openrouter": ("openai/gpt-5.6-luna", "anthropic/claude-sonnet-4.6"),
}
CHAT_KEY_NAMES: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
# Anthropic 경로의 effort는 턴 계획의 thinking과 관계없이 이 값으로 고정한다.
ANTHROPIC_EFFORT = "medium"
DEFAULT_TYPESAFE_MODEL = "jev-latest"


def _load_env_files() -> None:
    """이미 내보낸 키는 덮지 않고 프로젝트 `.env`를 읽는다."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    """Jev 하네스 Deep Agents RAG 데모의 런타임 설정."""

    project_root: Path
    corpus_dir: Path
    workspace_dir: Path
    skills_dir: Path
    typesafe_api_key: str | None
    typesafe_model: str
    llm_provider: str
    anthropic_api_key: str | None
    openrouter_api_key: str | None
    exa_api_key: str | None
    fast_model: str
    powerful_model: str
    retrieve_k: int
    web_retrieve_k: int
    exa_max_chars: int
    relevant_min: float
    evidence_min: float
    contradicts_min: float
    injection_max: float
    grounding_min: float
    citation_auto: float
    risk_block: float
    complexity_compare: float
    complexity_investigate: float
    confidence_escalate: float
    jev_mode: str
    langfuse_public_key: str | None
    langfuse_secret_key: str | None
    langfuse_base_url: str
    langfuse_environment: str

    @property
    def jev_live(self) -> bool:
        """TypeSafe System One을 호출해야 하면 True."""
        # JEV_MODE=fallback이면 키가 있어도 라이브를 끈다.
        if self.jev_mode == "fallback":
            return False
        return bool(self.typesafe_api_key)

    @property
    def chat_key_name(self) -> str:
        """활성 채팅 공급자가 읽는 `.env` 키 이름."""
        return CHAT_KEY_NAMES[self.llm_provider]

    @property
    def chat_api_key(self) -> str | None:
        """활성 채팅 공급자의 키. 없으면 None."""
        if self.llm_provider == "anthropic":
            return self.anthropic_api_key
        return self.openrouter_api_key

    @property
    def langfuse_enabled(self) -> bool:
        """Langfuse 키가 있고 추적이 꺼져 있지 않으면 True."""
        flag = os.getenv("LANGFUSE_TRACING_ENABLED", "true").strip().lower()
        if flag in {"0", "false", "no", "off"}:
            return False
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


def load_settings() -> Settings:
    """프로젝트 `.env`와 하드코드 기본값으로 설정을 읽는다."""
    _load_env_files()
    root = PROJECT_ROOT
    provider = resolve_provider(os.getenv("LLM_PROVIDER"))
    fast_model, powerful_model = CHAT_MODELS[provider]
    return Settings(
        project_root=root,
        corpus_dir=root / "corpus",
        workspace_dir=root / "workspace",
        skills_dir=root / "workspace" / "skills",
        typesafe_api_key=_optional("TYPESAFE_API_KEY"),
        typesafe_model=os.getenv("TYPESAFE_MODEL", DEFAULT_TYPESAFE_MODEL),
        llm_provider=provider,
        anthropic_api_key=_optional("ANTHROPIC_API_KEY"),
        openrouter_api_key=_optional("OPENROUTER_API_KEY"),
        exa_api_key=_optional("EXA_API_KEY"),
        fast_model=fast_model,
        powerful_model=powerful_model,
        retrieve_k=int(os.getenv("RETRIEVE_K", "8")),
        web_retrieve_k=int(os.getenv("WEB_RETRIEVE_K", "5")),
        exa_max_chars=int(os.getenv("EXA_MAX_CHARS", "1000")),
        # 게이트·그라운딩·라우팅 임계값. 프롬프트가 아니라 코드 정책.
        relevant_min=0.40,
        evidence_min=0.50,
        contradicts_min=0.85,
        injection_max=0.70,
        grounding_min=0.50,
        citation_auto=0.70,
        risk_block=0.50,
        complexity_compare=0.55,
        complexity_investigate=0.80,
        confidence_escalate=0.55,
        jev_mode=os.getenv("JEV_MODE", "auto"),
        langfuse_public_key=_optional("LANGFUSE_PUBLIC_KEY"),
        langfuse_secret_key=_optional("LANGFUSE_SECRET_KEY"),
        langfuse_base_url=(
            _optional("LANGFUSE_BASE_URL")
            or _optional("LANGFUSE_HOST")
            or "https://cloud.langfuse.com"
        ),
        langfuse_environment=os.getenv("LANGFUSE_TRACING_ENVIRONMENT", "demo"),
    )


def resolve_provider(raw: str | None) -> str:
    """`LLM_PROVIDER` 값을 공급자 이름으로 바꾼다. 비어 있으면 기본값을 쓴다."""
    value = (raw or "").strip().strip("'\"").lower() or DEFAULT_PROVIDER
    if value not in CHAT_MODELS:
        allowed = ", ".join(sorted(CHAT_MODELS))
        raise ValueError(f"LLM_PROVIDER={value!r} is not supported. Use one of: {allowed}.")
    return value


def chat_model(
    settings: Settings,
    model_name: str,
    thinking_effort: str | None = None,
) -> BaseChatModel:
    """활성 공급자(`settings.llm_provider`)의 채팅 모델을 만든다.

    Anthropic 경로는 `thinking_effort`를 쓰지 않고 `ANTHROPIC_EFFORT`로 고정한다.
    """
    if not settings.chat_api_key:
        raise RuntimeError(
            f"{settings.chat_key_name} is required for LLM_PROVIDER="
            f"{settings.llm_provider}. Put it in the project .env."
        )
    if settings.llm_provider == "anthropic":
        return ChatAnthropic(
            model=model_name,
            api_key=settings.chat_api_key,
            # temperature는 보내지 않는다. Claude 5.5 모델은 기본값이 아닌
            # 샘플링 값을 400으로 거절한다.
            reasoning_effort=ANTHROPIC_EFFORT,
            max_tokens=16_000,
            # ChatAnthropic.timeout은 초 단위다(ChatOpenRouter는 밀리초).
            timeout=120,
        )
    reasoning = (
        {"effort": thinking_effort} if thinking_effort else None
    )
    return ChatOpenRouter(
        model=model_name,
        api_key=settings.chat_api_key,
        temperature=0,
        # ChatOpenRouter.timeout은 초가 아니라 밀리초.
        timeout=120_000,
        reasoning=reasoning,
    )


def with_thinking(model: BaseChatModel, thinking_effort: str) -> BaseChatModel:
    """턴 계획의 thinking을 채팅 모델에 고정한다.

    OpenRouter는 reasoning effort를 계획 값으로 바꾼다. Anthropic은 effort가
    `ANTHROPIC_EFFORT`로 고정이라 모델을 그대로 돌려준다.
    """
    if isinstance(model, ChatAnthropic):
        return model
    return model.model_copy(update={"reasoning": {"effort": thinking_effort}})


def _optional(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value or None
