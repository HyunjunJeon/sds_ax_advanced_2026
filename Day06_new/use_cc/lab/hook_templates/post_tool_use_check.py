"""PostToolUse hook: 파일을 고친 직후 검사 명령을 돌리고, 실패하면 Claude에게 알린다.

Claude Code가 도구 호출 정보를 JSON으로 stdin에 넣어 준다. 이 hook은 tool_name이 Edit, Write, MultiEdit일
때만 CHECK_COMMAND를 돌린다(입력 필드는 docs/sources/claude_code/03_control.md의 C19).
PostToolUse는 도구가 성공한 뒤에 돈다(C21). 그래서 종료 코드 2는 편집을 되돌리지 못하고,
stderr의 문장을 Claude에게 보여 줄 뿐이다(C15, C21). Claude는 그 문장을 읽고 같은 턴에서 고친다.

검사를 돌릴 폴더: 입력의 cwd -> 환경 변수 CLAUDE_PROJECT_DIR -> 현재 폴더 순서다.

내 실험 폴더에 맞게 바꿀 곳은 CHECK_COMMAND 하나다(예: ["python3", "-m", "pytest", "-q"]).

한계:
- Bash 명령이 파일을 고친 경우는 settings의 matcher(Edit|Write|MultiEdit)에 걸리지 않아 돌지 않는다(C14, C21).
- 검사가 TIMEOUT_SECONDS를 넘으면 실패로 본다.
"""

import json
import os
import subprocess
import sys

CHECK_COMMAND = ["python3", "-m", "unittest", "-q"]
EDIT_TOOLS = ("Edit", "Write", "MultiEdit")
TIMEOUT_SECONDS = 60
MAX_OUTPUT_LINES = 20
FIRST_LINE = "편집 뒤 검사가 실패했습니다. 아래 출력을 읽고 고쳐 주세요."


def run_check(folder):
    """검사 명령을 돌려 (통과 여부, 출력 줄 목록)을 돌려준다."""
    try:
        proc = subprocess.run(
            CHECK_COMMAND, cwd=folder, capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        return False, [f"검사가 {TIMEOUT_SECONDS}초 안에 끝나지 않았습니다."]
    except OSError as error:
        return False, [f"검사 명령을 시작하지 못했습니다: {error}"]
    return proc.returncode == 0, (proc.stdout + proc.stderr).splitlines()


def main():
    # 입력을 읽지 못하면 막지 않는다(fail-open). 이 선택의 위험은 미션 카드에서 다룬다.
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(event, dict) or event.get("tool_name") not in EDIT_TOOLS:
        return 0
    folder = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    passed, lines = run_check(folder)
    if passed:
        return 0
    print(FIRST_LINE, file=sys.stderr)
    for line in lines[-MAX_OUTPUT_LINES:]:
        print(line, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
