"""내 Claude Code 세션 기록에서 반복 작업·품질 문제의 신호를 센다. 모델을 부르지 않는다.

업무 세션을 다루므로 **기본 출력에는 대화 내용이 나오지 않는다.** 나오는 것은 건수, 프로젝트 번호(P1, P2…),
세션 ID 앞 8글자, 차례 번호, 내장 도구 이름뿐이다. 프로젝트 폴더 이름과 MCP 서버·도구 이름도 기본으로 가린다.

세는 신호 (모두 휴리스틱이다. 신호는 "다시 볼 곳"이지 판정이 아니다):

    같은 명령 반복        한 세션에서 같은 Bash 명령을 3번 이상 실행했다
    실패 뒤 같은 재시도   오류로 끝난 도구 호출을 바로 다음에 같은 인자로 다시 불렀다
    도구 사용 거절        사람이 권한 확인에서 도구 사용을 거절했다
    hook이 막음           PreToolUse hook이 도구 호출을 막았다(내 장치가 실제로 일한 횟수이기도 하다)
    사람이 중단           사람이 진행 중인 응답을 중단했다(Esc). 도구 거절에 딸려 남는 중단 표식은 세지 않는다
    수정 뒤 검사 없음     한 차례 안에서 코드 파일을 고친 뒤(오류로 끝난 수정은 빼고), 그 차례가 끝날 때까지 검사 명령을 실행하지 않았다
                          (문서 파일 .md .mdx .txt .rst .adoc 수정은 세지 않는다)
    검사 파일 수정        이미 있는 테스트 파일(tests/, test_*.py, *_test.*, *.test.*, *.spec.*)을 Edit로 고쳤다(막히거나 실패한 Edit는 빼고)
                          (Write는 새 파일 생성과 구별할 수 없어 세지 않는다)
    문맥 압축             대화가 압축되었다(compact)

사용법 (Day06_new/use_cc 폴더에서):

    uv run python tools/diagnose_sessions.py                         # 최근 14일, 모든 프로젝트
    uv run python tools/diagnose_sessions.py --days 30
    uv run python tools/diagnose_sessions.py --project ~/day06-p3    # 그 폴더에서 시작한 세션만
    uv run python tools/diagnose_sessions.py --json                  # 건수만 JSON으로

내용을 보는 두 옵션은 **Claude Code 밖의 일반 터미널에서만** 친다. Claude Code 안에서 `!`로 치면 출력이 대화에 들어가
모델로 전송되기 때문이다. Claude Code 안(환경 변수 CLAUDECODE가 있음)에서 부르면 거절한다.

    uv run python tools/diagnose_sessions.py --show P2:1a2b3c4d#14   # 그 차례의 발화·도구 호출·결과 앞부분
    uv run python tools/diagnose_sessions.py --reveal                # 프로젝트 표에 폴더 이름과 MCP 이름을 함께

기록 위치와 형식: 대화형 세션 기록은 ~/.claude/projects/<시작 폴더 경로의 영숫자 아닌 글자를 -로 바꾼 이름>/<세션 ID>.jsonl
(https://code.claude.com/docs/en/sessions.md). 줄 형식은 Claude Code 내부 형식이라 버전마다 바뀔 수 있다.
이 도구는 2026-11-05에 Claude Code 2.1.318의 기록으로 확인했다. 쓰는 표식은 아래 상수에 모았다.
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# 2.1.318 기록에서 확인한 표식
INTERRUPT_PREFIX = "[Request interrupted by user"          # 중단 표식 전부(사람 발화로 세지 않기 위해)
INTERRUPT_BY_HUMAN = "[Request interrupted by user]"         # Esc로 응답을 끊은 것
# 도구 사용을 거절하면 "[Request interrupted by user for tool use]"도 함께 남는다. 이것은 거절로만 센다.
REJECT_PREFIX = "The user doesn't want to proceed"
HOOK_BLOCK = re.compile(r"^PreToolUse:\S+ hook error")       # 예: "PreToolUse:Edit hook error: [명령]: 이유"
SKILL_BODY_PREFIX = "Base directory for this skill:"
COMMAND_ECHO_PREFIXES = ("<command-name>", "<command-message>", "<local-command-stdout>", "<local-command-stderr>")

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
MODIFY_TOOLS = {"Edit", "MultiEdit"}
DOC_SUFFIXES = {".md", ".mdx", ".txt", ".rst", ".adoc"}
REPEAT_THRESHOLD = 3

# "검사 명령"으로 보는 Bash 명령. 언어별로 흔한 테스트·정적 검사 명령이다. 여기에 없는 검사는 세지 못한다.
CHECK_COMMAND = re.compile(
    r"(pytest|unittest|tox\b|nox\b|npm (run )?test|pnpm (run )?test|yarn test|bun test|vitest|jest|mocha|"
    r"go test|cargo (test|check|clippy)|mvn (test|verify)|gradle(w)? (test|check)|dotnet test|make (test|check)|"
    r"ruff|mypy|pyright|tsc\b|eslint|biome|flake8|pylint|black --check|check_evidence)"
)
TEST_PATH = re.compile(r"(^|/)(tests?/|__tests__/)|(^|/)test_[^/]*$|_test\.[^/]+$|\.(test|spec)\.[^/]+$")

SIGNALS = [
    ("repeat_command", "같은 명령 3회 이상", "실행 제어 · 도구"),
    ("retry_after_error", "실패 뒤 같은 재시도", "실행 제어"),
    ("rejected", "도구 사용 거절", "실행 제어 · 지침"),
    ("hook_block", "hook이 막음", "실행 제어"),
    ("interrupted", "사람이 중단", "지침"),
    ("edit_without_check", "수정 뒤 검사 없음", "검증"),
    ("test_edit", "검사 파일 수정", "검증"),
    ("compaction", "문맥 압축", "상태"),
]


@dataclass
class ToolCall:
    turn: int
    tool_use_id: str
    name: str
    arguments: dict
    is_error: bool = False
    rejected: bool = False
    hook_blocked: bool = False
    result_text: str = ""


@dataclass
class SessionScan:
    """세션 하나를 읽은 결과. prompts[i]는 i+1번째 차례의 사람 발화다(내용 보기에만 쓴다)."""

    session_id: str
    project_dir: str
    prompts: list = field(default_factory=list)
    calls: list = field(default_factory=list)
    interrupts: list = field(default_factory=list)
    compactions: list = field(default_factory=list)
    skipped_lines: int = 0

    @property
    def turns(self):
        return len(self.prompts)


def text_of(content):
    """tool_result의 content(문자열 또는 블록 목록)를 문자열 하나로."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(str(block.get("text", "")) for block in content if isinstance(block, dict))
    return ""


