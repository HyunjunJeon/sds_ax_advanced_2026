"""ask_jev tool rejects open prompts and accepts a Closed Loop."""

from __future__ import annotations

from dataclasses import replace

from src.agent.config import load_settings
from src.harness import JevHarness
from src.retriever import CorpusIndex
from src.tools.documentation import build_tools


class _FakeBackend:
    def upload_files(self, files):
        return []

    def download_files(self, paths):
        return []


def _tools():
    settings = replace(load_settings(), jev_mode="fallback")
    harness = JevHarness(settings)
    index = CorpusIndex(settings.corpus_dir)
    return {
        tool.name: tool
        for tool in build_tools(index, harness, _FakeBackend(), settings)
    }, harness


def test_ask_jev_tool_rejects_open_prompt() -> None:
    tools, _harness = _tools()
    result = tools["ask_jev"].invoke(
        {
            "state": {"question": "알파 SLA는?"},
            "questions": [
                {
                    "id": "advice",
                    "type": "noul",
                    "instructions": "What should I tell the user about SLA?",
                }
            ],
        }
    )
    assert "Closed Loop rejected" in result
    assert "jev-closed-loop" in result


def test_ask_jev_tool_returns_noul() -> None:
    tools, harness = _tools()
    result = tools["ask_jev"].invoke(
        {
            "state": {"question": "알파 SLA는?", "evidence": "공식 목표 99.9%"},
            "questions": [
                {
                    "id": "enough_evidence",
                    "type": "noul",
                    "instructions": "Does the evidence state a numeric SLA?",
                }
            ],
        }
    )
    assert "enough_evidence" in result
    assert harness.last_closed is not None
    assert "enough_evidence" in harness.last_closed.nouls
