"""PreToolUse hook: 이미 만든 커밋의 기록을 고치는 git 명령을 막는다.

Claude Code가 도구 호출 정보를 JSON으로 stdin에 넣어 준다. 이 hook은 tool_input.command만 본다
(근거: docs/sources/claude_code/03_control.md의 C19). 막을 때는 종료 코드 2로 끝내고,
stderr의 문장이 Claude에게 전달된다(C15).

막는 대상은 `git commit --amend`(인자 위치와 무관), `git rebase`, `git reset`이다.
`cd x && git commit --amend` 같은 복합 명령도 잡도록 문자열 어디에 있든 찾는다.
git과 하위 명령 사이의 전역 옵션(-c <k=v>, -C <dir>, --git-dir, --work-tree, --namespace,
--no-pager, -P, -p, --paginate, --bare)은 건너뛰고 하위 명령을 본다.
작은따옴표, 큰따옴표, 백틱 바로 뒤의 git도 명령 시작으로 본다(`sh -c 'git commit --amend'`).

이 hook이 못 막는 것(한계):
- git alias: `git ci --amend`처럼 alias 뒤에 숨은 재작성. alias 이름은 설정에 따라 달라 확인 필요.
- git을 부르는 스크립트나 Makefile 안의 재작성. 명령 문자열에는 스크립트 이름만 보인다.
- git 말고 다른 도구(IDE, 다른 CLI)나 Bash 도구가 아닌 경로로 하는 재작성.
- 따옴표 안의 글자도 명령으로 보므로 `echo "git reset"` 같은 출력 명령을 잘못 막을 수 있다.
"""

import json
import re
import sys

# 명령 시작이거나 ; & | ( 따옴표 백틱 공백 뒤에 오는 git만 본다. 다른 단어 속 "git"(예: digit)은 제외한다.
# git 뒤의 전역 옵션은 건너뛴다. 옵션 값(-c의 k=v, -C의 경로 등)은 공백 없는 한 단어로 본다.
GLOBAL_OPTION = r"(?:-[cC]\s+\S+|--(?:git-dir|work-tree|namespace)(?:=\S+|\s+\S+)|--no-pager|--paginate|--bare|-[Pp])\s+"
GIT = r"""(?:^|[;&|('"`\s])git\s+(?:""" + GLOBAL_OPTION + r")*"
REWRITES = (
    re.compile(GIT + r"commit\b[^;&|]*\s--amend\b"),
    re.compile(GIT + r"rebase\b"),
    re.compile(GIT + r"reset\b"),
)
MESSAGE = (
    "이미 만든 커밋은 고치지 않는다 (이 실험 폴더의 hook). "
    "기록이 틀렸으면 새 커밋으로 바로잡으세요.\n"
)


def main():
    # 입력을 읽지 못하면 막지 않는다(fail-open). 이 선택의 위험은 미션 카드에서 다룬다.
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    tool_input = event.get("tool_input") if isinstance(event, dict) else None
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    if not isinstance(command, str):
        return 0
    if any(pattern.search(command) for pattern in REWRITES):
        sys.stderr.write(MESSAGE)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
