"""SessionStart hook: 세션이 시작될 때 progress.md와 최근 git 기록을 맥락으로 넣는다.

SessionStart hook의 일반 텍스트 stdout은 Claude의 맥락에 들어간다(docs/sources/claude_code/03_control.md의 C20).
그래서 이 파일은 stderr가 아니라 stdout으로 출력한다. 이 hook은 모델을 막지 못하고 맥락만 더하므로(C20)
항상 종료 코드 0으로 끝난다. 종료 코드 2를 써도 사용자에게만 보인다(C15).

넣는 내용: 짧은 제목, 작업 폴더의 progress.md 앞 40줄, git 저장소이면 `git log --oneline -5`.
작업 폴더: 입력의 cwd(C19) -> 환경 변수 CLAUDE_PROJECT_DIR -> 현재 폴더 순서다.
다른 파일을 읽히려면 PROGRESS_FILE만 바꾼다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROGRESS_FILE = "progress.md"
MAX_PROGRESS_LINES = 40
GIT_LOG_COMMAND = ["git", "log", "--oneline", "-5"]
TIMEOUT_SECONDS = 10
HEADER = "== 세션 시작: 이어서 할 작업 상태 =="


def read_folder():
    """입력 JSON의 cwd를 쓰고, 입력이 비었거나 JSON이 아니면 환경 변수와 현재 폴더로 간다."""
    try:
        event = json.load(sys.stdin)
    except ValueError:
        event = None
    cwd = event.get("cwd") if isinstance(event, dict) else None
    return Path(cwd or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def progress_lines(folder):
    path = folder / PROGRESS_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [f"({PROGRESS_FILE}가 없습니다: {path})"]
    return text.splitlines()[:MAX_PROGRESS_LINES]


def git_log_lines(folder):
    """git 저장소가 아니거나 git이 없으면 빈 목록이다."""
    try:
        proc = subprocess.run(
            GIT_LOG_COMMAND, cwd=folder, capture_output=True, text=True, timeout=TIMEOUT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return proc.stdout.splitlines() if proc.returncode == 0 else []


def main():
    folder = read_folder()
    print(HEADER)
    print("\n".join(progress_lines(folder)))
    commits = git_log_lines(folder)
    if commits:
        print("\n최근 git 기록:")
        print("\n".join(commits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
