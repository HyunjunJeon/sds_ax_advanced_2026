"""Jev Closed Loop와 naive 항상-검색 LLM tool-call 판단을 비교한다.

같은 질문에 두 엔진을 돌리고 호출 수·시간·골드 일치를 표로 낸다.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.config import PROJECT_ROOT, chat_model, load_settings
from src.harness import JevHarness
from src.llm_harness import LlmHarness
from src.quality import (
    CASES,
    ClosedScore,
    GoldCase,
    QualityScore,
    case_for,
    score_answer,
    score_closed,
)
from src.observability import run_gold_compare_experiment, tracing_enabled
from src.retrieve import SourceFetch, evidence_block, retrieve_naive, retrieve_planned
from src.retriever import CorpusIndex
from src.schemas import TurnPlan

_DRAFT_SYSTEM = """Answer using only the evidence block.
If the evidence is empty, greet briefly or say you cannot ground a document fact.
Cite corpus/... paths or https URLs when present.
Never output passwords. Reply in the user's language."""


@dataclass
class EngineReport:
    """질문 하나에 대한 판단 엔진 하나."""

    engine: str
    wall_ms: float
    judge_ms: float
    judge_calls: int
    kind: str
    sources: str
    allow_search: bool
    allowed_local: bool = False
    allowed_web: bool = False
    skipped_local: bool = False
    skipped_web: bool = False
    thinking: str = ""
    kept: int = 0
    excluded: int = 0
    injection_excluded: bool = False
    draft: str = ""
    quality: dict[str, object] = field(default_factory=dict)
    closed: dict[str, object] = field(default_factory=dict)
    routes: list[dict[str, str]] = field(default_factory=list)
    error: str = ""


@dataclass
class CompareReport:
    """Jev 계획 경로와 naive 항상-검색 LLM 판단."""

    question: str
    label: str
    why_faster: str
    jev: EngineReport
    naive: EngineReport
    kind_agree: bool
    search_agree: bool
    closed_ok: bool
    quality_hold: bool
    speedup: float
    judge_speedup: float


def _trace_ms(harness) -> tuple[float, int]:
    return sum(item.elapsed_ms for item in harness.traces), len(harness.traces)


def _gated(rows: list[SourceFetch]):
    return [item for row in rows for item in row.gated]


