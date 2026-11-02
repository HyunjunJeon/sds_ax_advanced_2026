"""Day04/build_mcp/reference/server.py에서 가져온 사본. 수정: import 경로, from __future__ import annotations 제거, 도구 주석(ToolAnnotations), 장애 주입(--fault), H1 완료 기준 판정 게이트(--gate h1), 수업 비교용 약한 도구 인터페이스(--interface plain), Streamable HTTP 실행(--transport streamable-http).

강사용 기준 MCP 서버. 도구 공개와 업무 처리를 연결한다.
--gate off(기본)는 기준 서버와 같은 7개 도구를 같은 이름·인자·반환 형식으로 공개하고 판정기를 만들지 않는다.
--gate h1은 record_answer의 완료 기준을 판정기로 검사한다. 점수가 문턱값보다 낮으면 MRTR로 사용자에게
직접 묻고, 판정할 수 없으면 아무것도 기록하지 않는다(fail-closed).
--interface plain은 같은 7개 도구와 같은 업무·오류 코드를 약한 인터페이스로 공개한다(Part 2 비교의 한쪽):
enum 없는 str 인자, 짧은 설명, annotations·outputSchema 없음. rich(기본)는 지금의 도구 정의 그대로다.
--transport streamable-http는 stdio 대신 http://127.0.0.1:<--port>/mcp 에서 서버를 연다(Part 4).
판정기 키는 cap_lab.settings.load_settings가 읽는 Day04_new/.env(또는 DAY04_ENV_FILE이 가리키는 파일)에서 온다.
가짜 판정기(DAY04_ALLOW_FAKE_DECIDER, DAY04_FAKE_DECIDER)는 cap_lab/server/gate.py에 설명했다.
"""

# from __future__ import annotations를 쓰지 않는다. 주석이 문자열로 미뤄지면 SDK가 create_server 안의
# Resolve(assess)를 풀지 못해 resolver 인자를 찾지 못하고, assessment·revision이 모델이 보는 도구 인자가 된다.
import argparse
import functools
import json
import math
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

# 스크립트로 실행하면 sys.path[0]이 이 폴더다. cap_lab 패키지를 찾도록 Day04_new를 앞에 넣는다.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pydantic_core
from mcp.server import MCPServer
from mcp.server.elicitation import AcceptedElicitation, ElicitationResult
from mcp.server.mcpserver.resolve import Elicit, Resolve
from mcp_types import CallToolResult, TextContent, ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, ValidationError

from cap_lab.decisions import make_decider
from cap_lab.server.evidence import EvidenceError, EvidenceStore
from cap_lab.server.gate import (
    GateDecision,
    GateUnavailable,
    TestabilityGate,
    fake_decider_from_env,
)
from cap_lab.server.workflow import Workflow, WorkflowError
from cap_lab.settings import load_settings

# ToolAnnotations는 클라이언트에게 주는 힌트다. 명세 기본값이 destructiveHint=true, openWorldHint=true라서
# 이 서버에 맞는 값을 도구마다 모두 적는다. 호출 기록(call-*.json)은 미들웨어가 모든 도구에 남기는
# 감사 기록이므로 도구의 효과로 세지 않는다.
# 근거 폴더만 읽는 도구. 로컬 DB와 파일만 다루므로 닫힌 세계다.
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

ToolName = Literal[
    "start_interview", "record_answer", "get_session", "freeze_seed",
    "list_evidence", "read_evidence", "save_evidence",
]
AnswerField = Literal["constraints", "acceptance_criteria"]
FAULT_EXAMPLE = '{"permission_denied": ["save_evidence"], "transient": {"record_answer": 1}}'
# --transport streamable-http가 여는 주소. 인증이 없는 서버라 같은 컴퓨터의 클라이언트만 접속하게 한다.
LOOPBACK = "127.0.0.1"


class FaultPlan(BaseModel):
    """--fault JSON. 도구 이름 오타나 모르는 키는 서버를 시작할 때 거절한다."""

    model_config = ConfigDict(extra="forbid")
    # 이 도구의 모든 호출을 거절한다.
    permission_denied: list[ToolName] = []
    # 이 도구의 처음 n번 호출을 일시 장애로 돌려준다. 그 뒤에는 정상 동작한다.
    transient: dict[ToolName, NonNegativeInt] = {}


