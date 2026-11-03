"""TypeSafe System One 클라이언트. SDK·키가 없으면 로컬 대용으로 돌린다.

라이브 호출이 실패해도 데모가 멈추지 않게 한다.
UI는 어느 백엔드가 답했는지 항상 라벨을 붙인다.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from src.agent.config import Settings
from src.schemas import DecisionTrace

try:
    from typesafe_sdk import Choice, Noul, Score, TypeSafeClient
except ImportError:  # pragma: no cover - installed in the project env
    Choice = Noul = Score = TypeSafeClient = None  # type: ignore[assignment]


@dataclass
class AskResult:
    """한 System One 요청의 정규화된 답."""

    nouls: dict[str, float] = field(default_factory=dict)
    choices: dict[str, str] = field(default_factory=dict)
    probabilities: dict[str, dict[str, float]] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    live: bool = False
    elapsed_ms: float = 0.0


class JevClient:
    """공유 state에 Noul / Choice / Score를 묻는다."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Any = None
        if settings.jev_live and TypeSafeClient is not None:
            self._client = TypeSafeClient(api_key=settings.typesafe_api_key)

    def ask(
        self,
        *,
        stage: str,
        state: str | dict[str, Any],
        questions: dict[str, Any],
        note: str = "",
    ) -> tuple[AskResult, DecisionTrace]:
        """``state``에 ``questions``를 평가하고 UI 트레이스를 남긴다."""
        started = time.perf_counter()
        if self._client is not None:
            try:
                result = self._ask_live(state, questions)
            except Exception as exc:  # noqa: BLE001 - 데모는 멈추지 않는다
                # 라이브 실패는 fallback으로 내리고, 카드에 실패를 표시한다.
                result = self._ask_fallback(state, questions)
                result.live = False
                note = f"Jev 호출 실패, fallback 사용: {exc}"
        else:
            result = self._ask_fallback(state, questions)
        result.elapsed_ms = (time.perf_counter() - started) * 1000
        trace = DecisionTrace(
            stage=stage,
            questions=_question_summaries(questions),
            answers=_result_payload(result),
            elapsed_ms=result.elapsed_ms,
            live=result.live,
            note=note,
        )
        from src.observability import record_jev_call

        record_jev_call(trace)
        return result, trace

    def close(self) -> None:
        """만든 HTTP 클라이언트가 있으면 닫는다."""
        if self._client is not None:
            close = getattr(self._client, "close", None)
            if callable(close):
                close()

    def _ask_live(self, state: str | dict[str, Any], questions: dict[str, Any]) -> AskResult:
        response = self._client.system_one(
            state=state,
            questions=questions,
            model=self.settings.typesafe_model,
        )
        result = AskResult(live=True)
        answers = getattr(response, "answers", {})
        for name, answer in answers.items():
            kind = getattr(answer, "type", None) or answer.__class__.__name__.lower()
            # 라이브 SDK 객체를 AskResult 슬롯으로 정규화한다.
            if hasattr(answer, "noul"):
                result.nouls[name] = float(answer.noul)
            elif hasattr(answer, "choice"):
                result.choices[name] = str(answer.choice)
                result.probabilities[name] = {
                    key: float(value) for key, value in dict(answer.probabilities).items()
                }
                result.confidence[name] = float(getattr(answer, "confidence", 0.0) or 0.0)
            elif hasattr(answer, "score"):
                result.scores[name] = float(answer.score)
                result.confidence[name] = float(getattr(answer, "confidence", 0.0) or 0.0)
            else:
                result.nouls[name] = float(getattr(answer, kind, 0.0) or 0.0)
        return result

    def _ask_fallback(
        self,
        state: str | dict[str, Any],
        questions: dict[str, Any],
    ) -> AskResult:
        text = _flatten_state(state)
        route_text = _routing_text(state)
        attached_present = _attached_present(state)
        result = AskResult(live=False)
        for name, question in questions.items():
            kind = _question_kind(question)
            target = route_text if name in _TURN_ROUTE_FIELDS else text
            if kind == "noul":
                value = _fallback_noul(
                    name,
                    question,
                    target,
                    attached_present=attached_present,
                )
                result.nouls[name] = value
            elif kind == "choice":
                choice, probs, conf = _fallback_choice(name, question, target)
                result.choices[name] = choice
                result.probabilities[name] = probs
                result.confidence[name] = conf
            else:
                score = _fallback_score(name, question, target)
                result.scores[name] = score
                result.confidence[name] = 0.72
        return result


