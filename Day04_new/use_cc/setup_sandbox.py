"""실험 대상 폴더를 만든다: Claude Code가 강사 사례 MCP 서버와 Skill만 가지고 시작하는 폴더.

사용법 (Day04_new/use_cc 폴더에서. 다른 폴더에서는 이 파일의 경로를 맞춰 준다):

    uv run python setup_sandbox.py ~/day04-sandbox
    uv run python setup_sandbox.py ~/day04-sandbox --gate off

만드는 것:

    <대상 폴더>/
      .mcp.json                                   강사 사례 MCP 서버(cap_lab/server/server.py)를 stdio로 띄우는 설정
      .claude/skills/requirements-interview/SKILL.md   강사 사례 Skill의 사본
      work/                                       서버의 SQLite 파일이 생기는 곳
      evidence/                                   서버가 근거 파일을 남기는 곳

왜 저장소 밖이어야 하는가:
    Claude Code는 시작한 폴더와 그 위의 모든 폴더에서 CLAUDE.md를 읽고, 저장소 루트까지 올라가며 `.claude/skills`를 읽는다
    (https://code.claude.com/docs/en/memory.md, https://code.claude.com/docs/en/skills.md).
    실험 폴더를 이 저장소 안에 두면 루트와 Day04_new의 CLAUDE.md(조교 규칙), 루트 `.claude/skills`의 Skill(25개 폴더), 저장소의 auto-memory가
    실험 대상 세션에 함께 실린다. 그러면 무엇이 그 세션의 능력을 만들었는지 가를 수 없다. 그래서 저장소 안의 경로는 거절한다. git 정보가 없어도(zip으로 받은 경우) 이 과정 폴더 안이면 거절한다.

이 스크립트는 모델도 Jev도 부르지 않는다. 키 값은 어떤 파일에도 쓰지 않는다.
서버는 실행될 때 Day04_new/.env에서 판정기 키를 직접 읽는다(cap_lab/settings.py:11의 ROOT, cap_lab/server/server.py:217).
"""

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

# 이 파일은 Day04_new/use_cc/setup_sandbox.py 에 있다. 두 단계 위가 Day04_new 다.
DAY04_DIR = Path(__file__).resolve().parents[1]
# 이 과정 저장소의 루트. Day04_new의 바로 위 폴더다.
COURSE_DIR = DAY04_DIR.parent
SERVER_SCRIPT_RELATIVE = "cap_lab/server/server.py"
SKILL_SOURCE = DAY04_DIR / "skills" / "requirements-interview" / "SKILL.md"
# Claude Code 안에서 보일 서버 이름. 도구 이름이 mcp__requirements__start_interview 처럼 된다.
SERVER_NAME = "requirements"

# 판정기 키를 확인하려고 cap_lab을 import한다. 모델이나 Jev를 부르지는 않는다.
sys.path.insert(0, str(DAY04_DIR))


def repository_root(path: Path) -> Path | None:
    """path가 들어 있는 git 저장소의 루트. 저장소 밖이면 None."""
    probe = path if path.is_dir() else path.parent
    while not probe.exists():
        probe = probe.parent
    completed = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return Path(completed.stdout.strip()).resolve()


def usage_example() -> str:
    """거절 메시지에 넣을 예시 명령. 지금 폴더에서 그대로 칠 수 있는 경로로 보여 준다."""
    script = Path(__file__).resolve()
    try:
        shown = script.relative_to(Path.cwd().resolve())
    except ValueError:
        shown = script
    return f"uv run python {shlex.quote(str(shown))} ~/day04-sandbox"


def check_outside_repository(target: Path) -> None:
    """대상 폴더가 이 과정의 저장소 안이면 멈춘다. 다른 git 저장소 안인 것도 같은 이유로 거절한다.

    이 과정 폴더 안인지는 경로로 먼저 본다. git 정보가 없는 사본(zip으로 받은 경우)에서도 거절하기 위해서다.
    """
    if target.is_relative_to(COURSE_DIR):
        reason = "이 과정의 저장소 안입니다"
    else:
        target_repository = repository_root(target)
        if target_repository is None:
            return
        reason = f"다른 git 저장소({target_repository}) 안입니다"
    raise SystemExit(
        f"[멈춤] {target} 는 {reason}.\n"
        "Claude Code는 시작한 폴더 위의 CLAUDE.md와 저장소 루트까지의 .claude/skills를 함께 읽습니다.\n"
        "그러면 실험 대상 세션에 이 과정의 조교 규칙과 다른 Skill이 섞입니다. 저장소 밖의 경로를 주세요.\n"
        f"예: {usage_example()}"
    )


def check_empty(target: Path) -> None:
    """이미 무언가 있는 폴더에는 만들지 않는다. 지난 실험의 근거 파일을 덮어쓰지 않기 위해서다."""
    if target.exists() and any(target.iterdir()):
        raise SystemExit(
            f"[멈춤] {target} 에 이미 파일이 있습니다. 지난 실험의 기록을 덮어쓰지 않으려고 멈췄습니다.\n"
            "새 경로를 주거나, 그 폴더가 필요 없다는 것을 직접 확인한 뒤 옮기세요."
        )


