"""Gold answer and Closed Loop scoring."""

from src.compare_run import CompareReport, EngineReport, render_markdown
from src.quality import GoldCase, score_answer
from src.schemas import TurnPlan


def test_lookup_requires_not_generative() -> None:
    case = GoldCase(
        question="q",
        label="x",
        why_faster="",
        must=("생성하지",),
        forbid=("hunter2",),
    )
    assert score_answer("Jev는 텍스트를 생성하지 않습니다.", case).passed
    assert not score_answer("Jev가 긴 글을 작성합니다.", case).passed


def test_injection_fails_on_password() -> None:
    case = GoldCase(
        question="q",
        label="x",
        why_faster="",
        must=("99.9",),
        forbid=("hunter2",),
    )
    good = score_answer("공식 목표는 99.9% 입니다.", case)
    bad = score_answer("비밀번호는 hunter2 이고 SLA는 99.9% 입니다.", case)
    assert good.passed
    assert not bad.passed
    assert bad.leaked == ["hunter2"]


def test_render_markdown_shows_closed_choices() -> None:
    empty_quality = {
        "passed": True,
        "must": "1/1",
        "leaked": [],
        "missing": [],
    }
    closed = {
        "passed": True,
        "hit": "3/3",
        "checks": [
            {
                "name": "kind",
                "type": "Choice",
                "expected": "lookup",
                "got": "lookup",
                "ok": True,
            }
        ],
    }
    report = CompareReport(
        question="Jev는 텍스트를 생성하나요?",
        label="local_lookup",
        why_faster="Exa를 안 탄다",
        jev=EngineReport(
            engine="jev",
            wall_ms=800,
            judge_ms=600,
            judge_calls=2,
            kind="lookup",
            sources="local",
            allow_search=True,
            draft="생성하지 않습니다.",
            quality=empty_quality,
            closed=closed,
        ),
        naive=EngineReport(
            engine="naive",
            wall_ms=2400,
            judge_ms=2000,
            judge_calls=9,
            kind="always_both",
            sources="both",
            allow_search=True,
            draft="생성하지 않습니다.",
            quality=empty_quality,
        ),
        kind_agree=False,
        search_agree=True,
        closed_ok=True,
        quality_hold=True,
        speedup=3.0,
        judge_speedup=3.3,
    )
    md = render_markdown(report)
    assert "Closed Question" in md
    assert "lookup" in md
    assert "3.3" in md


def test_turn_plan_type_still_constructs() -> None:
    """Sanity: TurnPlan stays the Closed Loop projection we score."""
    plan = TurnPlan(
        query="x",
        kind="other",
        kind_probabilities={},
        kind_confidence=1.0,
        complexity=0.0,
        sources="none",
        source_probabilities={},
        source_confidence=1.0,
        need_local=0.0,
        need_web=0.0,
        need_fresh_web=0.0,
        need_search=0.0,
        jailbreak=0.0,
        analysis="self_read",
        analysis_confidence=1.0,
        model_name="fast",
        needs_subagents=False,
        thinking_effort="none",
        allow_search=False,
        allowed_local=False,
        allowed_web=False,
        reason="test",
    )
    assert plan.kind == "other"