def noul(instructions: str, criteria: dict[str, str] | None = None) -> Any:
    """Noul 질문을 만든다. SDK 타입이 있으면 그걸 쓴다."""
    if Noul is not None:
        if criteria:
            return Noul(instructions=instructions, criteria=criteria)
        return Noul(instructions=instructions)
    return {"type": "noul", "instructions": instructions, "criteria": criteria}


def choice(instructions: str, criteria: dict[str, str]) -> Any:
    """Choice 질문을 만든다."""
    if Choice is not None:
        return Choice(instructions=instructions, criteria=criteria)
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score(instructions: str, criteria: list[str]) -> Any:
    """Score 질문을 만든다."""
    if Score is not None:
        return Score(instructions=instructions, criteria=criteria)
    return {"type": "score", "instructions": instructions, "criteria": criteria}


def _question_kind(question: Any) -> str:
    if isinstance(question, dict):
        return str(question.get("type", "noul"))
    type_name = question.__class__.__name__.lower()
    if "choice" in type_name:
        return "choice"
    if "score" in type_name:
        return "score"
    return "noul"


def _question_instructions(question: Any) -> str:
    if isinstance(question, dict):
        return str(question.get("instructions", ""))
    return str(getattr(question, "instructions", "") or "")


def _question_criteria(question: Any) -> Any:
    if isinstance(question, dict):
        return question.get("criteria")
    return getattr(question, "criteria", None)


def _question_summaries(questions: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {
            "type": _question_kind(question),
            "instructions": _question_instructions(question),
        }
        for name, question in questions.items()
    }


def _result_payload(result: AskResult) -> dict[str, Any]:
    return {
        "nouls": result.nouls,
        "choices": result.choices,
        "probabilities": result.probabilities,
        "scores": result.scores,
        "confidence": result.confidence,
    }


_TURN_ROUTE_FIELDS = frozenset(
    {
        "kind",
        "sources",
        "analysis",
        "thinking",
        "complexity",
        "need_local",
        "need_web",
        "need_fresh_web",
        "need_search",
        "need_attachment",
        "jailbreak",
    }
)


def _routing_text(state: str | dict[str, Any]) -> str:
    """턴 라우팅은 질문 문장만 본다. corpus_topics가 로컬 힌트를 오염시키지 않게 한다."""
    if isinstance(state, dict) and "question" in state:
        return str(state.get("question") or "")
    return _flatten_state(state)


def _attached_present(state: str | dict[str, Any]) -> bool:
    if isinstance(state, dict):
        return bool(state.get("attached"))
    return False


def _flatten_state(state: str | dict[str, Any]) -> str:
    if isinstance(state, str):
        return state
    parts: list[str] = []
    for key, value in state.items():
        if isinstance(value, dict):
            parts.append(f"{key}: {_flatten_state(value)}")
        else:
            parts.append(f"{key}: {value}")
    return "\n".join(parts)


_INJECTION_PATTERNS = (
    r"ignore (all )?previous",
    r"you must",
    r"system prompt",
    r"hunter2",
    r"이전 지시",
    r"온콜 비번",
    r"do not cite",
    r"tell the (user|model)",
    r"password is",
)

_COMPARE_HINTS = ("비교", "차이", " vs ", "versus", "그리고", "와 ", "과 ")
_INVESTIGATE_HINTS = ("왜", "어떻게", "절차", "조사", "분석", "동작", "why", "how")
_LOCAL_HINTS = (
    "jev",
    "deep agent",
    "deepagents",
    "sla",
    "로그",
    "알파",
    "온콜",
    "sds",
    "corpus",
    "인용",
    "typesafe",
    "system one",
    "noul",
    "보관",
    "장애",
    "정책",
    "chunk-analyst",
)
_CHITCHAT_HINTS = ("안녕", "hello", "hi", "고마워", "thanks", "ㅎㅎ", "ㅋㅋ")
_WEB_HINTS = (
    "최신",
    "오늘",
    "가격",
    "release",
    "github",
    "exa",
    "openrouter",
    "공식 사이트",
    "뉴스",
    "latest",
    "현재",
    "공개 문서",
    "웹",
    "홈페이지",
    "docs.typesafe",
    "외부",
)


