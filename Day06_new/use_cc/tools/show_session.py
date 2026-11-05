"""Claude Code 세션 기록을 '차례 / 도구 / 인자 / 결과' 표로 풀어 쓴다. 모델을 부르지 않는다.

읽을 수 있는 기록은 두 가지다.

1. `claude -p ... --output-format stream-json --verbose` 의 출력을 저장한 파일
2. 대화형 세션이 남기는 기록 `~/.claude/projects/<프로젝트>/<세션 ID>.jsonl`
   <프로젝트>는 세션을 시작한 폴더의 경로에서 영숫자가 아닌 글자를 '-'로 바꾼 이름이다
   (https://code.claude.com/docs/en/sessions.md 의 "Where transcripts are stored").

주의: 두 기록의 줄 형식은 Claude Code 내부 형식이고 버전마다 바뀔 수 있다고 문서에 적혀 있다(같은 문서).
이 도구는 2026-11-04에 Claude Code 2.1.318의 두 형식으로 확인했다. 버전이 달라 표가 비면 이 파일을 고쳐야 한다.
두 형식 모두 `type`이 assistant 또는 user인 줄의 `message.content` 안에 `tool_use`(도구 호출)와
`tool_result`(도구 결과) 블록이 들어 있다는 점만 쓴다.

사용법 (Day06_new/use_cc 폴더에서):

    uv run python tools/show_session.py <stream-json 파일 또는 세션 기록 .jsonl>
    uv run python tools/show_session.py --latest ~/day06-p3      # 그 폴더에서 연 마지막 대화형 세션
    uv run python tools/show_session.py <기록> --width 200       # 칸을 덜 자른다

이 파일은 Day04_new/use_cc/tools/show_session.py(2026-11-04)를 복사해 사용법만 바꾼 것이다.
주의: 이 표에는 대화 내용(인자와 결과의 앞부분)이 나온다. 실험 폴더 세션에만 쓴다.
업무 세션은 내용 없이 집계하는 tools/diagnose_sessions.py로 본다.
"""

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# Skill을 부르면 Claude Code가 SKILL.md 본문을 이 문장으로 시작하는 사용자 메시지로 넣는다(2.1.318에서 관찰).
SKILL_BODY_PREFIX = "Base directory for this skill:"


@dataclass
class Step:
    """표의 한 줄. kind는 tool(도구 호출), skill_body(Skill 본문이 들어옴), turn(새 발화) 중 하나다."""

    kind: str
    turn: int | None = None
    tool_use_id: str = ""
    name: str = ""
    arguments: dict = field(default_factory=dict)
    result_text: str = ""
    is_error: bool | None = None
    note: str = ""


@dataclass
class Session:
    """기록 하나를 읽은 결과."""

    session_ids: list[str] = field(default_factory=list)
    claude_code_version: str = ""
    model: str = ""
    model_call_ids: set[str] = field(default_factory=set)
    steps: list[Step] = field(default_factory=list)
    final_texts: list[str] = field(default_factory=list)
    # JSON으로 읽을 수 없어 건너뛴 줄 수. 진행 중인 세션의 마지막 줄이 흔한 경우다.
    skipped_lines: int = 0


