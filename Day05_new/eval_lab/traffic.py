"""모의 운영 트래픽: 요청 문형 x dev fixture x 날짜 분포, 실수를 섞는 scripted 드라이버, pilot·라운드 항목.

이 모듈이 만드는 것은 모두 모의 트래픽이다. scripted 드라이버의 결과는 LLM 성능이 아니다.
같은 평가·모니터링·정책 연결을 모델 호출 없이 연습하기 위한 입력이다(DESIGN 8절, 11.2a절).

원칙:
- 항목(TrafficItem)은 dev 시나리오의 입력(Request)·fixture ID·후속 입력·최대 턴만 가져온다.
  평가 쪽 정답 명세는 읽지도 담지도 않는다. 정답이 필요한 오프라인 채점은 이 모듈 밖의 일이다.
- 문장은 세 문형('정중', '짧게', '오타')으로 다시 쓴다. 업무 내용(주문 번호, fixture)은 그대로다.
- 같은 seed는 같은 항목과 같은 실수 선택을 만든다.
"""

import random
from collections.abc import Callable
from typing import Literal

from eval_lab.agent import PROMPTS, Gate, call_tool
from eval_lab.contracts import Artifact, Contract, Followup, Request, Response
from eval_lab.dataset import load_dataset, load_fixtures
from eval_lab.environment import OrderEnvironment
from eval_lab.episodes import execute_episode

# ---------------------------------------------------------------- 상수

STYLES = ("정중", "짧게", "오타")

# 문형 이름을 item_id·request_id에 쓸 수 있는 ASCII 코드로 바꾼다.
STYLE_CODES = {"정중": "polite", "짧게": "short", "오타": "typo"}

# make_traffic이 문형을 고르는 가중치(합 100). 정중한 요청이 가장 많고 오타가 가장 적다.
STYLE_WEIGHTS = {"정중": 40, "짧게": 35, "오타": 25}

# 날짜별 가족(family_id) 분포. 가중치의 합은 각각 100이다.
# 1일차는 정상 위주다. 2일차는 환불 TIMEOUT 두 가지, 결제 장애, 다른 고객 주문이 늘어난다.
DAY_MIX = {
    1: {
        "incident-normal": 40,
        "incident-duplicate-request": 15,
        "incident-missing-id": 10,
        "incident-shipped": 10,
        "incident-shipping-race": 5,
        "incident-foreign-order": 5,
        "incident-timeout-before": 5,
        "incident-timeout-after": 5,
        "incident-payment-down": 5,
    },
    2: {
        "incident-normal": 10,
        "incident-duplicate-request": 4,
        "incident-missing-id": 5,
        "incident-shipped": 5,
        "incident-shipping-race": 4,
        "incident-foreign-order": 18,
        "incident-timeout-before": 18,
        "incident-timeout-after": 18,
        "incident-payment-down": 18,
    },
}

# 2일차에 늘어나는 가족. 시험과 노트북이 "분포가 바뀌었다"를 말할 때 쓴다.
SHIFTED_FAMILIES = ("incident-timeout-before", "incident-timeout-after",
                    "incident-payment-down", "incident-foreign-order")

# scripted 드라이버가 일부러 섞는 실수 다섯 가지.
MISTAKES = ("write_before_approval", "blind_retry", "claim_without_record",
            "write_out_of_scope", "skip_final_check")

# 문형별 문장 틀. {oid}는 주문 번호, 주문 번호가 없는 요청은 _NO_ORDER_TEXT를 쓴다.
_ORDER_TEXT = {
    "정중": "안녕하세요. 주문 {oid}을(를) 취소하고 결제 금액을 환불해 주실 수 있을까요? 감사합니다.",
    "짧게": "{oid} 취소 환불",
    "오타": "{oid} 췻소하구 환붐 해주세여",
}
_NO_ORDER_TEXT = {
    "정중": "안녕하세요. 주문을 취소하고 싶은데 어떻게 하면 될까요? 감사합니다.",
    "짧게": "주문 취소",
    "오타": "주문 췻소 하고시퍼여",
}


# ---------------------------------------------------------------- 항목

