"""run_live.py를 nohup으로 띄운 뒤 끝날 때까지 전경에서 기다린다. 도구의 명령 시간 제한 안에서 돌려 반복해 부른다.

사용법: uv run --no-sync python Day03_new/tests/wait_live.py <stem> [--seconds 540]
종료 코드: 0 성공, 1 실패로 끝남, 3 아직 실행 중
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1] / "outputs" / "live"
POLL_SECONDS = 5


def status(stem: str) -> dict | None:
    path = LIVE / f"{stem}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="실제 실행 대기")
    parser.add_argument("stem")
    parser.add_argument("--seconds", type=int, default=540)
    args = parser.parse_args(argv)
    deadline = time.monotonic() + args.seconds
    while time.monotonic() < deadline:
        report = status(args.stem)
        if report and report["errors"]:
            print(f"FAILED 셀 {report['errors'][0]['index']}: {report['errors'][0]['type']}: {report['errors'][0]['message'][:300]}")
            return 1
        if report and report["finished"]:
            print(f"FINISHED 모델 {report['model_calls']}회 {report['total_seconds']:.0f}초")
            return 0
        time.sleep(POLL_SECONDS)
    report = status(args.stem)
    print(f"RUNNING 코드 셀 {len(report['cells']) if report else 0}개 완료, 모델 {report['model_calls'] if report else 0}회")
    return 3


if __name__ == "__main__":
    sys.exit(main())