def is_prompt_text(text):
    stripped = text.lstrip()
    if not stripped:
        return False
    if stripped.startswith(INTERRUPT_PREFIX) or stripped.startswith(SKILL_BODY_PREFIX):
        return False
    return not stripped.startswith(COMMAND_ECHO_PREFIXES)


def scan_session(path, project_dir):
    """세션 기록 파일 하나를 읽는다. 읽을 수 없는 줄은 세기만 하고 건너뛴다."""
    scan = SessionScan(session_id=path.stem, project_dir=project_dir)
    by_id = {}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except ValueError:
                scan.skipped_lines += 1
                continue
            if not isinstance(event, dict) or event.get("isSidechain"):
                continue
            kind = event.get("type")
            if kind == "system" and event.get("subtype") == "compact_boundary":
                scan.compactions.append(scan.turns)
                continue
            if kind not in ("user", "assistant"):
                continue
            message = event.get("message") or {}
            content = message.get("content")
            if kind == "assistant":
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        call = ToolCall(
                            turn=scan.turns,
                            tool_use_id=str(block.get("id", "")),
                            name=str(block.get("name", "")),
                            arguments=block.get("input") if isinstance(block.get("input"), dict) else {},
                        )
                        scan.calls.append(call)
                        by_id[call.tool_use_id] = call
                continue
            # 사용자 쪽 줄: 사람 발화, 도구 결과, 중단 표식, 메타 메시지가 섞여 있다.
            if event.get("isMeta") or event.get("isCompactSummary"):
                continue
            if isinstance(content, str):
                if content.lstrip().startswith(INTERRUPT_PREFIX):
                    if content.strip().startswith(INTERRUPT_BY_HUMAN):
                        scan.interrupts.append(scan.turns)
                elif is_prompt_text(content):
                    scan.prompts.append(content)
                continue
            if not isinstance(content, list):
                continue
            has_result = False
            texts = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_result":
                    has_result = True
                    call = by_id.get(str(block.get("tool_use_id", "")))
                    if call is not None:
                        body = text_of(block.get("content"))
                        call.is_error = bool(block.get("is_error"))
                        call.rejected = body.lstrip().startswith(REJECT_PREFIX)
                        call.hook_blocked = bool(HOOK_BLOCK.match(body.lstrip()))
                        call.result_text = body
                elif block.get("type") == "text":
                    text = str(block.get("text", ""))
                    if text.lstrip().startswith(INTERRUPT_PREFIX):
                        if text.strip().startswith(INTERRUPT_BY_HUMAN):
                            scan.interrupts.append(scan.turns)
                    else:
                        texts.append(text)
            if not has_result:
                prompt = "\n".join(t for t in texts if is_prompt_text(t))
                if prompt:
                    scan.prompts.append(prompt)
    return scan


