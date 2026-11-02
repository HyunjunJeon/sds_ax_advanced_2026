"""저자 측정 실행 스크립트(유료 호출). 사례 분할 하나를 변형 하나(A, A2, B)로 run_experiment에 넘긴다. pytest가 수집하지 않는다.

실행: Day04_new 폴더에서 `../.venv/bin/python tests/run_measurement.py --variant A --split dev`
- 기록은 기본이 local이다(사전 등록 개정 2). Langfuse 없이 <mirror-dir>/<split>-<variant>-r<k>.jsonl과 .meta.json에 남긴다.
- 변형 이름은 <split>-<variant>다(dev-A, holdout-B). dev와 holdout의 실행 이름이 겹치지 않는다.
- holdout은 --open-holdout을 함께 줄 때만 연다. 없으면 설정을 읽거나 무엇을 부르기 전에 종료 코드 2로 멈춘다.
- 문턱값을 조정하지 않고 data/gate_labels_draft.jsonl을 읽지 않는다. 기본 0.5는 라벨로 재지 않은 자리값(미조정)이다.
- 규모 고지는 run_experiment가 시작할 때 한 줄로 출력한다(cap_lab/experiment.py의 cost_notice). 여기서 다시 출력하지 않는다.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
from pathlib import Path

DAY04_ROOT = Path(__file__).resolve().parents[1]
if str(DAY04_ROOT) not in sys.path:
    sys.path.insert(0, str(DAY04_ROOT))

from cap_lab.experiment import MIRROR_DIR, Variant, load_cases, run_experiment  # noqa: E402  sys.path를 맞춘 뒤에만 import할 수 있다.
from cap_lab.settings import load_settings  # noqa: E402

UNTUNED_THRESHOLD = 0.5
# holdout을 --open-holdout 없이 부르면 내는 종료 코드. argparse의 인자 오류도 2다.
EXIT_HOLDOUT_LOCKED = 2
EXIT_RUN_FAILED = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="저자 측정(유료): 사례 분할 하나를 변형 하나로 실행해 로컬 사본에 남긴다(사전 등록 P4, 개정 2).",
    )
    parser.add_argument("--variant", required=True, choices=("A", "A2", "B"),
                        help="A와 A2는 게이트를 모두 끈 같은 구성(A2는 잡음 폭용 반복), B는 H1과 H2 게이트를 모두 켠다.")
    parser.add_argument("--split", required=True, choices=("dev", "holdout"), help="실행할 사례 분할.")
    parser.add_argument("--open-holdout", action="store_true",
                        help="holdout을 연다. holdout은 저자가 정한 시점에 한 번만 연다. 없으면 holdout 실행을 거부한다.")
    parser.add_argument("--repeats", type=int, default=5, help="반복 수. 기본 5(P4 저자 실행 N=5). 결과를 본 뒤 늘리지 않는다.")
    parser.add_argument("--record", choices=("local", "langfuse"), default="local",
                        help="기록 방식. 기본 local(개정 2: Langfuse 없이 로컬 사본과 meta.json). langfuse는 인증이 필요하다.")
    parser.add_argument("--mirror-dir", type=Path, default=MIRROR_DIR,
                        help=f"로컬 사본 폴더. 기본 {MIRROR_DIR}. 작업 폴더는 그 부모 아래 work/다.")
    parser.add_argument("--threshold-h1", type=float, default=UNTUNED_THRESHOLD,
                        help="H1(서버 testability 게이트) 문턱값. 기본 0.5는 미조정 자리값이다.")
    parser.add_argument("--threshold-h2", type=float, default=UNTUNED_THRESHOLD,
                        help="H2(GoalGuard) 문턱값. 기본 0.5는 미조정 자리값이다.")
    return parser


def make_variant(name: str, split: str, threshold_h1: float, threshold_h2: float) -> Variant:
    """A와 A2는 게이트를 모두 끄고, B는 H1과 H2를 모두 켠다. 이름에 분할을 붙인다."""
    gates_on = name == "B"
    return Variant(
        f"{split}-{name}", gate_h1=gates_on, gate_h2=gates_on, threshold_h1=threshold_h1, threshold_h2=threshold_h2,
        metadata={"measurement": "author", "split": split},
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.split == "holdout" and not args.open_holdout:
        print("holdout은 --open-holdout을 함께 줄 때만 엽니다. 설정을 읽거나 아무것도 실행하지 않고 멈췄습니다.",
              file=sys.stderr)
        return EXIT_HOLDOUT_LOCKED
    variant = make_variant(args.variant, args.split, args.threshold_h1, args.threshold_h2)
    for gate, threshold, gate_on in (("H1", variant.threshold_h1, variant.gate_h1),
                                     ("H2", variant.threshold_h2, variant.gate_h2)):
        if threshold == UNTUNED_THRESHOLD:
            print(f"{gate} 문턱값 {threshold}는 라벨로 재지 않은 자리값입니다(미조정). "
                  f"이 변형의 {gate} 게이트: {'켬' if gate_on else '끔'}.")
    cases = load_cases(split=args.split)
    try:
        run_names = asyncio.run(run_experiment(variant, cases, args.repeats, settings=load_settings(),
                                               mirror_dir=args.mirror_dir, record=args.record))
    except Exception:
        traceback.print_exc()
        print(f"{variant.name} 측정이 멈췄습니다. 이미 남긴 로컬 사본 줄은 지우지 않습니다(P4).", file=sys.stderr)
        return EXIT_RUN_FAILED
    print("실행 이름:", ", ".join(run_names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
