"""Fallback Jev must hit Closed Question gold on the speed suite."""

from __future__ import annotations

from dataclasses import replace

from src.agent.config import load_settings
from src.harness import JevHarness
from src.quality import CASES, score_closed
from src.retriever import CorpusIndex


def _fallback() -> JevHarness:
    return JevHarness(replace(load_settings(), jev_mode="fallback"))


def test_every_suite_case_matches_closed_gold() -> None:
    settings = replace(load_settings(), jev_mode="fallback")
    index = CorpusIndex(settings.corpus_dir)
    harness = JevHarness(settings)
    for case in CASES:
        harness.reset_traces()
        plan = harness.plan_turn(case.question)
        gated = []
        if plan.allowed_local:
            gated = harness.gate_passages(
                case.question, index.search(case.question, k=settings.retrieve_k)
            )
        score = score_closed(plan, gated, case)
        assert score.passed, (
            f"{case.label}: {[item for item in score.checks if not item.ok]}"
        )
