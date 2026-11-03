"""얇은 Exa Search 클라이언트. 히트는 Passage로 매핑한다.

네트워크 I/O는 ``search``에만 두고, JSON 변환은 테스트가 직접 호출한다.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from src.schemas import Passage

EXA_SEARCH_URL = "https://api.exa.ai/search"


class ExaError(RuntimeError):
    """Exa 검색을 끝내지 못했을 때 올린다."""


class ExaClient:
    """POST /search 한 뒤 히트를 Jev 게이트용 패시지로 바꾼다."""

    def __init__(self, api_key: str, max_chars: int = 1000) -> None:
        self.api_key = api_key
        self.max_chars = max_chars

    def search(
        self,
        query: str,
        k: int = 5,
        *,
        fresh: bool = False,
        include_domains: list[str] | None = None,
    ) -> list[Passage]:
        """``query``에 대해 최대 ``k``개 웹 패시지를 돌려준다."""
        contents: dict[str, object] = {
            "highlights": {"maxCharacters": min(400, self.max_chars)},
            "text": {"maxCharacters": self.max_chars},
        }
        if fresh:
            # 최신성 질의는 캐시된 구버전 문서를 받지 않는다.
            contents["maxAgeHours"] = 24
        payload: dict[str, object] = {
            "query": query,
            "type": "auto",
            "numResults": k,
            "contents": contents,
        }
        if include_domains:
            payload["includeDomains"] = include_domains
        try:
            response = httpx.post(
                EXA_SEARCH_URL,
                json=payload,
                headers={
                    "x-api-key": self.api_key,
                    "User-Agent": "jev-deepagents-rag/0.1",
                },
                timeout=25.0,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:180]
            raise ExaError(f"Exa HTTP {exc.response.status_code}: {detail}") from exc
        except httpx.RequestError as exc:
            raise ExaError(f"Exa request failed: {exc}") from exc
        return passages_from_exa(body, max_chars=self.max_chars)


def passages_from_exa(body: dict[str, Any], *, max_chars: int) -> list[Passage]:
    """Exa JSON을 Passage로 매핑한다. 네트워크 I/O는 없다."""
    passages: list[Passage] = []
    for index, item in enumerate(body.get("results") or [], start=1):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("id") or "").strip()
        title = str(item.get("title") or url or f"exa-{index}").strip()
        text = _result_text(item, max_chars)
        if not url or not text:
            continue
        passages.append(
            Passage(
                doc_id=f"exa-{index:02d}-{_slug(title)}",
                title=title,
                source=url,
                source_type="web",
                text=text,
            )
        )
    return passages


def _result_text(item: dict[str, Any], max_chars: int) -> str:
    highlights = item.get("highlights") or []
    if isinstance(highlights, list):
        joined = "\n".join(str(part).strip() for part in highlights if str(part).strip())
        if joined:
            return joined[:max_chars]
    text = str(item.get("text") or "").strip()
    return text[:max_chars]


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "-", title).strip("-").lower()
    return (slug or "page")[:40]