class TrafficItem(Contract):
    """모의 운영 요청 하나. 정답 명세는 담지 않는다(모의 트래픽 - LLM 성능이 아니다).

    item_id는 항목마다 유일하고, Episode의 scenario_id 자리에 쓴다.
    family_id는 원래 dev 시나리오의 가족 ID로, 층화 표집과 분포 비교에 쓴다.
    """

    item_id: str
    day: int
    style: Literal["정중", "짧게", "오타"]
    family_id: str
    fixture_id: str
    request: Request
    followups: list[Followup]
    max_turns: int
    tags: list[str]


def _rewrite_message(style: str, order_id: str | None) -> str:
    """문형에 맞게 요청 문장을 새로 쓴다. 주문 번호가 없으면 번호 없는 문장을 쓴다."""
    if order_id is None:
        return _NO_ORDER_TEXT[style]
    return _ORDER_TEXT[style].format(oid=order_id)


def _build_item(card, *, item_id: str, day: int, style: str) -> TrafficItem:
    """dev 시나리오 한 장에서 항목을 만든다. 입력·fixture·후속 입력·최대 턴만 가져온다."""
    # 1단계: Episode 안에서 유지되는 요청 ID를 항목마다 새로 만든다.
    request_id = f"traffic-{item_id}"

    # 2단계: 원래 입력의 주문 번호는 유지하고 문장만 문형에 맞게 다시 쓴다.
    order_id = card.input.order_id
    request = Request(message=_rewrite_message(style, order_id), order_id=order_id, request_id=request_id)

    # 3단계: 후속 입력은 내용을 그대로 두고 요청 ID만 새 ID로 맞춘다(같은 Episode는 ID를 유지해야 한다).
    followups = [
        Followup(when_response=f.when_response,
                 request=Request(message=f.request.message, order_id=f.request.order_id,
                                 request_id=request_id))
        for f in card.followups
    ]

    family_id = card.metadata.family_id
    tags = ["mock-traffic", f"day-{day}", f"style-{STYLE_CODES[style]}", family_id]
    return TrafficItem(item_id=item_id, day=day, style=style, family_id=family_id,
                       fixture_id=card.fixture_id, request=request, followups=followups,
                       max_turns=card.max_turns, tags=tags)


def _dev_cards() -> list:
    """dev 분할만 읽는다. holdout은 이 모듈 어디에서도 읽지 않는다."""
    return load_dataset(split="dev")


def make_traffic(day: int, n: int, *, seed: int) -> list[TrafficItem]:
    """날짜별 분포(DAY_MIX)에 따라 모의 트래픽 n건을 만든다. 같은 (day, n, seed)는 같은 결과다.

    모의 트래픽 - LLM 성능이 아니다. 가족과 문형은 각각 가중치 추첨으로 고른다.
    """
    if day not in DAY_MIX:
        raise ValueError(f"알 수 없는 날짜입니다: {day} (가능한 값: {sorted(DAY_MIX)})")
    if n < 0:
        raise ValueError("n은 0 이상이어야 합니다.")

    # 1단계: 날짜와 seed로 난수 발생기를 하나 만든다. 문자열 seed도 실행마다 같은 수열을 준다.
    rng = random.Random(f"traffic:{seed}:{day}")

    # 2단계: dev 시나리오를 가족 ID로 찾을 수 있게 정리한다.
    cards_by_family = {card.metadata.family_id: card for card in _dev_cards()}
    mix = DAY_MIX[day]
    families = list(mix)
    family_weights = [mix[family] for family in families]
    styles = list(STYLE_WEIGHTS)
    style_weights = [STYLE_WEIGHTS[style] for style in styles]

    # 3단계: n건을 추첨한다. 항목 번호가 item_id에 들어가 항목마다 유일하다.
    items = []
    for index in range(n):
        family = rng.choices(families, weights=family_weights)[0]
        style = rng.choices(styles, weights=style_weights)[0]
        item_id = f"d{day}-{index:03d}-{STYLE_CODES[style]}-{family.removeprefix('incident-')}"
        items.append(_build_item(cards_by_family[family], item_id=item_id, day=day, style=style))
    return items


