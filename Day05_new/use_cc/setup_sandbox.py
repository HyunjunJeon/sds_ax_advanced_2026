"""Day05 Claude Code 실습 폴더를 저장소 밖에 만든다. 수강생의 Claude Code는 이 폴더에서 코드를 만들고 실행한다.

사용법 (저장소 루트에서):

    uv run --no-sync python Day05_new/use_cc/setup_sandbox.py ~/day05-lab

만드는 것:

    <실습 폴더>/
      CLAUDE.md                     이 폴더에서 연 Claude Code가 읽는 규칙과 eval_lab 지도
      .claude/settings.json         권한 규칙: .env 읽기 금지, 고정 부품(eval_lab, data) 수정 금지, 저장소의 data 읽기 금지
      .claude/skills/mission/       /mission m1 처럼 부르는 조교 Skill
      lab                           이 폴더의 Python. 저장소 루트의 uv 환경을 쓰고 이 폴더를 import 경로 맨 앞에 둔다
      .env                          Day05_new/.env가 있으면 그 사본(값은 출력하지 않는다), 없으면 .env.example 사본
      eval_lab/                     Day05_new/eval_lab의 사본(고정 부품)
      data/                         dev 카드 9장, dev fixture, 정책 문서, 인터뷰, holdout ID 목록(내용 없음), 운영 사례 fixture
      ops.py                        Part 3b·4·5의 모의 운영 트래픽(이어서 처리 사례 포함)
      tools/                        모델을 부르지 않는 보기 도구
      missions/                     미션 카드 m0~m6
      reference/                    노트북 00~06의 참고본(Claude Code가 함수 사용법을 읽는 곳, 실행하지 않는다)
      work/ notes/                  Claude Code가 만든 스크립트와 수강생의 예측·답

왜 저장소 밖이어야 하는가:
    1. holdout 카드가 dev 카드와 같은 파일(Day05_new/data/scenarios.json)에 있다. Claude Code는 작업 폴더 전체를 읽을 수 있고,
       Read 거부 규칙은 Python 스크립트가 직접 여는 파일에는 걸리지 않는다
       (https://code.claude.com/docs/en/permissions.md, "Read and Edit deny rules apply to Claude's built-in file tools ...").
       그래서 holdout 내용을 아예 복사하지 않는 것이 주 방어다.
    2. Claude Code는 시작한 폴더 위의 CLAUDE.md와 저장소 루트까지의 .claude/skills를 함께 읽는다. 저장소 안이면 노트북 과정의 규칙과
       다른 Day의 Skill이 섞인다(Day04_new/use_cc/setup_sandbox.py와 같은 이유).

이 스크립트는 모델도 Jev도 Langfuse도 부르지 않는다. 키 값은 출력하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

USE_CC_DIR = Path(__file__).resolve().parent  # Day05_new/use_cc
DAY05_DIR = USE_CC_DIR.parent  # Day05_new
COURSE_DIR = DAY05_DIR.parent  # 저장소 루트(uv workspace)
TEMPLATE_DIR = USE_CC_DIR / "sandbox"
MISSIONS_DIR = USE_CC_DIR / "missions"

# 실습 폴더에 그대로 복사하는 데이터 파일. scenarios.json과 fixtures.json은 dev만 골라 따로 쓴다.
PLAIN_DATA_FILES = ("order_policy.md", "interview.md")


# ---------------------------------------------------------------- 검사

def repository_root(path: Path) -> Path | None:
    """path가 들어 있는 git 저장소의 루트. 저장소 밖이면 None."""
    probe = path if path.is_dir() else path.parent
    while not probe.exists():
        probe = probe.parent
    completed = subprocess.run(["git", "-C", str(probe), "rev-parse", "--show-toplevel"],
                               capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None
    return Path(completed.stdout.strip()).resolve()


def check_outside_repository(target: Path) -> None:
    """대상 폴더가 이 과정의 저장소 안이거나 다른 git 저장소 안이면 멈춘다."""
    if target.is_relative_to(COURSE_DIR):
        reason = "이 과정의 저장소 안입니다"
    else:
        other = repository_root(target)
        if other is None:
            return
        reason = f"다른 git 저장소({other}) 안입니다"
    raise SystemExit(
        f"[멈춤] {target} 는 {reason}.\n"
        "holdout 카드가 dev 카드와 같은 파일에 있고, Claude Code는 작업 폴더를 모두 읽을 수 있습니다.\n"
        "또 Claude Code는 시작한 폴더 위의 CLAUDE.md와 Skill을 함께 읽습니다. 저장소 밖의 새 경로를 주세요.\n"
        "예: uv run --no-sync python Day05_new/use_cc/setup_sandbox.py ~/day05-lab"
    )


def check_empty(target: Path) -> None:
    """이미 무언가 있는 폴더에는 만들지 않는다. 지난 실습의 기록을 덮어쓰지 않기 위해서다."""
    if target.exists() and any(target.iterdir()):
        raise SystemExit(
            f"[멈춤] {target} 에 이미 파일이 있습니다. 지난 실습의 기록을 덮어쓰지 않으려고 멈췄습니다.\n"
            "새 경로를 주세요. 그 폴더가 필요 없다는 것은 직접 확인한 뒤 옮기세요."
        )


# ---------------------------------------------------------------- 데이터 고르기

def dev_scenarios() -> list[dict]:
    """scenarios.json에서 dev 카드만 고른다. holdout 카드(승인·검수 대기 모두)는 내용을 옮기지 않는다."""
    cards = json.loads((DAY05_DIR / "data" / "scenarios.json").read_text(encoding="utf-8"))
    return [card for card in cards if card["metadata"]["split"] == "dev"]


def holdout_ids() -> list[str]:
    """holdout 카드의 scenario_id만. 06의 오염 검사가 ID로만 쓴다(Day05_new/06 셀 31과 같다)."""
    cards = json.loads((DAY05_DIR / "data" / "scenarios.json").read_text(encoding="utf-8"))
    return sorted(card["metadata"]["scenario_id"] for card in cards if card["metadata"]["split"] == "holdout")


def dev_fixtures(dev_cards: list[dict]) -> dict:
    """dev 카드가 쓰는 fixture만 고르고, 운영 사례 fixture(ops_fixtures.json)를 더한다.

    holdout 전용 fixture는 옮기지 않는다. 운영 사례 fixture의 이름이 이미 있는 이름과 겹치면 멈춘다.
    """
    every = json.loads((DAY05_DIR / "data" / "fixtures.json").read_text(encoding="utf-8"))
    used = {card["fixture_id"] for card in dev_cards}
    chosen = {name: every[name] for name in sorted(used)}
    extra = json.loads((USE_CC_DIR / "ops_fixtures.json").read_text(encoding="utf-8"))
    clash = sorted(set(extra) & set(every))
    if clash:
        raise SystemExit(f"[멈춤] 운영 사례 fixture 이름이 Day05_new/data/fixtures.json과 겹칩니다: {clash}")
    chosen.update(extra)
    return chosen


# ---------------------------------------------------------------- 만들기

def lab_wrapper() -> str:
    """실습 폴더의 Python 실행기. 저장소 루트 환경으로 돌리고, 이 폴더를 import 경로 맨 앞에 둔다.

    uv는 절대 경로로 적는다. Claude Code를 터미널이 아닌 곳에서 열어 PATH가 짧아도 돌게 하려는 것이다.
    --no-sync: 실습 중에 패키지를 바꾸지 않는다(루트 AGENTS.md 3장).
    """
    uv = shutil.which("uv") or "uv"
    return "\n".join([
        "#!/bin/sh",
        "# Day05 실습 폴더의 Python. 사용법: ./lab work/m1_pair.py  또는  ./lab -c 'print(1)'",
        "# 저장소 루트의 uv 환경을 쓰고(설치는 저장소 루트에서 한 번), 이 폴더를 import 경로 맨 앞에 둔다.",
        'HERE="$(cd "$(dirname "$0")" && pwd)"',
        'cd "$HERE" || exit 1',
        f'PYTHONPATH="$HERE${{PYTHONPATH:+:$PYTHONPATH}}" exec {shlex.quote(uv)} run --no-sync --project {shlex.quote(str(COURSE_DIR))} python "$@"',
        "",
    ])


def render(text: str) -> str:
    """템플릿의 자리 표시를 이 기계의 경로로 바꾼다."""
    return (text.replace("{{COURSE_DIR}}", str(COURSE_DIR))
                .replace("{{DAY05_DIR}}", str(DAY05_DIR))
                .replace("{{USE_CC_DIR}}", str(USE_CC_DIR)))


def copy_template(target: Path) -> list[Path]:
    """sandbox/ 템플릿을 복사한다. 텍스트 파일은 경로 자리 표시를 바꾼다."""
    created = []
    for source in sorted(TEMPLATE_DIR.rglob("*")):
        if source.is_dir() or "__pycache__" in source.parts:
            continue
        destination = target / source.relative_to(TEMPLATE_DIR)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render(source.read_text(encoding="utf-8")), encoding="utf-8")
        created.append(destination)
    return created


def create_sandbox(target: Path) -> list[Path]:
    """폴더를 만들고 만든 항목 목록을 돌려준다. 검사는 부르는 쪽(main)에서 먼저 한다."""
    created: list[Path] = []
    target.mkdir(parents=True, exist_ok=True)

    # 1. 규칙, 권한, Skill, 보기 도구, 운영 트래픽 모듈(템플릿).
    created += copy_template(target)

    # 2. 고정 부품: eval_lab 사본. 캐시 폴더는 옮기지 않는다.
    shutil.copytree(DAY05_DIR / "eval_lab", target / "eval_lab", ignore=shutil.ignore_patterns("__pycache__"))
    created.append(target / "eval_lab")

    # 3. 데이터: dev만. holdout은 ID 목록만.
    data = target / "data"
    data.mkdir(exist_ok=True)
    cards = dev_scenarios()
    (data / "scenarios.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (data / "fixtures.json").write_text(json.dumps(dev_fixtures(cards), ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    (data / "holdout_ids.json").write_text(json.dumps(holdout_ids(), indent=2) + "\n", encoding="utf-8")
    for name in PLAIN_DATA_FILES:
        shutil.copyfile(DAY05_DIR / "data" / name, data / name)
    created.append(data)

    # 4. 미션 카드와 참고 노트북. 노트북은 Claude Code가 함수 사용법을 읽는 곳이다(실행하지 않는다).
    #    저장본에는 실행 출력이 없다(Day05_new/tests/check_notebook.py가 검사한다).
    missions = target / "missions"
    missions.mkdir()
    for card in sorted(MISSIONS_DIR.glob("*.md")):
        (missions / card.name).write_text(render(card.read_text(encoding="utf-8")), encoding="utf-8")
    created.append(missions)
    reference = target / "reference"
    reference.mkdir()
    for notebook in sorted(DAY05_DIR.glob("0*.ipynb")):
        shutil.copyfile(notebook, reference / notebook.name)
    created.append(reference)

    # 5. 키 파일: 수강생이 Day05_new/.env를 채웠으면 그 사본, 아니면 빈 양식. 값은 읽어 출력하지 않는다.
    env_source = DAY05_DIR / ".env"
    if not env_source.is_file():
        env_source = DAY05_DIR / ".env.example"
    shutil.copyfile(env_source, target / ".env")
    (target / ".env").chmod(0o600)
    created.append(target / ".env")

    # 6. Python 실행기와 빈 작업 폴더.
    wrapper = target / "lab"
    wrapper.write_text(lab_wrapper(), encoding="utf-8")
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    created.append(wrapper)
    for folder in ("work", "notes", "outputs"):
        (target / folder).mkdir(exist_ok=True)
        created.append(target / folder)
    return created


def next_steps(target: Path) -> str:
    """수강생이 이어서 할 일."""
    env_note = ("Day05_new/.env를 복사했습니다." if (DAY05_DIR / ".env").is_file()
                else "Day05_new/.env가 없어 빈 양식을 복사했습니다. 이 폴더의 .env를 직접 채우세요.")
    return "\n".join([
        "",
        f"키 파일: {env_note} (값은 출력하지 않습니다)",
        "",
        "다음 순서로 진행합니다.",
        f"  cd {shlex.quote(str(target))}",
        "  claude",
        "  처음 열면 폴더 신뢰 화면이 나옵니다. 기본 선택이 'No, exit'이므로 화살표로 'Yes, I trust this folder'를 고릅니다.",
        "  열린 뒤 /mission m0 을 입력하면 준비 카드부터 시작합니다.",
        "  브라우저에서 Langfuse 프로젝트를 열어 둡니다. 이 실습의 두 번째 화면입니다.",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Day05 Claude Code 실습 폴더를 저장소 밖에 만든다.")
    parser.add_argument("target", type=Path, help="만들 폴더. 저장소 밖이어야 하고 비어 있어야 한다")
    arguments = parser.parse_args()

    # 1. 절대 경로로 바꾼다. ~ 도 풀어 준다.
    target = arguments.target.expanduser().resolve()

    # 2. 만들기 전에 검사한다. 하나라도 걸리면 아무것도 만들지 않는다.
    check_outside_repository(target)
    check_empty(target)

    # 3. 만든다.
    created = create_sandbox(target)

    # 4. 무엇을 만들었는지와 다음 할 일.
    print(f"[완료] 실습 폴더를 만들었습니다: {target}")
    for path in created:
        print(f"  - {path.relative_to(target)}")
    print(next_steps(target))


if __name__ == "__main__":
    main()