def edited_path(call):
    """수정 도구가 고친 파일 경로(구분자는 /)."""
    raw = call.arguments.get("file_path") or call.arguments.get("notebook_path") or ""
    return str(raw).replace("\\", "/")


def is_doc(path):
    return Path(path).suffix.lower() in DOC_SUFFIXES


def same_arguments(a, b):
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


def find_signals(scan):
    """세션 하나에서 신호를 찾는다. {신호 키: [차례 번호, ...]} — 차례 번호는 1부터, 0은 첫 발화 전."""
    found = {key: [] for key, _, _ in SIGNALS}

    # 같은 명령 반복: 세 번째로 실행한 차례를 위치로 쓴다.
    seen = Counter()
    for call in scan.calls:
        if call.name != "Bash":
            continue
        command = re.sub(r"\s+", " ", str(call.arguments.get("command", ""))).strip()
        if not command:
            continue
        seen[command] += 1
        if seen[command] == REPEAT_THRESHOLD:
            found["repeat_command"].append(call.turn)

    # 실패 뒤 같은 재시도
    for previous, current in zip(scan.calls, scan.calls[1:]):
        if previous.is_error and previous.name == current.name and same_arguments(previous.arguments, current.arguments):
            found["retry_after_error"].append(current.turn)

    found["rejected"] = [call.turn for call in scan.calls if call.rejected]
    found["hook_block"] = [call.turn for call in scan.calls if call.hook_blocked]
    found["interrupted"] = list(scan.interrupts)
    found["compaction"] = list(scan.compactions)

    for call in scan.calls:
        if call.name in MODIFY_TOOLS and not call.is_error:
            target = edited_path(call)
            if TEST_PATH.search(target):
                found["test_edit"].append(call.turn)

    # 수정 뒤 검사 없음: 차례마다 마지막 수정 뒤에 검사 명령이 있었는지 본다.
    calls_by_turn = {}
    for call in scan.calls:
        calls_by_turn.setdefault(call.turn, []).append(call)
    for turn, calls in sorted(calls_by_turn.items()):
        last_edit = max(
            (i for i, c in enumerate(calls) if c.name in EDIT_TOOLS and not c.is_error and not is_doc(edited_path(c))),
            default=None,
        )
        if last_edit is None:
            continue
        checked = any(
            c.name == "Bash" and CHECK_COMMAND.search(str(c.arguments.get("command", "")))
            for c in calls[last_edit + 1 :]
        )
        if not checked:
            found["edit_without_check"].append(turn)
    return found


def project_label_map(root):
    """프로젝트 폴더(이름순) → P1, P2, … 기간 필터와 무관하게 같은 번호를 준다."""
    folders = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    return {name: f"P{index}" for index, name in enumerate(folders, start=1)}


