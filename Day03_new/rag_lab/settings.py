"""실습 설정과 모델 생성. 키는 Day03_new/.env에서만 읽고, 값은 어디에도 출력하지 않는다."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_MODEL = "claude-sonnet-5-5"
_DEFAULT_EFFORT = "medium"
_API_URL = "https://api.anthropic.com"  # 셸의 ANTHROPIC_BASE_URL로 키가 다른 곳에 가지 않게 고정한다.
_MAX_TOKENS = 16000  # 스트리밍 없는 요청이 HTTP 제한 시간 안에 끝나는 크기다.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str = _DEFAULT_MODEL
    effort: str = _DEFAULT_EFFORT
    exa_key: str = field(repr=False, default="")

    @property
    def has_key(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def has_exa_key(self) -> bool:
        return bool(self.exa_key.strip())


def load_settings() -> Settings:
    """ROOT/.env만 읽는다. 셸이나 다른 Day에 남은 키로 모르게 과금되는 일을 막는다."""
    values = dotenv_values(ROOT / ".env")
    return Settings(
        api_key=values.get("ANTHROPIC_API_KEY") or "",
        model=values.get("DAY02_MODEL") or _DEFAULT_MODEL,
        effort=values.get("DAY02_EFFORT") or _DEFAULT_EFFORT,
        exa_key=values.get("EXA_API_KEY") or "",
    )


def key_status(settings: Settings | None = None) -> dict[str, str]:
    """키는 설정됨/미설정만 알려 준다. 값, 앞자리, 길이를 돌려주지 않는다."""
    settings = settings or load_settings()
    return {
        "ANTHROPIC_API_KEY": "설정됨" if settings.has_key else "미설정",
        "DAY02_MODEL": settings.model,
        "DAY02_EFFORT": settings.effort,
        "EXA_API_KEY": "설정됨" if settings.has_exa_key else "미설정",
    }


def require_key(settings: Settings | None = None) -> Settings:
    """키가 없으면 바로 멈춘다. 이 수업에는 키 없이 도는 경로가 없다."""
    settings = settings or load_settings()
    if not settings.has_key:
        raise RuntimeError("ANTHROPIC_API_KEY가 미설정입니다. Day03_new/.env.example을 .env로 복사한 뒤 "
                           "ANTHROPIC_API_KEY에 본인의 키를 직접 채우세요.")
    return settings


def require_exa_key(settings: Settings | None = None) -> Settings:
    """06의 필수 실습에 쓴다. 본인의 EXA 크레딧을 쓴다."""
    settings = settings or load_settings()
    if not settings.has_exa_key:
        raise RuntimeError("EXA_API_KEY가 미설정입니다. https://exa.ai/ 에서 발급해 Day03_new/.env의 EXA_API_KEY에 "
                           "본인의 키를 직접 채우세요.")
    return settings


def announce(purpose: str, *, model_calls: int | str = 0, exa_calls: int | str = 0) -> None:
    """유료 호출 직전의 규모 고지 한 줄."""
    exa = f", EXA 호출 약 {exa_calls}회" if exa_calls else ""
    print(f"[{purpose}] 이 실행은 모델 호출 약 {model_calls}회{exa}입니다. 진행합니다.")


class UsageLog(BaseCallbackHandler):
    """모델 응답마다 토큰 수만 DAY02_USAGE_LOG 파일에 한 줄씩 덧붙인다. 내용은 남기지 않는다."""

    def on_llm_end(self, response: LLMResult, **kwargs: object) -> None:
        path = os.environ.get("DAY02_USAGE_LOG")
        if not path:
            return
        message = response.generations[0][0].message
        usage = message.usage_metadata or {}
        line = {"model": message.response_metadata.get("model"), "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "cache_read_tokens": usage.get("input_token_details", {}).get("cache_read", 0)}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as log:
            log.write(json.dumps(line) + "\n")


def _redact(text: str) -> str:
    settings = load_settings()
    for key in (settings.api_key, settings.exa_key):
        text = text.replace(key, "***") if key else text
    return text


def make_model(settings: Settings | None = None, *, timeout: float = 120.0) -> ChatAnthropic:
    """temperature와 thinking은 보내지 않는다. Opus 5.5는 둘 다 400으로 거부하고 깊이는 effort로만 정한다.

    max_retries=0: SDK 재시도는 Budget과 사용량 기록에 잡히지 않으므로 일시적 429도 실패로 드러낸다.
    """
    settings = require_key(settings)
    return ChatAnthropic(
        model=settings.model, api_key=settings.api_key, base_url=_API_URL, reasoning_effort=settings.effort,
        max_tokens=_MAX_TOKENS, timeout=timeout, max_retries=0, callbacks=[UsageLog()],
        betas=[_FALLBACK_BETA], model_kwargs={"fallbacks": "default"},  # 안전 분류기 거절 시 서버가 대체 모델로 다시 실행한다.
    )