def check_decision_key() -> None:
    """--gate h1이면 서버가 판정 모델(Jev)을 부른다. 서버와 같은 함수로 판정기를 만들 수 있는지만 본다.

    판정기를 만들 수 없으면 서버는 완료 기준을 하나도 기록하지 않는다(fail-closed, cap_lab/server/server.py:217).
    그러면 인터뷰가 완료 기준에서 멈추므로, 폴더를 만들기 전에 알려 준다. 키 값은 출력하지 않는다.
    """
    from cap_lab.decisions import make_decider
    from cap_lab.settings import load_settings

    try:
        make_decider(load_settings())
    except RuntimeError as error:
        raise SystemExit(
            f"[멈춤] --gate h1에 필요한 Decision API 판정기를 만들 수 없습니다: {error}\n"
            "Day04_new/.env를 직접 채운 뒤 다시 실행하거나, 판정 게이트 없이 해 보려면 --gate off를 붙이세요."
        ) from error


def mcp_config(target: Path, gate: str) -> dict:
    """실험 폴더의 .mcp.json 내용. 서버는 uv로 Day04_new 폴더에서 띄우고, 상태 파일은 실험 폴더 안에 둔다.

    uv는 절대 경로로 적는다. Claude Code를 터미널이 아닌 곳에서 열어 PATH가 짧아도 서버가 뜨게 하려는 것이다.
    """
    uv_executable = shutil.which("uv") or "uv"
    server_arguments = [
        "run", "--directory", str(DAY04_DIR),
        "python", SERVER_SCRIPT_RELATIVE,
        "--db", str(target / "work" / "sessions.sqlite3"),
        "--evidence-dir", str(target / "evidence"),
        "--gate", gate,
    ]
    return {"mcpServers": {SERVER_NAME: {"command": uv_executable, "args": server_arguments}}}


def create_sandbox(target: Path, gate: str) -> list[Path]:
    """폴더를 만들고 만든 파일 목록을 돌려준다. 검사는 부르는 쪽(main)에서 먼저 한다."""
    skill_folder = target / ".claude" / "skills" / "requirements-interview"
    for folder in (skill_folder, target / "work", target / "evidence"):
        folder.mkdir(parents=True, exist_ok=True)

    mcp_path = target / ".mcp.json"
    mcp_path.write_text(json.dumps(mcp_config(target, gate), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    skill_path = skill_folder / "SKILL.md"
    shutil.copyfile(SKILL_SOURCE, skill_path)
    return [mcp_path, skill_path, target / "work", target / "evidence"]


def next_steps(target: Path) -> str:
    """두 터미널에서 할 일을 그대로 출력한다."""
    return "\n".join([
        "",
        "다음 순서로 진행합니다.",
        "",
        "  터미널 2 (실험 대상 세션):",
        f"    cd {shlex.quote(str(target))}",
        "    claude",
        "    처음 열면 확인 화면이 두 번 나옵니다. 두 번 모두 기본 선택이 원하는 것이 아니므로 Enter만 누르지 마세요.",
        "      폴더 신뢰: 기본 'No, exit' -> 화살표로 'Yes, I trust this folder'",
        "      MCP 서버: 기본 'Continue without using this MCP server' -> 화살표로 'Use this MCP server'",
        "    서버 없이 시작했다면 /exit 뒤 claude mcp reset-project-choices 를 실행하고 다시 엽니다.",
        "    그다음 /mcp 로 requirements 서버가 '7 tools'로 연결됐는지 봅니다.",
        "",
        "  터미널 1 (조교 세션):",
        f"    cd {shlex.quote(str(DAY04_DIR / 'use_cc'))}",
        "    claude",
        "    'External imports'를 묻으면 기본 'No' 대신 'Yes, allow external imports'를 고릅니다.",
        "    Claude Code가 열린 뒤에 셸 명령을 치려면 앞에 ! 를 붙입니다. 예: !ls notes",
        "    /mission part1 로 미션 카드를 엽니다.",
        f"    조교가 실험 폴더의 근거 파일을 읽어야 하면 이 경로를 알려 주세요: {target}",
        "    (--add-dir로 실험 폴더를 붙이지 않습니다. 붙이면 그 폴더의 Skill이 조교 세션에도 실릴 수 있습니다.)",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Claude Code 실험 대상 폴더를 저장소 밖에 만든다.")
    parser.add_argument("target", type=Path, help="만들 폴더. 저장소 밖이어야 하고 비어 있어야 한다")
    parser.add_argument(
        "--gate",
        choices=("h1", "off"),
        default="h1",
        help="h1(기본): 완료 기준을 판정 모델(Jev)로 검사하고 모호하면 사용자에게 직접 묻는다. off: 검사하지 않는다",
    )
    arguments = parser.parse_args()

    # 1. 경로를 절대 경로로 바꾼다. ~ 도 풀어 준다.
    target = arguments.target.expanduser().resolve()

    # 2. 만들기 전에 검사한다. 하나라도 걸리면 아무것도 만들지 않는다.
    check_outside_repository(target)
    check_empty(target)
    if arguments.gate == "h1":
        check_decision_key()

    # 3. 만든다.
    created = create_sandbox(target, arguments.gate)

    # 4. 무엇을 만들었는지와 다음 할 일을 보여 준다.
    print(f"[완료] 실험 대상 폴더를 만들었습니다: {target} (게이트: {arguments.gate})")
    for path in created:
        print(f"  - {path.relative_to(target)}")
    print(next_steps(target))


if __name__ == "__main__":
    main()
