"""사례를 에이전트로 실행하고 채점해 Langfuse와 로컬 사본(outputs/runs/*.jsonl)에(record="local"이면 로컬 사본에만) 남기고, 변형을 비교한다.

사전 등록(docs/DESIGN.md의 P4~P6)을 코드로 옮긴 실행기다.
- 에이전트는 사례의 turns만 받는다. 기대값(expect, 데이터셋의 expected_output)은 채점에만 쓴다.
- 사용자 발화와 elicitation 응답은 사례에 적힌 대로 보낸다. 모델이 사용자를 흉내 내지 않는다.
- 로컬 사본은 오류가 난 항목을 포함해 모든 항목을 남긴다. 같은 실행 이름의 기록이 있으면 시작하지 않는다.
- 비교는 cap_lab.stats의 쌍체 부트스트랩과 사전 등록된 decide()를 그대로 쓴다.
"""
from __future__ import annotations

import asyncio
import gc
import hashlib
import json
import time
from collections import Counter, defaultdict
from collections.abc import Coroutine, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from langchain_anthropic._client_utils import _AsyncHttpxClientWrapper, _get_default_async_httpx_client
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langfuse import Evaluation, Langfuse
from langfuse.api import DatasetItem, NotFoundError
from langfuse.experiment import ExperimentItemResult
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Interrupt

from cap_lab.agent import SERVER_SCRIPT, SKILLS_DIR, build_agent, server_argv
from cap_lab.decisions import BACKENDS, DecisionBackend, make_decider
from cap_lab.scorers import STAGE_OF, STAGE_ORDER, RunRecord, Score, first_failure, score_run
from cap_lab.server.server import FaultPlan
from cap_lab.settings import ROOT, Settings, require
from cap_lab.stats import decide, noise_band, paired_bootstrap_diff, wilson_ci

CASES_PATH = ROOT / "data" / "cases.jsonl"
DATASET_NAME = "day04_new-capability-v1"
MIRROR_DIR = ROOT / "outputs" / "runs"
SKILL_FILE = "requirements-interview/SKILL.md"
# 서버 코드 sha256에 넣는 파일. 서버 스크립트 뒤에 이 순서로 이어 붙인다.
SERVER_MODULES = tuple(SERVER_SCRIPT.parent / name for name in ("workflow.py", "evidence.py", "gate.py"))

BOOLEAN_SCORES = (*STAGE_OF, "contamination_free")
LOWER_IS_BETTER = ("model_calls", "tool_calls", "latency_s")

# 사례당 Claude 호출 추정치(docs/DESIGN.md 8절, Day04/build_mcp/README.md:262의 4 사례 20~35회).
CLAUDE_CALLS_PER_RUN = (5, 9)
# 게이트 하나가 실행 한 번에 Jev를 부르는 횟수의 상한 추정(docs/DESIGN.md 8절 "1~3회").
JEV_CALLS_PER_GATE_RUN = 3
# 한 번에 한 사례만 실행한다. make_model이 max_retries=0이라 동시 호출의 429가 그대로 실패가 되고,
# latency_s는 가드 지표라 동시 실행의 경합이 섞이면 안 된다. 로컬 사본 쓰기도 한 줄씩 이어진다.
MAX_CONCURRENCY = 1
# 한 턴에서 elicitation 재개를 이어 갈 최대 횟수. 거절 -> criteria_not_testable -> 같은 답 재전송이 끝없이
# 이어지면 재개마다 과금된다. 넘으면 실행을 멈추고 오류로 남긴다(채점에서 확인 불가).
MAX_RESUMES_PER_TURN = 5

ELICITATION_INTERRUPT = "mcp_elicitation"


@dataclass(frozen=True)
class Variant:
    """비교할 구성 하나. 이름이 실행 이름(<name>-r<k>)과 작업 폴더 이름이 된다.

    interface는 서버의 --interface다(Part 2 비교: rich 또는 enum·설명·annotations·outputSchema를 뺀 plain).
    tool_disclosure는 build_agent의 MCP 도구 공개 방식이다(Part 5 비교: Skill을 읽은 뒤 공개 또는 처음부터 공개).
    """

    name: str
    gate_h1: bool = False
    gate_h2: bool = False
    threshold_h1: float = 0.5
    threshold_h2: float = 0.5
    skills_dir: Path = SKILLS_DIR
    interface: Literal["rich", "plain"] = "rich"
    tool_disclosure: Literal["skill", "upfront"] = "skill"
    metadata: dict[str, str] = field(default_factory=dict)