def business_failure(result: dict) -> dict:
    """도구가 업무 오류를 반환했을 때와 같은 tools/call 결과 모양으로 만든다."""
    text = json.dumps(result, ensure_ascii=False, indent=2)
    return CallToolResult(
        content=[TextContent(type="text", text=text)], structured_content=result
    ).model_dump(mode="json", by_alias=True, exclude_none=True)


def fault_middleware(plan: FaultPlan):
    """도구에 닿기 전에 장애 결과를 돌려준다. 업무 코드와 판정기가 실행되지 않으므로 부작용이 없다."""
    remaining = dict(plan.transient)

    async def inject_faults(ctx, call_next):
        if ctx.method != "tools/call":
            return await call_next(ctx)
        name = (ctx.params or {}).get("name")
        if name in plan.permission_denied:
            return business_failure(
                WorkflowError("permission_denied", "이 도구를 사용할 권한이 없습니다.").result
            )
        if remaining.get(name, 0) > 0:
            remaining[name] -= 1
            return business_failure(
                WorkflowError(
                    "temporarily_unavailable",
                    "일시적으로 처리할 수 없습니다. 잠시 뒤 같은 요청을 다시 보내세요.",
                    retryable=True,
                ).result
            )
        return await call_next(ctx)

    return inject_faults


class RevisedCriteria(BaseModel):
    """사용자에게 직접 받는 완료 기준. Resolve로 채우므로 모델이 보는 도구 인자가 아니다."""

    acceptance_criteria: str = Field(
        title="완료 기준", description="실행 결과로 참/거짓을 확인할 수 있는 완료 기준"
    )


def without_output_schema(tool: Callable[..., dict[str, Any]]) -> Callable[..., CallToolResult]:
    """plain 인터페이스의 도구 사본. outputSchema는 공개하지 않고 결과 모양은 rich와 같게 돌려준다.

    본문 텍스트는 rich에서 SDK가 dict 결과로 만드는 텍스트와 같은 방식으로 만든다
    (mcp/server/mcpserver/utilities/func_metadata.py:653). structuredContent도 그대로 둔다.
    실행기는 structuredContent의 success:false로 업무 오류를 가리므로(cap_lab/experiment.py의
    _record_tool_message) 결과 모양이 같아야 두 인터페이스를 같은 잣대로 채점한다.
    """

    @functools.wraps(tool)
    def unadvertised(**arguments: Any) -> CallToolResult:
        result = tool(**arguments)
        text = pydantic_core.to_json(result, fallback=str, indent=2).decode()
        return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=result)

    return unadvertised


@dataclass(frozen=True)
class Assessment:
    """record_answer 한 번에 대한 게이트 판단. 판정하지 않은 호출이면 decision이 None이다."""

    decision: GateDecision | None = None
    # 판정기를 만들 수 없거나 판정이 실패한 이유. 비어 있지 않으면 아무것도 기록하지 않는다.
    failure: str = ""


