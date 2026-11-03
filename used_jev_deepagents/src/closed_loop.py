"""Closed Question을 Jev에 보내기 전에 검증한다.

Jev는 Noul / Choice / Score만 받는다. 열린 프롬프트는 생성 요청이므로
여기서 거른다. ask_jev 도구와 jev-closed-loop 스킬이 같은 계약을 쓴다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from src.jev import choice, noul, score

QuestionType = Literal["noul", "choice", "score"]

MAX_QUESTIONS = 12
MAX_STATE_CHARS = 24_000
MAX_NOUL_CRITERIA = 2
MIN_CHOICE_OPTIONS = 2
MAX_CHOICE_OPTIONS = 8
MIN_SCORE_LEVELS = 2
MAX_SCORE_LEVELS = 6

# 생성 요청으로 보이는 동사. Jev에 보내면 Closed Loop가 깨진다.
_OPEN_ENDED = (
    r"\bexplain\b",
    r"\bdescribe\b",
    r"\bsummarize\b",
    r"\banalyze\b",
    r"\brecommend\b",
    r"\blist all\b",
    r"\bin your own words\b",
    r"\bwhat should (i|we|the agent)\b",
    r"\bhow (should|would) (i|we|the agent)\b",
    r"\bwrite (a|the|an)\b",
    r"설명해",
    r"분석해",
    r"요약해",
    r"추천해",
    r"어떻게 해야",
    r"뭘 해야",
    r"작성해",
)

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
# stem이 맞거나 물음표로 끝나면 통과. what/how 차단은 _OPEN_ENDED가 한다.
_NOUL_STEM = re.compile(
    r"^(does|do|is|are|was|were|has|have|had|can|could|would|should|"
    r"will|did|may|might|must)\b",
    re.IGNORECASE,
)


class ClosedLoopError(ValueError):
    """제안된 Jev 질문이 Closed Question이 아닐 때 올린다."""


@dataclass(frozen=True)
class ClosedQuestion:
    """에이전트가 Jev에 보낼 수 있는 타입 있는 판단 하나."""

    id: str
    type: QuestionType
    instructions: str
    criteria: dict[str, str] | list[str] | None = None


def parse_state(state: str | dict[str, Any]) -> dict[str, Any]:
    """JSON 객체 또는 이미 파싱된 매핑을 받는다."""
    if isinstance(state, str):
        try:
            loaded = json.loads(state)
        except json.JSONDecodeError as exc:
            raise ClosedLoopError(
                "state must be a JSON object with named fields, not a blob of prose."
            ) from exc
    else:
        loaded = state
    if not isinstance(loaded, dict) or not loaded:
        raise ClosedLoopError(
            "state must be a non-empty object. Name the fields "
            "(question, evidence, candidates) so Jev can address them."
        )
    flattened = json.dumps(loaded, ensure_ascii=False)
    # System One 예산 안에 남기려고 산문을 통째로 넣지 못하게 한다.
    if len(flattened) > MAX_STATE_CHARS:
        raise ClosedLoopError(
            f"state is {len(flattened)} chars; keep it under {MAX_STATE_CHARS} "
            "so the Closed Loop stays inside the System One budget."
        )
    return loaded


def parse_questions(raw: str | list[Any]) -> list[ClosedQuestion]:
    """Closed Question 목록을 파싱하고 검증한다."""
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ClosedLoopError(
                "questions must be a JSON array of Closed Questions."
            ) from exc
    else:
        loaded = raw
    if not isinstance(loaded, list) or not loaded:
        raise ClosedLoopError("Provide 1–12 Closed Questions in one fan-out.")
    if len(loaded) > MAX_QUESTIONS:
        raise ClosedLoopError(
            f"{len(loaded)} questions is too many. Cap is {MAX_QUESTIONS} "
            "independent judgments on the same state."
        )
    seen: set[str] = set()
    parsed: list[ClosedQuestion] = []
    for index, item in enumerate(loaded):
        question = _parse_one(item, index)
        if question.id in seen:
            raise ClosedLoopError(f"Duplicate question id `{question.id}`.")
        seen.add(question.id)
        parsed.append(question)
    return parsed


def compile_questions(questions: list[ClosedQuestion]) -> dict[str, Any]:
    """검증된 Closed Question을 SDK Noul / Choice / Score로 바꾼다."""
    compiled: dict[str, Any] = {}
    for question in questions:
        if question.type == "noul":
            criteria = question.criteria if isinstance(question.criteria, dict) else None
            compiled[question.id] = noul(question.instructions, criteria)
        elif question.type == "choice":
            compiled[question.id] = choice(
                question.instructions, dict(question.criteria or {})
            )
        else:
            compiled[question.id] = score(
                question.instructions, list(question.criteria or [])
            )
    return compiled


def _parse_one(item: Any, index: int) -> ClosedQuestion:
    if not isinstance(item, dict):
        raise ClosedLoopError(f"questions[{index}] must be an object.")
    qid = str(item.get("id") or "").strip()
    if not _ID_RE.match(qid):
        raise ClosedLoopError(
            f"questions[{index}].id must be snake_case (e.g. enough_evidence). "
            "Ids are for code; they are not sent to Jev as meaning."
        )
    qtype = str(item.get("type") or "").strip().lower()
    if qtype not in {"noul", "choice", "score"}:
        raise ClosedLoopError(
            f"`{qid}` type must be noul, choice, or score. "
            "Jev does not answer open-ended questions."
        )
    instructions = str(item.get("instructions") or "").strip()
    if len(instructions) < 12:
        raise ClosedLoopError(
            f"`{qid}` instructions are too short. State the full judgment; "
            "do not rely on the id."
        )
    if _is_open_ended(instructions):
        raise ClosedLoopError(
            f"`{qid}` is open-ended. Rewrite as a Closed Question "
            "(Noul yes/no, Choice among named options, or Score on ordered levels). "
            "Read /skills/jev-closed-loop/SKILL.md."
        )
    criteria = item.get("criteria")
    if qtype == "noul":
        _validate_noul(qid, instructions, criteria)
    elif qtype == "choice":
        _validate_choice(qid, criteria)
    else:
        _validate_score(qid, criteria)
    return ClosedQuestion(
        id=qid,
        type=qtype,  # type: ignore[arg-type]
        instructions=instructions,
        criteria=criteria,
    )


def _is_open_ended(instructions: str) -> bool:
    lowered = instructions.lower()
    return any(re.search(pattern, lowered) for pattern in _OPEN_ENDED)


def _validate_noul(qid: str, instructions: str, criteria: Any) -> None:
    first = instructions.split("?", 1)[0].strip()
    if not (_NOUL_STEM.match(first) or instructions.rstrip().endswith("?")):
        raise ClosedLoopError(
            f"`{qid}` Noul must be a yes/no proposition "
            "(Does / Is / Would / Can … ?). Not a what/how prompt."
        )
    if criteria is None:
        return
    if not isinstance(criteria, dict):
        raise ClosedLoopError(
            f"`{qid}` Noul criteria must be "
            '{{"true": "...", "false": "..."}} or omitted.'
        )
    keys = {str(key).lower() for key in criteria}
    if keys - {"true", "false"} or len(criteria) > MAX_NOUL_CRITERIA:
        raise ClosedLoopError(
            f"`{qid}` Noul criteria may only define true/false situations."
        )


def _validate_choice(qid: str, criteria: Any) -> None:
    if not isinstance(criteria, dict) or not (
        MIN_CHOICE_OPTIONS <= len(criteria) <= MAX_CHOICE_OPTIONS
    ):
        raise ClosedLoopError(
            f"`{qid}` Choice needs {MIN_CHOICE_OPTIONS}–{MAX_CHOICE_OPTIONS} "
            "named options, each a concrete situation."
        )
    for key, value in criteria.items():
        if not str(key).strip() or len(str(value).strip()) < 8:
            raise ClosedLoopError(
                f"`{qid}` option `{key}` needs a concrete description, "
                "not a one-word label."
            )


def _validate_score(qid: str, criteria: Any) -> None:
    if not isinstance(criteria, list) or not (
        MIN_SCORE_LEVELS <= len(criteria) <= MAX_SCORE_LEVELS
    ):
        raise ClosedLoopError(
            f"`{qid}` Score needs {MIN_SCORE_LEVELS}–{MAX_SCORE_LEVELS} "
            "ordered level strings that stand on their own."
        )
    for index, level in enumerate(criteria):
        if len(str(level).strip()) < 8:
            raise ClosedLoopError(
                f"`{qid}` score level {index} is too thin. "
                "Describe a concrete situation."
            )
