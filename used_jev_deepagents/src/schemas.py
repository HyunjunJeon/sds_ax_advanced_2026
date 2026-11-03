"""Jev 결정과 RAG 한 번의 타입 있는 레코드.

TurnPlan은 before_agent 팬아웃 결과이고, GatedPassage는 코드 route() 결과다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

QueryKind = Literal["lookup", "compare", "investigate", "other"]
AnalysisMode = Literal["self_read", "chunk_analyst"]
SourceName = Literal["local", "web", "both", "none"]
ThinkingEffort = Literal["none", "minimal", "low", "medium", "high"]
ReconcileVerdict = Literal[
    "prefer_local", "prefer_web", "present_both", "flag_conflict"
]
PassageRoute = Literal["include", "conflicting_evidence", "exclude"]
CitationVerdict = Literal[
    "verified", "unsupported", "contradicted", "fabricated", "review"
]


@dataclass
class DecisionTrace:
    """UI가 카드로 그릴 Jev(또는 fallback) 호출 하나."""

    stage: str
    questions: dict[str, Any]
    answers: dict[str, Any]
    elapsed_ms: float
    live: bool
    note: str = ""


@dataclass
class QueryRoute:
    """이 질문을 하네스가 어떻게 돌릴지."""

    kind: QueryKind
    probabilities: dict[str, float]
    confidence: float
    complexity: float
    model_name: str
    needs_subagents: bool
    thinking_effort: ThinkingEffort = "low"


@dataclass
class TurnPlan:
    """before_agent 팬아웃 한 번: 라우트, 소스, 검색 생략, 분석."""

    query: str
    kind: QueryKind
    kind_probabilities: dict[str, float]
    kind_confidence: float
    complexity: float
    sources: SourceName
    source_probabilities: dict[str, float]
    source_confidence: float
    need_local: float
    need_web: float
    need_fresh_web: float
    need_search: float
    jailbreak: float
    analysis: AnalysisMode
    analysis_confidence: float
    model_name: str
    needs_subagents: bool
    thinking_effort: ThinkingEffort
    # Choice가 아니라 코드 정책이 최종으로 켠/끈 소스.
    allow_search: bool
    allowed_local: bool
    allowed_web: bool
    reason: str
    need_attachment: float = 0.0
    allowed_attachment: bool = False

    def to_query_route(self) -> QueryRoute:
        """턴 계획을 예전 query-route 모양으로 투영한다."""
        return QueryRoute(
            kind=self.kind,
            probabilities=self.kind_probabilities,
            confidence=self.kind_confidence,
            complexity=self.complexity,
            model_name=self.model_name,
            needs_subagents=self.needs_subagents,
            thinking_effort=self.thinking_effort,
        )

    def to_source_plan(self) -> SourcePlan:
        """턴 계획을 source-plan 도구 모양으로 투영한다."""
        return SourcePlan(
            query=self.query,
            sources=self.sources,
            probabilities=self.source_probabilities,
            confidence=self.source_confidence,
            need_local=self.need_local,
            need_web=self.need_web,
            need_fresh_web=self.need_fresh_web,
            allowed_local=self.allowed_local,
            allowed_web=self.allowed_web,
            allowed_attachment=self.allowed_attachment,
            reason=self.reason,
        )


@dataclass
class SourcePlan:
    """이 질문에 Jev가 허용한 데이터 소스."""

    query: str
    sources: SourceName
    probabilities: dict[str, float]
    confidence: float
    need_local: float
    need_web: float
    need_fresh_web: float
    allowed_local: bool
    allowed_web: bool
    reason: str
    allowed_attachment: bool = False


@dataclass
class ReconcileResult:
    """로컬 코퍼스 히트와 Exa 웹 히트를 어떻게 다룰지."""

    verdict: ReconcileVerdict
    confidence: float
    web_contradicts_local: float
    local_is_authoritative: float
    web_is_trustworthy: float
    reason: str


@dataclass
class Passage:
    """검색된 청크 하나와 출처 메타데이터."""

    doc_id: str
    title: str
    source: str
    source_type: str
    text: str
    bm25: float = 0.0


@dataclass
class GatedPassage:
    """Jev Noul 네 개와 코드 라우팅을 지난 패시지."""

    passage: Passage
    is_relevant: float
    contains_answer_evidence: float
    contradicts_query_premise: float
    contains_prompt_injection: float
    route: PassageRoute
    # 남긴 청크만 /retrieved 경로를 가진다. exclude는 None일 수 있다.
    path: str | None = None


@dataclass
class GroundingResult:
    """답 이후 검사: 남긴 근거로 뒷받침되는가."""

    grounded: float
    has_citation: float
    invents_facts: float
    ok: bool


@dataclass
class CitationCheck:
    """검색 근거와 맞춘 주장 하나."""

    claim: str
    verdict: CitationVerdict
    confidence: float | None
    auto: bool
    relation: str | None = None


@dataclass
class ToolRisk:
    """도구 호출용 Auto Mode 스타일 게이트."""

    tool_name: str
    risk: float
    blocked: bool
    reason: str


@dataclass
class EvidenceJudgment:
    """검색 파일 하나와 사용자 질문에 대한 Jev Closed Loop."""

    path: str
    relation: str
    relation_confidence: float
    usable_facts: float
    enough_to_answer: float
    reason: str


@dataclass
class ClosedLoopResult:
    """``ask_jev`` Closed Loop의 타입 있는 답."""

    nouls: dict[str, float]
    choices: dict[str, str]
    probabilities: dict[str, dict[str, float]]
    scores: dict[str, float]
    confidence: dict[str, float]
    elapsed_ms: float
    live: bool
    reason: str


@dataclass
class RunResult:
    """질문 한 번 뒤 CLI와 UI가 쓰는 전부."""

    question: str
    answer: str
    query_route: QueryRoute
    gated: list[GatedPassage]
    grounding: GroundingResult | None
    citations: list[CitationCheck]
    tool_risks: list[ToolRisk]
    traces: list[DecisionTrace]
    published_path: str | None = None
    jev_live: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)
    source_plan: SourcePlan | None = None
    turn_plan: TurnPlan | None = None
    reconcile: ReconcileResult | None = None