def folder_slug(folder):
    """Claude Code가 기록 폴더 이름을 만드는 규칙: 시작 폴더 경로의 영숫자 아닌 글자를 -로."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(folder).expanduser().resolve()))


def collect(root, days, project=None):
    labels = project_label_map(root)
    cutoff = time.time() - days * 86400
    scans = []
    for name, label in labels.items():
        if project is not None and name != folder_slug(project):
            continue
        for path in sorted((root / name).glob("*.jsonl")):
            if path.stat().st_mtime < cutoff:
                continue
            scan = scan_session(path, name)
            scans.append((label, scan))
    return labels, scans


def public_tool_name(name, reveal):
    if name.startswith("mcp__") and not reveal:
        return "MCP 도구(이름 가림)"
    return name


def summarize(labels, scans, reveal=False, examples=3):
    """건수만 담은 요약. 대화 내용은 넣지 않는다."""
    totals = {key: 0 for key, _, _ in SIGNALS}
    sessions_with = {key: 0 for key, _, _ in SIGNALS}
    where = {key: [] for key, _, _ in SIGNALS}
    tools = Counter()
    per_project = {}
    for label, scan in scans:
        signals = find_signals(scan)
        row = per_project.setdefault(
            label,
            {"label": label, "folder": scan.project_dir if reveal else None, "sessions": 0, "turns": 0,
             "tool_calls": 0, "tool_errors": 0, "signals": 0},
        )
        row["sessions"] += 1
        row["turns"] += scan.turns
        row["tool_calls"] += len(scan.calls)
        row["tool_errors"] += sum(1 for c in scan.calls if c.is_error)
        for call in scan.calls:
            tools[public_tool_name(call.name, reveal)] += 1
        for key, turns in signals.items():
            if not turns:
                continue
            totals[key] += len(turns)
            sessions_with[key] += 1
            row["signals"] += len(turns)
            for turn in turns:
                place = f"{label}:{scan.session_id[:8]}#{turn}"
                if len(where[key]) < examples and place not in where[key]:
                    where[key].append(place)
    return {
        "sessions": len(scans),
        "projects": len({label for label, _ in scans}),
        "turns": sum(scan.turns for _, scan in scans),
        "tool_calls": sum(len(scan.calls) for _, scan in scans),
        "signals": [
            {"key": key, "name": name, "responsibility": resp, "count": totals[key],
             "sessions": sessions_with[key], "examples": where[key]}
            for key, name, resp in SIGNALS
        ],
        "projects_table": sorted(per_project.values(), key=lambda r: int(r["label"][1:])),
        "top_tools": tools.most_common(8),
    }


def render(summary, days, reveal):
    lines = [
        f"진단 범위: 최근 {days}일, 프로젝트 {summary['projects']}개, 세션 {summary['sessions']}개, "
        f"사람 차례 {summary['turns']}개, 도구 호출 {summary['tool_calls']}개",
        "(모델 호출 없음. 대화 내용은 출력하지 않음. 신호는 다시 볼 곳이지 판정이 아님)",
        "",
        "| 신호 | 건수 | 세션 수 | 관련될 수 있는 책임(추정) | 위치 예 (프로젝트:세션#차례) |",
        "|---|---|---|---|---|",
    ]
    for item in summary["signals"]:
        lines.append(
            f"| {item['name']} | {item['count']} | {item['sessions']} | {item['responsibility']} | "
            f"{', '.join(item['examples']) or '-'} |"
        )
    lines += ["", "| 프로젝트 | 세션 | 사람 차례 | 도구 호출 | 오류 결과 | 신호 합 |" + (" 폴더 |" if reveal else ""),
              "|---|---|---|---|---|---|" + ("---|" if reveal else "")]
    for row in summary["projects_table"]:
        line = (f"| {row['label']} | {row['sessions']} | {row['turns']} | {row['tool_calls']} | "
                f"{row['tool_errors']} | {row['signals']} |")
        if reveal:
            line += f" {row['folder']} |"
        lines.append(line)
    if summary["top_tools"]:
        lines += ["", "많이 쓴 도구: " + ", ".join(f"{name} {count}" for name, count in summary["top_tools"])]
    lines += ["", "위치 하나를 자세히 보려면 Claude Code 밖의 일반 터미널에서:",
              "  uv run python tools/diagnose_sessions.py --show <위치 예의 값>"]
    return "\n".join(lines)


def clip(text, limit):
    flat = re.sub(r"\s+", " ", str(text)).strip()
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def show(labels, root, token):
    """P2:1a2b3c4d#14 형식의 위치 하나를 풀어 쓴다. 대화 내용이 나온다."""
    match = re.fullmatch(r"(P\d+):([0-9a-fA-F-]{4,})#(\d+)", token.strip())
    if not match:
        return f"[형식 오류] 위치는 P2:1a2b3c4d#14 형식입니다: {token}"
    label, prefix, turn = match.group(1), match.group(2).lower(), int(match.group(3))
    folder = next((name for name, value in labels.items() if value == label), None)
    if folder is None:
        return f"[찾을 수 없음] {label} 프로젝트가 없습니다."
    candidates = sorted((root / folder).glob(f"{prefix}*.jsonl"))
    if len(candidates) != 1:
        return f"[찾을 수 없음] {label}에서 {prefix}로 시작하는 세션이 {len(candidates)}개입니다."
    scan = scan_session(candidates[0], folder)
    lines = [f"{label} 세션 {scan.session_id} 차례 {turn} (이 출력에는 대화 내용이 있습니다)"]
    if 1 <= turn <= scan.turns:
        lines.append(f"사람: {clip(scan.prompts[turn - 1], 400)}")
    for call in (c for c in scan.calls if c.turn == turn):
        flags = " [오류]" if call.is_error else ""
        flags += " [거절]" if call.rejected else ""
        flags += " [hook이 막음]" if call.hook_blocked else ""
        lines.append(f"- {call.name}{flags}: {clip(json.dumps(call.arguments, ensure_ascii=False), 200)}")
        if call.result_text:
            lines.append(f"    결과: {clip(call.result_text, 200)}")
    if turn in scan.interrupts:
        lines.append("- (사람이 이 차례에서 중단함)")
    return "\n".join(lines)


