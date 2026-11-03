"""Deep Agent 도구: Jev 판단, 로컬 검색, Exa 검색, 게시.

허용되지 않은 소스는 여기서 거절한다. exclude 청크는 디스크에 남기지 않는다.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from langchain.tools import tool

from src.agent.config import Settings
from src.closed_loop import ClosedLoopError, parse_questions, parse_state
from src.judge_api import JudgeApi
from src.retrieve import fetch_local, fetch_web
from src.retriever import CorpusIndex
from src.schemas import ClosedLoopResult, EvidenceJudgment, GatedPassage, TurnPlan
from src.tools.exa import ExaError

if TYPE_CHECKING:
    from deepagents.backends.protocol import BackendProtocol


def build_tools(
    index: CorpusIndex,
    harness: JudgeApi,
    backend: BackendProtocol,
    settings: Settings,
):
    """오케스트레이터가 호출할 검색·Closed Loop 도구를 만든다."""

    # 아래 도구 DocString은 에이전트용 설명이라 영어를 유지한다.
    @tool(parse_docstring=True)
    def plan_sources(query: str) -> str:
        """Read the Jev turn plan (already computed). Not an LLM decision.

        Args:
            query: The user question the plan was made for.

        Returns:
            Allowed sources and Jev probabilities. Call only the allowed search tools.
        """
        plan = _current_plan(harness, query)
        summary = _turn_markdown(plan)
        backend.upload_files(
            [
                ("/harness/source_plan.md", summary.encode("utf-8")),
                ("/harness/turn_plan.md", summary.encode("utf-8")),
            ]
        )
        return summary

    @tool(parse_docstring=True)
    def search_documentation(query: str) -> str:
        """Search the local corpus, gate hits with Jev, and save kept chunks.

        Args:
            query: Natural language search query.

        Returns:
            File paths and Jev route labels. Full text is on the filesystem.
        """
        plan = _current_plan(harness, query)
        if not plan.allow_search or not plan.allowed_local:
            return (
                f"Jev skipped the local corpus.\n{plan.reason}\n"
                "Use search_web if web is allowed, or answer without retrieval."
            )
        hits, _fetch_ms = fetch_local(index, query, settings.retrieve_k)
        gated = harness.gate_passages(query, hits)
        label = _engine_label(harness)
        return _store_gated(
            backend,
            gated,
            batch_prefix="local",
            headline=f"{label} gated {len(gated)} local BM25 hits for: {query}",
        )

    @tool(parse_docstring=True)
    def search_web(query: str) -> str:
        """Search the live web with Exa, then gate hits with the same Jev route().

        Args:
            query: Natural language web search query.

        Returns:
            File paths and Jev route labels for Exa hits, or a skip reason.
        """
        plan = _current_plan(harness, query)
        if not plan.allow_search or not plan.allowed_web:
            return (
                f"Jev skipped Exa.\n{plan.reason}\n"
                "Use search_documentation if the local corpus is allowed."
            )
        try:
            hits, _fetch_ms = fetch_web(
                settings,
                query,
                fresh=plan.need_fresh_web >= 0.70,
            )
        except ExaError as exc:
            return f"Exa search failed: {exc}"
        if not hits:
            return f"Exa returned no usable passages for: {query}"
        gated = harness.gate_passages(query, hits)
        extra = ""
        if plan.need_fresh_web >= 0.70:
            extra = (
                f"{_engine_label(harness)} marked this as freshness-sensitive. "
                "Prefer recent official pages.\n"
            )
        return _store_gated(
            backend,
            gated,
            batch_prefix="web",
            headline=f"{_engine_label(harness)} gated {len(gated)} Exa hits for: {query}",
            prefix=extra,
        )

    @tool(parse_docstring=True)
    def reconcile_sources(query: str) -> str:
        """Ask Jev how to treat local corpus hits versus Exa hits.

        Args:
            query: The user question both searches were run for.

        Returns:
            A verdict: prefer_local, prefer_web, present_both, or flag_conflict.
        """
        decision = harness.reconcile_sources(query)
        if decision is None:
            return (
                "Nothing to reconcile. Need at least one kept local passage "
                "and one kept Exa passage. Search both sources first."
            )
        lines = [
            "# Jev source reconcile\n",
            f"verdict: `{decision.verdict}`  confidence={decision.confidence:.2f}",
            f"web_contradicts_local={decision.web_contradicts_local:.2f}",
            f"local_is_authoritative={decision.local_is_authoritative:.2f}",
            f"web_is_trustworthy={decision.web_is_trustworthy:.2f}",
            "",
            decision.reason,
        ]
        summary = "\n".join(lines)
        backend.upload_files([("/harness/reconcile.md", summary.encode("utf-8"))])
        return summary

    @tool(parse_docstring=True)
    def ask_jev(state: dict[str, Any], questions: list[dict[str, Any]]) -> str:
        """Ask Jev a Closed Loop. Open-ended questions are rejected.

        Follow /skills/jev-closed-loop/SKILL.md. Use this instead of asking
        the chat model to decide.

        Args:
            state: Named JSON fields (question, evidence, candidates, ...).
            questions: Closed Questions. Each item is
                {id, type: noul|choice|score, instructions, criteria?}.
                Fan-out independent questions in one call.

        Returns:
            Typed Noul/Choice/Score answers. Apply thresholds yourself.
        """
        try:
            parsed_state = parse_state(state)
            parsed_questions = parse_questions(questions)
        except ClosedLoopError as exc:
            return (
                f"Closed Loop rejected: {exc}\n"
                "Read /skills/jev-closed-loop/SKILL.md and resubmit "
                "Noul / Choice / Score only."
            )
        decision = harness.ask_closed(parsed_state, parsed_questions)
        summary = _closed_markdown(decision, parsed_questions)
        backend.upload_files([("/harness/ask_jev.md", summary.encode("utf-8"))])
        return summary

    @tool(parse_docstring=True)
    def judge_evidence(path: str, question: str) -> str:
        """Ask Jev whether a retrieved file supports, conflicts, or is silent.

        Replaces LLM chunk classification. Extraction can stay with read_file.

        Args:
            path: A kept file under /retrieved/.
            question: The user question to judge against.

        Returns:
            relation (supports|conflicts|silent) plus usable_facts / enough_to_answer.
        """
        text, source = _load_evidence_text(backend, harness, path)
        if not text:
            return (
                f"No text at {path}. Search first, then judge a kept /retrieved/ file."
            )
        decision = harness.judge_evidence(
            question, text, path=path, source=source
        )
        summary = _evidence_markdown(decision)
        backend.upload_files(
            [(f"/harness/judge_{_safe(path)}.md", summary.encode("utf-8"))]
        )
        return summary

    @tool(parse_docstring=True)
    def publish_answer(title: str, body: str) -> str:
        """Publish a grounded answer to /published/. Auto Mode may block this.

        Args:
            title: Short filename-safe title.
            body: Final answer text to persist.

        Returns:
            The published path, or an error if the harness blocked the call.
        """
        path = f"/published/{_safe(title) or 'answer'}.md"
        backend.upload_files([(path, body.encode("utf-8"))])
        return f"Published to {path}"

    return [
        plan_sources,
        search_documentation,
        search_web,
        reconcile_sources,
        ask_jev,
        judge_evidence,
        publish_answer,
    ]


def _current_plan(harness: JudgeApi, query: str) -> TurnPlan:
    """이미 계산된 턴 계획을 쓴다. 검색 질의로 다시 분류하지 않는다."""
    if harness.last_turn is not None:
        return harness.last_turn
    return harness.plan_turn(query)


def _engine_label(harness: JudgeApi) -> str:
    return "Jev" if getattr(harness, "engine", "jev") == "jev" else "LLM tool-call"


def _turn_markdown(plan: TurnPlan) -> str:
    return (
        "# Jev turn plan\n\n"
        f"{plan.reason}\n\n"
        f"- kind: {plan.kind} (confidence={plan.kind_confidence:.2f})\n"
        f"- sources: {plan.sources}\n"
        f"- analysis: {plan.analysis}\n"
        f"- allow_search: {plan.allow_search}\n"
        f"- allowed_local: {plan.allowed_local}\n"
        f"- allowed_web: {plan.allowed_web}\n"
        f"- needs_subagents: {plan.needs_subagents}\n"
        f"- model: {plan.model_name}\n"
        f"- thinking: {plan.thinking_effort}\n"
    )


def _closed_markdown(decision: ClosedLoopResult, questions: list) -> str:
    lines = [
        "# Jev Closed Loop\n",
        f"live={decision.live}  elapsed_ms={decision.elapsed_ms:.1f}",
        "",
        decision.reason,
        "",
    ]
    for question in questions:
        qid = question.id
        if qid in decision.nouls:
            lines.append(f"- noul `{qid}` = {decision.nouls[qid]:.2f}")
        elif qid in decision.choices:
            conf = decision.confidence.get(qid, 0.0)
            probs = decision.probabilities.get(qid, {})
            pretty = ", ".join(f"{key}={value:.2f}" for key, value in probs.items())
            lines.append(
                f"- choice `{qid}` = {decision.choices[qid]}  "
                f"conf={conf:.2f}  [{pretty}]"
            )
        elif qid in decision.scores:
            lines.append(
                f"- score `{qid}` = {decision.scores[qid]:.2f}  "
                f"conf={decision.confidence.get(qid, 0.0):.2f}"
            )
    return "\n".join(lines)


def _evidence_markdown(decision: EvidenceJudgment) -> str:
    return (
        "# Jev evidence judgment\n\n"
        f"path: {decision.path}\n"
        f"relation: `{decision.relation}`  "
        f"confidence={decision.relation_confidence:.2f}\n"
        f"usable_facts={decision.usable_facts:.2f}\n"
        f"enough_to_answer={decision.enough_to_answer:.2f}\n\n"
        f"{decision.reason}\n"
    )


def _load_evidence_text(
    backend: BackendProtocol,
    harness: JudgeApi,
    path: str,
) -> tuple[str, str]:
    for item in [*harness.last_gated, *getattr(harness, "last_attachments", [])]:
        if item.path == path:
            return item.passage.text, item.passage.source
    responses = backend.download_files([path])
    if not responses:
        return "", ""
    response = responses[0]
    if getattr(response, "error", None) or not getattr(response, "content", None):
        return "", ""
    text = response.content.decode("utf-8", errors="replace")
    return text, path


def _store_gated(
    backend: BackendProtocol,
    gated: list[GatedPassage],
    *,
    batch_prefix: str,
    headline: str,
    prefix: str = "",
) -> str:
    batch_id = uuid.uuid4().hex[:8]
    uploads: list[tuple[str, bytes]] = []
    lines = [
        headline,
        "Treat `exclude` as dropped. Do not reopen those passages.",
        "",
    ]
    if prefix:
        lines.insert(1, prefix.rstrip())
    for index, item in enumerate(gated, start=1):
        path = f"/retrieved/{batch_prefix}/{batch_id}/chunk_{index:02d}_{item.passage.doc_id}.md"
        item.path = path
        # 모델이 exclude 본문을 되살리지 못하게 한다.
        if item.route != "exclude":
            uploads.append((path, _chunk_markdown(item).encode("utf-8")))
        lines.append(
            f"- {item.route:22} {path}  "
            f"rel={item.is_relevant:.2f} evid={item.contains_answer_evidence:.2f} "
            f"contra={item.contradicts_query_premise:.2f} "
            f"inj={item.contains_prompt_injection:.2f}  "
            f"{item.passage.doc_id}"
        )
    if uploads:
        backend.upload_files(uploads)
    kept = sum(1 for item in gated if item.route != "exclude")
    lines.append(f"\nSaved {kept} files under /retrieved/{batch_prefix}/{batch_id}/")
    summary = "\n".join(lines)
    backend.upload_files(
        [
            (
                f"/harness/last_gate_{batch_prefix}.md",
                f"# Jev passage gate\n\n{summary}\n".encode(),
            )
        ]
    )
    return summary


def _chunk_markdown(item: GatedPassage) -> str:
    passage = item.passage
    return (
        f"# Source: {passage.source}\n"
        f"Title: {passage.title}\n"
        f"Route: {item.route}\n"
        f"Source type: {passage.source_type}\n\n"
        f"{passage.text}\n"
    )


def _safe(title: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in title)
