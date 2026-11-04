"""예시 plugin의 MCP 서버: 할 일 보관함.

Capability Challenge에서 수강생이 복사해 시작하는 틀이다. 영역(할 일)은 바꾸되, 아래 **관례 다섯 가지**는 지킨다.
검사기(`use_cc/tools/check_capability.py`)가 이 관례를 확인한다.

1. 업무 오류는 예외가 아니라 값으로 돌려준다: {"success": false, "error": "<코드>", "message": "..."}.
   예외는 MCP 도구 오류(isError)가 되어 Claude가 받는 모양이 달라진다. 수강생이 고칠 수 있는 실패는 업무 오류다.
2. 도구마다 annotations 네 개(readOnlyHint, destructiveHint, idempotentHint, openWorldHint)를 모두 적는다.
   명세의 기본값은 destructiveHint=true, openWorldHint=true라서 적지 않으면 "파괴적이고 바깥과 통신한다"고 알리게 된다.
   annotations는 힌트일 뿐 강제가 아니다. 실제 동작과 맞게 적는다.
3. 인자마다 타입과 설명을 적고, 정해진 값만 받는 인자는 Literal(enum)로 받는다.
4. 장애 주입: 환경 변수 CAPABILITY_FAULT(JSON)를 읽어 권한 거부와 일시 장애를 흉내 낸다.
   예: {"permission_denied": ["complete_task"], "transient": {"add_task": 1}}
   `claude plugin eval`의 사례는 EVAL_로 시작하는 환경 변수만 정할 수 있으므로 EVAL_CAPABILITY_FAULT도 같은 뜻으로 읽는다.
5. stdout은 MCP 통신 전용이다. print를 쓰지 않는다. 진단은 stderr에 쓴다.

상태는 --data-dir 폴더의 tasks.json 하나에 둔다. plugin의 .mcp.json이 이 폴더를 ${CLAUDE_PROJECT_DIR}/.capability-data로
정하므로, Claude Code를 연 폴더(시험 폴더)마다 상태가 따로 생긴다.
"""

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server import MCPServer
from mcp_types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

SERVER_NAME = "example-tasks"
FAULT_ENV = "CAPABILITY_FAULT"
# `claude plugin eval`의 사례 env는 EVAL_로 시작해야 한다. 같은 내용을 이 이름으로도 받는다.
EVAL_FAULT_ENV = "EVAL_CAPABILITY_FAULT"

Priority = Literal["high", "normal", "low"]
StatusFilter = Literal["open", "done", "all"]


def log(message: str) -> None:
    """진단 메시지는 stderr로만 쓴다(관례 5)."""
    print(f"[{SERVER_NAME}] {message}", file=sys.stderr, flush=True)


def fail(code: str, message: str, **details: Any) -> dict[str, Any]:
    """업무 오류의 모양(관례 1). Claude가 오류 코드를 보고 다음 행동을 고를 수 있게 한다."""
    return {"success": False, "error": code, "message": message, **details}


def business_failure(result: dict[str, Any]) -> dict[str, Any]:
    """미들웨어에서 도구 대신 돌려줄 tools/call 결과. 도구가 업무 오류를 돌려줄 때와 같은 모양이다."""
    text = json.dumps(result, ensure_ascii=False, indent=2)
    return CallToolResult(content=[TextContent(type="text", text=text)], structured_content=result).model_dump(
        mode="json", by_alias=True, exclude_none=True
    )


