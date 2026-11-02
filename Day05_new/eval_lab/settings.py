"""실습 설정과 모델 생성. 키는 Day05_new/.env에서만 읽고, 값은 어디에도 출력하지 않는다."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values
from langchain_anthropic import ChatAnthropic

ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_MODEL = "claude-sonnet-5-5"
_DEFAULT_EFFORT = "medium"
_DEFAULT_JUDGE_MODEL = "claude-sonnet-5-5"
_DEFAULT_JUDGE_EFFORT = "xhigh"  # 저자 결정: 판정자는 가장 깊게 생각하게 한다.
_DEFAULT_IMPROVER_EFFORT = "high"
_DEFAULT_ENVIRONMENT = "day05_new"
_API_URL = "https://api.anthropic.com"  # 셸의 ANTHROPIC_BASE_URL로 키가 다른 곳에 가지 않게 고정한다.
_AGENT_MAX_TOKENS = 16000  # 스트리밍 없는 요청이 HTTP 제한 시간 안에 끝나는 크기다.
_AGENT_TIMEOUT = 120.0
_JUDGE_MAX_TOKENS = 32000  # xhigh에서는 적응형 thinking이 max_tokens를 답변과 나눠 쓴다.
_JUDGE_TIMEOUT = 300.0
_ENV_FILE_VARIABLE = "DAY05_ENV_FILE"  # 테스트가 존재하지 않는 경로를 가리켜 .env 읽기를 끈다.

# 값이 비밀인 환경 변수 이름. key_status와 require가 이 목록만 다룬다.
KEY_ENV_NAMES = (
    "ANTHROPIC_API_KEY", "TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY",
)
# 테스트 fixture가 지우는 전체 목록. 키가 아닌 설정 이름도 포함한다.
ALL_ENV_NAMES = KEY_ENV_NAMES + (
    "DAY05_MODEL", "DAY05_EFFORT", "DAY05_JUDGE_MODEL", "DAY05_JUDGE_EFFORT", "DAY05_IMPROVER_EFFORT",
    "DAY05_DECISION_BACKEND", "DAY05_AZURE_ENDPOINT", "DAY05_AZURE_DEPLOYMENT",
    "LANGFUSE_HOST", "LANGFUSE_TRACING_ENVIRONMENT",
)


@dataclass(frozen=True)
class Settings:
    """실습 설정 한 벌. 키 필드는 repr에 나타나지 않는다."""

    anthropic_api_key: str = field(default="", repr=False)
    model: str = _DEFAULT_MODEL
    effort: str = _DEFAULT_EFFORT
    judge_model: str = _DEFAULT_JUDGE_MODEL
    judge_effort: str = _DEFAULT_JUDGE_EFFORT
    improver_effort: str = _DEFAULT_IMPROVER_EFFORT
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
    """Day05_new/.env 한 파일만 읽는다. 셸이나 다른 Day에 남은 키로 모르게 과금되는 일을 막는다.

    우선순위: 인자 env_file, 환경 변수 DAY05_ENV_FILE, ROOT/.env 순이다.
    가리킨 파일이 없으면 아무것도 읽지 않고 기본값 Settings를 돌려준다.
    """
    # 1단계: 읽을 파일 경로를 정한다.
    path = Path(env_file or os.environ.get(_ENV_FILE_VARIABLE) or ROOT / ".env")
    # 2단계: 파일이 있을 때만 읽는다. 셸 환경 변수는 보지 않는다.
    values = dotenv_values(path) if path.is_file() else {}
    # 3단계: 빈 값은 기본값으로 대신한다.
    return Settings(
        anthropic_api_key=values.get("ANTHROPIC_API_KEY") or "",
        model=values.get("DAY05_MODEL") or _DEFAULT_MODEL,
        effort=values.get("DAY05_EFFORT") or _DEFAULT_EFFORT,
        judge_model=values.get("DAY05_JUDGE_MODEL") or _DEFAULT_JUDGE_MODEL,
        judge_effort=values.get("DAY05_JUDGE_EFFORT") or _DEFAULT_JUDGE_EFFORT,
        improver_effort=values.get("DAY05_IMPROVER_EFFORT") or _DEFAULT_IMPROVER_EFFORT,
        typesafe_api_key=values.get("TYPESAFE_API_KEY") or "",
        openrouter_api_key=values.get("OPENROUTER_API_KEY") or "",
        openai_api_key=values.get("OPENAI_API_KEY") or "",
        azure_openai_api_key=values.get("AZURE_OPENAI_API_KEY") or "",
        decision_backend=(values.get("DAY05_DECISION_BACKEND") or "").strip().lower(),
        azure_endpoint=(values.get("DAY05_AZURE_ENDPOINT") or "").strip(),
        azure_deployment=(values.get("DAY05_AZURE_DEPLOYMENT") or "").strip(),
        langfuse_public_key=values.get("LANGFUSE_PUBLIC_KEY") or "",
        langfuse_secret_key=values.get("LANGFUSE_SECRET_KEY") or "",
        langfuse_host=(values.get("LANGFUSE_HOST") or "").strip(),
        langfuse_environment=(values.get("LANGFUSE_TRACING_ENVIRONMENT") or "").strip() or _DEFAULT_ENVIRONMENT,
    )


def key_status(settings: Settings | None = None) -> dict[str, str]:
    """키는 설정됨/미설정만 알려 준다. 값, 앞자리, 길이를 돌려주지 않는다."""
    settings = settings or load_settings()
    status: dict[str, str] = {}
    for name in KEY_ENV_NAMES:
        value = getattr(settings, name.lower())
        status[name] = "설정됨" if value.strip() else "미설정"
    return status


def require(settings: Settings, *env_names: str) -> Settings:
    """필요한 키 중 비어 있는 것이 있으면 이름만 대고 멈춘다. 값은 메시지에 담지 않는다."""
    missing = [name for name in env_names if not getattr(settings, name.lower()).strip()]
    if missing:
        raise RuntimeError(f"{', '.join(missing)}가 미설정입니다. Day05_new/.env.example을 .env로 복사한 뒤 "
                           "본인의 키를 직접 채우세요.")
    return settings


def _make_claude(settings: Settings, *, model: str, effort: str, max_tokens: int, timeout: float) -> ChatAnthropic:
    """세 모델이 공유하는 생성부. temperature와 thinking은 보내지 않고 깊이는 reasoning_effort로만 정한다.

    max_retries=0: SDK 재시도는 호출 수 집계에 잡히지 않으므로 일시적 429도 실패로 드러낸다.
    """
    settings = require(settings, "ANTHROPIC_API_KEY")
    return ChatAnthropic(
        model=model, api_key=settings.anthropic_api_key, base_url=_API_URL,
        reasoning_effort=effort, max_tokens=max_tokens, timeout=timeout, max_retries=0,
    )


def make_agent_model(settings: Settings) -> ChatAnthropic:
    """평가 대상 에이전트용 모델. settings.model과 settings.effort, max_tokens 16000, timeout 120초."""
    return _make_claude(settings, model=settings.model, effort=settings.effort,
                        max_tokens=_AGENT_MAX_TOKENS, timeout=_AGENT_TIMEOUT)


def make_judge_model(settings: Settings) -> ChatAnthropic:
    """판정자(Judge)용 모델. judge_model과 judge_effort(기본 xhigh), max_tokens 32000, timeout 300초."""
    return _make_claude(settings, model=settings.judge_model, effort=settings.judge_effort,
                        max_tokens=_JUDGE_MAX_TOKENS, timeout=_JUDGE_TIMEOUT)


def make_improver_model(settings: Settings) -> ChatAnthropic:
    """개선안 제안용 모델. settings.model과 improver_effort(기본 high), max_tokens 16000, timeout 120초."""
    return _make_claude(settings, model=settings.model, effort=settings.improver_effort,
                        max_tokens=_AGENT_MAX_TOKENS, timeout=_AGENT_TIMEOUT)


def make_langfuse(settings: Settings | None = None):
    """Langfuse 클라이언트를 만든다. 두 LANGFUSE 키가 없으면 이름만 대고 멈춘다.

    LANGFUSE_HOST가 있으면 그 주소를, 없으면 라이브러리 기본 주소를 쓴다.
    """
    from langfuse import Langfuse  # 키가 필요 없는 경로에서 import 비용을 내지 않는다.

    settings = require(settings or load_settings(), "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY")
    options: dict[str, str] = {
        "public_key": settings.langfuse_public_key,
        "secret_key": settings.langfuse_secret_key,
    }
    if settings.langfuse_host:
        options["host"] = settings.langfuse_host
    return Langfuse(**options)
