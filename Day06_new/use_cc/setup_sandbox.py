"""Part 3·5 실험 폴더를 만든다: 회의실 예약 서비스와 "이전 두 세션"의 git 기록. 모델을 부르지 않는다.

만들어지는 폴더는 이전 세션들이 남긴 상태를 그대로 재현한다.

    커밋 1  초기 설정: 작업 규칙(CLAUDE.md), 요구사항 목록(feature_list.json), 검사(test_reservation.py)
    커밋 2  R1·R2·R7 코드 (사용자마다 파일 하나에 저장)
    커밋 3  기록: R1·R2·R7 통과 (verified_at = 커밋 2)
    커밋 4  R3 코드 (include_others 옵션 추가)
    커밋 5  기록: R3 완료 (verified_at = 커밋 4) ← 실제로는 R3 검사가 실패한다

커밋 작성자와 시각을 고정하므로 누가 만들어도 커밋 해시가 같다. 강사 예시와 수강생 폴더의 해시를 그대로 비교할 수 있다.

사용법 (Day06_new/use_cc 폴더에서):

    uv run python setup_sandbox.py ~/day06-p3

저장소 안의 경로는 거절한다. Claude Code는 시작한 폴더 위의 CLAUDE.md와 저장소의 .claude/skills를 함께 읽기 때문에,
실험 폴더가 저장소 안에 있으면 이 과정의 조교 규칙이 실험 대상 세션에 섞인다.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "sandbox_template"

# feature_list.json의 요구사항. 회의실 예약 사례(Day06 이론자료 슬라이드 20~21)의 R1~R7을 이 예제의 검사 이름에 연결했다.
REQUIREMENTS = [
    ("R1", "회의실과 시간을 선택해 예약", "목록에 정확한 시간과 회의실이 표시된다", "test_R1_reserved_item_is_listed"),
    ("R2", "예약 후 새로고침(새 서비스 객체)", "등록한 예약이 유지된다", "test_R2_reservation_kept_after_reload"),
    ("R3", "독립된 사용자 B가 조회", "A가 등록한 같은 예약이 표시된다", "test_R3_other_user_sees_reservation"),
    ("R4", "기존 10:00-11:00, 신규 10:30-11:30", "겹치므로 거절하고 중복 데이터도 없다", "test_R4_overlap_rejected"),
    ("R5", "기존 10:00-11:00, 신규 11:00-12:00", "바로 이어지는 예약은 허용한다", "test_R5_back_to_back_allowed"),
    ("R6", "종료 시각이 시작 시각과 같거나 앞섬", "저장하지 않고 이유를 알린다", "test_R6_invalid_time_rejected"),
    ("R7", "서버 재시작(새 프로세스) 뒤 같은 예약 조회", "저장된 예약을 다시 확인할 수 있다", "test_R7_kept_after_restart"),
]

PROGRESS_0 = """# 진행 기록

## 세션 0 (2026-11-02 09:00) 초기 설정
- 한 일: 작업 규칙(CLAUDE.md), 요구사항 목록(feature_list.json, R1~R7), 검사(test_reservation.py)를 만들었다.
- 다음: R1부터 구현.
"""

PROGRESS_1 = """
## 세션 1 (2026-11-02 09:45)
- 한 일: 예약 저장과 조회(reservation.py)를 구현했다. 사용자마다 파일 하나에 저장한다.
- 실행한 검사: `python3 -m unittest -v` → R1·R2·R5·R7 통과, R3·R4·R6 실패.
  R5는 겹침 규칙(R4)을 만들 때 같이 확인하기로 하고 통과로 표시하지 않았다.
- 확인하지 못한 것: 없음.
- 다음: R3 사용자 간 예약 공유.
"""

PROGRESS_2 = """
## 세션 2 (2026-11-03 14:25)
- 한 일: R3를 구현했다. `list`에 다른 사용자의 예약도 보여 주는 `include_others` 옵션을 추가했다.
- 실행한 검사: 직접 확인함.
- 상태: R1~R3 완료.
- 다음: R4 겹치는 예약 거절.
"""

GITIGNORE = "__pycache__/\n*.pyc\ndata/\n"

# 커밋 작성자와 시각을 고정한다(해시를 같게 만들기 위해).
AUTHOR = ("Day06 sandbox", "sandbox@example.invalid")
COMMIT_TIMES = [
    "2026-11-02T09:00:00+09:00",
    "2026-11-02T09:40:00+09:00",
    "2026-11-02T09:45:00+09:00",
    "2026-11-03T14:20:00+09:00",
    "2026-11-03T14:25:00+09:00",
]


def find_repo_root():
    """이 스크립트가 들어 있는 git 저장소의 루트. git이 없으면 폴더 구조로 추정한다."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(HERE),
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(out.stdout.strip()).resolve()
    except (OSError, subprocess.CalledProcessError):
        return HERE.parents[1].resolve()