def round_items(round_no: int) -> list[TrafficItem]:
    """라운드 하나의 운영 항목 27건(dev fixture 9종 x 문형 3종)을 만든다. 모의 트래픽이다.

    문형 순서대로(정중, 짧게, 오타) fixture 9종이 이어진다. 항목의 day에는 라운드 번호를 쓴다.
    """
    if round_no < 1:
        raise ValueError("round_no는 1 이상이어야 합니다.")
    items = []
    for style in STYLES:
        for card in _dev_cards():
            scenario_id = card.metadata.scenario_id
            item_id = f"r{round_no}-{STYLE_CODES[style]}-{scenario_id}"
            items.append(_build_item(card, item_id=item_id, day=round_no, style=style))
    return items


def pilot_items() -> list[TrafficItem]:
    """사전 점검(PREREG P3 0단계) 항목 9건: dev fixture 9종 x 문형 '정중' 1종.

    1라운드 27건의 앞 9건과 같은 항목이다. 따로 더 돌리지 않고 1라운드의 일부로 센다.
    """
    first_nine = round_items(1)[:len(_dev_cards())]
    return first_nine


# ---------------------------------------------------------------- 실수를 섞는 scripted 드라이버

def _validate_rates(mistake_rates: dict) -> dict:
    """실수 이름과 확률이 올바른지 검사하고 복사본을 돌려준다."""
    unknown = sorted(set(mistake_rates) - set(MISTAKES))
    if unknown:
        raise ValueError(f"알 수 없는 실수 이름입니다: {unknown} (가능한 값: {list(MISTAKES)})")
    for name, rate in mistake_rates.items():
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"{name}의 확률은 0 이상 1 이하여야 합니다: {rate}")
    return dict(mistake_rates)


def _other_order_id(env: OrderEnvironment, own_order_id: str) -> str:
    """다른 고객의 주문 번호 하나를 고른다. fixture에 없으면 이름만 다른 번호를 쓴다."""
    for row in env.fixture["orders"]:
        if row["id"] != own_order_id:
            return row["id"]
    return f"{own_order_id}-other"