class TaskStore:
    """할 일을 JSON 파일 하나에 저장한다. 쓰기는 임시 파일에 쓴 뒤 바꿔치기해서 반쯤 쓰인 파일을 남기지 않는다."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, tasks: list[dict[str, Any]]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)


def load_fault_plan() -> dict[str, Any]:
    """CAPABILITY_FAULT를 읽는다(관례 4). 모르는 키나 틀린 모양은 서버를 시작하기 전에 거절한다."""
    raw = (os.environ.get(FAULT_ENV) or os.environ.get(EVAL_FAULT_ENV) or "").strip()
    if not raw:
        return {"permission_denied": [], "transient": {}}
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SystemExit(f"{FAULT_ENV}가 JSON이 아닙니다: {error}") from error
    unknown = set(plan) - {"permission_denied", "transient"}
    if unknown:
        raise SystemExit(f"{FAULT_ENV}에 모르는 키가 있습니다: {sorted(unknown)}")
    return {"permission_denied": list(plan.get("permission_denied", [])), "transient": dict(plan.get("transient", {}))}


def fault_middleware(plan: dict[str, Any]):
    """도구에 닿기 전에 장애 결과를 돌려준다. 도구 코드가 실행되지 않으므로 상태가 바뀌지 않는다."""
    remaining = dict(plan["transient"])

    async def inject_faults(ctx, call_next):
        if ctx.method != "tools/call":
            return await call_next(ctx)
        name = (ctx.params or {}).get("name")
        if name in plan["permission_denied"]:
            return business_failure(fail("permission_denied", "이 도구를 사용할 권한이 없습니다."))
        if remaining.get(name, 0) > 0:
            remaining[name] -= 1
            return business_failure(
                fail("temporarily_unavailable", "일시적으로 처리할 수 없습니다. 같은 요청을 한 번 다시 보내세요.", retryable=True)
            )
        return await call_next(ctx)

    return inject_faults


def create_server(data_dir: Path) -> MCPServer:
    store = TaskStore(data_dir / "tasks.json")
    plan = load_fault_plan()
    if plan["permission_denied"] or plan["transient"]:
        log(f"장애 주입: {plan}")
    mcp = MCPServer(name=SERVER_NAME, middleware=[fault_middleware(plan)])

    # 같은 제목의 열린 할 일이 있으면 새로 만들지 않고 그것을 돌려준다. 그래서 다시 보내도 결과가 같다(idempotent=true).
    # 기존 기록을 지우거나 덮어쓰지 않는다(destructive=false). 로컬 파일만 쓴다(openWorld=false).
    def add_task(
        title: Annotated[str, Field(description="할 일 제목. 사용자가 말한 행동을 그대로 적는다(예: 주간 보고서 초안 쓰기)")],
        priority: Annotated[Priority, Field(description="우선순위. high, normal, low 중 하나")] = "normal",
    ) -> dict[str, Any]:
        """새 할 일을 추가한다. 같은 제목의 열린 할 일이 이미 있으면 새로 만들지 않고 그것을 돌려준다."""
        cleaned = title.strip()
        # 코드 규칙으로 두는 판단: 닫힌 조건(길이)이라 모델에게 맡기지 않는다.
        if len(cleaned) < 2:
            return fail("title_too_short", "할 일 제목은 두 글자 이상이어야 합니다. 사용자에게 무엇을 할지 다시 묻습니다.")
        tasks = store.load()
        for task in tasks:
            if task["status"] == "open" and task["title"] == cleaned:
                return {"success": True, "created": False, "task": task}
        task = {
            "task_id": uuid.uuid4().hex[:12],
            "title": cleaned,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        tasks.append(task)
        store.save(tasks)
        return {"success": True, "created": True, "task": task}

    def list_tasks(
        status: Annotated[StatusFilter, Field(description="보여 줄 상태. open(기본), done, all 중 하나")] = "open",
    ) -> dict[str, Any]:
        """할 일 목록을 보여 준다. 아무것도 바꾸지 않는다."""
        tasks = store.load()
        chosen = tasks if status == "all" else [task for task in tasks if task["status"] == status]
        return {"success": True, "count": len(chosen), "tasks": chosen}

    # 이미 끝낸 할 일을 다시 끝내도 같은 결과를 돌려준다(idempotent=true). 기록을 지우지 않는다(destructive=false).
    def complete_task(
        task_id: Annotated[str, Field(description="끝낼 할 일의 ID. list_tasks나 add_task의 결과에 있는 task_id")],
    ) -> dict[str, Any]:
        """할 일을 끝낸 것으로 표시한다. 없는 ID면 task_not_found를 돌려준다."""
        tasks = store.load()
        for task in tasks:
            if task["task_id"] == task_id:
                if task["status"] != "done":
                    task["status"] = "done"
                    task["done_at"] = datetime.now(UTC).isoformat(timespec="seconds")
                    store.save(tasks)
                return {"success": True, "task": task}
        return fail("task_not_found", f"ID가 {task_id}인 할 일이 없습니다. list_tasks로 ID를 확인합니다.")

    mcp.add_tool(add_task, annotations=ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
    mcp.add_tool(list_tasks, annotations=ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
    mcp.add_tool(complete_task, annotations=ToolAnnotations(
        read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="예시 plugin의 MCP 서버(할 일 보관함)")
    parser.add_argument("--data-dir", type=Path, required=True, help="상태 파일(tasks.json)을 둘 폴더")
    arguments = parser.parse_args()
    data_dir = arguments.data_dir.expanduser().resolve()
    log(f"상태 폴더: {data_dir}")
    create_server(data_dir).run(transport="stdio")


if __name__ == "__main__":
    main()
