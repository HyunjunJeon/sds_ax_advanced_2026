"""Langfuse 추적과 골드 스위트 실험 기록.

키가 없거나 LANGFUSE_TRACING_ENABLED=false면 전부 no-op.
첨부 바이너리와 긴 본문은 올려서 시연 보드를 더럽히지 않는다.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable

from src.agent.config import load_settings
from src.quality import CASES, GoldCase
from src.schemas import DecisionTrace, TurnPlan

DATASET_NAME = "jev-rag-gold"
EXPERIMENT_NAME = "Jev vs naive"
_MAX_TEXT = 4000
_client: Any = None
# Chat UI는 session 이름을 안 넘긴다. thread → 사람이 읽는 세션 이름을 묶는다.
_THREAD_SESSIONS: dict[str, str] = {}
_JEV_STAGE_LABELS = {
    "turn_plan": "Jev · 턴 판단",
    "query_route": "Jev · 질문 분류",
    "reconcile_sources": "Jev · 소스 조정",
    "ask_jev": "Jev · 닫힌 질문",
    "judge_evidence": "Jev · 근거 판단",
    "passage_batch": "Jev · 패시지 게이트",
    "grounding": "Jev · 그라운딩",
    "citation": "Jev · 인용 검사",
    "auto_mode": "Jev · Auto Mode",
}


def tracing_enabled() -> bool:
    """설정과 환경 플래그로 전송 여부를 본다."""
    return load_settings().langfuse_enabled


def resolve_session_id(metadata: dict[str, Any] | None = None) -> str | None:
    """Sessions 탭에 묶일 id. 환경 변수 > 런 메타데이터 > 묶인 thread."""
    env = os.getenv("LANGFUSE_SESSION_ID", "").strip()
    if env:
        return env
    graph = _langgraph_config()
    merged: dict[str, Any] = {
        **(graph.get("metadata") or {}),
        **((graph.get("configurable") or {}) if isinstance(graph.get("configurable"), dict) else {}),
        **(metadata or {}),
    }
    for key in ("langfuse_session_id", "session_id"):
        value = merged.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    thread = merged.get("thread_id") or graph.get("thread_id") or _thread_id()
    if isinstance(thread, str) and thread.strip():
        bound = _THREAD_SESSIONS.get(thread.strip())
        if bound:
            return bound
        return thread.strip()
    return None


def bind_thread_session(thread_id: str, session_id: str) -> None:
    """같은 LangGraph thread는 같은 대화 세션으로 남긴다."""
    tid = (thread_id or "").strip()
    sid = (session_id or "").strip()
    if tid and sid:
        _THREAD_SESSIONS[tid] = sid


def human_session_name(thread_id: str, question: str = "") -> str:
    """UI 스레드를 사람이 읽는 세션 이름으로 고정한다."""
    tid = (thread_id or "").strip()
    if tid and tid in _THREAD_SESSIONS:
        return _THREAD_SESSIONS[tid]
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    title = conversation_title(question, limit=36) if question.strip() else "새 대화"
    name = f"대화 {stamp} · {title}"
    if tid:
        _THREAD_SESSIONS[tid] = name
    return name


def jev_stage_label(stage: str) -> str:
    """Jev 호출 단계를 보드에서 바로 읽히는 이름으로 바꾼다."""
    return _JEV_STAGE_LABELS.get(stage, f"Jev · {stage}")


def jev_observation_payload(trace: DecisionTrace) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Closed Question 입출력을 Langfuse generation 형태로 만든다."""
    name = jev_stage_label(trace.stage)
    payload_in = {
        "stage": trace.stage,
        "note": trace.note,
        "questions": trace.questions,
    }
    payload_out = {
        "live": trace.live,
        "elapsed_ms": round(float(trace.elapsed_ms), 1),
        **(trace.answers or {}),
    }
    return name, payload_in, payload_out