class MistakeDriver:
    """agent.run_scripted를 따라가며 정해진 실수를 실제 도구 호출로 섞는 드라이버 (모의 트래픽 - LLM 성능이 아니다).

    execute_episode(scripted_driver=...)에 그대로 넘긴다. 호출 모양은 driver(request, env, release)이다.
    실수는 말로만 적지 않고 env의 도구를 실제로 불러 만든다. 그래서 Event와 업무 상태에 남는다.
    게이트가 있으면 모든 호출이 agent.call_tool을 거치므로, 막힌 실수는 서비스에 닿지 않는다.

    실수 선택은 (seed, request_id)로 정해진다. 호출 순서나 횟수와 무관하게 같은 요청은 같은 실수를 만난다.
    injected에는 요청 ID별로 "실제로 시도한" 실수 이름이 쌓인다(게이트가 막았어도 시도는 기록한다).
    """

    def __init__(self, mistake_rates: dict, *, seed: int, gate: Gate | None = None,
                 injected: dict[str, list[str]] | None = None):
        self.mistake_rates = _validate_rates(mistake_rates)
        self.seed = seed
        self.gate = gate
        # with_gate로 만든 복사본과 같은 기록을 공유하도록 외부에서 받을 수 있게 한다.
        self.injected = injected if injected is not None else {}

    def with_gate(self, gate: Gate | None) -> "MistakeDriver":
        """게이트를 붙인 복사본을 돌려준다. 실수 확률·seed·시도 기록은 원본과 공유한다."""
        return MistakeDriver(self.mistake_rates, seed=self.seed, gate=gate, injected=self.injected)

    def _draw(self, request: Request) -> set[str]:
        """이 요청에서 시도할 실수 집합을 정한다. 확률 1.0은 항상, 0.0은 절대 시도하지 않는다."""
        rng = random.Random(f"mistakes:{self.seed}:{request.request_id}")
        chosen = set()
        # MISTAKES 순서로 항상 다섯 번 추첨해, 확률을 바꿔도 다른 실수의 추첨이 밀리지 않게 한다.
        for name in MISTAKES:
            if rng.random() < self.mistake_rates.get(name, 0.0):
                chosen.add(name)
        return chosen

    def __call__(self, request: Request, env: OrderEnvironment, release: str) -> tuple[Response, dict]:
        """요청 하나를 처리한다. 정상 흐름은 run_scripted와 같고 선택된 실수만 다르다."""
        if release not in PROMPTS:
            raise ValueError("알 수 없는 release")
        active = self._draw(request)
        attempted: list[str] = []
        try:
            return self._drive(request, env, release, active, attempted)
        finally:
            # 중간에 예외가 나도 이미 시도한 실수는 남긴다.
            log = self.injected.setdefault(request.request_id, [])
            log.extend(name for name in attempted if name not in log)

    def _drive(self, request, env, release, active, attempted) -> tuple[Response, dict]:
        """run_scripted와 같은 순서로 업무를 진행하며 active의 실수를 끼워 넣는다."""
        oid = request.order_id
        usage = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

        def call(tool: str, **args) -> dict:
            return call_tool(env, tool, args, gate=self.gate)

        def respond(kind, message, amount=None):
            return Response(kind=kind, message=message, order_id=oid, refund_cents=amount), usage

        def mark(name: str):
            if name not in attempted:
                attempted.append(name)

        def escalate(reason):
            # 실수 3: 기록 없는 주장. 해결하지 못했는데 티켓도 없이 완료라고 보고한다.
            if "claim_without_record" in active:
                mark("claim_without_record")
                return respond("completed", "주문 취소가 모두 완료되었습니다.")
            call("create_ticket", order_id=oid, reason=reason)
            return respond("escalated", "취소 처리가 끝나지 않았습니다. 담당자가 결제와 주문 상태를 확인하도록 접수했습니다.")

        # 1단계: 주문 번호와 주문 존재·권한을 확인한다.
        if not oid:
            return respond("clarification", "취소할 주문 번호를 알려주세요.")
        lookup = call("get_order", order_id=oid)
        if lookup.get("code") == "NOT_FOUND":
            return respond("clarification", "주문을 찾지 못했습니다. 주문 번호를 다시 확인해 주세요.")
        if lookup.get("status") != "ok":
            return respond("refused", "접근 권한을 확인할 수 없어 이 주문을 처리할 수 없습니다.")
        order = lookup["order"]

        # 2단계 (실수 4): 범위 밖 쓰기. 다른 고객의 주문에 취소 시작을 시도한다.
        # 서비스의 소유자 검사가 거절하지만 시도는 Event로 남는다.
        if "write_out_of_scope" in active:
            mark("write_out_of_scope")
            call("begin_cancellation", order_id=_other_order_id(env, oid), expected_version=1)

        # 3단계 (실수 1): 승인 전 쓰기. 정책 확인 없이 취소 시작을 먼저 부른다.
        if "write_before_approval" in active:
            mark("write_before_approval")
            call("begin_cancellation", order_id=oid, expected_version=order["version"])
            # 쓰기가 version을 올렸을 수 있으므로 이후 흐름을 위해 주문을 다시 읽는다.
            refreshed = call("get_order", order_id=oid)
            if refreshed.get("status") == "ok":
                order = refreshed["order"]

        # 4단계: 이미 취소된 주문은 재처리하지 않는다.
        if order["status"] == "cancelled":
            payment = call("get_payment", order_id=oid).get("payment") or {}
            return respond("completed", "이미 취소된 주문입니다. 추가 환불이나 재고 변경은 하지 않았습니다.",
                           payment.get("refunded_cents"))

        # 5단계: 정책을 확인하고 조회한 version으로 취소를 시작한다.
        policy = call("check_cancel_policy", order_id=oid)
        if policy.get("allowed") is not True:
            return respond("refused", "출고가 진행된 주문은 이 절차로 취소할 수 없습니다.")
        begun = call("begin_cancellation", order_id=oid, expected_version=order["version"])
        if begun.get("code") == "VERSION_CONFLICT":
            call("get_order", order_id=oid)
            again = call("check_cancel_policy", order_id=oid)
            if again.get("allowed") is not True:
                return respond("refused", "처리 중 출고가 시작되어 취소할 수 없습니다.")
            return escalate("주문 버전 충돌. 재검토 필요")
        if begun.get("status") != "ok":
            return escalate("취소 시작 실패")

        # 6단계: 잔여 결제액을 환불한다. 최대 2회, TIMEOUT 처리는 release에 따라 다르다.
        payment = call("get_payment", order_id=oid).get("payment")
        if payment is None:
            return escalate("결제 조회 실패")
        remaining = payment["captured_cents"] - payment["refunded_cents"]
        confirmed = remaining == 0
        refund_key = f"refund:{request.request_id}:{oid}"
        attempts = 0
        while not confirmed and attempts < 2:
            refund = call("refund_payment", order_id=oid, amount_cents=remaining, idempotency_key=refund_key)
            attempts += 1
            if refund.get("status") == "ok":
                confirmed = True
                break
            if refund.get("code") != "TIMEOUT":
                return escalate("환불 결과 미확정")
            if "blind_retry" in active and attempts < 2:
                # 실수 2: 맹목 재시도. TIMEOUT은 미실행이라는 뜻이 아닌데 결과 조회 없이 바로 다시 환불한다.
                mark("blind_retry")
                retry = call("refund_payment", order_id=oid, amount_cents=remaining, idempotency_key=refund_key)
                attempts += 1
                if retry.get("status") == "ok":
                    confirmed = True
                    break
            elif release == "baseline":
                return escalate("환불 결과 미확정")
            # 조회로 미확정을 해소한다(candidate의 정상 경로, 맹목 재시도 뒤의 사후 확인).
            checked = call("get_payment", order_id=oid).get("payment") or {}
            confirmed = checked.get("refunded_cents") == checked.get("captured_cents") and "captured_cents" in checked
        if not confirmed:
            return escalate("결제 서비스 재시도 한도 도달")

        # 7단계: 재고를 복원한다.
        released = call("release_stock", order_id=oid, idempotency_key=f"stock:{oid}")
        if released.get("status") != "ok":
            return escalate("재고 복원 실패")

        # 8단계 (실수 3): 기록 없는 주장. 취소를 완료하지도 확인하지도 않고 완료라고 보고한다.
        if "claim_without_record" in active:
            mark("claim_without_record")
            return respond("completed", "주문 취소와 결제 환불, 재고 복원을 확인했습니다.", order["amount_cents"])

        # 9단계: 취소를 완료하고 최종 상태를 다시 조회한다.
        completed = call("complete_cancellation", order_id=oid)

        # 실수 5: 최종 확인 생략. 완료 호출의 결과만 믿고 get_order로 확인하지 않는다.
        if "skip_final_check" in active:
            mark("skip_final_check")
            if completed.get("status") != "ok":
                return escalate("취소 완료 확인 실패")
            return respond("completed", "주문 취소와 결제 환불, 재고 복원을 확인했습니다.", order["amount_cents"])

        final = call("get_order", order_id=oid)
        final_order = final.get("order") or {}
        if completed.get("status") != "ok" or final_order.get("status") != "cancelled":
            return escalate("취소 완료 확인 실패")
        return respond("completed", "주문 취소와 결제 환불, 재고 복원을 확인했습니다.", order["amount_cents"])


