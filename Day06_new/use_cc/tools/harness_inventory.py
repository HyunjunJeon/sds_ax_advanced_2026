"""어떤 폴더에서 Claude Code를 열면 무엇이 함께 실리는지, 설정 파일만 읽어 여섯 책임으로 묶어 센다. 모델을 부르지 않는다.

"내 하네스 지도"를 그리는 출발점이다. 세는 것은 Claude Code 문서의 규칙을 따른 **추정**이다. 실제로 실린 것은
그 폴더에서 연 세션 안에서 `/context`(문맥 구성)와 `/memory`(실린 지침 파일)로 확인한다.

읽는 곳 (문서 근거는 Day06_new/docs/SOURCES.md):

    지침   시작 폴더와 그 위 모든 폴더의 CLAUDE.md · CLAUDE.local.md · .claude/CLAUDE.md, ~/.claude/CLAUDE.md
           (그 위 어디에도 CLAUDE.md가 없으면 AGENTS.md), 지침 파일이 @경로로 가져오는 파일
           시작 폴더부터 git 저장소 루트까지의 .claude/skills/*/SKILL.md, ~/.claude/skills/*/SKILL.md
           auto memory: ~/.claude/projects/<저장소 루트(없으면 시작 폴더) 경로를 바꾼 이름>/memory/
    도구   시작 폴더의 .mcp.json, ~/.claude.json의 사용자·이 폴더 MCP 서버, 설정의 enabledPlugins
    제어   ~/.claude/settings.json, 시작 폴더의 .claude/settings.json · settings.local.json 의 permissions와 hooks
    상태   auto memory, 이 폴더에서 시작한 세션 기록 수, 흔한 진행 기록 파일 이름(progress.md 등)이 있는지
    검증   실행 뒤 hook(PostToolUse · Stop · SubagentStop), 지침 파일에 적힌 검사 명령 줄 수, 테스트 폴더·파일이 있는지
    기록   세션 기록(자동으로 남음), 텔레메트리 환경 변수 이름이 설정에 있는지

기본 출력에는 **개수만** 나온다. 파일 경로, Skill 이름, MCP 서버 이름, hook 명령은 나오지 않는다.
이름까지 보려면 Claude Code 밖의 일반 터미널에서 `--reveal`을 붙인다(Claude Code 안에서는 거절한다).
설정 값(키, 토큰, 환경 변수 값)은 어떤 옵션으로도 출력하지 않는다.

사용법 (Day06_new/use_cc 폴더에서):

    uv run python tools/harness_inventory.py ~/work/my-project
    uv run python tools/harness_inventory.py ~/work/my-project --reveal     # 일반 터미널에서만
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from diagnose_sessions import CHECK_COMMAND, folder_slug, inside_claude_code

INSTRUCTION_NAMES = ["CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md"]
PROGRESS_NAMES = ["progress.md", "PROGRESS.md", "claude-progress.txt", "feature_list.json", "plan.md", "PLAN.md",
                  "handoff.md", "HANDOFF.md", "TODO.md", "spec.md", "intent.md"]
TEST_MARKERS = ["tests", "test", "__tests__", "spec"]
BEFORE_HOOKS = {"PreToolUse", "PermissionRequest", "UserPromptSubmit"}
AFTER_HOOKS = {"PostToolUse", "PostToolUseFailure", "Stop", "SubagentStop"}
TELEMETRY_ENV = {"CLAUDE_CODE_ENABLE_TELEMETRY", "OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_METRICS_EXPORTER",
                 "OTEL_LOGS_EXPORTER"}


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def git_root(folder):
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(folder),
                             capture_output=True, text=True, check=True)
        return Path(out.stdout.strip()).resolve()
    except (OSError, subprocess.CalledProcessError):
        return None


def ancestors(folder):
    """시작 폴더부터 위로, 파일 시스템 루트 바로 아래 폴더까지."""
    chain = [folder]
    for parent in folder.parents:
        if parent == parent.parent:
            break
        chain.append(parent)
    return chain


def instruction_files(folder, home):
    found = []
    for depth, directory in enumerate(ancestors(folder)):
        for name in INSTRUCTION_NAMES:
            path = directory / name
            if path.is_file():
                where = "시작 폴더" if depth == 0 else f"위 {depth}단계"
                if directory == home:
                    where = "홈 폴더"
                found.append((where, path))
    # 공식 문서: 시작 폴더와 그 위에 CLAUDE.md가 없을 때만 AGENTS.md를 읽는다(docs/SOURCES.md, memory 문서).
    if not any(path.name == "CLAUDE.md" for _, path in found):
        for depth, directory in enumerate(ancestors(folder)):
            path = directory / "AGENTS.md"
            if path.is_file():
                found.append(("시작 폴더" if depth == 0 else f"위 {depth}단계", path))
    user_file = home / ".claude" / "CLAUDE.md"
    if user_file.is_file():
        found.append(("사용자 전역", user_file))
    return found


def skill_dirs(folder, repo, home):
    found = []
    stop = repo if repo is not None else folder
    for directory in ancestors(folder):
        skills = directory / ".claude" / "skills"
        if skills.is_dir() and directory != home:
            for skill in sorted(p for p in skills.iterdir() if (p / "SKILL.md").is_file()):
                found.append(("프로젝트", skill))
        if directory == stop:
            break
    user_skills = home / ".claude" / "skills"
    if user_skills.is_dir():
        for skill in sorted(p for p in user_skills.iterdir() if (p / "SKILL.md").is_file()):
            found.append(("사용자 전역", skill))
    return found


IMPORT_LINE = re.compile(r"^\s*@(\S+)")
MAX_IMPORT_DEPTH = 5


def expand_imports(roots, home):
    """지침 파일의 줄 첫머리 @경로를 따라가 가져오는 파일 목록을 만든다. 코드 블록 안의 @는 구별하지 않는다."""
    seen = {path.resolve() for path in roots}
    found = []
    frontier = [(path, 0) for path in roots]
    while frontier:
        path, depth = frontier.pop(0)
        if depth >= MAX_IMPORT_DEPTH:
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = IMPORT_LINE.match(line)
            if not match:
                continue
            raw = match.group(1)
            target = Path(raw.replace("~", str(home), 1)) if raw.startswith("~") else path.parent / raw
            target = target.resolve()
            if target.is_file() and target not in seen:
                seen.add(target)
                found.append(target)
                frontier.append((target, depth + 1))
    return found


def settings_files(folder, home):
    return [
        ("사용자", home / ".claude" / "settings.json"),
        ("프로젝트", folder / ".claude" / "settings.json"),
        ("로컬", folder / ".claude" / "settings.local.json"),
    ]


def inventory(folder, home=None, projects_root=None, claude_json=None):
    folder = Path(folder).expanduser().resolve()
    home = Path(home or Path.home()).resolve()
    projects_root = Path(projects_root or home / ".claude" / "projects")
    claude_json = Path(claude_json or home / ".claude.json")
    repo = git_root(folder)

    inv = {"folder": str(folder), "repo_root": str(repo) if repo else None}

    # 지침: 지침 파일과, 그 파일이 @경로로 가져오는 파일(재귀, 최대 5단계)
    files = instruction_files(folder, home)
    imported = expand_imports([path for _, path in files], home)
    total_lines = 0
    check_lines = 0
    for path in [path for _, path in files] + imported:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        total_lines += len(lines)
        check_lines += sum(1 for line in lines if CHECK_COMMAND.search(line))
    skills = skill_dirs(folder, repo, home)
    memory_dir = projects_root / folder_slug(repo or folder) / "memory"
    memory_files = sorted(memory_dir.glob("*.md")) if memory_dir.is_dir() else []
    inv["instructions"] = {
        "files": [{"where": where, "path": str(path)} for where, path in files],
        "imported": [str(path) for path in imported],
        "total_lines": total_lines,
        "skills": [{"where": where, "name": path.name} for where, path in skills],
        "memory_files": len(memory_files),
    }

    # 도구와 실행 제어 (설정 파일)
    allow = ask = deny = 0
    default_mode = []
    hooks = {}
    plugins = 0
    env_names = set()
    for scope, path in settings_files(folder, home):
        data = read_json(path) if path.is_file() else None
        if not isinstance(data, dict):
            continue
        perms = data.get("permissions") or {}
        allow += len(perms.get("allow") or [])
        ask += len(perms.get("ask") or [])
        deny += len(perms.get("deny") or [])
        if perms.get("defaultMode"):
            default_mode.append(scope)
        for event, matchers in (data.get("hooks") or {}).items():
            count = sum(len(m.get("hooks") or []) for m in matchers if isinstance(m, dict))
            hooks[event] = hooks.get(event, 0) + count
        plugins += sum(1 for enabled in (data.get("enabledPlugins") or {}).values() if enabled)
        env_names.update((data.get("env") or {}).keys())

    project_mcp = read_json(folder / ".mcp.json") if (folder / ".mcp.json").is_file() else None
    user_config = read_json(claude_json) if claude_json.is_file() else None
    user_mcp = (user_config or {}).get("mcpServers") or {}
    local_mcp = ((user_config or {}).get("projects") or {}).get(str(folder), {}).get("mcpServers") or {}
    inv["tools"] = {
        "mcp_project": sorted(((project_mcp or {}).get("mcpServers") or {}).keys()),
        "mcp_user": sorted(user_mcp.keys()),
        "mcp_local": sorted(local_mcp.keys()),
        "plugins_enabled": plugins,
    }
    inv["control"] = {
        "allow": allow, "ask": ask, "deny": deny, "default_mode_in": default_mode,
        "hooks_before": {e: n for e, n in hooks.items() if e in BEFORE_HOOKS},
    }

    # 상태 (대소문자를 구분하지 않는 파일 시스템에서도 실제 이름만 센다)
    present_names = {entry.name for entry in folder.iterdir()}
    session_dir = projects_root / folder_slug(folder)
    sessions = len(list(session_dir.glob("*.jsonl"))) if session_dir.is_dir() else 0
    inv["state"] = {
        "memory_files": len(memory_files),
        "sessions": sessions,
        "progress_files": [name for name in PROGRESS_NAMES if name in present_names],
    }

    # 검증
    has_tests = any((folder / marker).is_dir() for marker in TEST_MARKERS) or any(folder.glob("test_*.py")) \
        or any(folder.glob("*_test.*")) or any(folder.glob("*.test.*"))
    inv["verification"] = {
        "hooks_after": {e: n for e, n in hooks.items() if e in AFTER_HOOKS},
        "check_lines_in_instructions": check_lines,
        "tests_present": bool(has_tests),
    }

    # 기록
    telemetry = sorted(name for name in env_names if name in TELEMETRY_ENV)
    inv["records"] = {"sessions": sessions, "telemetry_env_names": telemetry}
    inv["other_hooks"] = {e: n for e, n in hooks.items() if e not in BEFORE_HOOKS | AFTER_HOOKS}
    return inv


def count_by(items, key="where"):
    counts = {}
    for item in items:
        counts[item[key]] = counts.get(item[key], 0) + 1
    return ", ".join(f"{where} {n}" for where, n in counts.items()) or "없음"


def describe_hooks(hooks):
    return ", ".join(f"{event} {n}" for event, n in sorted(hooks.items())) or "없음"


def render(inv, reveal=False):
    ins, tools, control, state, ver, rec = (inv["instructions"], inv["tools"], inv["control"], inv["state"],
                                           inv["verification"], inv["records"])
    mcp_total = len(tools["mcp_project"]) + len(tools["mcp_user"]) + len(tools["mcp_local"])
    rows = [
        ("지침",
         f"CLAUDE.md류 {len(ins['files'])}개({count_by(ins['files'])}), @로 가져온 파일 {len(ins['imported'])}개, 합계 {ins['total_lines']}줄 · "
         f"Skill {len(ins['skills'])}개({count_by(ins['skills'])}) · auto memory 파일 {ins['memory_files']}개"),
        ("도구",
         f"내장 도구(늘 있음) · MCP 서버 {mcp_total}개(프로젝트 {len(tools['mcp_project'])}, 이 폴더 {len(tools['mcp_local'])}, "
         f"사용자 {len(tools['mcp_user'])}) · 켜진 plugin {tools['plugins_enabled']}개"),
        ("실행 제어",
         f"권한 규칙 allow {control['allow']} / ask {control['ask']} / deny {control['deny']} · "
         f"기본 권한 모드 설정: {', '.join(control['default_mode_in']) or '없음'} · 실행 전 hook: {describe_hooks(control['hooks_before'])}"),
        ("상태",
         f"auto memory 파일 {state['memory_files']}개 · 이 폴더 세션 기록 {state['sessions']}개 · "
         f"진행 기록 파일: {', '.join(state['progress_files']) or '없음'}"),
        ("검증",
         f"실행 뒤 hook: {describe_hooks(ver['hooks_after'])} · 지침 파일의 검사 명령 {ver['check_lines_in_instructions']}줄 · "
         f"테스트 폴더·파일: {'있음' if ver['tests_present'] else '없음'}"),
        ("기록",
         f"세션 기록(자동) {rec['sessions']}개 · 텔레메트리 설정: {', '.join(rec['telemetry_env_names']) or '없음'}"),
    ]
    lines = [
        "이 폴더에서 Claude Code를 열 때 함께 실리는 것 (설정 파일로 센 추정. 실제는 세션 안의 /context, /memory로 확인)",
        f"시작 폴더가 git 저장소 안: {'예' if inv['repo_root'] else '아니오'}",
        "",
        "| 책임 | 찾은 것 |",
        "|---|---|",
    ]
    lines += [f"| {name} | {text} |" for name, text in rows]
    if inv["other_hooks"]:
        lines.append(f"\n그 밖의 hook: {describe_hooks(inv['other_hooks'])}")
    if reveal:
        lines += ["", "[이름] 지침 파일:"]
        lines += [f"  - {f['where']}: {f['path']}" for f in ins["files"]] or ["  - 없음"]
        lines += [f"  - (가져옴) {path}" for path in ins["imported"]]
        lines.append("[이름] Skill: " + (", ".join(f"{s['name']}({s['where']})" for s in ins["skills"]) or "없음"))
        lines.append("[이름] MCP 서버: 프로젝트 " + (", ".join(tools["mcp_project"]) or "-") + " / 이 폴더 "
                     + (", ".join(tools["mcp_local"]) or "-") + " / 사용자 " + (", ".join(tools["mcp_user"]) or "-"))
    else:
        lines += ["", "파일 경로·Skill·MCP 이름은 가렸습니다. 보려면 Claude Code 밖의 일반 터미널에서 --reveal."]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="폴더별로 Claude Code에 함께 실리는 지침·도구·제어·상태·검증·기록을 센다 (모델 호출 없음).")
    parser.add_argument("folder", help="Claude Code를 여는 폴더")
    parser.add_argument("--reveal", action="store_true", help="파일 경로와 이름을 보여 준다 (일반 터미널에서만)")
    parser.add_argument("--json", action="store_true", help="표 대신 JSON (이름 포함이므로 --reveal과 같은 제한)")
    parser.add_argument("--allow-in-claude", action="store_true", help="Claude Code 안에서도 --reveal/--json을 허용한다(권하지 않음)")
    args = parser.parse_args(argv)

    if (args.reveal or args.json) and inside_claude_code() and not args.allow_in_claude:
        print("[거절] --reveal과 --json은 파일 경로와 이름을 출력합니다. Claude Code 안에서 치면 그 출력이 모델로 전송됩니다. "
              "Claude Code 밖의 일반 터미널에서 다시 실행하세요.")
        return 2
    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        print(f"[확인 불가] 폴더가 없습니다: {folder}")
        return 2
    inv = inventory(folder)
    print(json.dumps(inv, ensure_ascii=False, indent=2) if args.json else render(inv, args.reveal))
    return 0


if __name__ == "__main__":
    sys.exit(main())