def inside_claude_code():
    return bool(os.environ.get("CLAUDECODE"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Claude Code 세션 기록에서 반복 작업·품질 문제의 신호를 센다 (모델 호출 없음).")
    parser.add_argument("--days", type=int, default=14, help="최근 며칠의 세션을 볼지 (기본 14)")
    parser.add_argument("--project", help="이 폴더에서 시작한 세션만 본다")
    parser.add_argument("--root", default="~/.claude/projects", help="세션 기록 폴더 (기본 ~/.claude/projects)")
    parser.add_argument("--json", action="store_true", help="표 대신 건수만 JSON으로")
    parser.add_argument("--show", metavar="위치", help="P2:1a2b3c4d#14 위치의 내용을 보여 준다 (일반 터미널에서만)")
    parser.add_argument("--reveal", action="store_true", help="프로젝트 폴더 이름과 MCP 이름을 보여 준다 (일반 터미널에서만)")
    parser.add_argument("--allow-in-claude", action="store_true", help="Claude Code 안에서도 --show/--reveal을 허용한다(권하지 않음)")
    args = parser.parse_args(argv)

    if (args.show or args.reveal) and inside_claude_code() and not args.allow_in_claude:
        print("[거절] --show와 --reveal은 대화 내용이나 폴더 이름을 출력합니다. Claude Code 안에서 치면 그 출력이 "
              "모델로 전송됩니다. Claude Code 밖의 일반 터미널에서 다시 실행하세요.")
        return 2

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"[확인 불가] 세션 기록 폴더가 없습니다: {root}")
        return 2
    labels, scans = collect(root, args.days, args.project)
    if args.show:
        print(show(labels, root, args.show))
        return 0
    summary = summarize(labels, scans, reveal=args.reveal)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render(summary, args.days, args.reveal))
    return 0


if __name__ == "__main__":
    sys.exit(main())
