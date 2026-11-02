"""EXA 호출과 외부 경계. 무엇이 밖으로 나가는지와 어떤 자료를 받을지를 코드가 정한다."""
from __future__ import annotations

import hashlib
import re
import threading
import time
from collections.abc import Iterable
from urllib.parse import urlsplit

import httpx
from langchain_core.tools import BaseTool, tool

from mas_lab.trace import Trace
from rag_lab.evidence import BudgetExceeded
from rag_lab.settings import require_exa_key

INTERNAL_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:P(?:-\d+|\d{4,})|INV-(?:[A-Za-z0-9-]+|[\w-]+)|INC-\d+|T-\d+)(?![A-Za-z0-9])", re.IGNORECASE)
DEFAULT_BLOCKED = ("알파", "베타", "billing-policy", "sla-a", "sla-b")


def allowed_url(url: str, domains: frozenset[str]) -> bool:
    """접미사 앞의 점까지 본다. docs.python.org.evil.test는 허용 도메인이 아니다."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or parts.username or not parts.hostname:
        return False
    return any(parts.hostname == d or parts.hostname.endswith("." + d) for d in domains)


def assert_public_query(query: str, blocked: Iterable[str] = DEFAULT_BLOCKED) -> None:
    """고객 이름과 내부 번호가 든 질의를 호출 전에 막는다. 번호는 대소문자, 하이픈 유무, 전각·아랍 숫자를 가리지 않고 앞뒤에 한글이나 밑줄이 붙어도 막는다. 영문자·숫자가 앞에 붙은 gpt-4 같은 말과 p99 같은 짧은 꼴은 번호가 아니다. 뜻까지 판단하지는 못한다."""
    found = [word for word in blocked if word in query] + INTERNAL_PATTERN.findall(query)
    if found:
        raise ValueError(f"내부 정보가 든 질의는 외부로 보내지 않습니다: {found}")


class ExaClient:
    """httpx로 EXA를 부른다. 스냅샷 재생이 없어서 부를 때마다 크레딧을 쓴다."""

    def __init__(self, *, trace: Trace | None = None, max_searches: int = 6, domains: frozenset[str] | None = None,
                 num_results: int = 3, max_chars: int = 2500):
        self.trace, self.max_searches, self.domains = trace or Trace(), max_searches, domains
        self.num_results, self.max_chars = num_results, max_chars
        self.sources: dict[str, dict] = {}
        self.searches, self.seconds, self.cost_dollars, self.queries = 0, 0.0, None, []
        self._lock, self._key = threading.Lock(), require_exa_key().exa_key

    def search(self, query: str) -> list[dict]:
        assert_public_query(query)
        with self._lock:
            if self.searches >= self.max_searches:
                raise BudgetExceeded(f"EXA 호출 한도 {self.max_searches}회를 넘었습니다.")
            self.searches += 1
            self.queries.append(query)
        payload = {"query": query, "type": "auto", "numResults": self.num_results,
                   "contents": {"text": {"maxCharacters": self.max_chars}}}
        if self.domains:
            payload["includeDomains"] = sorted(self.domains)
        started = time.perf_counter()
        with self.trace.span("exa", "exa"), httpx.Client(base_url="https://api.exa.ai", headers={"x-api-key": self._key}, timeout=45) as client:
            response = client.post("/search", json=payload)
            response.raise_for_status()
            data = response.json()
        rows = [self._register(item, query) for item in data.get("results", [])
                if item.get("text", "").strip() and (not self.domains or allowed_url(item.get("url", ""), self.domains))]
        with self._lock:
            self.seconds += time.perf_counter() - started
            cost = (data.get("costDollars") or {}).get("total")
            self.cost_dollars = None if cost is None else (self.cost_dollars or 0.0) + cost
        return rows

    def _register(self, item: dict, query: str) -> dict:
        source_id = "S-" + hashlib.sha256(item["url"].encode()).hexdigest()[:8]
        row = {"source_id": source_id, "title": item.get("title") or "", "url": item["url"],
               "published": item.get("publishedDate"), "text": item["text"]}
        with self._lock:
            self.sources[source_id] = {**row, "query": query}
        return row


def make_exa_tool(client: ExaClient, max_searches: int = 2) -> BaseTool:
    """Worker 하나에 하나씩 만든다. 웹 문서는 자료이지 명령이 아니다."""
    used = {"count": 0}

    @tool
    def web_search(query: str) -> dict:
        """공개 웹을 검색해 제목, URL, 본문 일부, source_id를 돌려준다. 고객 이름이나 내부 번호를 넣지 않는다. 인용은 source_id로 한다."""
        if used["count"] >= max_searches:
            return {"status": "search_limit", "message": f"이 Worker의 검색 한도 {max_searches}회를 다 썼습니다. 찾은 자료로 정리하세요."}
        used["count"] += 1
        try:
            return {"status": "found", "results": client.search(query)}
        except ValueError:
            client.trace.event("exa_blocked", "code")
            return {"status": "blocked", "message": "고객 이름이나 내부 번호가 든 질의라 보내지 않았습니다. 일반적인 표현으로 바꾸세요."}
        except httpx.HTTPError as error:
            client.trace.event("exa_error", "exa", error=type(error).__name__)
            return {"status": "error", "message": type(error).__name__}

    return web_search