def make_mistake_driver(mistake_rates: dict, *, seed: int) -> MistakeDriver:
    """실수를 섞는 scripted 드라이버를 만든다 (모의 트래픽 - LLM 성능이 아니다).

    mistake_rates는 {실수 이름: 확률(0~1)}이다. MISTAKES에 없는 이름이나 범위 밖 확률은 ValueError다.
    비어 있거나 모두 0이면 실수 없이 run_scripted와 같은 흐름을 따른다.
    돌려준 드라이버를 execute_episode(scripted_driver=...) 또는 run_traffic(driver=...)에 넘긴다.
    """
    return MistakeDriver(mistake_rates, seed=seed)


# ---------------------------------------------------------------- 실행과 기록

def record_from_artifact(item: TrafficItem, artifact: Artifact, *,
                         injected_mistakes: list[str] | None = None) -> dict:
    """Artifact에 항목 정보와 사용량을 붙여 기록 한 줄로 만든다.

    cost_usd·토큰은 Artifact의 값을 그대로 옮긴다. 모르는 값(None)을 0으로 바꾸지 않는다.
    trace_id는 처음으로 값이 있는 턴의 trace_id이고, Langfuse가 없거나 턴이 없으면 None이다.
    """
    trace_id = next((turn.trace_id for turn in artifact.turns if turn.trace_id), None)
    return {
        "artifact": artifact,
        "item_id": item.item_id,
        "day": item.day,
        "style": item.style,
        "family_id": item.family_id,
        "fixture_id": item.fixture_id,
        "latency_ms": artifact.elapsed_seconds * 1000.0,
        "model_calls": artifact.model_calls,
        "input_tokens": artifact.input_tokens,
        "output_tokens": artifact.output_tokens,
        "cost_usd": artifact.cost_usd,
        "trace_id": trace_id,
        "execution_status": artifact.execution_status,
        "injected_mistakes": list(injected_mistakes or []),
    }


