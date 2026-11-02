"""실습 설정과 모델 생성. 키는 Day02_new/.env에서만 읽고, 값은 어디에도 출력하지 않는다."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import dotenv_values
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

if TYPE_CHECKING:
    from rag_lab.embeddings import LocalE5Embeddings
    from rag_lab.rerank import CrossEncoderReranker

ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_MODEL = "claude-sonnet-5-5"
_DEFAULT_EFFORT = "medium"
_DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
_DEFAULT_RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
_API_URL = "https://api.anthropic.com"  # 셸의 ANTHROPIC_BASE_URL로 키가 다른 곳에 가지 않게 고정한다.
_MAX_TOKENS = 16000  # 스트리밍 없는 요청이 HTTP 제한 시간 안에 끝나는 크기다.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str = _DEFAULT_MODEL
    effort: str = _DEFAULT_EFFORT
    embedding_model: str = _DEFAULT_EMBEDDING_MODEL
    rerank_model: str = _DEFAULT_RERANK_MODEL
    typesafe_api_key: str = field(default="", repr=False)
    openrouter_api_key: str = field(default="", repr=False)
    openai_api_key: str = field(default="", repr=False)
    azure_openai_api_key: str = field(default="", repr=False)
    azure_endpoint: str = ""
    azure_deployment: str = ""
    openrouter_model: str = ""
    decision_backend: str = ""

    @property
    def has_key(self) -> bool:
        return bool(self.api_key.strip())


def load_settings() -> Settings:
    """ROOT/.env만 읽는다. 셸이나 다른 Day에 남은 키로 모르게 과금되는 일을 막는다."""
    values = dotenv_values(ROOT / ".env")
    return Settings(
        api_key=values.get("ANTHROPIC_API_KEY") or "",
        model=values.get("DAY02_MODEL") or _DEFAULT_MODEL,
        effort=values.get("DAY02_EFFORT") or _DEFAULT_EFFORT,
        embedding_model=values.get("DAY02_EMBEDDING_MODEL") or _DEFAULT_EMBEDDING_MODEL,
        rerank_model=values.get("DAY02_RERANK_MODEL") or _DEFAULT_RERANK_MODEL,
        typesafe_api_key=values.get("TYPESAFE_API_KEY") or "",
        openrouter_api_key=values.get("OPENROUTER_API_KEY") or "",
        openai_api_key=values.get("OPENAI_API_KEY") or "",
        azure_openai_api_key=values.get("AZURE_OPENAI_API_KEY") or "",
        azure_endpoint=(values.get("DAY02_AZURE_ENDPOINT") or "").strip(),
        azure_deployment=(values.get("DAY02_AZURE_DEPLOYMENT") or "").strip(),
        openrouter_model=(values.get("DAY02_OPENROUTER_MODEL") or "").strip(),
        decision_backend=(values.get("DAY02_DECISION_BACKEND") or "").strip().lower(),
    )


def key_status(settings: Settings | None = None) -> dict[str, str]:
    """키는 설정됨/미설정만 알려 준다. 값, 앞자리, 길이를 돌려주지 않는다."""
    settings = settings or load_settings()
    return {
        "ANTHROPIC_API_KEY": "설정됨" if settings.has_key else "미설정",
        "DAY02_MODEL": settings.model,
        "DAY02_EFFORT": settings.effort,
        "DAY02_EMBEDDING_MODEL": settings.embedding_model,
        "DAY02_RERANK_MODEL": settings.rerank_model,
        **{name: "설정됨" if getattr(settings, name.lower()).strip() else "미설정"
           for name in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY")},
        "DAY02_DECISION_BACKEND": settings.decision_backend,
    }


def require_key(settings: Settings | None = None) -> Settings:
    """키가 없으면 바로 멈춘다. 이 수업에는 키 없이 도는 경로가 없다."""
    settings = settings or load_settings()
    if not settings.has_key:
        raise RuntimeError("ANTHROPIC_API_KEY가 미설정입니다. Day02_new/.env.example을 .env로 복사한 뒤 "
                           "ANTHROPIC_API_KEY에 본인의 키를 직접 채우세요.")
    return settings


def announce(purpose: str, *, model_calls: int = 0) -> None:
    """유료 호출 직전의 규모 고지 한 줄."""
    print(f"[{purpose}] 이 실행은 모델 호출 약 {model_calls}회입니다. 진행합니다.")


def _cache_writes(details: dict) -> tuple[int, int]:
    """(캐시 쓰기 전체, 그중 1시간 TTL). langchain-anthropic은 TTL별 수치가 있으면 cache_creation을 0으로 비운다.

    그래서 쓰기는 TTL별 합이 있으면 그것을, 없으면 cache_creation을 쓴다. 둘을 더하지 않는다.
    """
    five_minutes = details.get("ephemeral_5m_input_tokens") or 0
    one_hour = details.get("ephemeral_1h_input_tokens") or 0
    return (five_minutes + one_hour) or (details.get("cache_creation") or 0), one_hour


def append_usage(line: dict) -> None:
    """DAY02_USAGE_LOG 파일에 사용량 한 줄을 덧붙인다. 환경 변수가 없으면 아무것도 하지 않는다."""
    path = os.environ.get("DAY02_USAGE_LOG")
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as log:
            log.write(json.dumps(line) + "\n")


class UsageLog(BaseCallbackHandler):
    """모델 응답마다 토큰 수만 DAY02_USAGE_LOG 파일에 한 줄씩 덧붙인다. 내용은 남기지 않는다."""

    def on_llm_end(self, response: LLMResult, **kwargs: object) -> None:
        message = response.generations[0][0].message
        usage = message.usage_metadata or {}
        details = usage.get("input_token_details", {})
        written, one_hour = _cache_writes(details)
        line = {"model": message.response_metadata.get("model"), "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0), "cache_read_tokens": details.get("cache_read", 0),
                "cache_write_tokens": written}
        if one_hour:
            line["cache_write_1h_tokens"] = one_hour  # cache_write_tokens에 이미 포함된 1시간 TTL 몫
        append_usage(line)


def _redact(text: str) -> str:
    s = load_settings()
    for key in (s.api_key, s.typesafe_api_key, s.openrouter_api_key, s.openai_api_key, s.azure_openai_api_key):
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


def make_embeddings(settings: Settings | None = None) -> LocalE5Embeddings:
    """API를 부르지 않는 로컬 임베딩. 첫 호출 때 모델 파일을 내려받는다. 키는 필요 없다."""
    from rag_lab.embeddings import LocalE5Embeddings  # torch 적재가 느려 쓸 때만 import한다.

    return LocalE5Embeddings((settings or load_settings()).embedding_model)


def make_reranker(settings: Settings | None = None) -> CrossEncoderReranker:
    """API를 부르지 않는 로컬 교차 인코더. 첫 호출 때 모델 파일을 내려받는다. 키는 필요 없다."""
    from rag_lab.rerank import CrossEncoderReranker  # torch 적재가 느려 쓸 때만 import한다.

    return CrossEncoderReranker((settings or load_settings()).rerank_model)
