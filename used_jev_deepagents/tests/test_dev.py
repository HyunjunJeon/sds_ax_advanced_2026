"""LangGraph readiness probe uses httpx, not urllib."""

import httpx
import pytest

from src.dev import _wait_http


def test_wait_http_accepts_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        del kwargs
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr("src.dev.httpx.get", fake_get)
    _wait_http("http://127.0.0.1:2024/ok", timeout=1)


def test_wait_http_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        del kwargs
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("refused")
        return httpx.Response(200, request=httpx.Request("GET", url))

    monkeypatch.setattr("src.dev.httpx.get", fake_get)
    monkeypatch.setattr("src.dev.time.sleep", lambda *_args: None)
    _wait_http("http://127.0.0.1:2024/ok", timeout=2)
    assert calls["n"] == 2


def test_wait_http_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    times = iter([0.0, 0.0, 2.0])

    def fake_get(*args: object, **kwargs: object) -> httpx.Response:
        del args, kwargs
        raise httpx.ConnectError("refused")

    monkeypatch.setattr("src.dev.httpx.get", fake_get)
    monkeypatch.setattr("src.dev.time.sleep", lambda *_args: None)
    monkeypatch.setattr("src.dev.time.time", lambda: next(times, 2.0))
    with pytest.raises(SystemExit, match="LangGraph API did not become ready"):
        _wait_http("http://127.0.0.1:2024/ok", timeout=1)