def is_inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def feature_list(verified):
    """verified: {요구사항 ID: 커밋 해시}. 여기에 있는 요구사항만 passes=true로 적는다."""
    items = []
    for req_id, action, criterion, test in REQUIREMENTS:
        items.append(
            {
                "id": req_id,
                "action": action,
                "criterion": criterion,
                "test": test,
                "passes": req_id in verified,
                "verified_at": verified.get(req_id),
            }
        )
    return json.dumps(items, ensure_ascii=False, indent=2) + "\n"


def git(target, *args, when=None):
    env = dict(os.environ)
    if when:
        env.update(
            GIT_AUTHOR_NAME=AUTHOR[0],
            GIT_AUTHOR_EMAIL=AUTHOR[1],
            GIT_COMMITTER_NAME=AUTHOR[0],
            GIT_COMMITTER_EMAIL=AUTHOR[1],
            GIT_AUTHOR_DATE=when,
            GIT_COMMITTER_DATE=when,
        )
    result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=str(target),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout.strip()


def commit(target, message, when):
    git(target, "add", "-A")
    git(target, "commit", "-q", "-m", message, when=when)
    return git(target, "rev-parse", "--short=7", "HEAD")


def write(target, relative, text):
    path = target / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(target):
    """실험 폴더에 다섯 커밋을 만든다. 각 커밋의 짧은 해시 목록을 돌려준다."""
    git(target, "init", "-q")
    git(target, "checkout", "-q", "-b", "main")
    hashes = []

    # 커밋 1: 초기 설정
    shutil.copy(TEMPLATE / "CLAUDE.md", target / "CLAUDE.md")
    shutil.copy(TEMPLATE / "test_reservation.py", target / "test_reservation.py")
    write(target, ".claude/settings.json", (TEMPLATE / "settings.json").read_text(encoding="utf-8"))
    write(target, ".claude/hooks/protect_tests.py", (TEMPLATE / "protect_tests.py").read_text(encoding="utf-8"))
    write(target, ".gitignore", GITIGNORE)
    write(target, "feature_list.json", feature_list({}))
    write(target, "progress.md", PROGRESS_0)
    hashes.append(commit(target, "초기 설정: 작업 규칙, 요구사항 목록(R1~R7), 검사", COMMIT_TIMES[0]))

    # 커밋 2: R1·R2·R7 코드
    shutil.copy(TEMPLATE / "reservation_v1.py", target / "reservation.py")
    hashes.append(commit(target, "R1·R2·R7: 예약 저장과 조회", COMMIT_TIMES[1]))
    code_v1 = hashes[-1]

    # 커밋 3: 기록 (R1·R2·R7 통과, verified_at = 커밋 2)
    write(target, "feature_list.json", feature_list({"R1": code_v1, "R2": code_v1, "R7": code_v1}))
    write(target, "progress.md", PROGRESS_0 + PROGRESS_1)
    hashes.append(commit(target, "기록: R1·R2·R7 통과", COMMIT_TIMES[2]))

    # 커밋 4: R3 코드 (include_others 옵션)
    shutil.copy(TEMPLATE / "reservation_v2.py", target / "reservation.py")
    hashes.append(commit(target, "R3: 다른 사용자 예약 조회 옵션 추가", COMMIT_TIMES[3]))
    code_v2 = hashes[-1]

    # 커밋 5: 기록 (R3 완료, verified_at = 커밋 4)
    verified = {"R1": code_v1, "R2": code_v1, "R7": code_v1, "R3": code_v2}
    write(target, "feature_list.json", feature_list(verified))
    write(target, "progress.md", PROGRESS_0 + PROGRESS_1 + PROGRESS_2)
    hashes.append(commit(target, "기록: R3 완료", COMMIT_TIMES[4]))
    return hashes


def main(argv=None):
    parser = argparse.ArgumentParser(description="Part 3·5 실험 폴더(회의실 예약 서비스)를 저장소 밖에 만든다.")
    parser.add_argument("target", help="만들 폴더. 저장소 밖의 새 경로(예: ~/day06-p3)")
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser().resolve()
    repo_root = find_repo_root()
    if is_inside(target, repo_root):
        print(f"[거절] {target} 는 저장소({repo_root}) 안입니다. 저장소 밖의 새 경로를 주세요. 예: ~/day06-p3")
        return 2
    if target.exists() and any(target.iterdir()):
        print(f"[거절] {target} 가 이미 있고 비어 있지 않습니다. 새 경로를 주거나 그 폴더를 직접 지운 뒤 다시 실행하세요.")
        return 2
    if shutil.which("git") is None:
        print("[거절] git이 없습니다. git을 설치한 뒤 다시 실행하세요.")
        return 2

    target.mkdir(parents=True, exist_ok=True)
    hashes = build(target)

    print(f"실험 폴더를 만들었습니다: {target}")
    print("git 기록 (오래된 것부터):")
    labels = ["초기 설정", "R1·R2·R7 코드", "기록: R1·R2·R7 통과", "R3 코드", "기록: R3 완료"]
    for short_hash, label in zip(hashes, labels):
        print(f"  {short_hash}  {label}")
    print()
    print("다음 단계:")
    print(f"  터미널 2:  cd {target} && claude --permission-mode acceptEdits")
    print(f"  터미널 1:  !uv run python tools/check_evidence.py {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