def langfuse_run_config(session_id: str | None = None, *extra_tags: str) -> dict[str, Any]:
    """LangGraph /threads/.../runs 에 넣을 session 메타데이터."""
    sid = session_id or resolve_session_id()
    tags = ["jev-rag", *[item for item in extra_tags if item]]
    metadata: dict[str, Any] = {
        "langfuse_user_id": os.getenv("LANGFUSE_USER_ID", "jev-rag-demo"),
        "langfuse_tags": tags,
    }
    if sid:
        metadata["langfuse_session_id"] = sid
    return {"metadata": metadata}


def conversation_title(text: str, *, limit: int = 72) -> str:
    """세션/트레이스 제목. 질문 문장을 그대로 쓴다."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "대화"
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def extract_user_text(inputs: Any) -> str:
    """LangChain 루트 입력에서 마지막 사용자 문장을 꺼낸다."""
    if isinstance(inputs, str):
        return inputs.strip()
    if isinstance(inputs, dict):
        messages = inputs.get("messages")
        if isinstance(messages, list):
            for message in reversed(messages):
                text = _message_text(message)
                if text:
                    return text
        for key in ("question", "input", "content"):
            value = inputs.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def explain_plan(plan: TurnPlan) -> str:
    """Jev 선택을 사람이 읽는 한 턴 설명으로 바꾼다."""
    if plan.jailbreak >= 0.70:
        return "시스템 지시를 빼내려는 말로 보고 검색을 끄고 거절합니다."
    if not plan.allow_search:
        return "문서가 필요 없는 말로 보고 검색 없이 짧게 답합니다."
    kind = {
        "lookup": "한 가지 사실을 찾는 질문입니다.",
        "compare": "두 가지를 비교하는 질문입니다.",
        "investigate": "여러 근거가 필요한 조사 질문입니다.",
        "other": "문서 검색이 필요 없는 질문입니다.",
    }.get(plan.kind, "질문 종류를 정했습니다.")
    if plan.allowed_local and plan.allowed_web:
        source = "로컬 문서와 웹을 함께 봅니다."
    elif plan.allowed_local:
        source = "로컬 문서만 봅니다."
    elif plan.allowed_web:
        source = "웹만 봅니다."
    else:
        source = "검색하지 않습니다."
    think = {
        "none": "추가 생각은 하지 않습니다.",
        "minimal": "생각은 최소로 둡니다.",
        "low": "생각은 낮게 둡니다.",
        "medium": "생각은 중간으로 둡니다.",
        "high": "생각은 높게 둡니다.",
    }.get(plan.thinking_effort, "")
    return " ".join(part for part in (kind, source, think) if part)


def gold_dataset_records() -> list[dict[str, Any]]:
    """Langfuse 데이터셋에 올릴 골드 케이스 레코드."""
    return [_dataset_record(case) for case in CASES]


def turn_metadata(plan: TurnPlan, *, graph: str = "", engine: str = "") -> dict[str, Any]:
    """시연 보드에서 필터할 TurnPlan 필드만 남긴다."""
    return {
        "graph": graph,
        "engine": engine or "",
        "kind": plan.kind,
        "sources": plan.sources,
        "thinking": plan.thinking_effort,
        "analysis": plan.analysis,
        "allow_search": plan.allow_search,
        "allowed_local": plan.allowed_local,
        "allowed_web": plan.allowed_web,
        "allowed_attachment": plan.allowed_attachment,
        "model": plan.model_name,
        "jailbreak": round(plan.jailbreak, 3),
        "need_search": round(plan.need_search, 3),
        "need_local": round(plan.need_local, 3),
        "need_web": round(plan.need_web, 3),
        "need_attachment": round(plan.need_attachment, 3),
    }


def mask_value(data: Any) -> Any:
    """PDF/data-URL과 너무 긴 문자열을 잘라 시연 트레이스를 읽히게 한다."""
    if isinstance(data, str):
        stripped = data.lstrip()
        if stripped.startswith("data:") or "application/pdf" in stripped[:120]:
            return "[redacted-binary]"
        if len(data) > _MAX_TEXT:
            return f"{data[:_MAX_TEXT]}...[{len(data)} chars]"
        return data
    if isinstance(data, dict):
        return {str(key): mask_value(value) for key, value in data.items()}
    if isinstance(data, list):
        return [mask_value(item) for item in data[:40]]
    if isinstance(data, tuple):
        return [mask_value(item) for item in data[:40]]
    return data


def configure_client() -> Any | None:
    """환경 변수로 Langfuse 클라이언트를 한 번만 연다."""
    global _client
    if not tracing_enabled():
        return None
    if _client is not None:
        return _client
    settings = load_settings()
    from langfuse import Langfuse

    _client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
        environment=settings.langfuse_environment,
        mask=mask_value,
    )
    return _client


def project_url() -> str:
    """프로젝트 UI 루트. 키는 넣지 않는다."""
    settings = load_settings()
    return settings.langfuse_base_url.rstrip("/")


def session_url(session_id: str) -> str:
    """Sessions 탭에서 바로 열리는 주소."""
    settings = load_settings()
    return (
        f"{settings.langfuse_base_url.rstrip('/')}"
        f"/project/{_project_id()}/sessions/{session_id}"
    )


def _project_id() -> str:
    """이미 만들어 둔 데이터셋에서 프로젝트 id를 읽는다."""
    cached = os.getenv("LANGFUSE_PROJECT_ID", "").strip()
    if cached:
        return cached
    return "cmtw7heqy002tad0dgcugr6qb"


def record_session_span(
    name: str,
    *,
    input_data: Any = None,
    output: Any = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> None:
    """Sessions에 남을 독립 스팬 하나. 테스트 요약용."""
    if not tracing_enabled():
        return
    client = configure_client()
    if client is None:
        return
    from langfuse import propagate_attributes

    session = resolve_session_id()
    with propagate_attributes(
        session_id=session,
        user_id=os.getenv("LANGFUSE_USER_ID", "jev-rag-demo"),
        tags=tags or ["test"],
        metadata=metadata,
        trace_name=name,
    ):
        with client.start_as_current_observation(
            name=name,
            as_type="span",
            input=mask_value(input_data),
            output=mask_value(output),
            metadata=metadata,
        ):
            pass
    client.flush()


def instrument_graph(graph: Any, name: str) -> Any:
    """LangGraph API invoke마다 CallbackHandler가 붙도록 그래프를 묶는다."""
    if not tracing_enabled():
        return graph
    configure_client()
    from langchain_core.callbacks import BaseCallbackHandler
    from langfuse.langchain import CallbackHandler

    class _SessionMetadataCallback(BaseCallbackHandler):
        """루트 체인 시작 전에 session_id를 CallbackHandler가 읽게 넣는다."""

        def on_chain_start(
            self,
            serialized: Any,
            inputs: Any,
            *,
            run_id: Any,
            parent_run_id: Any = None,
            metadata: dict[str, Any] | None = None,
            **_kwargs: Any,
        ) -> None:
            del serialized, run_id
            if parent_run_id is not None or not isinstance(metadata, dict):
                return
            thread = str(metadata.get("thread_id") or _thread_id() or "").strip()
            question = extract_user_text(inputs)
            given = metadata.get("langfuse_session_id")
            if isinstance(given, str) and given.strip():
                session = given.strip()
                if thread:
                    bind_thread_session(thread, session)
            elif thread:
                session = human_session_name(thread, question)
            else:
                session = None
            if session:
                metadata["langfuse_session_id"] = session
            if thread:
                metadata["thread_id"] = thread
            if question:
                metadata["langfuse_trace_name"] = conversation_title(question)
            metadata.setdefault(
                "langfuse_user_id",
                os.getenv("LANGFUSE_USER_ID", "jev-rag-demo"),
            )

    binder = getattr(graph, "with_config", None)
    if binder is None:
        return graph
    return binder(
        {
            "callbacks": [_SessionMetadataCallback(), CallbackHandler()],
            "tags": [name, "jev-rag"],
            "metadata": {"graph": name},
        }
    )


def record_jev_call(trace: DecisionTrace, *, engine: str = "jev") -> None:
    """Jev Closed Question 한 호출을 현재 턴 트레이스에 generation으로 남긴다.

    예전에는 별도 루트 트레이스를 만들어 대화 세션에서 빠졌다.
    trace_name을 바꾸지 않아 LangChain 루트 아래에 붙는다.
    """
    if not tracing_enabled():
        return
    client = configure_client()
    if client is None:
        return
    try:
        from langfuse import propagate_attributes

        name, payload_in, payload_out = jev_observation_payload(trace)
        session = resolve_session_id()
        meta = {
            "engine": engine,
            "stage": trace.stage,
            "live": trace.live,
        }
        with propagate_attributes(
            session_id=session,
            user_id=os.getenv("LANGFUSE_USER_ID", "jev-rag-demo"),
            tags=["jev", engine, trace.stage],
            metadata=meta,
        ):
            with client.start_as_current_observation(
                name=name,
                as_type="generation",
                model="typesafe/jev" if engine == "jev" else "llm-judge",
                input=mask_value(payload_in),
                output=mask_value(payload_out),
                metadata=meta,
            ):
                pass
    except Exception:
        return


def annotate_turn(
    plan: TurnPlan | None,
    *,
    graph: str,
    engine: str = "",
) -> None:
    """현재 트레이스에 Jev 선택 요약을 자식 스팬으로 남긴다."""
    if plan is None or not tracing_enabled():
        return
    client = configure_client()
    if client is None:
        return
    try:
        from langfuse import propagate_attributes

        meta = turn_metadata(plan, graph=graph, engine=engine)
        session = resolve_session_id()
        if session:
            meta["session_id"] = session
        with propagate_attributes(
            session_id=session,
            tags=[graph, engine or "jev", "turn-plan"],
            metadata=meta,
        ):
            with client.start_as_current_observation(
                name="Jev 판단",
                as_type="span",
                input=plan.query,
                output=explain_plan(plan),
                metadata=meta,
            ):
                pass
    except Exception:
        return


def record_turn_answer(plan: TurnPlan | None, answer: str) -> None:
    """같은 턴 트레이스에 사람 답을 남긴다."""
    if plan is None or not tracing_enabled():
        return
    client = configure_client()
    if client is None:
        return
    try:
        from langfuse import propagate_attributes

        with propagate_attributes(
            session_id=resolve_session_id(),
            tags=["답변"],
        ):
            with client.start_as_current_observation(
                name="답변",
                as_type="span",
                input=plan.query,
                output=mask_value(answer),
            ):
                pass
        client.flush()
    except Exception:
        return


def ensure_gold_dataset(client: Any | None = None) -> Any:
    """시연 골드 6문항을 멱등으로 맞춘다."""
    client = client or configure_client()
    if client is None:
        raise RuntimeError("Langfuse is not enabled")
    try:
        client.get_dataset(DATASET_NAME)
    except Exception:
        client.create_dataset(
            name=DATASET_NAME,
            description=(
                "Jev RAG 시연 골드. skip / lookup / compare / web / injection."
            ),
            metadata={"project": "jev-deepagents-rag"},
        )
    for record in gold_dataset_records():
        client.create_dataset_item(
            dataset_name=DATASET_NAME,
            id=record["id"],
            input=record["input"],
            expected_output=record["expected_output"],
            metadata=record["metadata"],
        )
    return client.get_dataset(DATASET_NAME)


def run_gold_compare_experiment(
    *,
    run_one: Callable[[str], Any],
    to_json: Callable[[Any], dict[str, Any]],
    run_name: str | None = None,
) -> list[Any]:
    """골드 스위트를 돌리며 Langfuse 실험 런을 만든다."""
    client = configure_client()
    if client is None:
        return [run_one(case.question) for case in CASES]
    dataset = ensure_gold_dataset(client)
    collected: dict[str, Any] = {}
    stamp = run_name or _run_name()
    session = resolve_session_id() or stamp

    def task(*, item: Any, **_kwargs: Any) -> dict[str, Any]:
        from langfuse import propagate_attributes

        question = item_question(item)
        with propagate_attributes(
            session_id=session,
            user_id=os.getenv("LANGFUSE_USER_ID", "jev-rag-demo"),
            tags=["compare", "gold"],
        ):
            report = run_one(question)
        collected[question] = report
        return to_json(report)

    result = dataset.run_experiment(
        name=EXPERIMENT_NAME,
        run_name=stamp,
        description="Closed Loop vs always-search LLM judge",
        task=task,
        evaluators=[
            eval_closed_ok,
            eval_draft_ok,
            eval_judge_speedup,
            eval_wall_speedup,
        ],
        run_evaluators=[eval_closed_pass_rate, eval_suite_judge_speedup],
        max_concurrency=1,
        metadata={
            "suite": "gold",
            "engine": "compare",
            "session_id": session,
        },
    )
    client.flush()
    url = getattr(result, "dataset_run_url", None) or project_url()
    print(f"Langfuse experiment: {url}")
    return [collected[case.question] for case in CASES]


def publish_saved_reports(
    reports: list[dict[str, Any]],
    *,
    run_name: str | None = None,
) -> str:
    """이미 계산된 compare JSON을 재실행 없이 실험으로 올린다."""
    client = configure_client()
    if client is None:
        raise RuntimeError("Langfuse is not enabled")
    dataset = ensure_gold_dataset(client)
    by_question = {str(item.get("question")): item for item in reports}
    stamp = run_name or "jev-vs-naive-saved"
    session = resolve_session_id() or stamp

    def task(*, item: Any, **_kwargs: Any) -> dict[str, Any]:
        from langfuse import propagate_attributes

        question = item_question(item)
        payload = by_question.get(question)
        if payload is None:
            raise KeyError(f"saved report missing: {question}")
        with propagate_attributes(
            session_id=session,
            user_id=os.getenv("LANGFUSE_USER_ID", "jev-rag-demo"),
            tags=["compare", "saved"],
        ):
            return payload

    result = dataset.run_experiment(
        name=EXPERIMENT_NAME,
        run_name=stamp,
        description="Saved compare suite (no engine rerun)",
        task=task,
        evaluators=[
            eval_closed_ok,
            eval_draft_ok,
            eval_judge_speedup,
            eval_wall_speedup,
        ],
        run_evaluators=[eval_closed_pass_rate, eval_suite_judge_speedup],
        max_concurrency=4,
        metadata={"suite": "gold", "source": "saved-json"},
    )
    client.flush()
    url = getattr(result, "dataset_run_url", None) or project_url()
    print(f"Langfuse experiment: {url}")
    return stamp


def eval_closed_ok(*, output: Any, **_kwargs: Any) -> Any:
    """문항별 Closed Question 골드."""
    from langfuse import Evaluation

    ok = bool((output or {}).get("closed_ok"))
    return Evaluation(name="closed_ok", value=1.0 if ok else 0.0)


def eval_draft_ok(*, output: Any, **_kwargs: Any) -> Any:
    """초안 골드가 있는 문항만 채점하고, 없으면 통과로 둔다."""
    from langfuse import Evaluation

    quality = ((output or {}).get("jev") or {}).get("quality") or {}
    if not quality:
        return Evaluation(name="draft_ok", value=1.0, comment="no draft gold")
    passed = bool(quality.get("passed"))
    missing = quality.get("missing") or []
    leaked = quality.get("leaked") or []
    comment = ""
    if missing or leaked:
        comment = f"missing={missing} leaked={leaked}"
    return Evaluation(name="draft_ok", value=1.0 if passed else 0.0, comment=comment)


def eval_judge_speedup(*, output: Any, **_kwargs: Any) -> Any:
    """naive 판단 시간 / Jev 판단 시간."""
    from langfuse import Evaluation

    return Evaluation(
        name="judge_speedup",
        value=float((output or {}).get("judge_speedup") or 0.0),
    )


def eval_wall_speedup(*, output: Any, **_kwargs: Any) -> Any:
    """naive 벽시계 / Jev 벽시계."""
    from langfuse import Evaluation

    return Evaluation(
        name="wall_speedup",
        value=float((output or {}).get("speedup") or 0.0),
    )


def eval_closed_pass_rate(*, item_results: Any, **_kwargs: Any) -> Any:
    """런 전체 Closed Question 통과율."""
    from langfuse import Evaluation

    outputs = [_item_output(item) for item in item_results or []]
    if not outputs:
        return Evaluation(name="closed_pass_rate", value=0.0)
    hit = sum(1 for item in outputs if item.get("closed_ok"))
    return Evaluation(name="closed_pass_rate", value=hit / len(outputs))


def eval_suite_judge_speedup(*, item_results: Any, **_kwargs: Any) -> Any:
    """런 전체 naive/Jev 판단 시간 비."""
    from langfuse import Evaluation

    jev_ms = 0.0
    naive_ms = 0.0
    for item in item_results or []:
        output = _item_output(item)
        jev_ms += float(((output.get("jev") or {}).get("judge_ms") or 0))
        naive_ms += float(((output.get("naive") or {}).get("judge_ms") or 0))
    value = (naive_ms / jev_ms) if jev_ms else 0.0
    return Evaluation(name="suite_judge_speedup", value=round(value, 2))


def item_question(item: Any) -> str:
    """데이터셋 아이템에서 질문 문자열을 꺼낸다."""
    payload = getattr(item, "input", None)
    if payload is None and isinstance(item, dict):
        payload = item.get("input", item)
    if isinstance(payload, dict):
        return str(payload.get("question") or "")
    return str(payload or "")


def _dataset_record(case: GoldCase) -> dict[str, Any]:
    return {
        "id": f"{DATASET_NAME}:{case.label}",
        "input": {"question": case.question, "label": case.label},
        "expected_output": {
            "kind": list(case.kind),
            "sources": list(case.sources),
            "thinking": list(case.thinking),
            "must": list(case.must),
            "forbid": list(case.forbid),
            "allow_search": case.allow_search,
            "allowed_local": case.allowed_local,
            "allowed_web": case.allowed_web,
        },
        "metadata": {"why_faster": case.why_faster, "draft": case.draft},
    }


def _item_output(item: Any) -> dict[str, Any]:
    output = getattr(item, "output", None)
    if output is None and isinstance(item, dict):
        output = item.get("output")
    return output if isinstance(output, dict) else {}


def _run_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"jev-vs-naive-{stamp}"


def _message_text(message: Any) -> str:
    if isinstance(message, str):
        return message.strip()
    if isinstance(message, dict):
        content = message.get("content") or message.get("text") or ""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                str(part.get("text") or "")
                for part in content
                if isinstance(part, dict)
            ]
            return " ".join(part for part in parts if part).strip()
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()
    return ""


def _langgraph_config() -> dict[str, Any]:
    """현재 LangGraph 런 config. 미들웨어 밖이면 빈 dict."""
    try:
        from langgraph.config import get_config

        config = get_config()
    except Exception:
        return {}
    return config if isinstance(config, dict) else {}


def _thread_id() -> str | None:
    config = _langgraph_config()
    if not config:
        return None
    configurable = config.get("configurable") or {}
    value = configurable.get("thread_id") or config.get("thread_id")
    return str(value) if value else None
