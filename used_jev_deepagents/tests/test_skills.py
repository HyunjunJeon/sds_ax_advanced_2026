"""Skills are on the composite backend and named for Deep Agents."""

from __future__ import annotations

from src.agent.backend import build_backend
from src.agent.config import load_settings


def test_closed_loop_skill_is_readable() -> None:
    backend = build_backend(load_settings())
    responses = backend.download_files(["/skills/jev-closed-loop/SKILL.md"])
    assert responses
    payload = responses[0]
    assert payload.error is None
    text = (payload.content or b"").decode("utf-8")
    assert "name: jev-closed-loop" in text
    assert "Closed Loop" in text
    assert "ask_jev" in text


def test_rag_harness_points_at_closed_loop() -> None:
    backend = build_backend(load_settings())
    responses = backend.download_files(["/skills/rag-harness/SKILL.md"])
    text = (responses[0].content or b"").decode("utf-8")
    assert "jev-closed-loop" in text
    assert "ask_jev" in text
