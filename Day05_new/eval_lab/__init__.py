"""Day05_new 실습 라이브러리. 오프라인 평가, 온라인 선정, 모니터링, 개선 라운드를 담는다."""

import os

# DESIGN 14절 외부 전송 목록에 없는 DeepEval 텔레메트리 전송을 막는다.
# deepeval을 import하는 judges.py보다 먼저 실행되어야 한다. 사용자가 이미 정한 값은 그대로 둔다.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")