def content_blocks(event: dict) -> list[dict]:
    """assistant/user 줄의 message.content를 블록 목록으로. 문자열 하나뿐이면 text 블록 하나로 본다."""
    content = (event.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def result_as_text(block: dict) -> str:
    """tool_result의 content를 문자열 하나로. 텍스트 블록 목록이면 이어 붙이고, 그 밖의 것은 JSON으로 적는다."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                pieces.append(item.get("text", ""))
            elif isinstance(item, dict) and item.get("type") == "tool_reference":
                pieces.append(f"[도구 불러옴] {item.get('tool_name')}")
            else:
                pieces.append(json.dumps(item, ensure_ascii=False))
        return "\n".join(pieces)
    return json.dumps(content, ensure_ascii=False)


def read_session(path: Path) -> Session:
    """기록 파일을 읽어 Session으로 만든다. 모르는 줄은 건너뛴다."""
    session = Session()
    steps_by_tool_use: dict[str, Step] = {}
    current_turn: int | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # 진행 중인 세션은 마지막 줄이 아직 덜 쓰였을 수 있다. 읽을 수 없는 줄은 세어 두고 건너뛴다.
            session.skipped_lines += 1
            continue
        event_type = event.get("type")

        # 1. 세션 ID와 버전. stream-json은 init 줄에, 대화형 기록은 모든 줄에 sessionId가 있다.
        session_id = event.get("session_id") or event.get("sessionId")
        if session_id and session_id not in session.session_ids:
            session.session_ids.append(session_id)
        if event_type == "system" and event.get("subtype") == "init":
            session.claude_code_version = event.get("claude_code_version") or session.claude_code_version
            session.model = event.get("model") or session.model
        if event.get("version") and not session.claude_code_version:
            session.claude_code_version = event["version"]

        # 2. 녹화본은 줄마다 _turn(몇 번째 발화인가)을 붙여 두었다. 바뀔 때 구분 줄을 넣는다.
        turn = event.get("_turn")
        if turn is not None and turn != current_turn:
            current_turn = turn
            session.steps.append(Step(kind="turn", turn=turn))

        if event_type == "assistant":
            message = event.get("message") or {}
            if message.get("id"):
                # 응답 하나가 여러 줄로 나뉘어 와도 message.id는 같다. 서로 다른 id의 수가 모델 호출 수다.
                session.model_call_ids.add(message["id"])
            session.model = session.model or message.get("model", "")
            for block in content_blocks(event):
                if block.get("type") == "tool_use" and block.get("id") not in steps_by_tool_use:
                    step = Step(kind="tool", turn=current_turn, tool_use_id=block.get("id", ""),
                                name=block.get("name", ""), arguments=block.get("input") or {})
                    steps_by_tool_use[step.tool_use_id] = step
                    session.steps.append(step)
                elif block.get("type") == "text" and block.get("text", "").strip():
                    session.final_texts.append(block["text"].strip())

        elif event_type == "user":
            for block in content_blocks(event):
                if block.get("type") == "tool_result":
                    step = steps_by_tool_use.get(block.get("tool_use_id", ""))
                    if step is not None:
                        step.result_text = result_as_text(block)
                        step.is_error = block.get("is_error")
                elif block.get("type") == "text" and block.get("text", "").startswith(SKILL_BODY_PREFIX):
                    # 지침이 대화에 들어오는 순간이다. 본문 길이만 적는다.
                    session.steps.append(Step(kind="skill_body", turn=current_turn,
                                              note=f"Skill 본문이 대화에 들어옴 ({len(block['text'])}자)"))
    return session


def summarize_result(text: str) -> str:
    """도구 결과를 한 줄로. 강사 사례 서버처럼 JSON으로 답하면 success, error, status만 뽑는다."""
    stripped = text.strip()
    try:
        payload = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return re.sub(r"\s+", " ", stripped)
    if isinstance(payload, dict) and "success" in payload:
        parts = [f"success={str(payload['success']).lower()}"]
        for key in ("error", "status", "session_id", "evidence_id"):
            if key in payload:
                parts.append(f"{key}={payload[key]}")
        return " ".join(parts)
    return re.sub(r"\s+", " ", stripped)


def shorten(text: str, width: int) -> str:
    """표 칸 하나에 들어가게 자르고, 표를 깨는 | 와 줄바꿈을 바꾼다."""
    flat = re.sub(r"\s+", " ", text).replace("|", "/")
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def turn_utterances(path: Path) -> dict[int, str]:
    """녹화본 폴더의 meta.json에 적힌 발화. 없으면 빈 사전."""
    meta_path = path.parent / "meta.json"
    if not meta_path.is_file():
        return {}
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {item["turn"]: item.get("user", "") for item in meta.get("turns", [])}


def render(session: Session, width: int, utterances: dict[int, str]) -> str:
    """Session을 마크다운 표로. 터미널에서 읽기 쉽고 강사 노트에 그대로 붙일 수 있다."""
    tool_steps = [step for step in session.steps if step.kind == "tool"]
    lines = [
        f"세션 ID: {', '.join(session.session_ids) or '(없음)'}",
        f"Claude Code 버전: {session.claude_code_version or '(기록에 없음)'} / 모델: {session.model or '(기록에 없음)'}",
        f"모델 호출 수(서로 다른 응답 id): {len(session.model_call_ids)} / 도구 호출 수: {len(tool_steps)}",
    ]
    if session.skipped_lines:
        lines.append(f"읽을 수 없어 건너뛴 줄: {session.skipped_lines} (진행 중인 세션이면 마지막 줄이 덜 쓰였을 수 있다)")
    lines += [
        "",
        "| 차례 | 도구 | 인자 | 결과 | is_error |",
        "|---|---|---|---|---|",
    ]
    number = 0
    for step in session.steps:
        if step.kind == "turn":
            said = utterances.get(step.turn, "")
            lines.append(f"| | **발화 {step.turn}** | {shorten(said, width)} | | |")
        elif step.kind == "skill_body":
            lines.append(f"| | (지침) | {step.note} | | |")
        else:
            number += 1
            arguments = json.dumps(step.arguments, ensure_ascii=False)
            result = summarize_result(step.result_text) if step.result_text else "(결과 없음)"
            error = "" if step.is_error is None else str(step.is_error).lower()
            lines.append(f"| {number} | {step.name} | {shorten(arguments, width)} | {shorten(result, width)} | {error} |")
    return "\n".join(lines)


def latest_transcript(sandbox: Path) -> Path:
    """그 폴더에서 시작한 세션 중 마지막으로 바뀐 기록 파일."""
    project_name = re.sub(r"[^A-Za-z0-9]", "-", str(sandbox.expanduser().resolve()))
    project_dir = Path.home() / ".claude" / "projects" / project_name
    transcripts = sorted(project_dir.glob("*.jsonl"), key=lambda path: path.stat().st_mtime)
    if not transcripts:
        raise SystemExit(f"[멈춤] {project_dir} 에 세션 기록이 없습니다. 그 폴더에서 claude를 한 번 이상 열었는지 확인하세요.")
    return transcripts[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Claude Code 세션 기록을 표로 풀어 쓴다 (모델 호출 없음).")
    parser.add_argument("record", nargs="?", type=Path, help="stream-json 출력 또는 ~/.claude/projects/.../<세션>.jsonl")
    parser.add_argument("--latest", type=Path, help="이 폴더에서 연 마지막 세션의 기록을 읽는다")
    parser.add_argument("--width", type=int, default=90, help="표 칸 하나의 최대 글자 수 (기본 90)")
    arguments = parser.parse_args()

    if arguments.latest is not None:
        record = latest_transcript(arguments.latest)
    elif arguments.record is not None:
        record = arguments.record
    else:
        parser.error("기록 파일을 주거나 --latest <폴더>를 주세요.")
    print(f"기록: {record}")
    print(render(read_session(record), arguments.width, turn_utterances(record)))


if __name__ == "__main__":
    main()
