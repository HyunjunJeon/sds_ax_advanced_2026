"""PreToolUse hook: 요구사항 검사 파일(test_reservation.py)을 고치려는 도구 호출을 막는다.

Claude Code가 도구 호출 정보를 JSON으로 stdin에 넣어 준다. 이 hook은 tool_input.file_path만 본다.
막을 때는 종료 코드 2로 끝내고, stderr의 문장이 Claude에게 전달된다.
"""

import json
import sys
from pathlib import Path

PROTECTED = {"test_reservation.py"}


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool_input = event.get("tool_input") or {}
    file_path = str(tool_input.get("file_path") or "")
    if file_path and Path(file_path).name in PROTECTED:
        sys.stderr.write(
            "test_reservation.py는 요구사항 검사라 이 세션에서 고칠 수 없습니다(CLAUDE.md). "
            "검사가 틀렸다고 생각하면 사람에게 이유를 설명하고 물어보세요.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
