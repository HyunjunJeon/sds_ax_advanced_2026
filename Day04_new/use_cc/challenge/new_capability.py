"""내 plugin을 만든다: 예시 plugin(example-tasks)을 복사해 이름을 바꾸고, CAPABILITY.md를 빈 틀로 바꾼다.

사용법 (Day04_new/use_cc 폴더에서):

    uv run python challenge/new_capability.py incident-triage

만드는 곳은 challenge/work/<이름>/ 이다(git에 올라가지 않는다). 예시와 깊이가 같은 폴더라서 .mcp.json의
상대 경로(${CLAUDE_PLUGIN_ROOT}/../../../../../.venv/bin/python)가 그대로 이 저장소의 파이썬을 가리킨다.

복사한 뒤 서버(server/server.py), Skill(skills/), 계약 사례(checks/), eval 사례(evals/)는 아직 예시(할 일 보관함) 내용이다.
Claude와 함께 내 능력으로 바꾼다. 이 스크립트는 모델을 부르지 않는다.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

CHALLENGE_DIR = Path(__file__).resolve().parent
EXAMPLE = CHALLENGE_DIR / "examples" / "example-tasks"
BLANK_CAPABILITY = CHALLENGE_DIR / "blank" / "CAPABILITY.md"
WORK_DIR = CHALLENGE_DIR / "work"
EXAMPLE_NAME = "example-tasks"
NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
IGNORED = shutil.ignore_patterns("results", "__pycache__", ".capability-data", "*.tmp")


def create(name: str) -> Path:
    """예시를 복사하고 이름을 바꾼다. 만든 폴더를 돌려준다."""
    if not NAME_PATTERN.fullmatch(name):
        raise SystemExit(f"[멈춤] 이름은 소문자, 숫자, -로만 씁니다(예: incident-triage). 지금: {name!r}")
    if name == EXAMPLE_NAME:
        raise SystemExit(f"[멈춤] {EXAMPLE_NAME}는 예시의 이름입니다. 다른 이름을 고르세요.")
    target = WORK_DIR / name
    if target.exists():
        raise SystemExit(f"[멈춤] {target} 가 이미 있습니다. 지난 작업을 덮어쓰지 않으려고 멈췄습니다.")

    # 1. 예시를 통째로 복사한다(지난 실행 결과와 상태 파일은 빼고).
    shutil.copytree(EXAMPLE, target, ignore=IGNORED)

    # 2. plugin 이름을 바꾼다. eval 판정기의 도구 이름(mcp__plugin_<plugin>_...)에도 들어 있으므로 함께 바꾼다.
    for path in [target / ".claude-plugin" / "plugin.json", target / "server" / "server.py",
                 *sorted((target / "evals").rglob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace(EXAMPLE_NAME, name), encoding="utf-8")

    # 3. CAPABILITY.md는 예시 내용이 아니라 빈 틀에서 시작한다. 이 파일은 수강생이 자기 말로 쓴다.
    shutil.copyfile(BLANK_CAPABILITY, target / "CAPABILITY.md")
    return target


def next_steps(target: Path) -> str:
    relative = target.relative_to(CHALLENGE_DIR.parent)
    return "\n".join([
        "",
        "다음 순서로 진행합니다. (모든 명령은 Day04_new/use_cc 에서. Claude Code 화면 안에서는 앞에 ! 를 붙입니다.)",
        "",
        "  1. 이 세션(조교 세션)에서 Claude와 함께 예시 내용을 내 능력으로 바꿉니다.",
        f"     바꿀 것: {relative}/server/server.py, skills/, checks/contract.jsonl, evals/",
        "     정하는 것은 내가 합니다: 무엇을 만들지, 도구를 어떻게 나눌지, 판단을 어디에 둘지, 사례의 기대 동작.",
        "",
        "  2. 모양을 검사합니다 (모델 호출 없음):",
        f"     uv run python tools/check_capability.py {relative}",
        "",
        "  3. 써 봅니다. 저장소 밖의 빈 폴더에서 plugin만 불러 Claude Code를 엽니다(다른 터미널):",
        f"     mkdir -p ~/cap-trial-{target.name} && cd ~/cap-trial-{target.name} && claude --plugin-dir {target}",
        "",
        "  4. 정말 되는지 확인합니다 (유료, 실행 직전에 규모를 알려 줍니다):",
        f"     uv run python tools/run_eval.py {relative} --runs 1",
        "",
        f"  5. 결과와 결정을 {relative}/CAPABILITY.md 에 내 말로 씁니다.",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="예시를 복사해 내 Capability Challenge plugin을 만든다 (모델 호출 없음)")
    parser.add_argument("name", help="plugin 이름. 소문자, 숫자, -만 (예: incident-triage)")
    arguments = parser.parse_args()
    target = create(arguments.name)
    print(f"[완료] 내 plugin을 만들었습니다: {target}")
    print(next_steps(target))


if __name__ == "__main__":
    sys.exit(main())