# 키워드 휴리스틱. 라이브 Jev가 없을 때 시연을 멈추지 않기 위한 대용이다.
def _fallback_noul(
    name: str,
    question: Any,
    text: str,
    *,
    attached_present: bool = False,
) -> float:
    name = _strip_passage_prefix(name)
    lowered = text.lower()
    passage = _section_after(lowered, ("passage:", "tool_call:"))
    instructions = _question_instructions(question).lower()
    if name in {"contains_prompt_injection", "is_risky"} or "injection" in instructions:
        target = passage or _section_after(lowered, ("passages:",)) or lowered
        hits = sum(1 for pat in _INJECTION_PATTERNS if re.search(pat, target))
        return min(0.99, 0.12 + 0.35 * hits) if hits else 0.08
    if name == "contradicts_query_premise":
        query = _section_before(lowered, "passage:")
        if "passages:" in lowered:
            query = _section_before(lowered, "passages:")
        passage = _section_after(lowered, ("passage:", "passages:")) or lowered
        false_sla = "99.999" in query and "99.9" in passage and "99.999" not in passage
        false_ttl = ("30일" in query or "30 day" in query) and (
            "무기한" in passage or "indefinitely" in passage
        )
        return 0.91 if false_sla or false_ttl else 0.18
    if name in {
        "is_relevant",
        "contains_answer_evidence",
        "grounded",
        "has_citation",
        "usable_facts",
        "enough_to_answer",
        "enough_evidence",
    }:
        overlap = _token_overlap(text)
        if name == "has_citation":
            cited = bool(re.search(r"https?://|출처|source:|\[.+\]\(", text))
            return 0.88 if cited else 0.25
        if name == "grounded":
            return min(0.95, 0.40 + overlap)
        return min(0.94, 0.30 + 1.4 * overlap)
    if name == "invents_facts":
        if "hunter2" in lowered or "99.999" in lowered.split("evidence:", 1)[-1:]:
            return 0.82
        return 0.16
    if name == "need_local":
        return 0.88 if any(hint in lowered for hint in _LOCAL_HINTS) else 0.12
    if name == "need_web":
        return 0.88 if any(hint in lowered for hint in _WEB_HINTS) else 0.12
    if name == "need_fresh_web":
        fresh = ("최신", "오늘", "latest", "현재", "release", "가격")
        return 0.82 if any(hint in lowered for hint in fresh) else 0.18
    if name == "web_contradicts_local":
        return 0.86 if ("99.999" in lowered and "99.9" in lowered) else 0.20
    if name == "local_is_authoritative":
        official = ("internal_policy", "corpus/", "official_documentation")
        return 0.90 if any(hint in lowered for hint in official) else 0.35
    if name == "web_is_trustworthy":
        return 0.18 if "forum" in lowered or "community" in lowered else 0.68
    if name == "need_another_source":
        return 0.78 if any(hint in lowered for hint in _WEB_HINTS) else 0.22
    if name == "need_attachment":
        if not attached_present:
            return 0.06
        if any(hint in lowered for hint in _CHITCHAT_HINTS):
            return 0.08
        return 0.90
    if name == "need_search":
        local = any(hint in lowered for hint in _LOCAL_HINTS)
        web = any(hint in lowered for hint in _WEB_HINTS)
        return 0.88 if local or web else 0.08
    if name == "jailbreak":
        hits = sum(1 for pat in _INJECTION_PATTERNS if re.search(pat, lowered))
        return min(0.99, 0.20 + 0.35 * hits) if hits else 0.07
    return 0.2


