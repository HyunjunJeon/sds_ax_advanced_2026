"""저자용: 고른 Decision API가 지금 응답하는지 Noul 한 개로 확인한다. 실제 Decision API를 한 번 부른다.

저장소 루트에서 `uv run --no-sync python Day02_new/benchmarks/check_decider.py`. 키 값은 출력하지 않는다.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag_lab.decisions import DecisionError, Noul, make_decider  # noqa: E402  (경로 설정 뒤에 import해야 한다)


def main() -> int:
    try:
        decider = make_decider()
    except RuntimeError as error:
        print(error)
        return 1
    question = Noul("answers", "근거가 질문에 답하는가?", "근거가 질문에 직접 답한다", "근거가 질문과 무관하다")
    started = time.perf_counter()
    try:
        judgment = decider.judge("질문: 환불 기한은? 근거: 환불은 구매 후 7일 이내에 신청한다.", [question])
    except DecisionError as error:
        print(f"{error}. 상태 코드가 401이나 403이면 키를, 404면 주소나 모델 id를, 400이면 모델 id를 .env에서 확인하세요.")
        return 1
    verdict = judgment.verdicts["answers"]
    print(f"backend={judgment.backend} model={judgment.model} probability={verdict.probability} refused={verdict.refused} "
          f"seconds={time.perf_counter() - started:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
