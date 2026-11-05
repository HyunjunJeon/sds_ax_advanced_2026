"""실습 설정과 모델 생성. 키는 Day04_new/.env에서만 읽고, 값은 어디에도 출력하지 않는다."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values
from langchain_anthropic import ChatAnthropic

ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_MODEL = "claude-sonnet-5-5"
_DEFAULT_EFFORT = "medium"
_DEFAULT_ENVIRONMENT = "day04_new"
_API_URL = "https://api.anthropic.com"  # 셸의 ANTHROPIC_BASE_URL로 키가 다른 곳에 가지 않게 고정한다.
_MAX_TOKENS = 16000  # 스트리밍 없는 요청이 HTTP 제한 시간 안에 끝나는 크기다.
_ENV_FILE_VARIABLE = (
    "DAY04_ENV_FILE"  # 테스트가 존재하지 않는 경로를 가리켜 .env 읽기를 끈다.
)

# 값이 비밀인 환경 변수 이름. key_status와 require가 이 목록만 다룬다.
KEY_ENV_NAMES = (
    "ANTHROPIC_API_KEY",
    "TYPESAFE_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)
# 테스트 fixture가 지우는 전체 목록. 키가 아닌 설정 이름도 포함한다.
ALL_ENV_NAMES = KEY_ENV_NAMES + (
    "DAY04_MODEL",
    "DAY04_EFFORT",
    "DAY04_DECISION_BACKEND",
    "DAY04_AZURE_ENDPOINT",
    "DAY04_AZURE_DEPLOYMENT",
    "LANGFUSE_HOST",
    "LANGFUSE_TRACING_ENVIRONMENT",
)


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = field(default="", repr=False)
    model: str = _DEFAULT_MODEL
    effort: str = _DEFAULT_EFFORT
    typesafe_api_key: str = field(default="", repr=False)
    openrouter_api_key: str = field(default="", repr=False)
    openai_api_key: str = field(default="", repr=False)
    azure_openai_api_key: str = field(default="", repr=False)
    decision_backend: str = ""
    azure_endpoint: str = ""
    azure_deployment: str = ""
    langfuse_public_key: str = field(default="", repr=False)
    langfuse_secret_key: str = field(default="", repr=False)
    langfuse_host: str = ""
    langfuse_environment: str = _DEFAULT_ENVIRONMENT


def load_settings(env_file: Path | str | None = None) -> Settings:
    """Day04_new/.env 한 파일만 읽는다. 셸이나 다른 Day에 남은 키로 모르게 과금되는 일을 막는다.

    우선순위: 인자 env_file, 환경 변수 DAY04_ENV_FILE, ROOT/.env 순이다. 가리킨 파일이 없으면 아무것도 읽지 않는다.
    """
    path = Path(env_file or os.environ.get(_ENV_FILE_VARIABLE) or ROOT / ".env")
    values = dotenv_values(path) if path.is_file() else {}
    return Settings(
        anthropic_api_key=values.get("ANTHROPIC_API_KEY") or "",
        model=values.get("DAY04_MODEL") or _DEFAULT_MODEL,
        effort=values.get("DAY04_EFFORT") or _DEFAULT_EFFORT,
        typesafe_api_key=values.get("TYPESAFE_API_KEY") or "",
        openrouter_api_key=values.get("OPENROUTER_API_KEY") or "",
        openai_api_key=values.get("OPENAI_API_KEY") or "",
        azure_openai_api_key=values.get("AZURE_OPENAI_API_KEY") or "",
        decision_backend=(values.get("DAY04_DECISION_BACKEND") or "").strip().lower(),
        azure_endpoint=(values.get("DAY04_AZURE_ENDPOINT") or "").strip(),
        azure_deployment=(values.get("DAY04_AZURE_DEPLOYMENT") or "").strip(),
        langfuse_public_key=values.get("LANGFUSE_PUBLIC_KEY") or "",
        langfuse_secret_key=values.get("LANGFUSE_SECRET_KEY") or "",
        langfuse_host=(values.get("LANGFUSE_HOST") or "").strip(),
        langfuse_environment=(values.get("LANGFUSE_TRACING_ENVIRONMENT") or "").strip()
        or _DEFAULT_ENVIRONMENT,
    )


def key_status(settings: Settings | None = None) -> dict[str, str]:
    """키는 설정됨/미설정만 알려 준다. 값, 앞자리, 길이를 돌려주지 않는다."""
    settings = settings or load_settings()
    return {
        name: "설정됨" if getattr(settings, name.lower()).strip() else "미설정"
        for name in KEY_ENV_NAMES
    }


def require(settings: Settings, *env_names: str) -> Settings:
    """필요한 키 중 비어 있는 것이 있으면 이름만 대고 멈춘다. 값은 메시지에 담지 않는다."""
    missing = [
        name for name in env_names if not getattr(settings, name.lower()).strip()
    ]
    if missing:
        raise RuntimeError(
            f"{', '.join(missing)}가 미설정입니다. Day04_new/.env.example을 .env로 복사한 뒤 "
            "본인의 키를 직접 채우세요."
        )
    return settings


def make_model(settings: Settings, *, timeout: float = 120.0) -> ChatAnthropic:
    """temperature와 thinking은 보내지 않는다. 깊이는 reasoning_effort로만 정한다.

    max_retries=0: SDK 재시도는 호출 수 집계에 잡히지 않으므로 일시적 429도 실패로 드러낸다.
    """
    settings = require(settings, "ANTHROPIC_API_KEY")
    return ChatAnthropic(
        model=settings.model,
        api_key=settings.anthropic_api_key,
        base_url=_API_URL,
        reasoning_effort=settings.effort,
        max_tokens=_MAX_TOKENS,
        timeout=timeout,
        max_retries=0,
    )
