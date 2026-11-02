"""Day02_new/rag_lab/decisions.py에서 가져와 고친 사본이다. 바이트 동일 사본이 아니다.

Decision API 계층. 질문(Noul/Choice/Score)에 대한 판단을 공급자와 무관하게 받는다.
사용량은 파일에 쓰지 않고 on_usage 콜백으로만 내보낸다.

확률은 보정(calibration)을 가정하지 않는다. 문턱값은 호출하는 쪽이 본인의 라벨로 재서 정한다.
질문 문장과 근거(state)는 선택한 공급자에게 그대로 전송된다.
새 Decision API는 _HttpBackend를 상속해 _body·_verdicts를 적고 BACKENDS에 등록하면 된다.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import ClassVar, Protocol

import httpx

from cap_lab.settings import Settings, load_settings

UsageCallback = Callable[[dict], None]

_TIMEOUT = 15.0  # AutoRAG와 같은 값. 재시도는 없다.


@dataclass(frozen=True)
class Noul:
    """참/거짓 질문. true와 false는 각 판정의 기준 문장이다."""
    kind: ClassVar[str] = "noul"
    name: str
    instructions: str
    true: str
    false: str


@dataclass(frozen=True)
class Choice:
    """하나를 고르는 질문. options는 {라벨: 의미}다."""
    kind: ClassVar[str] = "choice"
    name: str
    instructions: str
    options: dict[str, str]


@dataclass(frozen=True)
class Score:
    """순서 있는 단계 질문. levels[0]이 가장 낮은 단계다."""
    kind: ClassVar[str] = "score"
    name: str
    instructions: str
    levels: list[str]


Question = Noul | Choice | Score


@dataclass(frozen=True)
class Verdict:
    """질문 하나의 답. 모델이 거절했거나 답이 빠졌으면 refused=True이고 나머지는 비어 있다."""
    name: str
    kind: str
    probability: float | None = None
    choice: str | None = None
    score: float | None = None
    probabilities: dict[str, float] = field(default_factory=dict)
    confidence: float | None = None
    refused: bool = False


@dataclass(frozen=True)
class Judgment:
    """judge() 한 번의 결과. cost는 공급자가 알려 준 경우에만 값이 있다."""
    verdicts: dict[str, Verdict]
    backend: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float | None = None


class DecisionError(RuntimeError):
    """전송, HTTP, 응답 형식 실패. 메시지에는 종류와 HTTP 상태만 담고 키와 state는 담지 않는다."""


class DecisionBackend(Protocol):
    name: str

    def judge(self, state: str, questions: list[Question]) -> Judgment: ...


class _HttpBackend:
    name, key_env, base_url, path, model = "", "", "", "", ""  # 하위 클래스가 채운다.
    auth_header, auth_scheme = "Authorization", "Bearer "

    def __init__(self, api_key: str, base_url: str | None = None, client: httpx.Client | None = None, model: str | None = None,
                 on_usage: UsageCallback | None = None) -> None:
        self._api_key, self._client, self._on_usage = api_key, client or httpx.Client(), on_usage
        self._base_url, self.model = (base_url or self.base_url).rstrip("/"), model or self.model

    def judge(self, state: str, questions: list[Question]) -> Judgment:
        try:
            response = self._client.post(self._base_url + self.path, json=self._body(state, questions), timeout=_TIMEOUT, headers={self.auth_header: self.auth_scheme + self._api_key})
        except httpx.HTTPError as error:
            raise DecisionError(f"{self.name}: 전송 실패 {type(error).__name__}") from None
        if response.status_code >= 400:
            raise DecisionError(f"{self.name}: HTTP {response.status_code}")
        try:
            data = response.json()
            usage = data.get("usage") or {}
            judgment = Judgment(self._verdicts(data.get("answers"), questions), self.name, data.get("model") or self.model,
                                int(usage.get("input_tokens") or 0), int(usage.get("output_tokens") or 0), usage.get("cost"))
        except (AttributeError, TypeError, ValueError):
            raise DecisionError(f"{self.name}: 응답 형식 오류") from None
        if self._on_usage:
            self._on_usage({"model": judgment.model, "input_tokens": judgment.input_tokens,
                            "output_tokens": judgment.output_tokens, **({"cost": judgment.cost} if judgment.cost is not None else {})})
        return judgment



class _NativeBackend(_HttpBackend):
    """Jev 고유 방언. 질문은 이름을 키로 하는 map이고 답도 이름을 키로 하는 map이다."""

    def _body(self, state: str, questions: list[Question]) -> dict:
        wire = {q.name: {"type": q.kind, "instructions": q.instructions, "criteria": {"true": q.true, "false": q.false} if isinstance(q, Noul)
                         else q.options if isinstance(q, Choice) else q.levels} for q in questions}
        return {"model": self.model, "state": state, "questions": wire}

    def _verdicts(self, answers: object, questions: list[Question]) -> dict[str, Verdict]:
        # 거절했거나 답이 빠졌으면 refused다.
        return {q.name: Verdict(q.name, q.kind, refused=True) if (a := answers.get(q.name)) is None or a.get(q.kind) is None
                else Verdict(q.name, q.kind, probability=float(a["noul"]) if q.kind == "noul" else None, choice=a.get("choice"),
                             score=a.get("score"), confidence=a.get("confidence"), probabilities=a.get("probabilities") or {})
                for q in questions}


class TypeSafeBackend(_NativeBackend):
    name, key_env, base_url, path, model = "typesafe", "TYPESAFE_API_KEY", "https://api.typesafe.ai", "/v1/systemone", "jev-latest"


class OpenRouterBackend(_NativeBackend):
    # 알파 엔드포인트라 경로가 옮겨질 수 있다. jev-latest는 HTTP 400이라 1.13으로 고정한다.
    # 이 id는 미확인이다: OpenRouter 모델 페이지가 2026-11-01에 404였다.
    name, key_env, base_url, path, model = "openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai", "/api/alpha/decisions", "typesafe/jev-1.13"


class OpenAIDecisionsBackend(_HttpBackend):
    """OpenAI Decisions. criteria 필드가 없어 참/거짓 기준은 instructions 문장에 합친다. 답은 목록이다."""
    name, key_env, base_url, path, model = "openai", "OPENAI_API_KEY", "https://api.openai.com", "/v1/decisions", "gpt-6-luna"
    _KINDS = {"noul": "predicate", "choice": "choice", "score": "score"}

    def _body(self, state: str, questions: list[Question]) -> dict:
        wire = []
        for q in questions:
            item = {"type": self._KINDS[q.kind], "name": q.name, "instructions": q.instructions}
            if isinstance(q, Noul):
                item["instructions"] += f"\n참이면: {q.true}\n거짓이면: {q.false}"
            elif isinstance(q, Choice):
                item["choices"] = [{"value": value, "description": meaning} for value, meaning in q.options.items()]
            else:
                item["levels"] = [{"label": level, "description": level} for level in q.levels]
            wire.append(item)
        return {"model": self.model, "input": state, "questions": wire}

    def _verdicts(self, answers: object, questions: list[Question]) -> dict[str, Verdict]:
        by_name = {a.get("name"): a for a in answers}
        # refusal이거나 답이 빠졌으면 refused다. refusal의 name은 null일 수 있다.
        return {q.name: Verdict(q.name, q.kind, refused=True) if (a := by_name.get(q.name)) is None or a.get("type") != self._KINDS[q.kind]
                else Verdict(q.name, q.kind, probability=a.get("probability"), choice=a.get("choice"), score=a.get("score"),
                             confidence=a.get("confidence"),
                             probabilities={str(p["label" if q.kind == "score" else "value"]): p["probability"] for p in a.get("probabilities", [])})
                for q in questions}


class AzureOpenAIDecisionsBackend(OpenAIDecisionsBackend):
    """Azure OpenAI. 본문과 해석은 OpenAI와 같다. base_url은 리소스 endpoint, model은 배포 이름이고 키는 api-key 헤더로 보낸다."""
    name, key_env, base_url, path, model = "azure", "AZURE_OPENAI_API_KEY", "", "/openai/v1/decisions", ""
    auth_header, auth_scheme = "api-key", ""


BACKENDS: dict[str, type[_HttpBackend]] = {cls.name: cls for cls in (TypeSafeBackend, OpenRouterBackend, OpenAIDecisionsBackend, AzureOpenAIDecisionsBackend)}


def make_decider(settings: Settings | None = None, *, on_usage: UsageCallback | None = None) -> DecisionBackend:
    """DAY04_DECISION_BACKEND로 고른다. 비어 있으면 TYPESAFE, OPENROUTER, OPENAI, AZURE 순으로 키가 있는 첫 번째를 쓴다.

    Claude로 대신하는 경로는 없다. 키가 없으면 멈춘다.
    """
    settings = settings or load_settings()
    if settings.decision_backend and settings.decision_backend not in BACKENDS:
        raise RuntimeError(f"DAY04_DECISION_BACKEND는 {', '.join(BACKENDS)} 중 하나여야 합니다.")
    candidates = [BACKENDS[settings.decision_backend]] if settings.decision_backend else list(BACKENDS.values())
    for cls in candidates:
        key = getattr(settings, cls.key_env.lower())
        if not key.strip():
            continue
        if cls is AzureOpenAIDecisionsBackend:
            if not (settings.azure_endpoint.strip() and settings.azure_deployment.strip()):
                raise RuntimeError("AZURE_OPENAI_API_KEY가 있으면 DAY04_AZURE_ENDPOINT와 DAY04_AZURE_DEPLOYMENT도 필요합니다. Day04_new/.env에 직접 채우세요.")
            return cls(key, settings.azure_endpoint.strip(), model=settings.azure_deployment.strip(), on_usage=on_usage)
        return cls(key, on_usage=on_usage)
    raise RuntimeError(f"{', '.join(cls.key_env for cls in candidates)} 중 사용할 키가 미설정입니다. "
                       "Day04_new/.env.example을 .env로 복사한 뒤 본인의 키를 직접 채우세요.")