def create_server(
    db_path: Path,
    evidence_dir: Path | None = None,
    *,
    gate: Literal["off", "h1"] = "off",
    threshold: float = 0.5,
    faults: FaultPlan | None = None,
    interface: Literal["rich", "plain"] = "rich",
) -> MCPServer:
    evidence = EvidenceStore(evidence_dir or db_path.parent / "evidence")
    workflow = Workflow(db_path, evidence)

    async def record_tools(ctx, call_next):
        if ctx.method != "tools/call":
            return await call_next(ctx)
        # 입력 검증 전부터 감싸므로 형식을 어긴 호출도 기록한다.
        params = dict(ctx.params or {})
        # 메타데이터·환경변수·통신 헤더는 기록하지 않는다.
        request = {key: params[key] for key in ("name", "arguments") if key in params}
        try:
            result = await call_next(ctx)
        except Exception as error:
            evidence.record_call(request, {"isError": True, "error": str(error)})
            raise
        serialized = (
            result.model_dump(mode="json", by_alias=True)
            if isinstance(result, BaseModel)
            else result
        )
        evidence.record_call(request, serialized)
        # 응답을 반환하기 전에 저장을 끝낸다. 저장 실패를 성공으로 반환하지 않는다.
        return result

    # 바깥부터 차례로 감싼다. 장애 결과도 record_tools가 근거 파일로 기록한다.
    mcp = MCPServer(
        name="requirements-lab",
        middleware=[record_tools, fault_middleware(faults or FaultPlan())],
    )

    def publish(
        annotations: ToolAnnotations, plain_description: str
    ) -> Callable[[Callable[..., dict[str, Any]]], Callable[..., dict[str, Any]]]:
        """도구를 등록한다. rich는 docstring 설명과 annotations를 공개하고 SDK가 반환 형식에서 outputSchema를 만든다.
        plain은 plain_description만 공개한다. 등록한 원래 함수를 그대로 돌려준다.
        """

        def register(tool: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
            if interface == "rich":
                mcp.add_tool(tool, annotations=annotations)
            else:
                mcp.add_tool(without_output_schema(tool), description=plain_description, structured_output=False)
            return tool

        return register

    # plain은 record_answer의 field를 enum 없는 str로 받는다. 맨 위 주석대로 이 파일은 주석을 정의할 때
    # 평가하므로, 여기서 고른 타입이 그대로 도구의 입력 형식이 된다. 모르는 값은 업무 코드가 unknown_field로 거절한다.
    answer_field = AnswerField if interface == "rich" else str

    def invoke(action: Callable[[], dict]) -> dict[str, Any]:
        try:
            return action()
        except (WorkflowError, EvidenceError) as error:
            return error.result
        # DB 오류 등 예상하지 못한 실패는 SDK의 도구 오류로 전달한다.
        # 업무 오류와 실행 실패를 모두 success=true로 바꾸지 않는다.

    testability_gate: TestabilityGate | None = None

    def open_gate() -> TestabilityGate:
        """첫 판정 때 판정기를 만든다. 게이트를 끈 서버는 이 함수를 부르지 않는다."""
        nonlocal testability_gate
        if testability_gate is None:
            try:
                decider = fake_decider_from_env(os.environ) or make_decider(load_settings())
            except (RuntimeError, ValueError) as error:
                # 두 함수가 직접 쓴 메시지다. 키 이름만 담고 키 값은 담지 않는다.
                raise GateUnavailable(f"판정기를 만들 수 없습니다({error}).") from error
            testability_gate = TestabilityGate(decider, threshold)
        return testability_gate

    def assess(field: str, answer: str) -> Assessment:
        """도구 인자 field·answer를 이름으로 받아 완료 기준만 판정한다."""
        # 빈 답변은 판정하지 않는다. 업무 코드가 empty_answer로 거절하고 아무것도 기록하지 않는다.
        if field != "acceptance_criteria" or not answer.strip():
            return Assessment()
        try:
            return Assessment(open_gate().check(answer.strip()))
        except GateUnavailable as error:
            # resolver가 예외를 내면 SDK가 일반 도구 오류로 바꾼다. 값으로 넘겨 본문이 업무 오류로 답한다.
            return Assessment(failure=str(error))

    def ask_if_untestable(
        assessment: Annotated[Assessment, Resolve(assess)], answer: str
    ) -> RevisedCriteria | Elicit[RevisedCriteria]:
        """점수가 문턱값보다 낮을 때만 사용자에게 직접 묻는다. 그 밖에는 원래 답을 그대로 넘긴다."""
        decision = assessment.decision
        if decision is None or decision.passed:
            return RevisedCriteria(acceptance_criteria=answer)
        return Elicit(
            f'완료 기준 "{answer.strip()}"은(는) 실행 결과로 참/거짓을 판정하기 어렵습니다. '
            "테스트나 명령의 실행 결과로 확인할 수 있는 완료 기준을 직접 적어 주세요.",
            RevisedCriteria,
        )

    # 기록을 추가만 하고 지우지 않는다(destructive=false). 호출마다 새 세션 ID를 만들므로
    # 응답을 놓쳤다고 다시 부르면 업무가 중복된다(idempotent=false).
    @publish(ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False),
        "인터뷰를 시작한다.")
    def start_interview(goal: str) -> dict[str, Any]:
        """새 업무의 목표를 저장하고 세션 ID와 첫 질문을 반환한다."""
        return invoke(lambda: workflow.start_interview(goal))

    # 두 정의 모두 함수 이름이 record_answer다. 입력 형식의 title도 함수 이름에서 오므로
    # 게이트를 켜도 모델이 보는 이름·인자·설명·입력 형식이 같다. Resolve 인자는 입력 형식에 나오지 않는다.
    if gate == "h1":

        def record_answer(
            session_id: str,
            field: answer_field,
            answer: str,
            assessment: Annotated[Assessment, Resolve(assess)],
            revision: Annotated[ElicitationResult[RevisedCriteria], Resolve(ask_if_untestable)],
        ) -> dict[str, Any]:
            """세션의 제약 또는 완료 기준을 기록한다. 확정 뒤에는 수정할 수 없다."""
            if assessment.failure:
                return WorkflowError(
                    "decision_unavailable",
                    f"{assessment.failure} 아무것도 기록하지 않았습니다. 판정기 설정을 확인한 뒤 다시 호출하세요.",
                    state_saved=False,
                ).result
            decision = assessment.decision
            if decision is None:
                return invoke(lambda: workflow.record_answer(session_id, field, answer))
            if not isinstance(revision, AcceptedElicitation):
                return WorkflowError(
                    "criteria_not_testable",
                    "사용자가 실행 결과로 확인할 수 있는 완료 기준을 주지 않았습니다. 아무것도 기록하지 않았습니다.",
                ).result
            record = {"score": decision.score, "threshold": decision.threshold, "source": "agent"}
            if not decision.passed:
                record |= {"source": "elicited", "original": answer.strip()}
            return invoke(
                lambda: workflow.record_answer(
                    session_id, field, revision.data.acceptance_criteria, gate=record
                )
            )

    else:

        def record_answer(
            session_id: str,
            field: answer_field,
            answer: str,
        ) -> dict[str, Any]:
            """세션의 제약 또는 완료 기준을 기록한다. 확정 뒤에는 수정할 수 없다."""
            return invoke(lambda: workflow.record_answer(session_id, field, answer))

    # 답변 수정도 새 변경 기록을 추가할 뿐 이전 기록을 지우지 않는다(destructive=false).
    # 같은 답변의 재전송은 변경 기록을 늘리지 않는다(idempotent=true).
    # 게이트를 켜면 완료 기준을 외부 Decision API로 판정하므로 열린 세계다(openWorld=gate on).
    publish(
        ToolAnnotations(
            read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=gate == "h1"
        ),
        "답변을 기록한다.",
    )(record_answer)

    # 조회처럼 보이지만 읽기 전용이 아니다: 파일에만 있는 기록을 DB로 복원하고 근거 파일을 다시 내보낸다.
    # 빠진 기록만 추가하고 내용이 다른 기존 파일은 덮어쓰지 않는다(destructive=false).
    # 다시 불러도 같은 상태와 같은 파일이 된다(idempotent=true).
    @publish(ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False),
        "세션을 조회한다.")
    def get_session(session_id: str) -> dict[str, Any]:
        """세션을 조회하고 근거 파일을 복구한다. DB가 없으면 근거에서 복원한다."""
        return invoke(lambda: workflow.get_session(session_id))

    # 확정 기록을 추가만 한다. 이미 확정한 세션을 다시 확정하면 같은 명세를 반환한다(idempotent=true).
    @publish(ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False),
        "명세를 확정한다.")
    def freeze_seed(session_id: str) -> dict[str, Any]:
        """제약과 완료 기준이 기록된 명세를 확정한다. 업무 구현을 실행하지 않는다."""
        return invoke(lambda: workflow.freeze_seed(session_id))

    @publish(READ_ONLY, "근거 목록을 조회한다.")
    def list_evidence(session_id: str = "") -> dict[str, Any]:
        """근거 파일의 ID·제목·경로를 조회한다. 세션 ID 생략 시 세션 목록을 반환한다."""
        return invoke(lambda: evidence.list(session_id))

    @publish(READ_ONLY, "근거를 읽는다.")
    def read_evidence(session_id: str, evidence_id: str) -> dict[str, Any]:
        """근거 파일의 본문을 읽는다. 이후 작업은 이 내용과 근거 ID를 사용한다."""
        return invoke(lambda: evidence.read(session_id, evidence_id))

    # 같은 제목·본문·원본 ID는 같은 산출물 ID라 다시 보내도 파일이 늘지 않는다(idempotent=true).
    # 내용이 바뀌면 별도 파일로 남기고 기존 파일을 덮어쓰지 않는다(destructive=false).
    @publish(ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False),
        "근거를 저장한다.")
    def save_evidence(
        session_id: str, title: str, content: str, source_evidence_id: str = ""
    ) -> dict[str, Any]:
        """작성한 보고서·계획·메모의 전체 본문을 파일로 저장한다. 원본 근거 ID도 연결할 수 있다."""
        return invoke(
            lambda: evidence.save(session_id, title, content, source_evidence_id)
        )

    return mcp


def finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError("유한한 숫자여야 합니다.")
    return value


def port_number(text: str) -> int:
    value = int(text)
    if not 1 <= value <= 65535:
        raise argparse.ArgumentTypeError("1~65535 사이의 정수여야 합니다.")
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path.cwd() / "evidence",
        help="독립적으로 보관하고 다음 작업에 전달할 근거 폴더 (기본: 현재 폴더/evidence)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).resolve().parent / "work" / "sessions.sqlite3",
        help="세션 기록을 저장할 SQLite 파일",
    )
    parser.add_argument(
        "--gate",
        choices=("off", "h1"),
        default="off",
        help="off: 기준 서버와 같다. h1: record_answer의 완료 기준을 판정기로 검사한다",
    )
    parser.add_argument(
        "--gate-threshold",
        type=finite_float,
        default=0.5,
        help="미조정 자리값(기본 0.5). testability 점수가 이 값 이상이면 그대로 기록하고 미만이면 사용자에게 묻는다",
    )
    parser.add_argument(
        "--fault",
        default="",
        help=f"실험용 장애 주입 JSON. 예: {FAULT_EXAMPLE}",
    )
    parser.add_argument(
        "--interface",
        choices=("rich", "plain"),
        default="rich",
        help="rich(기본): 지금의 도구 정의. plain: 같은 도구·업무를 enum·설명·annotations·outputSchema 없이 공개한다(Part 2 비교)",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help=f"stdio(기본): 표준 입출력으로 통신한다. streamable-http: http://{LOOPBACK}:<--port>/mcp 에서 연다(Part 4)",
    )
    parser.add_argument(
        "--port",
        type=port_number,
        default=8765,
        help=f"--transport streamable-http가 {LOOPBACK}에서 열 포트 (기본 8765). stdio에서는 쓰지 않는다",
    )
    args = parser.parse_args()
    try:
        faults = FaultPlan.model_validate_json(args.fault or "{}")
    except ValidationError as error:
        first = error.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        parser.error(f"--fault 형식이 잘못되었습니다({where}: {first['msg']}). 예: {FAULT_EXAMPLE}")
    server = create_server(
        args.db.resolve(),
        args.evidence_dir.resolve(),
        gate=args.gate,
        threshold=args.gate_threshold,
        faults=faults,
        interface=args.interface,
    )
    if args.transport == "stdio":
        # stdio의 stdout은 MCP 통신에 사용한다. 진단 로그는 stderr에 쓴다.
        server.run(transport="stdio")
    else:
        # mcp 2.3.0의 전송 이름도 streamable-http다. 경로는 SDK 기본값 /mcp다.
        server.run(transport="streamable-http", host=LOOPBACK, port=args.port)