def load_cases(path: Path | str = CASES_PATH, split: str | None = None) -> list[dict]:
    """사례 파일(JSON Lines)을 읽는다. split을 주면 그 분할(dev, holdout)만 돌려준다."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]
    return [case for case in cases if split is None or case["split"] == split]


def _dataset_fields(case: dict) -> dict:
    """데이터셋 항목의 내용. input에는 에이전트가 받을 turns만 넣고 기대값은 expected_output에 둔다."""
    return {
        "input": {"id": case["id"], "turns": case["turns"]},
        "expected_output": case["expect"],
        "metadata": {"split": case["split"], "stage": case["stage"], "kind": case["kind"]},
    }


def sync_dataset(client: Langfuse, cases: Sequence[dict], name: str = DATASET_NAME) -> list[str]:
    """Langfuse 데이터셋을 사례와 맞춘다. 항목 ID는 사례 ID다. 반환: 새로 쓰거나 고친 사례 ID.

    이미 같은 내용인 항목은 다시 쓰지 않는다. 그래서 두 번 불러도 두 번째에는 아무것도 쓰지 않는다.
    """
    try:
        existing = {item.id: item for item in client.get_dataset(name).items}
    except NotFoundError:
        client.create_dataset(
            name=name,
            description="Day04_new 능력 수준 평가 사례(dev 10, holdout 8). Day04_new/data/cases.jsonl에서 만든다.",
            metadata={"source": "Day04_new/data/cases.jsonl"},
        )
        existing = {}
    written = []
    for case in cases:
        fields = _dataset_fields(case)
        current = existing.get(case["id"])
        if current is not None and fields == {
            "input": current.input, "expected_output": current.expected_output, "metadata": current.metadata,
        }:
            continue
        client.create_dataset_item(dataset_name=name, id=case["id"], **fields)
        written.append(case["id"])
    return written


def _describe(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


async def run_case(
    case: dict,
    *,
    variant: Variant,
    settings: Settings,
    workdir: Path | str,
    repeat: int,
    callbacks: list[BaseCallbackHandler] | None = None,
    model: BaseChatModel | None = None,
    decider: DecisionBackend | None = None,
    server_env: dict[str, str] | None = None,
) -> RunRecord:
    """사례 하나를 새 DB와 새 근거 폴더(workdir/<변형>-r<반복>/<사례 ID>/)에서 실행하고 기록을 돌려준다.

    예외를 밖으로 내지 않는다. 실패는 RunRecord.error에 남기고 채점에서 확인 불가가 된다.
    case.requires가 있으면 그 사례를 같은 근거 폴더에서 먼저 실행한다. 선행 실행은 채점하지 않고
    호출 수·토큰·시간도 이 기록에 넣지 않는다. 선행 실행이 예외로 끝나면 본 사례는 실행하지 않는다.
    """
    run = f"{variant.name}-r{repeat}"
    run_dir = Path(workdir) / run / case["id"]
    record = RunRecord(case=case, evidence_dir=run_dir / "evidence")
    options = {
        "variant": variant, "settings": settings, "callbacks": callbacks,
        "model": model, "decider": decider, "server_env": server_env,
    }
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
        if case.get("requires"):
            # DB는 따로 쓴다. 본 사례가 DB가 아니라 근거 파일로 이전 세션을 이어 가는지를 본다.
            required = RunRecord(case=_case_by_id(case["requires"]), evidence_dir=record.evidence_dir)
            try:
                await _drive(
                    required, db=run_dir / "prerequisite.sqlite3", thread_id=f"{run}-{case['requires']}", **options
                )
            except Exception as error:
                raise RuntimeError(
                    f"선행 사례 {case['requires']} 실행 오류({_describe(error)}). 본 사례를 실행하지 않았습니다."
                ) from error
        await _drive(record, db=run_dir / "sessions.sqlite3", thread_id=f"{run}-{case['id']}", **options)
    except Exception as error:
        record.error = _describe(error)
    return record


def _case_by_id(case_id: str) -> dict:
    """선행 사례는 실행 목록이 아니라 사례 파일 전체에서 찾는다. dev-08만 골라 돌려도 dev-07을 찾는다."""
    for case in load_cases():
        if case["id"] == case_id:
            return case
    raise KeyError(f"선행 사례 {case_id}가 {CASES_PATH}에 없습니다.")


async def _drive(
    record: RunRecord,
    *,
    variant: Variant,
    settings: Settings,
    db: Path,
    thread_id: str,
    callbacks: list[BaseCallbackHandler] | None,
    model: BaseChatModel | None,
    decider: DecisionBackend | None,
    server_env: dict[str, str] | None,
) -> None:
    """에이전트를 만들고 사례의 turns를 한 스레드에서 차례로 보낸다. 기록은 record에 쌓는다."""
    fault = FaultPlan.model_validate(record.case["fault"]) if record.case.get("fault") else None
    earlier_events = set(record.evidence_dir.glob("*/event-*.json"))
    handle = await build_agent(
        settings,
        server_args=server_argv(
            db, record.evidence_dir,
            gate="h1" if variant.gate_h1 else "off", threshold=variant.threshold_h1, fault=fault,
            interface=variant.interface,
        ),
        skills_dir=variant.skills_dir,
        tool_disclosure=variant.tool_disclosure,
        gate_h2=variant.gate_h2,
        h2_threshold=variant.threshold_h2,
        decider=decider,
        model=model,
        checkpointer=InMemorySaver(),
        server_env=server_env,
    )
    config = {"configurable": {"thread_id": thread_id}, "callbacks": callbacks or []}
    started = time.perf_counter()
    try:
        for turn in record.case["turns"]:
            await _send_turn(handle.agent, record, turn, config)
    finally:
        record.latency_s = time.perf_counter() - started
        if handle.goal_guard is not None:
            record.gate_decisions += [{"gate": "h2", **asdict(d)} for d in handle.goal_guard.decisions]
        await handle.aclose()
    # 서버는 도구 결과를 돌려주기 전에 이벤트 파일을 쓴다. 실행이 끝난 뒤 한 번 읽으면 된다.
    record.gate_decisions += _h1_gate_records(record.evidence_dir, earlier_events)


async def _send_turn(agent: CompiledStateGraph, record: RunRecord, turn: str, config: dict) -> None:
    """사용자 발화 하나를 보내고, elicitation interrupt가 남지 않을 때까지 사례의 응답으로 재개한다."""
    pending = await _stream(agent, {"messages": [{"role": "user", "content": turn}]}, config, record)
    resumes = 0
    while pending:
        if resumes == MAX_RESUMES_PER_TURN:
            raise RuntimeError(f"한 턴에서 elicitation 재개가 {MAX_RESUMES_PER_TURN}번을 넘었습니다. 재개를 멈췄습니다.")
        resumes += 1
        pending = await _stream(agent, Command(resume=_answer_interrupts(pending, record)), config, record)


async def _stream(agent: CompiledStateGraph, request: dict | Command, config: dict, record: RunRecord) -> list[Interrupt]:
    """updates 스트림에서 모델 호출·도구 호출·결과를 기록한다. 반환: 답해야 할 interrupt."""
    pending: list[Interrupt] = []
    async for update in agent.astream(request, config, stream_mode="updates"):
        for node, output in update.items():
            if node == "__interrupt__":
                pending.extend(output)
            elif node == "model":
                record.model_calls += 1
                for message in output.get("messages", []):
                    _record_model_message(message, record)
            elif node == "tools":
                # 병렬 도구 호출도 호출마다 따로 dict 갱신으로 온다(작성 시 탐침으로 확인).
                for message in output.get("messages", []):
                    _record_tool_message(message, record)
    return pending


def _record_model_message(message: BaseMessage, record: RunRecord) -> None:
    if not isinstance(message, AIMessage):
        return
    usage = message.usage_metadata or {}
    record.input_tokens += usage.get("input_tokens", 0)
    record.output_tokens += usage.get("output_tokens", 0)
    record.tool_calls += [
        {"id": call["id"], "name": call["name"], "args": call["args"], "result": None, "ok": None}
        for call in message.tool_calls
    ]
    if not message.tool_calls:
        record.final_text = message.text


def _record_tool_message(message: BaseMessage, record: RunRecord) -> None:
    """도구 결과를 같은 tool_call_id의 호출에 붙인다. 성공한 SKILL.md 읽기는 skill_reads에도 남긴다.

    ok는 도구 오류(status=error)도 업무 오류(success=false)도 아닐 때만 참이다.
    """
    if not isinstance(message, ToolMessage):
        return
    call = [call for call in record.tool_calls if call["id"] == message.tool_call_id][-1]
    structured = message.artifact.get("structured_content") if isinstance(message.artifact, dict) else None
    call["result"] = structured if structured is not None else message.content
    business_failure = structured is not None and structured.get("success") is False
    call["ok"] = message.status != "error" and not business_failure
    path = str(call["args"].get("file_path", ""))
    if call["name"] == "read_file" and message.status != "error" and path.endswith("SKILL.md"):
        record.skill_reads.append(path)


def _answer_interrupts(pending: list[Interrupt], record: RunRecord) -> dict[str, dict]:
    """interrupt마다 요청 key별 응답을 만든다. interrupt ID로 묶어 병렬 도구 호출도 각자 답을 받게 한다."""
    elicitation = record.case.get("elicitation") or {}
    resume = {}
    for interrupt in pending:
        payload = interrupt.value
        if payload.get("type") != ELICITATION_INTERRUPT:
            raise RuntimeError(f"답할 수 없는 interrupt입니다: {payload.get('type')}")
        responses = {}
        for request in payload["requests"]:
            response = _elicitation_response(request, elicitation)
            responses[request["key"]] = response
            record.interrupts.append({"tool_name": payload["tool_name"], "message": request["message"], **response})
        resume[interrupt.id] = {"responses": responses}
    return resume


def _elicitation_response(request: dict, elicitation: dict) -> dict:
    """요청 형식의 필드를 사례의 elicitation이 모두 갖고 있으면 그 값으로 수락하고, 하나라도 없으면 거절한다."""
    fields = list((request.get("requested_schema") or {}).get("properties", {}))
    if fields and all(name in elicitation for name in fields):
        return {"action": "accept", "content": {name: elicitation[name] for name in fields}}
    return {"action": "decline"}


def _h1_gate_records(evidence_dir: Path, earlier_events: set[Path]) -> list[dict]:
    """이번 실행에서 새로 생긴 answer_recorded 이벤트의 gate 기록(H1 판정 점수·문턱값·출처)."""
    found = []
    for path in sorted(set(evidence_dir.glob("*/event-*.json")) - earlier_events):
        content = json.loads(path.read_text(encoding="utf-8"))["content"]
        payload = content["payload"]
        if content["event"] == "answer_recorded" and "gate" in payload:
            found.append({"gate": "h1", "session_id": path.parent.name, "field": payload["field"], **payload["gate"]})
    return found


def _mirror_line(record: RunRecord, scores: list[Score], *, run_name: str, variant: Variant, repeat: int) -> dict:
    case = record.case
    return {
        "run_name": run_name,
        "variant": variant.name,
        "repeat": repeat,
        "case_id": case["id"],
        "split": case["split"],
        "stage": case["stage"],
        "kind": case["kind"],
        "scores": [asdict(score) for score in scores],
        "first_failure": first_failure(scores),
        "error": record.error,
        "calls": record.tool_calls,
        "skill_reads": record.skill_reads,
        "gate_decisions": record.gate_decisions,
        "interrupts": record.interrupts,
        "final_text": record.final_text,
        "evidence_dir": str(record.evidence_dir),
    }


def _score(record: RunRecord) -> list[Score]:
    """채점이 실패해도 항목을 버리지 않는다(P4: 오류를 포함한 모든 항목). 그때는 점수 없이 오류를 남긴다."""
    try:
        return score_run(record)
    except Exception as error:
        record.error = "; ".join(filter(None, [record.error, f"채점 오류: {_describe(error)}"]))
        return []


def _append_line(path: Path, line: dict) -> None:
    with path.open("a", encoding="utf-8") as mirror:
        mirror.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")


def _item_evaluations(*, output: dict, **_: object) -> list[Evaluation]:
    """항목 점수. None(해당 없음·확인 불가)은 보내지 않는다. 참/거짓은 BOOLEAN 1/0으로 보낸다."""
    return [
        Evaluation(
            name=score["name"],
            value=float(score["value"]),
            comment=score["comment"],
            data_type="BOOLEAN" if score["name"] in BOOLEAN_SCORES else "NUMERIC",
        )
        for score in output["scores"]
        if score["value"] is not None
    ]


def _pass_rates(*, item_results: Sequence[ExperimentItemResult], **_: object) -> list[Evaluation]:
    """실행 단위 점수. 검사마다 통과율과 95% Wilson 구간. 확인한 항목이 없는 검사는 보내지 않는다."""
    evaluations = []
    for name in BOOLEAN_SCORES:
        values = [s["value"] for result in item_results for s in result.output["scores"] if s["name"] == name]
        checked = [value for value in values if value is not None]
        passed = sum(checked)
        interval = wilson_ci(passed, len(checked))
        if interval is None:
            continue
        lo, hi = interval
        evaluations.append(Evaluation(
            name=f"{name}_pass_rate",
            value=passed / len(checked),
            comment=f"{passed}/{len(checked)} 통과, 95% Wilson 구간 [{lo:.3f}, {hi:.3f}], 확인 불가 {len(values) - len(checked)}건",
            metadata={"passed": passed, "checked": len(checked), "unchecked": len(values) - len(checked),
                      "wilson_lo": lo, "wilson_hi": hi},
        ))
    return evaluations


def _sha256(paths: Iterable[Path | str]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def _jev_model(variant: Variant, decider: DecisionBackend | None, settings: Settings) -> str:
    """판정기 공급자와 모델 id. 게이트를 모두 끄면 off. H1은 서버 프로세스가 같은 .env로 만든 판정기를 쓴다."""
    if decider is None or not (variant.gate_h1 or variant.gate_h2):
        return "off"
    if decider.name == "azure":
        return f"azure:{settings.azure_deployment}"
    backend = BACKENDS.get(decider.name)
    return f"{decider.name}:{backend.model}" if backend else decider.name


def run_metadata(variant: Variant, settings: Settings, model: BaseChatModel | None, decider: DecisionBackend | None) -> dict[str, str]:
    """실행 metadata(P4). 변형의 metadata가 고정 항목을 덮어쓰지 못하게 고정 항목을 뒤에 둔다."""
    return {
        **{key: str(value) for key, value in variant.metadata.items()},
        "variant": variant.name,
        "model": settings.model if model is None else f"injected:{type(model).__name__}",
        "effort": settings.effort,
        "skill_sha256": _sha256([variant.skills_dir / SKILL_FILE]),
        "server_sha256": _sha256([SERVER_SCRIPT, *SERVER_MODULES]),
        "interface": variant.interface,
        "tool_disclosure": variant.tool_disclosure,
        "gate_h1": "on" if variant.gate_h1 else "off",
        "gate_h2": "on" if variant.gate_h2 else "off",
        "threshold_h1": str(variant.threshold_h1),
        "threshold_h2": str(variant.threshold_h2),
        "jev_model": _jev_model(variant, decider, settings),
        "dataset": DATASET_NAME,
    }


def cost_notice(variant: Variant, cases: Sequence[dict], repeats: int, record: Literal["langfuse", "local"] = "langfuse") -> str:
    """실행 직전 한 줄 비용 고지(AGENTS.md 6절). 선행 사례 실행도 Claude와 Jev를 부르므로 따로 센다. record는 기록 위치 문구만 바꾼다."""
    runs = len(cases) * repeats
    prerequisites = sum(1 for case in cases if case.get("requires")) * repeats
    agent_runs = runs + prerequisites
    low, high = (calls * agent_runs for calls in CLAUDE_CALLS_PER_RUN)
    jev = JEV_CALLS_PER_GATE_RUN * (variant.gate_h1 + variant.gate_h2) * agent_runs
    extra = f"(선행 사례 실행 {prerequisites}회 별도)" if prerequisites else ""
    return (f"이 실행은 사례 {len(cases)} x 반복 {repeats} = {runs}회{extra}, Claude 호출 약 {low}~{high}회(추정), "
            f"Jev 호출 최대 {jev}회(추정), {'Langfuse에' if record == 'langfuse' else '로컬 사본에만'} 기록합니다.")


def _connect_langfuse(settings: Settings) -> Langfuse:
    """키는 settings(Day04_new/.env)에서만 가져온다. 셸 환경 변수의 다른 프로젝트 키를 쓰지 않는다."""
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_host or None,
        environment=settings.langfuse_environment,
    )


def _check_langfuse_auth(client: Langfuse) -> None:
    """유료 실행 전에 Langfuse 인증을 확인한다(P4). 실패하면 아무것도 실행하지 않는다."""
    try:
        authed = client.auth_check()
    except Exception as error:
        raise RuntimeError(
            f"Langfuse 인증 확인에 실패했습니다({type(error).__name__}). Day04_new/.env의 LANGFUSE 키와 "
            "LANGFUSE_HOST를 직접 확인하세요. 아무것도 실행하지 않았습니다."
        ) from error
    if not authed:
        raise RuntimeError("Langfuse 인증 확인이 통과하지 않았습니다. 아무것도 실행하지 않았습니다.")


def _dataset_items(client: Langfuse, cases: Sequence[dict]) -> list[DatasetItem]:
    """실행할 사례의 데이터셋 항목을 사례 순서대로. 데이터셋 항목으로 실행해야 Langfuse가 실행을 데이터셋에 묶는다."""
    items = {item.id: item for item in client.get_dataset(DATASET_NAME).items}
    missing = [case["id"] for case in cases if case["id"] not in items]
    if missing:
        raise RuntimeError(f"Langfuse 데이터셋 {DATASET_NAME}에 사례 {missing}가 없습니다.")
    return [items[case["id"]] for case in cases]


async def run_experiment(
    variant: Variant,
    cases: Sequence[dict],
    repeats: int,
    *,
    settings: Settings,
    mirror_dir: Path | str = MIRROR_DIR,
    client: Langfuse | None = None,
    model: BaseChatModel | None = None,
    decider: DecisionBackend | None = None,
    server_env: dict[str, str] | None = None,
    record: Literal["langfuse", "local"] = "langfuse",
) -> list[str]:
    """변형 하나를 사례 x 반복으로 실행해 실행 이름(<변형>-r<k>)마다 기록을 남긴다. 반환: 실행 이름.

    record="langfuse"(기본, 07 노트북): Langfuse 데이터셋 실행과 점수로 남긴다. client가 없으면 Day04_new/.env의
    LANGFUSE 키로 만들고 LangChain 호출도 Langfuse에 추적한다. 키가 비어 있거나 인증이 실패하면 로컬에만 남기지 않고 멈춘다.
    record="local"(저자 측정, 사전 등록 개정 2): Langfuse를 만들지도 부르지도 않는다(client도 쓰지 않는다).
    반복 x 사례를 사례 순서대로 하나씩 실행하고, 실행 이름마다 mirror_dir/<실행 이름>.meta.json에 실행 metadata,
    repeat, record, 시작·끝 시각(UTC), 사례 ID를 남긴다. 키 값은 담지 않는다. 한 실행 이름의 처음 세 항목이 모두
    오류로 끝나면 세 줄을 남긴 채 RuntimeError로 멈춘다(_run_local). 그밖의 record 값은 아무것도 하기 전에 ValueError다.
    두 방식 모두 항목마다 mirror_dir/<실행 이름>.jsonl에 같은 키의 한 줄을 남기고, 같은 실행 이름의 기록이 있으면
    아무 호출도 하기 전에 멈춘다. 작업 폴더(DB와 근거 파일)는 mirror_dir의 부모 아래 work/<실행 이름>/이다.
    model을 주지 않으면 실행마다 make_model로 새로 만든다(ChatAnthropic의 비동기 클라이언트는 이벤트 루프에 묶인다).
    """
    if record not in ("langfuse", "local"):
        raise ValueError(f"record는 'langfuse' 또는 'local'이어야 합니다(받은 값: {record!r}). 아무것도 실행하지 않았습니다.")
    print(cost_notice(variant, cases, repeats, record))
    needed = (["ANTHROPIC_API_KEY"] if model is None else []) + (
        ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"] if client is None and record == "langfuse" else [])
    require(settings, *needed)
    mirror_dir = Path(mirror_dir)
    workdir = mirror_dir.parent / "work"
    run_names = [f"{variant.name}-r{k}" for k in range(1, repeats + 1)]
    taken = [name for name in run_names if (mirror_dir / f"{name}.jsonl").exists() or (workdir / name).exists()]
    if taken:
        raise RuntimeError(
            f"실행 기록 {taken}이(가) 이미 있습니다. 같은 이름에 이어 쓰면 서로 다른 실행이 섞이므로 시작하지 않았습니다. "
            "변형 이름을 바꾸거나 기존 기록을 다른 곳으로 옮기세요."
        )
    if decider is None and (variant.gate_h1 or variant.gate_h2):
        decider = make_decider(settings)
    if record == "local":
        return await _run_local(variant, cases, run_names, settings=settings, mirror_dir=mirror_dir, workdir=workdir,
                                model=model, decider=decider, server_env=server_env)
    trace_langchain = client is None
    client = client or _connect_langfuse(settings)
    _check_langfuse_auth(client)
    sync_dataset(client, cases)
    items = _dataset_items(client, cases)
    metadata = run_metadata(variant, settings, model, decider)
    by_id = {case["id"]: case for case in cases}
    mirror_dir.mkdir(parents=True, exist_ok=True)

    for repeat, run_name in enumerate(run_names, start=1):

        async def task(*, item: DatasetItem, **_: object) -> dict:
            # 이 함수는 아래 run_experiment 호출이 끝나기 전에만 불리므로 repeat·run_name은 이번 반복의 값이다.
            callbacks = [CallbackHandler(public_key=settings.langfuse_public_key)] if trace_langchain else None
            run_record = await with_own_anthropic_client(run_case(
                by_id[item.input["id"]], variant=variant, settings=settings, workdir=workdir, repeat=repeat,
                callbacks=callbacks, model=model, decider=decider, server_env=server_env,
            ))
            line = _mirror_line(run_record, _score(run_record), run_name=run_name, variant=variant, repeat=repeat)
            _append_line(mirror_dir / f"{run_name}.jsonl", line)
            return {key: line[key] for key in ("final_text", "scores", "first_failure", "error")}

        # Langfuse의 run_experiment는 동기 함수이고 안에서 새 이벤트 루프를 돈다. 이 루프를 막지 않게 스레드에서 부른다.
        await asyncio.to_thread(
            client.run_experiment,
            name=f"{DATASET_NAME}:{variant.name}",
            run_name=run_name,
            description=(f"H1 {metadata['gate_h1']}(문턱값 {variant.threshold_h1}), "
                         f"H2 {metadata['gate_h2']}(문턱값 {variant.threshold_h2})"),
            data=items,
            task=task,
            evaluators=[_item_evaluations],
            run_evaluators=[_pass_rates],
            max_concurrency=MAX_CONCURRENCY,
            metadata={**metadata, "repeat": str(repeat)},
        )
    return run_names


async def with_own_anthropic_client[T](coroutine: Coroutine[None, None, T]) -> T:
    """이 이벤트 루프가 Anthropic 비동기 HTTP 클라이언트를 새로 만들어 쓰고, 루프가 끝나기 전에 같은 루프에서 닫는다.

    langchain_anthropic은 클라이언트 하나를 lru_cache로 공유한다. 닫힌 루프에 묶인 클라이언트를 다음 루프가 받으면
    "Connection error."가 나고, 버려진 클라이언트의 __del__은 그때 도는 루프에 aclose()를 예약해
    "Event loop is closed" 경고를 낸다. 실행 전에 캐시를 비우고, 실행 중 새로 생긴 클라이언트만 실행 뒤에 닫는다.
    다른 곳에서 열어 둔 클라이언트는 건드리지 않는다.
    """
    _get_default_async_httpx_client.cache_clear()
    before = {id(obj) for obj in gc.get_objects() if isinstance(obj, _AsyncHttpxClientWrapper)}
    try:
        return await coroutine
    finally:
        for obj in gc.get_objects():
            if isinstance(obj, _AsyncHttpxClientWrapper) and id(obj) not in before and not obj.is_closed:
                await obj.aclose()
        _get_default_async_httpx_client.cache_clear()


# local 기록의 중단 장치. 한 실행 이름의 처음 이만큼의 항목이 모두 오류로 끝나면 멈춘다. 키·한도·설정 문제로
# 모든 항목이 실패하는 실행을 사례 x 반복만큼 되풀이해 과금하지 않기 위해서다. 오류 줄은 지우지 않는다(P4).
ABORT_AFTER_ERRORS = 3


async def _run_local(
    variant: Variant,
    cases: Sequence[dict],
    run_names: list[str],
    *,
    settings: Settings,
    mirror_dir: Path,
    workdir: Path,
    model: BaseChatModel | None,
    decider: DecisionBackend | None,
    server_env: dict[str, str] | None,
) -> list[str]:
    """record="local"의 실행 본체. Langfuse 없이 반복 x 사례를 사례 순서대로 하나씩 실행한다(MAX_CONCURRENCY와 같은 1개씩).

    항목마다 langfuse 기록의 task와 같은 run_case -> _score -> _mirror_line -> _append_line 경로를 거친다.
    <실행 이름>.meta.json은 그 실행 이름을 시작할 때 finished_at을 null로 써 두고, 모든 사례가 끝나면 끝난 시각을 채워
    다시 쓴다. 중간에 멈춘 실행(중단 장치, 프로세스 종료)은 finished_at이 null로 남는다.
    """
    metadata = run_metadata(variant, settings, model, decider)
    case_ids = [case["id"] for case in cases]
    mirror_dir.mkdir(parents=True, exist_ok=True)
    for repeat, run_name in enumerate(run_names, start=1):
        meta_path = mirror_dir / f"{run_name}.meta.json"
        meta = {**metadata, "repeat": repeat, "record": "local", "started_at": _utc_now(), "finished_at": None,
                "case_ids": case_ids}
        _write_json(meta_path, meta)
        errors = []
        for case in cases:
            record = await run_case(case, variant=variant, settings=settings, workdir=workdir, repeat=repeat,
                                    model=model, decider=decider, server_env=server_env)
            line = _mirror_line(record, _score(record), run_name=run_name, variant=variant, repeat=repeat)
            _append_line(mirror_dir / f"{run_name}.jsonl", line)
            errors.append(line["error"])
            if len(errors) == ABORT_AFTER_ERRORS and all(errors):
                listed = "\n".join(f"  {n}. {error}" for n, error in enumerate(errors, start=1))
                raise RuntimeError(
                    f"{run_name}의 처음 {ABORT_AFTER_ERRORS}개 항목이 모두 오류로 끝나 실행을 멈췄습니다. "
                    f"오류 줄은 {mirror_dir / f'{run_name}.jsonl'}에 그대로 남겼습니다.\n{listed}"
                )
        _write_json(meta_path, {**meta, "finished_at": _utc_now()})
    return run_names


def _utc_now() -> str:
    """ISO 8601 UTC 시각(초 단위). 예: 2026-11-02T09:30:00Z."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path: Path, content: dict) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_mirrors(paths: Iterable[Path | str]) -> list[dict]:
    lines = []
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        lines += [json.loads(line) for line in text.splitlines() if line.strip()]
    return lines


