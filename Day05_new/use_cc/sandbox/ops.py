"""Part 3b·4·5의 모의 운영 트래픽. eval_lab.traffic의 dev 트래픽에 '이어서 처리' 요청을 섞는다.

이 파일은 실습 폴더의 고정 부품이다(eval_lab과 같다). 수강생의 Claude Code는 이 함수를 불러 쓰고 고치지 않는다.

'이어서 처리' 사례(fx-ops-resume):
    고객 customer-c의 주문 order-r이 이미 cancelling이다. 결제는 전액 환불되었고 재고는 아직 복원되지 않았다.
    정책 문서 P2는 "cancelling 주문은 부분 완료 상태를 조회해 이어서 처리한다"고 하고(data/order_policy.md),
    에이전트 Prompt도 "이미 cancelling인 주문은 get_payment로 부분 완료 상태를 확인하고 남은 단계만 수행"하라고 한다
    (eval_lab/agent.py의 COMMON_PROMPT). 이 사례는 dev·holdout 어느 카드에도 없는 운영 요청이다.

날짜별로 섞는 비율이 다르다. 2일차에 이어서 처리 요청이 늘어난다(입력 분포 변화).
"""

from __future__ import annotations

import random

from eval_lab.contracts import Request
from eval_lab.traffic import STYLE_CODES, STYLE_WEIGHTS, TrafficItem, make_traffic

RESUME_FAMILY = "incident-ops-resume"
RESUME_FIXTURE = "fx-ops-resume"
RESUME_ORDER = "order-r"

# 날짜별 이어서 처리 요청의 비율(%). 나머지는 eval_lab.traffic.make_traffic의 dev 트래픽이다.
RESUME_PERCENT = {1: 10, 2: 40}

# 문형별 문장. 업무 내용(주문 번호)은 같고 말투만 다르다.
_RESUME_TEXT = {
    "정중": "안녕하세요. 주문 {oid} 취소가 중간에 멈춘 것 같아요. 남은 처리를 마저 해 주실 수 있을까요?",
    "짧게": "{oid} 취소 마저 처리",
    "오타": "{oid} 췻소가 멈췄어여 마저 해주세여",
}


def resume_item(item_id: str, *, day: int, style: str = "정중") -> TrafficItem:
    """이어서 처리 요청 하나. 정답 명세는 담지 않는다."""
    request_id = f"ops-{item_id}"
    request = Request(message=_RESUME_TEXT[style].format(oid=RESUME_ORDER), order_id=RESUME_ORDER,
                      request_id=request_id)
    tags = ["mock-ops", f"day-{day}", f"style-{STYLE_CODES[style]}", RESUME_FAMILY]
    return TrafficItem(item_id=item_id, day=day, style=style, family_id=RESUME_FAMILY,
                       fixture_id=RESUME_FIXTURE, request=request, followups=[], max_turns=1, tags=tags)


def ops_items(day: int, n: int, *, seed: int = 7) -> list[TrafficItem]:
    """day일차 모의 운영 요청 n건. 이어서 처리 요청을 RESUME_PERCENT 비율로 섞는다. 같은 인자는 같은 결과다.

    모의 트래픽이다. 이 목록을 실제 모델로 돌린 결과는 '1회 관찰'이고, scripted로 돌린 결과는 LLM 성능이 아니다.
    """
    if day not in RESUME_PERCENT:
        raise ValueError(f"알 수 없는 날짜입니다: {day} (가능한 값: {sorted(RESUME_PERCENT)})")
    # 1단계: 몇 건을 이어서 처리 요청으로 바꿀지 정한다. 반올림하되 n이 있으면 최소 1건.
    resume_count = max(1, round(n * RESUME_PERCENT[day] / 100)) if n else 0
    # 2단계: 나머지는 dev 트래픽에서 가져온다(날짜별 분포는 eval_lab.traffic.DAY_MIX).
    base = make_traffic(day, n - resume_count, seed=seed)
    # 3단계: 이어서 처리 요청을 만들고 같은 seed로 자리를 섞는다.
    rng = random.Random(f"ops:{seed}:{day}")
    styles = list(STYLE_WEIGHTS)
    weights = [STYLE_WEIGHTS[style] for style in styles]
    resumes = []
    for index in range(resume_count):
        style = rng.choices(styles, weights=weights)[0]
        resumes.append(resume_item(f"d{day}-r{index:02d}-{STYLE_CODES[style]}-ops-resume", day=day, style=style))
    items = base + resumes
    rng.shuffle(items)
    return items
