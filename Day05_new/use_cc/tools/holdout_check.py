"""m6 holdout 재확인: 실습 폴더의 라운드 기록을 받아, 저장소의 승인된 holdout 카드로 π0와 π*를 실제 모델로 돌린다.

사용법 (실습 폴더의 Claude Code 화면에서 앞에 !를 붙여, 또는 아무 셸에서):

    uv run --no-sync --project <저장소> python <저장소>/Day05_new/use_cc/tools/holdout_check.py <실습 폴더의 round-1.json>

- holdout 카드는 이 명령만 읽는다. 실습 폴더에는 holdout 내용이 없다(setup_sandbox.py).
  화면과 결과 파일에는 노트북 06 셀 44~46과 같은 수준(scenario_id, family_id, 최대 턴, 검수자, Code 판정)만 나온다.
- π0는 빈 정책, π*는 라운드 기록의 chosen_spec이다. 재생 풀은 라운드 폴더의 pool/에서 읽어 오염 검사(P7)에 쓴다.
- 결과는 라운드 폴더 아래 holdout/holdout.json에 한 번만 쓴다. 이미 있으면 실행 전에 멈춘다(holdout은 한 번만 연다).
- 키는 실습 폴더의 .env에서 읽는다(DAY05_ENV_FILE로 지정, eval_lab/settings.py의 load_settings). 값은 출력하지 않는다.
- 유료다: 에이전트 모델 최대 (승인 카드 수 x 반복 x 정책 2개 x 12)회. 실행 전에 한 줄로 알린다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DAY05_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(DAY05_DIR))  # 저장소의 eval_lab과 data를 쓴다(실습 폴더의 사본이 아니다).

from eval_lab import settings as lab_settings
from eval_lab.agent import MAX_MODEL_CALLS, PROMPTS
from eval_lab.dataset import load_dataset, load_fixtures
from eval_lab.episodes import execute_episode
from eval_lab.evaluators import check_outcome
from eval_lab.notebook import announce, langfuse_or_none
from eval_lab.policy import EMPTY_POLICY, as_gate, describe, validate_spec
from eval_lab.replay import load_pool
from eval_lab.rsi import holdout_check
from eval_lab.trajectory_rules import evaluate_trajectory

ENVIRONMENT = "cc_m6"


def read_round(round_path: Path) -> tuple[dict, list]:
    """라운드 기록과 그 라운드 폴더의 재생 풀 전체를 읽는다."""
    if not round_path.is_file():
        raise SystemExit(f"[멈춤] 라운드 기록이 없습니다: {round_path}")
    if round_path.resolve().is_relative_to(DAY05_DIR.parent.resolve()):
        raise SystemExit("[멈춤] 라운드 기록이 저장소 안에 있습니다. 실습 폴더(저장소 밖)의 round-*.json을 주세요.")
    record = json.loads(round_path.read_text(encoding="utf-8"))
    pool_files = sorted((round_path.parent / "pool").glob("pool-round-*.json"))
    if not pool_files:
        raise SystemExit(f"[멈춤] {round_path.parent / 'pool'} 에 재생 풀(pool-round-*.json)이 없습니다.")
    pool = [episode for path in pool_files for episode in load_pool(path)]
    return record, pool


def sandbox_root(round_path: Path) -> Path:
    """라운드 기록이 들어 있는 실습 폴더의 뿌리. CLAUDE.md, lab, .env가 함께 있는 가장 가까운 위 폴더다."""
    for folder in round_path.parents:
        if all((folder / name).exists() for name in ("CLAUDE.md", "lab", ".env")):
            return folder
    raise SystemExit(f"[멈춤] {round_path} 위에서 실습 폴더(CLAUDE.md, lab, .env가 있는 곳)를 찾지 못했습니다.")


def main() -> None:
    parser = argparse.ArgumentParser(description="실습 폴더의 라운드 결과를 승인된 holdout 카드로 한 번 재확인한다(유료).")
    parser.add_argument("round_json", type=Path, help="실습 폴더의 round-<n>.json")
    parser.add_argument("--reps", type=int, default=1, help="카드마다 정책별 반복 수(기본 1, 노트북 06과 같다)")
    arguments = parser.parse_args()
    round_path = arguments.round_json.expanduser().resolve()

    # 1단계: 라운드 기록과 풀. 고른 정책 명세를 검증한다(형식이 틀리면 여기서 멈춘다).
    record, pool = read_round(round_path)
    # 키는 수강생이 채운 실습 폴더의 .env 하나만 쓴다(Day05_new/.env가 아니다).
    os.environ["DAY05_ENV_FILE"] = str(sandbox_root(round_path) / ".env")
    pistar = validate_spec(record["chosen_spec"])
    out_dir = round_path.parent / "holdout"

    # 2단계: 승인된 holdout 카드만. 검수 대기 초안은 쓰지 않는다(Day05_new/AGENTS.md 6장).
    cards = load_dataset(split="holdout", approved_only=True)
    expected = {card.metadata.scenario_id: card.expected_output for card in cards}
    fixtures = load_fixtures()
    print("승인된 holdout 카드(내용은 보이지 않는다):")
    for card in cards:
        print(f"  - {card.metadata.scenario_id} | {card.metadata.family_id} | 최대 턴 {card.max_turns} | 검수자 {card.metadata.reviewer}")
    print("π* 정책:", describe(pistar))

    # 3단계: 비용 고지. 실행은 막지 않는다.
    calls = len(cards) * arguments.reps * 2 * MAX_MODEL_CALLS
    announce("m6 holdout 재확인", model_calls=calls)

    settings = lab_settings.load_settings()
    model = lab_settings.make_agent_model(settings)
    langfuse = langfuse_or_none(settings)

    def run_live(spec, reps: int) -> list:
        """승인 카드마다 reps회, 정책 spec을 게이트로 걸고 실제 모델로 돌린다."""
        artifacts = []
        for card in cards:
            for trial in range(1, reps + 1):
                artifacts.append(execute_episode(
                    card.input, fixtures[card.fixture_id], followups=card.followups, max_turns=card.max_turns,
                    scenario_id=card.metadata.scenario_id, release="baseline", trial=trial, mode="live",
                    prompt=PROMPTS["baseline"], model=model, langfuse=langfuse, gate=as_gate(spec),
                    environment_tag=ENVIRONMENT, tags=["holdout", f"holdout-{spec.version}"], version=spec.version))
        return artifacts

    def evaluate(artifacts: list) -> list[tuple]:
        """Code 판정만: (궤적 판정, 업무 결과 통과). 의미 판정은 P5의 입력이 아니다(P1)."""
        return [(evaluate_trajectory(a), check_outcome(a, expected[a.scenario_id]).passed) for a in artifacts]

    # 4단계: 한 번만 연다. out_dir/holdout.json이 이미 있으면 holdout_check가 실행 전에 거부한다.
    out_dir.mkdir(exist_ok=True)
    result = holdout_check(pi0_spec=EMPTY_POLICY, pistar_spec=pistar, run_holdout_fn=run_live,
                           evaluate_fn=evaluate, pool=pool, holdout_ids=set(expected), out_dir=out_dir,
                           reps=arguments.reps)
    if langfuse is not None:
        langfuse.flush()

    # 5단계: 노트북 06 셀 46과 같은 것을 출력한다.
    print(f"\nP5 판정: {result['decision']}  (π0 = {EMPTY_POLICY.version}, π* = {pistar.version})")
    for reason in result["reasons"]:
        print(" -", reason)
    print("누락된 Episode:", result["missing"])
    for label, rows in result["rows"].items():
        print(f"holdout 행: {label}")
        for row in rows:
            print(f"  {row['scenario_id']:16s} trial {row['trial']}  궤적 {row['trajectory_status']:5s} "
                  f"치명 {row['fatal_rule_ids']}  업무 결과 통과 {row['outcome_passed']}")
    print("기록:", out_dir / "holdout.json")
    print(f"Langfuse: environment '{ENVIRONMENT}', tag 'holdout'으로 거르면 이 실행의 trace가 보입니다.")


if __name__ == "__main__":
    main()