def _fallback_choice(
    name: str,
    question: Any,
    text: str,
) -> tuple[str, dict[str, float], float]:
    criteria = _question_criteria(question) or {}
    keys = list(criteria) if isinstance(criteria, dict) else list(criteria or [])
    if name == "kind" or set(keys) >= {"lookup", "compare", "investigate"}:
        lowered = text.lower()
        has_local = any(hint in lowered for hint in _LOCAL_HINTS)
        has_web = any(hint in lowered for hint in _WEB_HINTS)
        kind = "lookup"
        if any(hint in text for hint in _COMPARE_HINTS):
            kind = "compare"
        elif any(hint in lowered for hint in _INVESTIGATE_HINTS):
            kind = "investigate"
        elif any(hint in lowered for hint in _CHITCHAT_HINTS) or (
            not has_local and not has_web
        ):
            kind = "other"
        labels = ("lookup", "compare", "investigate", "other")
        if "other" not in keys:
            labels = ("lookup", "compare", "investigate")
            if kind == "other":
                kind = "lookup"
        probs = {key: (0.78 if key == kind else 0.07) for key in labels}
        total = sum(probs.values())
        probs = {key: value / total for key, value in probs.items()}
        return kind, probs, 0.74
    if name == "analysis" or set(keys) >= {"self_read", "chunk_analyst"}:
        picked = (
            "chunk_analyst"
            if any(hint in text for hint in _COMPARE_HINTS)
            or any(hint in text.lower() for hint in _INVESTIGATE_HINTS)
            else "self_read"
        )
        labels = ("self_read", "chunk_analyst")
        probs = {key: (0.8 if key == picked else 0.2) for key in labels}
        return picked, probs, 0.72
    if name == "relation":
        labels = keys or ["supports", "contradicts", "says_nothing"]
        conflict_key = next(
            (key for key in labels if key in {"conflicts", "contradicts"}),
            labels[-1],
        )
        silent_key = next(
            (key for key in labels if key in {"silent", "says_nothing"}),
            labels[-1],
        )
        support_key = "supports" if "supports" in labels else labels[0]
        if "99.999" in text and "99.9" in text:
            picked = conflict_key
            conf = 0.88
        elif _token_overlap(text) > 0.25:
            picked = support_key
            conf = 0.81
        else:
            picked = silent_key
            conf = 0.55
        probs = {key: (0.82 if key == picked else 0.09) for key in labels}
        total = sum(probs.values())
        probs = {key: value / total for key, value in probs.items()}
        return picked, probs, conf
    if name == "sources" or set(keys) >= {"local", "web", "both", "none"}:
        lowered = text.lower()
        has_local = any(hint in lowered for hint in _LOCAL_HINTS)
        has_web = any(hint in lowered for hint in _WEB_HINTS)
        if has_local and has_web:
            picked = "both"
        elif has_web:
            picked = "web"
        elif has_local:
            picked = "local"
        else:
            picked = "none"
        labels = ("local", "web", "both", "none")
        probs = {key: (0.76 if key == picked else 0.08) for key in labels}
        total = sum(probs.values())
        probs = {key: value / total for key, value in probs.items()}
        return picked, probs, 0.73
    if name == "thinking" or set(keys) >= {
        "none",
        "minimal",
        "low",
        "medium",
        "high",
    }:
        lowered = text.lower()
        if any(hint in lowered for hint in _CHITCHAT_HINTS) or any(
            pat in lowered for pat in ("ignore previous", "system prompt")
        ):
            picked = "none"
        elif any(hint in text for hint in _COMPARE_HINTS):
            picked = "medium"
        elif any(hint in lowered for hint in _INVESTIGATE_HINTS):
            picked = "high"
        else:
            picked = "low"
        labels = ("none", "minimal", "low", "medium", "high")
        probs = {key: (0.76 if key == picked else 0.06) for key in labels}
        total = sum(probs.values())
        probs = {key: value / total for key, value in probs.items()}
        return picked, probs, 0.74
    if name == "verdict" or set(keys) >= {
        "prefer_local",
        "prefer_web",
        "present_both",
        "flag_conflict",
    }:
        lowered = text.lower()
        if "99.999" in lowered or "contradict" in lowered:
            picked = "flag_conflict"
        elif "internal_policy" in lowered or "corpus/" in lowered:
            picked = "prefer_local"
        else:
            picked = "present_both"
        labels = ("prefer_local", "prefer_web", "present_both", "flag_conflict")
        probs = {key: (0.76 if key == picked else 0.08) for key in labels}
        total = sum(probs.values())
        probs = {key: value / total for key, value in probs.items()}
        return picked, probs, 0.71
    winner = keys[0] if keys else "other"
    probs = {key: (0.7 if key == winner else 0.3 / max(len(keys) - 1, 1)) for key in keys}
    return winner, probs, 0.6


def _fallback_score(name: str, question: Any, text: str) -> float:
    if any(hint in text.lower() for hint in _INVESTIGATE_HINTS):
        return 1.7
    if any(hint in text for hint in _COMPARE_HINTS):
        return 1.15
    return 0.4


def _strip_passage_prefix(name: str) -> str:
    """배치 키 ``p3_is_relevant``를 fallback 채점용 ``is_relevant``로 되돌린다."""
    match = re.match(r"^p\d+_(.+)$", name)
    return match.group(1) if match else name


def _section_after(text: str, markers: tuple[str, ...]) -> str:
    lowered = text.lower()
    for marker in markers:
        if marker in lowered:
            return lowered.split(marker, 1)[1]
    return ""


def _section_before(text: str, marker: str) -> str:
    if marker in text:
        return text.split(marker, 1)[0]
    return text


def _token_overlap(text: str) -> float:
    """passage/evidence/section 기준으로 나눠 값싼 토큰 겹침을 본다."""
    parts = re.split(r"\npassage:|\nevidence:|\nsection:", text, maxsplit=1)
    if len(parts) == 1:
        return 0.4
    left, right = _tokens(parts[0]), _tokens(parts[1])
    if not left or not right:
        return 0.1
    shared = len(left & right)
    return shared / max(len(left), 1)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{2,}|[가-힣]{2,}", text.lower()))
