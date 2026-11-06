"""Stop hook 래퍼: 완료 Gate(tools/check_evidence.py)가 통과하지 않으면 Claude가 멈추지 못하게 한다.

왜 래퍼가 필요한가. check_evidence.py의 종료 코드는 0=통과, 1=불통과, 2=확인 불가다.
Claude Code의 hook은 종료 코드 2만 "멈추지 말고 계속 일하라"로 받아들이고, 1은 막지 않는 오류로 넘어간다.
그래서 검사기의 코드를 그대로 돌려주면 불통과(1)는 막지 못하고, 확인 불가(2)는 오히려 막아 버린다.
이 래퍼가 코드를 바꿔 준다: 불통과 -> 2(막음), 통과·확인 불가 -> 0.

입력: 표준입력의 JSON. stop_hook_active가 true면 이미 hook 때문에 이어 가는 중이므로 다시 막지 않는다(대장 C16).
입력이 비었거나 JSON이 아니면 폴더를 알 수 없으므로 확인하지 못했다고 알리고 막지 않는다.
검사할 폴더(입력의 cwd는 대장 C19): 입력의 cwd -> 환경 변수 CLAUDE_PROJECT_DIR -> 현재 폴더 순서다.
검사기 경로는 이 파일 위치에서 정하므로, 절대 경로로 설정하면 저장소 밖의 실험 폴더에서도 동작한다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "tools" / "check_evidence.py"
FIRST_LINE = "완료 Gate 불통과: 아직 끝나지 않았습니다."
MAX_REASONS = 5
UNCHECKED_NOTICE = "완료 Gate를 확인하지 못해 막지 않습니다."


def read_input():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def gate_reasons(output):
    """검사기 출력에서 '완료 Gate: 불통과' 아래의 '  - ' 줄만 모은다."""
    lines = output.splitlines()
    if "완료 Gate: 불통과" not in lines:
        return []
    after = lines[lines.index("완료 Gate: 불통과") + 1:]
    return [line.strip() for line in after if line.startswith("  - ")]


def main():
    data = read_input()
    if data is None:
        print(UNCHECKED_NOTICE, file=sys.stderr)
        return 0
    if data.get("stop_hook_active") is True:
        return 0
    folder = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    proc = subprocess.run(
        [sys.executable, str(CHECKER), str(folder)], capture_output=True, text=True
    )
    if proc.returncode == 1:
        print(FIRST_LINE, file=sys.stderr)
        for reason in gate_reasons(proc.stdout)[:MAX_REASONS]:
            print(reason, file=sys.stderr)
        return 2
    if proc.returncode == 2:
        print(UNCHECKED_NOTICE, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
