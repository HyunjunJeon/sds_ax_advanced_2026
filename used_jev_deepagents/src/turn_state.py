"""Jev 턴 계획에 넣는 이름 있는 state.

질문은 문자열로 붙이지 않는다. 첨부·코퍼스·사용 가능 소스는
코드가 채우고, Closed Question이 필드 경로로 가리킨다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agent.config import Settings
from src.retriever import _first_heading


def corpus_topics(corpus_dir: Path) -> list[str]:
    """색인된 마크다운의 제목. 본문은 넣지 않는다."""
    topics: list[str] = []
    if not corpus_dir.is_dir():
        return topics
    for path in sorted(corpus_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        topics.append(_first_heading(raw) or path.stem)
    return topics


def attached_records(files: list[Any]) -> list[dict[str, Any]]:
    """첨부 메타만. PDF 본문·바이너리는 빼 둔다."""
    records: list[dict[str, Any]] = []
    for item in files:
        records.append(
            {
                "filename": str(getattr(item, "filename", "") or "attachment"),
                "pages": int(getattr(item, "pages", 0) or 0),
                "chars": len(str(getattr(item, "text", "") or "")),
                "error": str(getattr(item, "error", "") or ""),
            }
        )
    return records


def build_turn_state(
    question: str,
    settings: Settings,
    attached: list[Any] | None = None,
) -> dict[str, Any]:
    """턴 라우팅용 state. 채팅 모델이 채우지 않는다."""
    files = list(attached or [])
    return {
        "question": question,
        "attached": attached_records(files),
        "corpus_topics": corpus_topics(settings.corpus_dir),
        "available_sources": {
            "local_corpus": True,
            "exa_web": bool(settings.exa_api_key),
            "user_attachment": bool(files),
        },
    }