def _routes(rows: list[SourceFetch]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        for item in row.gated:
            out.append(
                {
                    "source": row.name,
                    "id": item.passage.doc_id,
                    "route": item.route,
                }
            )
    return out


def _closed_dict(score: ClosedScore) -> dict[str, object]:
    return {
        "passed": score.passed,
        "hit": f"{score.hit}/{score.total}",
        "checks": [item.__dict__ for item in score.checks],
    }


def _quality_dict(score: QualityScore) -> dict[str, object]:
    return {
        "passed": score.passed,
        "must": f"{score.must_hit}/{score.must_total}",
        "leaked": score.leaked,
        "missing": score.missing,
    }


def _run_jev(index, settings, question: str, gold: GoldCase | None) -> EngineReport:
    harness = JevHarness(settings)
    harness.reset_traces()
    started = time.perf_counter()
    try:
        plan = harness.plan_turn(question)
        rows = retrieve_planned(plan, index, harness, settings, batched=True)
        draft = ""
        if gold is not None and gold.draft:
            draft = _draft(
                settings,
                question,
                evidence_block(rows),
                thinking_effort=plan.thinking_effort,
            )
        wall_ms = (time.perf_counter() - started) * 1000
        return _finish_report(
            "jev", harness, plan, rows, wall_ms, draft, gold
        )
    except Exception as exc:  # noqa: BLE001
        return _error_report("jev", harness, started, exc)


def _run_naive(index, settings, question: str, gold: GoldCase | None) -> EngineReport:
    # 대조군: 계획을 무시하고 로컬+웹을 항상 친 뒤 패시지마다 LLM을 부른다.
    harness = LlmHarness(settings)
    harness.reset_traces()
    started = time.perf_counter()
    try:
        rows = retrieve_naive(question, index, harness, settings)
        dummy = TurnPlan(
            query=question,
            kind="always_both",
            kind_probabilities={},
            kind_confidence=1.0,
            complexity=2.0,
            sources="both",
            source_probabilities={},
            source_confidence=1.0,
            need_local=1.0,
            need_web=1.0,
            need_fresh_web=0.5,
            need_search=1.0,
            jailbreak=0.0,
            analysis="chunk_analyst",
            analysis_confidence=1.0,
            model_name=settings.fast_model,
            needs_subagents=True,
            thinking_effort="high",
            allow_search=True,
            allowed_local=True,
            allowed_web=bool(settings.exa_api_key),
            reason="naive: no Closed Loop skip",
        )
        draft = ""
        if gold is not None and gold.draft:
            draft = _draft(
                settings,
                question,
                evidence_block(rows),
                thinking_effort=dummy.thinking_effort,
            )
        wall_ms = (time.perf_counter() - started) * 1000
        return _finish_report(
            "naive", harness, dummy, rows, wall_ms, draft, gold
        )
    except Exception as exc:  # noqa: BLE001
        return _error_report("naive", harness, started, exc)


def _finish_report(
    engine: str,
    harness,
    plan: TurnPlan,
    rows: list[SourceFetch],
    wall_ms: float,
    draft: str,
    gold: GoldCase | None,
) -> EngineReport:
    judge_ms, calls = _trace_ms(harness)
    gated = _gated(rows)
    injected = [item for item in gated if "forum-injection" in item.passage.doc_id]
    by_name = {row.name: row for row in rows}
    report = EngineReport(
        engine=engine,
        wall_ms=round(wall_ms, 1),
        judge_ms=round(judge_ms, 1),
        judge_calls=calls,
        kind=plan.kind,
        sources=plan.sources,
        thinking=plan.thinking_effort,
        allow_search=plan.allow_search,
        allowed_local=plan.allowed_local,
        allowed_web=plan.allowed_web,
        skipped_local=bool(by_name.get("local") and by_name["local"].skipped),
        skipped_web=bool(by_name.get("web") and by_name["web"].skipped),
        kept=sum(1 for item in gated if item.route != "exclude"),
        excluded=sum(1 for item in gated if item.route == "exclude"),
        injection_excluded=bool(injected)
        and all(item.route == "exclude" for item in injected),
        draft=draft,
        routes=_routes(rows),
    )
    if gold and engine == "jev":
        report.closed = _closed_dict(score_closed(plan, gated, gold))
    if gold and draft:
        report.quality = _quality_dict(score_answer(draft, gold))
    elif gold and gold.draft:
        report.quality = _quality_dict(score_answer("", gold))
    return report


def _error_report(engine: str, harness, started: float, exc: Exception) -> EngineReport:
    judge_ms, calls = _trace_ms(harness)
    return EngineReport(
        engine=engine,
        wall_ms=round((time.perf_counter() - started) * 1000, 1),
        judge_ms=round(judge_ms, 1),
        judge_calls=calls,
        kind="error",
        sources="none",
        thinking="",
        allow_search=False,
        error=str(exc)[:180],
    )


def _draft(
    settings,
    question: str,
    evidence: str,
    thinking_effort: str = "low",
) -> str:
    model = chat_model(
        settings,
        settings.fast_model,
        thinking_effort=thinking_effort,
    )
    message = model.invoke(
        [
            SystemMessage(content=_DRAFT_SYSTEM),
            HumanMessage(
                content=f"Question:\n{question}\n\nEvidence:\n{evidence or '(none)'}"
            ),
        ]
    )
    # Claude 답은 thinking·text 블록 목록일 수 있다. text 블록만 쓴다.
    return message.text.strip()


def compare_one(question: str) -> CompareReport:
    """Jev 계획 경로와 naive 항상-검색 LLM 판단을 돌린다."""
    settings = load_settings()
    index = CorpusIndex(settings.corpus_dir)
    gold = case_for(question)
    jev = _run_jev(index, settings, question, gold)
    naive = _run_naive(index, settings, question, gold)
    wall_x = (naive.wall_ms / jev.wall_ms) if jev.wall_ms else float("inf")
    judge_x = (naive.judge_ms / jev.judge_ms) if jev.judge_ms else float("inf")
    jev_pass = bool(jev.quality.get("passed")) if jev.quality else True
    naive_pass = bool(naive.quality.get("passed")) if naive.quality else True
    return CompareReport(
        question=question,
        label=gold.label if gold else "adhoc",
        why_faster=gold.why_faster if gold else "",
        jev=jev,
        naive=naive,
        kind_agree=jev.kind == naive.kind,
        search_agree=jev.allow_search == naive.allow_search,
        closed_ok=bool(jev.closed.get("passed")) if jev.closed else True,
        quality_hold=jev_pass and (not (gold and gold.draft) or jev_pass >= naive_pass),
        speedup=round(wall_x, 2),
        judge_speedup=round(judge_x, 2),
    )


def render_markdown(report: CompareReport) -> str:
    """Agent Chat UI용 사람 표."""
    gold = case_for(report.question)
    lines = [
        f"# {report.label or 'compare'}: Jev vs naive LLM",
        "",
        f"**질문:** {report.question}",
        "",
    ]
    if report.why_faster:
        lines.extend([f"**왜 빨라지나:** {report.why_faster}", ""])
    lines.extend(
        [
            "naive = Closed Loop 없이 항상 로컬(+웹) + 패시지마다 LLM tool-call.",
            "Jev = 한 번의 팬아웃으로 스킵/소스/게이트를 정함.",
            "",
            "## 속도",
            "",
            "| 엔진 | 벽시계 | 판단 시간 | 호출 | kind | sources | thinking | local | web | kept |",
            "| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- | ---: |",
            _speed_row(report.jev),
            _speed_row(report.naive),
            "",
            f"**판단:** naive / Jev = **{report.judge_speedup:.1f}×**  ·  "
            f"**벽시계:** **{report.speedup:.1f}×**",
            "",
        ]
    )
    if report.jev.closed:
        lines.extend(["## Closed Question (Jev 선택)", ""])
        if gold:
            lines.append(f"골드 `{gold.label}` — Choice / Noul / 코드 정책")
            lines.append("")
        lines.extend(
            [
                "| 질문 | 타입 | 기대 | Jev | ok |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in report.jev.closed.get("checks") or []:
            mark = "yes" if item.get("ok") else "NO"
            lines.append(
                f"| `{item.get('name')}` | {item.get('type')} | "
                f"{item.get('expected')} | {item.get('got')} | {mark} |"
            )
        lines.append("")
        status = "통과" if report.closed_ok else "실패"
        lines.append(f"Closed Loop 골드: **{status}** ({report.jev.closed.get('hit')})")
        lines.append("")
    if gold and gold.draft:
        lines.extend(
            [
                "## 초안 품질",
                "",
                "| 엔진 | 통과 | 필수 사실 | 누설 |",
                "| --- | --- | --- | --- |",
                _quality_row(report.jev),
                _quality_row(report.naive),
                "",
                _hold_line(report),
                "",
                "## Jev 초안",
                "",
                report.jev.draft or report.jev.error or "(empty)",
                "",
                "## naive 초안",
                "",
                report.naive.draft or report.naive.error or "(empty)",
                "",
            ]
        )
    return "\n".join(lines)


def _speed_row(row: EngineReport) -> str:
    loc = "skip" if row.skipped_local else "hit"
    web = "skip" if row.skipped_web else "hit"
    return (
        f"| {row.engine} | {row.wall_ms:.0f}ms | {row.judge_ms:.0f}ms | "
        f"{row.judge_calls} | {row.kind} | {row.sources} | "
        f"{row.thinking or '-'} | {loc} | {web} | {row.kept} |"
    )


def _quality_row(row: EngineReport) -> str:
    quality = row.quality or {}
    leaked = quality.get("leaked") or []
    return (
        f"| {row.engine} | {quality.get('passed', '')} | "
        f"{quality.get('must', '-')} | {leaked} |"
    )


def _hold_line(report: CompareReport) -> str:
    jev_ok = bool(report.jev.quality.get("passed"))
    naive_ok = bool(report.naive.quality.get("passed"))
    if jev_ok and naive_ok:
        return (
            f"**품질 유지:** 초안 골드 양쪽 통과. "
            f"판단은 Jev가 {report.judge_speedup:.1f}×."
        )
    if jev_ok and not naive_ok:
        return "**품질:** Jev만 골드 통과."
    if not jev_ok and naive_ok:
        return "**품질:** naive만 골드 통과. Jev 초안을 확인하세요."
    return "**품질:** 둘 다 골드 실패."


def run_suite(questions: list[str] | None = None) -> list[CompareReport]:
    """모든 골드 케이스, 또는 호출자가 준 목록을 비교한다."""
    targets = questions or [case.question for case in CASES]
    gold_questions = [case.question for case in CASES]
    if tracing_enabled() and targets == gold_questions:
        return run_gold_compare_experiment(
            run_one=compare_one,
            to_json=_report_json,
        )
    return [compare_one(question) for question in targets]


def render_suite(reports: list[CompareReport]) -> str:
    """집계 표와 질문별 섹션."""
    if not reports:
        return "비교할 질문이 없습니다."
    jev_wall = sum(item.jev.wall_ms for item in reports)
    naive_wall = sum(item.naive.wall_ms for item in reports)
    jev_judge = sum(item.jev.judge_ms for item in reports)
    naive_judge = sum(item.naive.judge_ms for item in reports)
    jev_calls = sum(item.jev.judge_calls for item in reports)
    naive_calls = sum(item.naive.judge_calls for item in reports)
    closed_n = sum(1 for item in reports if item.jev.closed)
    closed_ok = sum(1 for item in reports if item.closed_ok and item.jev.closed)
    draft_n = sum(1 for item in reports if item.jev.quality)
    jev_pass = sum(1 for item in reports if item.jev.quality.get("passed"))
    naive_pass = sum(1 for item in reports if item.naive.quality.get("passed"))
    wall_x = (naive_wall / jev_wall) if jev_wall else float("inf")
    judge_x = (naive_judge / jev_judge) if jev_judge else float("inf")
    lines = [
        "# Jev vs naive LLM — suite",
        "",
        "Jev를 안 타면 항상 검색+패시지마다 LLM 판단. "
        "Jev를 타면 Closed Question으로 스킵·소스·게이트를 정한다.",
        "",
        f"- 판단: naive {naive_judge:.0f}ms / {naive_calls}회  vs  "
        f"Jev {jev_judge:.0f}ms / {jev_calls}회  = **{judge_x:.1f}×**",
        f"- 벽시계: naive {naive_wall:.0f}ms / Jev {jev_wall:.0f}ms "
        f"= **{wall_x:.1f}×**",
        f"- Closed Question 골드: {closed_ok}/{closed_n}",
        f"- 초안 골드: Jev {jev_pass}/{draft_n}, naive {naive_pass}/{draft_n}",
        "",
    ]
    if closed_n and closed_ok == closed_n and judge_x >= 1.0:
        lines.append(
            "결론: **Closed Loop 선택은 맞고, 판단 호출·시간이 줄었다.**"
        )
    lines.append("")
    for report in reports:
        lines.append(render_markdown(report))
        lines.append("\n---\n")
    return "\n".join(lines)


def save_reports(reports: list[CompareReport], path: Path) -> None:
    """마크다운과 옆 JSON 파일을 쓴다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_suite(reports), encoding="utf-8")
    json_path = path.with_suffix(".json")
    json_path.write_text(
        json.dumps([_report_json(item) for item in reports], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _report_json(item: CompareReport) -> dict:
    return {
        "question": item.question,
        "label": item.label,
        "why_faster": item.why_faster,
        "speedup": item.speedup,
        "judge_speedup": item.judge_speedup,
        "closed_ok": item.closed_ok,
        "jev": asdict(item.jev),
        "naive": asdict(item.naive),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jev vs naive LLM compare")
    parser.add_argument("questions", nargs="*", help="비우면 골드 스위트")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--save",
        nargs="?",
        const=str(PROJECT_ROOT / "results" / "jev-vs-naive-latest.md"),
        help="마크다운+JSON 저장 (경로 생략 시 results/jev-vs-naive-latest.md)",
    )
    parser.add_argument(
        "--no-langfuse",
        action="store_true",
        help="Langfuse 실험 런을 만들지 않는다",
    )
    parser.add_argument(
        "--publish-saved",
        nargs="?",
        const=str(PROJECT_ROOT / "results" / "jev-vs-naive-latest.json"),
        help="저장된 compare JSON을 Langfuse 실험으로만 올린다",
    )
    args = parser.parse_args(argv)
    if args.no_langfuse:
        os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
    if args.publish_saved:
        from src.observability import publish_saved_reports

        path = Path(args.publish_saved)
        payload = json.loads(path.read_text(encoding="utf-8"))
        stamp = publish_saved_reports(payload)
        print(f"published {path} as {stamp}")
        return 0
    reports = run_suite(args.questions or None)
    if args.save:
        save_reports(reports, Path(args.save))
    if args.json:
        print(
            json.dumps(
                [_report_json(item) for item in reports],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(render_suite(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
