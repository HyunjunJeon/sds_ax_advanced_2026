"""Exa payload mapping and the httpx transport."""

import httpx
import pytest

from src.tools.exa import EXA_SEARCH_URL, ExaClient, ExaError, passages_from_exa


def test_passages_from_exa_prefers_highlights() -> None:
    body = {
        "results": [
            {
                "title": "Search API",
                "url": "https://exa.ai/docs/reference/search",
                "highlights": ["Use contents.text", "numResults defaults to 10"],
                "text": "long unused body",
            },
            {"title": "empty", "url": "https://example.com"},
        ]
    }
    passages = passages_from_exa(body, max_chars=80)
    assert len(passages) == 1
    assert passages[0].source_type == "web"
    assert passages[0].source.startswith("https://exa.ai")
    assert "contents.text" in passages[0].text


def test_exa_client_search_posts_json(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured["url"] = url
        captured.update(kwargs)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Search API",
                        "url": "https://exa.ai/docs/reference/search",
                        "highlights": ["Use contents.text"],
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("src.tools.exa.httpx.post", fake_post)
    passages = ExaClient("test-key", max_chars=80).search(
        "contents",
        k=3,
        fresh=True,
        include_domains=["exa.ai"],
    )
    payload = captured["json"]
    assert captured["url"] == EXA_SEARCH_URL
    assert captured["timeout"] == 25.0
    assert isinstance(payload, dict)
    assert payload["numResults"] == 3
    assert payload["includeDomains"] == ["exa.ai"]
    assert payload["contents"]["maxAgeHours"] == 24
    assert passages[0].source.startswith("https://exa.ai")


def test_exa_client_search_wraps_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        del kwargs
        return httpx.Response(
            401,
            text="bad key",
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("src.tools.exa.httpx.post", fake_post)
    with pytest.raises(ExaError, match="Exa HTTP 401"):
        ExaClient("test-key").search("contents")


def test_exa_client_search_wraps_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(*args: object, **kwargs: object) -> httpx.Response:
        del args, kwargs
        raise httpx.ConnectError("boom")

    monkeypatch.setattr("src.tools.exa.httpx.post", fake_post)
    with pytest.raises(ExaError, match="Exa request failed"):
        ExaClient("test-key").search("contents")
