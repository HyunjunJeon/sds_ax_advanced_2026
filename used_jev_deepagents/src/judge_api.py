"""Jev와 LLM tool-call 판단 엔진이 공유하는 표면.

도구는 엔진을 구분하지 않고 같은 슬롯만 호출한다.
"""

from __future__ import annotations

from typing import Protocol

from src.agent.config import Settings
from src.closed_loop import ClosedQuestion
from src.schemas import (
    ClosedLoopResult,
    DecisionTrace,
    EvidenceJudgment,
    GatedPassage,
    Passage,
    ReconcileResult,
    TurnPlan,
)


class JudgeApi(Protocol):
    """RAG 도구가 쓰는 turn / gate / reconcile / evidence 결정."""

    settings: Settings
    engine: str
    traces: list[DecisionTrace]
    last_turn: TurnPlan | None
    last_gated: list[GatedPassage]
    last_reconcile: ReconcileResult | None
    last_closed: ClosedLoopResult | None
    last_evidence: list[EvidenceJudgment]
    last_attachments: list[GatedPassage]

    def reset_traces(self) -> None:
        """실행마다 트레이스와 캐시된 결정을 비운다."""

    def plan_turn(
        self,
        question: str,
        *,
        attached: list | None = None,
    ) -> TurnPlan:
        """kind, sources, 검색 생략, 분석 모드를 분류한다."""

    def gate_passages(self, question: str, passages: list[Passage]) -> list[GatedPassage]:
        """검색 패시지를 남기거나, 충돌로 표시하거나, 버린다."""

    def gate_passages_per_item(
        self,
        question: str,
        passages: list[Passage],
    ) -> list[GatedPassage]:
        """패시지마다 판단 한 번. Jev는 예전 per-item 경로."""

    def reconcile_sources(self, question: str) -> ReconcileResult | None:
        """남긴 로컬 패시지와 웹 패시지를 비교한다."""

    def ask_closed(
        self,
        state: dict[str, object],
        questions: list[ClosedQuestion],
        *,
        note: str = "",
    ) -> ClosedLoopResult:
        """검증된 Closed Loop에 답한다."""

    def judge_evidence(
        self,
        question: str,
        text: str,
        *,
        path: str = "",
        source: str = "",
    ) -> EvidenceJudgment:
        """파일 하나의 supports / conflicts / silent."""
