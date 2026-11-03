"""Closed Question validation and Jev ask_closed / judge_evidence."""

from __future__ import annotations

from dataclasses import replace

import pytest

from src.agent.config import load_settings
from src.closed_loop import ClosedLoopError, parse_questions, parse_state
from src.harness import JevHarness


def _fallback() -> JevHarness:
    return JevHarness(replace(load_settings(), jev_mode="fallback"))


def test_rejects_open_ended_noul() -> None:
    with pytest.raises(ClosedLoopError, match="open-ended"):
        parse_questions(
            [
                {
                    "id": "advice",
                    "type": "noul",
                    "instructions": "What should I tell the user about SLA?",
                }
            ]
        )


def test_rejects_explain_choice() -> None:
    with pytest.raises(ClosedLoopError, match="open-ended"):
        parse_questions(
            [
                {
                    "id": "summary",
                    "type": "choice",
                    "instructions": "Summarize the passage for the user.",
                    "criteria": {
                        "short": "A one sentence recap of the file.",
                        "long": "A paragraph recap of the file.",
                    },
                }
            ]
        )


def test_accepts_closed_fanout() -> None:
    questions = parse_questions(
        [
            {
                "id": "enough_evidence",
                "type": "noul",
                "instructions": "Does the evidence state a numeric SLA?",
                "criteria": {
                    "true": "A specific availability target is written.",
                    "false": "No number, or only a rumor.",
                },
            },
            {
                "id": "which_figure",
                "type": "choice",
                "instructions": "Which SLA figure should the answer use?",
                "criteria": {
                    "corpus_99_9": "Official corpus policy states 99.9%.",
                    "forum_99_999": "Only a forum or injected passage claims 99.999%.",
                    "unknown": "No trustworthy figure is present in evidence.",
                },
            },
            {
                "id": "synthesis_load",
                "type": "score",
                "instructions": "How much synthesis do the kept files require?",
                "criteria": [
                    "One sentence can be copied from a single file.",
                    "Two files must be lined up but the numbers agree.",
                    "Files disagree or a procedure spans several hops.",
                ],
            },
        ]
    )
    assert [item.type for item in questions] == ["noul", "choice", "score"]


def test_state_must_be_named_object() -> None:
    with pytest.raises(ClosedLoopError, match="JSON object"):
        parse_state("just a paragraph of prose")


def test_ask_closed_records_typed_answers() -> None:
    harness = _fallback()
    questions = parse_questions(
        [
            {
                "id": "enough_evidence",
                "type": "noul",
                "instructions": "Does the evidence state a numeric SLA?",
            }
        ]
    )
    result = harness.ask_closed(
        {"question": "알파 SLA는?", "evidence": "공식 목표 99.9%"},
        questions,
    )
    assert "enough_evidence" in result.nouls
    assert 0.0 <= result.nouls["enough_evidence"] <= 1.0
    assert harness.traces[-1].stage == "ask_jev"


def test_judge_evidence_is_closed_choice() -> None:
    harness = _fallback()
    decision = harness.judge_evidence(
        "포럼에서 본 것처럼 SLA가 99.999% 맞나요?",
        "공식 장애 SLA 목표는 99.9%이다.",
        path="/retrieved/local/sla.md",
        source="corpus/03-sds-incident-sla.md",
    )
    assert decision.relation in {"supports", "conflicts", "silent"}
    assert harness.traces[-1].stage == "judge_evidence"