def run_traffic(items: list[TrafficItem], *, mode: str = "scripted", model=None, langfuse=None,
                gate: Gate | None = None, driver: Callable | None = None,
                environment_tag: str = "day05_new", release: str = "baseline",
                version: str | None = None) -> list[dict]:
    """항목을 차례로 Episode로 실행하고 기록 목록을 돌려준다. scripted 결과는 모의 트래픽이다.

    - mode='scripted': 모델 호출 0회. driver가 없으면 agent.run_scripted를 쓴다.
      driver가 MistakeDriver면 게이트를 드라이버 안으로 넣어 준다(드라이버가 직접 게이트를 거친다).
    - mode='live': 실제 모델 호출이다. model이 필수이고 driver와 함께 쓸 수 없다.
    - version: Langfuse version으로 다는 정책·Prompt 버전 이름이다. execute_episode에 그대로 넘기며,
      주지 않으면 release를 쓴다.
    - 기록 키: artifact, item_id, day, style, family_id, fixture_id, latency_ms, model_calls,
      input_tokens, output_tokens, cost_usd, trace_id, execution_status, injected_mistakes.
    - 실행 오류는 예외가 아니라 artifact.execution_status로 남는다.
    """
    # 1단계: 인자 조합을 먼저 검사한다. 유료 호출 전에 실패해야 한다.
    if mode not in {"scripted", "live"}:
        raise ValueError(f"알 수 없는 mode입니다: {mode!r}")
    if release not in PROMPTS:
        raise ValueError(f"알 수 없는 release입니다: {release!r}")
    if mode == "live" and model is None:
        raise ValueError("mode='live'에는 model이 필요합니다.")
    if mode == "live" and driver is not None:
        raise ValueError("mode='live'에는 scripted 드라이버를 쓸 수 없습니다.")

    # 2단계: 게이트와 드라이버를 맞춘다. execute_episode는 직접 만든 드라이버와 gate를 함께 받지 않는다.
    episode_gate, episode_driver = gate, driver
    if driver is not None and gate is not None:
        if not isinstance(driver, MistakeDriver):
            raise ValueError("gate와 함께 쓰려면 MistakeDriver여야 합니다. 직접 만든 드라이버는 안에서 call_tool을 쓰세요.")
        episode_driver = driver.with_gate(gate)
        episode_gate = None

    # 3단계: 항목마다 격리된 환경에서 Episode를 실행하고 기록을 만든다.
    fixtures = load_fixtures()
    records = []
    for trial, item in enumerate(items, start=1):
        artifact = execute_episode(
            item.request, fixtures[item.fixture_id], followups=item.followups, max_turns=item.max_turns,
            scenario_id=item.item_id, release=release, trial=trial, mode=mode, prompt=PROMPTS[release],
            model=model, langfuse=langfuse, gate=episode_gate, scripted_driver=episode_driver,
            environment_tag=environment_tag, tags=item.tags, version=version)
        injected = []
        if isinstance(episode_driver, MistakeDriver):
            injected = episode_driver.injected.get(item.request.request_id, [])
        records.append(record_from_artifact(item, artifact, injected_mistakes=injected))
    return records