def case_values(
    paths: Iterable[Path | str], metrics: Sequence[str], split: str | None
) -> tuple[dict[str, dict[str, list[float]]], dict[str, int]]:
    """지표별 {사례 ID: 반복 값}과 지표별 확인 불가 수. 반복은 사례마다 모은다(여러 사본 파일도 합친다).

    None(해당 없음·확인 불가)은 값에서 빼고 확인 불가로 센다. 오류가 난 줄은 숫자 지표도 빼고 모두 확인 불가로 센다.
    중간에 멈춘 실행의 호출 수·시간이 작게 잡혀 개선처럼 보이지 않게 하기 위해서다.
    """
    values: dict[str, dict[str, list[float]]] = {metric: defaultdict(list) for metric in metrics}
    unchecked: Counter[str] = Counter()
    for line in _read_mirrors(paths):
        if split is not None and line["split"] != split:
            continue
        scores = {score["name"]: score["value"] for score in line["scores"]}
        for metric in metrics:
            value = None if line["error"] else scores.get(metric)
            if value is None:
                unchecked[metric] += 1
            else:
                values[metric][line["case_id"]].append(float(value))
    return values, {metric: unchecked[metric] for metric in metrics}


def compare(
    mirror_a: Iterable[Path | str],
    mirror_a2: Iterable[Path | str],
    mirror_b: Iterable[Path | str],
    *,
    target: str,
    guards: Sequence[str],
    lower_is_better: Sequence[str] = LOWER_IS_BETTER,
    split: str | None = None,
) -> dict:
    """A 대 B를 사례 단위 쌍체 부트스트랩으로 비교하고 사전 등록 규칙(stats.decide)으로 판정한다.

    잡음 폭은 A 대 A2 비교에서 구한다. 인자는 변형별 로컬 사본 파일 목록이다(반복 r1, r2, ...).
    가드 지표는 받은 그대로 decide에 넘긴다. 비교 결과나 잡음 폭이 없는 가드가 있으면 decide가
    '판정 불가: 데이터 부족'을 낸다(P5 4번). 어떤 가드가 그랬는지는 guards_without_data에 적는다.
    """
    metrics = [target, *guards]
    a, unchecked_a = case_values(mirror_a, metrics, split)
    a2, unchecked_a2 = case_values(mirror_a2, metrics, split)
    b, unchecked_b = case_values(mirror_b, metrics, split)
    comparisons = {metric: paired_bootstrap_diff(a[metric], b[metric]) for metric in metrics}
    noise = {metric: noise_band(a[metric], a2[metric]) for metric in metrics}
    verdict = decide(
        comparisons[target],
        {guard: comparisons[guard] for guard in guards},
        {guard: noise[guard] for guard in guards},
        lower_is_better=frozenset(lower_is_better),
    )
    return {
        "target": target,
        "split": split,
        "verdict": verdict["verdict"],
        "reasons": verdict["reasons"],
        "comparisons": comparisons,
        "noise": noise,
        "guards_without_data": [g for g in guards if comparisons[g] is None or noise[g] is None],
        "unchecked": {"A": unchecked_a, "A2": unchecked_a2, "B": unchecked_b},
    }


def prereg_guards(target: str) -> list[str]:
    """사전 등록 P6의 가드 지표: 목표가 아닌 모든 참/거짓 검사와 model_calls, tool_calls, latency_s."""
    return [name for name in BOOLEAN_SCORES if name != target] + list(LOWER_IS_BETTER)


def attribute(mirror_paths: Iterable[Path | str]) -> dict[str, int]:
    """첫 실패 단계별 실행 수(P3 병목 귀속). 오류로 확인하지 못한 실행은 unchecked, 실패가 없으면 no_failure."""
    counts = dict.fromkeys(STAGE_ORDER, 0) | {"unchecked": 0, "no_failure": 0}
    for line in _read_mirrors(mirror_paths):
        if line["first_failure"]:
            counts[line["first_failure"]] += 1
        elif line["error"]:
            counts["unchecked"] += 1
        else:
            counts["no_failure"] += 1
    return counts
