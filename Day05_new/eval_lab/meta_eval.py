"""평가자 자체의 평가(meta-evaluation): 궤적 규칙이 결함을 잡고 무해한 변형은 통과시키는지 잰다.

왜 필요한가
- 규칙이 PASS를 많이 낸다고 규칙이 좋은 것은 아니다. 결함이 없는 기록에서 PASS는 당연하기 때문이다.
- 그래서 정상 기록에 결함을 하나씩 직접 심고(`inject_defect`), 규칙이 그 결함을 잡는지(재현율, recall) 본다.
- 반대로 행동을 바꾸지 않는 변형(`benign_variants`)에는 치명 위반을 내지 않아야 한다(오탐률, false positive rate).
- 두 비율은 표본이 작으므로 점추정만 내지 않고 Wilson 95% 구간(`wilson_interval`)을 함께 낸다.

설계 원칙
- 결함 주입은 입력 Artifact를 바꾸지 않는다. 항상 깊은 복사본에서 결함 하나만 만든다.
- 주입 결과는 `seed`로 결정된다. 같은 입력과 seed는 같은 결함을 만든다(사건 ID까지 같다).
- 이 모듈은 정답(Expected)을 읽지 않고 외부 호출도 하지 않는다. 규칙은 trajectory_rules를 그대로 쓴다.
- "잡았다"는 판정 상태(FAIL)가 아니라 **치명 규칙 hit**으로 센다. 여기서 재는 것은 규칙이지 판정 상태가 아니다.
  FAIL은 치명 규칙 중 하나가 걸렸다는 것만 알려 주므로, 규칙별 재현율·정밀도에 필요한 "어느 규칙이 걸렸나"를 잃는다.
  또 판정 상태는 규칙과 무관한 이유(기록이 불완전함, 실행 오류, 고객의 답을 기다리는 중)로
  INCOMPLETE·PROVISIONAL·NO_EVIDENCE가 될 수 있어, 상태로 세면 기록의 완결성이 규칙의 성능에 섞인다.
"""

import math
import random
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from eval_lab.contracts import Artifact, Event, Response
from eval_lab.trajectory_rules import RULES, run_rules

# 결함을 주입할 수 있는 치명 규칙 ID. RULES에서 읽어 규칙표와 어긋나지 않게 한다.
FATAL_RULE_IDS: tuple[str, ...] = tuple(rule_id for rule_id, severity, _ in RULES if severity == "fatal")

# 응답 문구를 바꿀 때 덧붙이는 사실 없는 인사말. 환불액·상태 같은 사실은 담지 않는다.
POLITE_SUFFIXES = (
    "추가로 궁금한 점이 있으면 말씀해 주세요.",
    "이용해 주셔서 감사합니다.",
    "다른 도움이 필요하시면 알려 주세요.",
)


# ---------------------------------------------------------------- 통계

def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """성공 k번 / 시도 n번에 대한 Wilson 신뢰구간(기본 z=1.96, 약 95%)을 낸다.

    표본이 작거나 비율이 0 또는 1에 가까울 때도 구간이 [0, 1] 밖으로 나가지 않는다.
    n이 0이면 구간을 만들 근거가 없으므로 None을 돌려준다(없는 구간을 꾸며 내지 않는다).
    k가 0보다 작거나 n보다 크면 ValueError다.
    """
    # 1단계: 입력을 검사한다. n == 0은 오류가 아니라 "구간 없음"이다.
    if n < 0 or k < 0 or k > n:
        raise ValueError(f"0 <= k <= n 이어야 합니다 (k={k}, n={n}).")
    if n == 0:
        return None

    # 2단계: Wilson 공식. 중심을 0.5쪽으로 당기고 폭을 표본 크기로 정한다.
    proportion = k / n
    z_squared = z * z
    denominator = 1 + z_squared / n
    center = (proportion + z_squared / (2 * n)) / denominator
    spread = z * math.sqrt(proportion * (1 - proportion) / n + z_squared / (4 * n * n)) / denominator

    # 3단계: 부동소수 오차로 0, 1을 넘지 않게 자른다.
    return max(0.0, center - spread), min(1.0, center + spread)


def _rate(k: int, n: int) -> float | None:
    """k / n. n이 0이면 비율이 정의되지 않으므로 None이다."""
    return None if n == 0 else k / n


# ---------------------------------------------------------------- 결과 모델

Interval = tuple[float, float]


class RuleMetric(BaseModel):
    """치명 규칙 하나의 재현율과 정밀도.

    injected: 이 규칙의 결함을 주입한 기록 수(정상 기록이 이미 이 규칙을 어겼으면 제외).
    detected: 그중 규칙이 실제로 잡은 수. recall = detected / injected.
    false_detections: 이 규칙이 결함 없는 곳(다른 규칙의 결함 기록, 무해한 변형)에서 새로 낸 hit 수.
    precision = detected / (detected + false_detections).
    """

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    injected: int
    detected: int
    recall: float | None
    recall_interval: Interval | None
    false_detections: int
    precision: float | None
    precision_interval: Interval | None


class MetaEvalReport(BaseModel):
    """평가자 평가 결과. 모든 비율은 분모가 0이면 None이다."""

    model_config = ConfigDict(extra="forbid")

    seed: int
    clean_count: int  # 입력으로 받은 정상 기록 수
    per_rule: list[RuleMetric]
    skipped_injections: dict[str, int] = Field(default_factory=dict)  # 규칙별: 정상 기록이 이미 어겨 건너뜀
    benign_total: int  # 만든 무해한 변형 수
    benign_with_fatal: int  # 그중 치명 hit이 새로 생긴 변형 수
    false_positive_rate: float | None
    false_positive_interval: Interval | None
    true_detections: int  # 주입한 규칙이 바로 그 규칙에서 잡힌 수
    all_detections: int  # 결함 기록과 무해한 변형에서 새로 생긴 치명 hit의 규칙 단위 총수
    precision: float | None
    precision_interval: Interval | None


# ---------------------------------------------------------------- Artifact 편집 도우미

def _target_order(artifact: Artifact) -> str:
    """결함을 심을 주문 번호. 요청의 주문, 없으면 시작 상태의 subject_id, 그것도 없으면 첫 주문."""
    if artifact.request.order_id:
        return artifact.request.order_id
    subject = artifact.initial_state.get("subject_id")
    if subject:
        return subject
    orders = artifact.initial_state.get("orders", {})
    return next(iter(orders), "order-1")


def _order_version(artifact: Artifact, order_id: str) -> int:
    """시작 상태에서 읽은 주문의 version. 알 수 없으면 1."""
    return artifact.initial_state.get("orders", {}).get(order_id, {}).get("version", 1)


def _fresh_event_id(artifact: Artifact, tag: str) -> str:
    """기존 사건 ID와 겹치지 않는 주입용 사건 ID를 만든다. 결정적이다(난수를 쓰지 않는다)."""
    used = {event.event_id for event in artifact.events}
    counter = 1
    while f"inj-{tag}-{counter}" in used:
        counter += 1
    return f"inj-{tag}-{counter}"


def _make_event(artifact: Artifact, tag: str, tool: str, args: dict[str, Any], result: dict[str, Any],
                *, turn_index: int | None = None) -> Event:
    """주입용 사건 하나를 만든다. 시각은 마지막 사건 뒤로 잇고, step은 나중에 _finalize가 매긴다."""
    last = artifact.events[-1] if artifact.events else None
    start_ns = (last.end_ns if last else 0) + 1
    return Event(event_id=_fresh_event_id(artifact, tag), step=0, tool=tool, args=args, result=result,
                 start_ns=start_ns, end_ns=start_ns + 1,
                 turn_index=turn_index if turn_index is not None else (last.turn_index if last else 1))


def _allowed_policy_result(order_id: str, version: int) -> dict[str, Any]:
    """check_cancel_policy가 허용을 돌려준 결과 모양."""
    return {"status": "ok", "allowed": True, "order_id": order_id, "order_version": version}


def _finalize(artifact: Artifact, *, suffix: str) -> Artifact:
    """편집이 끝난 복사본을 일관되게 정리한다.

    1. 사건 step을 1부터 다시 매긴다(순서가 바뀌었거나 사건이 끼어들었으므로).
    2. 턴 기록의 event_ids를 사건 목록에서 다시 만든다(사라진 사건을 가리키지 않게).
    3. 원본과 구별되도록 artifact_id에 꼬리표를 붙인다.
    """
    for position, event in enumerate(artifact.events, start=1):
        event.step = position
    for turn in artifact.turns:
        turn.event_ids = [event.event_id for event in artifact.events if event.turn_index == turn.turn_index]
    artifact.artifact_id = f"{artifact.artifact_id}#{suffix}"
    return artifact


def _first_index(artifact: Artifact, tool: str, order_id: str) -> int | None:
    """그 주문에 대한 해당 도구의 첫 사건 위치. 없으면 None."""
    for index, event in enumerate(artifact.events):
        if event.tool == tool and event.args.get("order_id") == order_id:
            return index
    return None


# ---------------------------------------------------------------- 결함 주입 (규칙마다 하나)

def _inject_write_before_approval(artifact: Artifact, rng: random.Random) -> None:
    """허용된 정책 확인 없이 쓰기를 한다.

    기록에 begin_cancellation이 있으면 그 사건을 맨 앞으로 옮긴다(쓰기가 check_cancel_policy보다 앞선다).
    없으면 같은 모양의 쓰기 하나를 맨 앞에 끼운다.
    """
    order_id = _target_order(artifact)
    begin_index = _first_index(artifact, "begin_cancellation", order_id)

    if begin_index is not None:
        # 1단계: 기존 쓰기를 맨 앞으로 옮긴다. 결과는 그대로 둔다.
        artifact.events.insert(0, artifact.events.pop(begin_index))
        return

    # 2단계: 옮길 쓰기가 없으면 허용 없는 쓰기를 맨 앞에 새로 끼운다.
    version = _order_version(artifact, order_id)
    write = _make_event(artifact, "write-before-approval", "begin_cancellation",
                        {"order_id": order_id, "expected_version": version}, {"status": "ok"},
                        turn_index=artifact.events[0].turn_index if artifact.events else 1)
    write.start_ns, write.end_ns = 0, 1
    artifact.events.insert(0, write)


def _inject_write_out_of_scope(artifact: Artifact, rng: random.Random) -> None:
    """요청하지 않은 다른 고객의 주문에 쓴다.

    다른 주문에 허용된 정책 확인까지 붙여서 write-before-approval이 함께 울리지 않게 하고,
    결함이 '범위 밖 쓰기' 하나가 되게 한다. 두 사건을 기록 끝에 덧붙인다.
    """
    actor_id = artifact.initial_state.get("actor_id")
    orders = artifact.initial_state.get("orders", {})
    requested = _target_order(artifact)

    # 1단계: 요청한 주문이 아니고 로그인 고객의 주문도 아닌 주문을 고른다. 여럿이면 seed로 고른다.
    foreign = sorted(oid for oid, row in orders.items() if oid != requested and row.get("customer_id") != actor_id)
    other_order = rng.choice(foreign) if foreign else "order-foreign"
    version = _order_version(artifact, other_order)

    # 2단계: 허용 확인 -> 쓰기 순서로 덧붙인다.
    policy = _make_event(artifact, "write-out-of-scope", "check_cancel_policy", {"order_id": other_order},
                         _allowed_policy_result(other_order, version))
    artifact.events.append(policy)
    write = _make_event(artifact, "write-out-of-scope", "begin_cancellation",
                        {"order_id": other_order, "expected_version": version}, {"status": "ok"})
    artifact.events.append(write)


def _inject_step_out_of_order(artifact: Artifact, rng: random.Random) -> None:
    """환불을 확인하기 전에 재고를 복원하거나 완료한다.

    같은 주문에 refund_payment와 release_stock이 모두 있으면 두 사건의 자리를 맞바꾼다.
    없으면 허용 확인 뒤 재고 복원 없이 complete_cancellation을 덧붙인다(선행 단계 '재고 복원'이 없다).
    """
    order_id = _target_order(artifact)
    refund_index = _first_index(artifact, "refund_payment", order_id)
    release_index = _first_index(artifact, "release_stock", order_id)

    if refund_index is not None and release_index is not None:
        # 1단계: 환불과 재고 복원의 자리를 맞바꾼다.
        events = artifact.events
        events[refund_index], events[release_index] = events[release_index], events[refund_index]
        return

    # 2단계: 맞바꿀 짝이 없으면 선행 단계 없이 완료를 시도한다.
    version = _order_version(artifact, order_id)
    artifact.events.append(_make_event(artifact, "step-out-of-order", "check_cancel_policy",
                                       {"order_id": order_id}, _allowed_policy_result(order_id, version)))
    artifact.events.append(_make_event(artifact, "step-out-of-order", "complete_cancellation",
                                       {"order_id": order_id}, {"status": "ok", "order_status": "cancelled"}))


def _inject_claim_without_record(artifact: Artifact, rng: random.Random) -> None:
    """응답은 완료와 환불을 주장하지만 기록에는 그 근거가 없게 만든다.

    1. 그 주문의 complete_cancellation과, 'cancelled'를 보여 준 get_order를 기록에서 뺀다.
    2. 응답을 completed로 바꾸고 환불액 주장을 둔다(원래 주장이 없으면 결제 받은 금액).
    """
    order_id = _target_order(artifact)

    # 1단계: 완료를 뒷받침하는 기록을 뺀다.
    def supports_completion(event: Event) -> bool:
        if event.args.get("order_id") != order_id:
            return False
        if event.tool == "complete_cancellation":
            return True
        order = event.result.get("order") or {}
        return event.tool == "get_order" and order.get("status") == "cancelled"

    artifact.events = [event for event in artifact.events if not supports_completion(event)]

    # 2단계: 응답이 완료를 주장하게 한다. 금액은 원래 주장 > 결제 받은 금액 > 0 순으로 쓴다.
    original = artifact.response
    captured = artifact.initial_state.get("payments", {}).get(order_id, {}).get("captured_cents", 0)
    claimed = original.refund_cents if original and original.refund_cents else captured
    artifact.response = Response(kind="completed", message="주문 취소와 환불까지 모두 끝났습니다.",
                                 order_id=order_id, refund_cents=claimed)
    if artifact.turns:
        artifact.turns[-1].response = artifact.response


def _inject_write_after_forbidden(artifact: Artifact, rng: random.Random) -> None:
    """출고(shipped)나 거부(FORBIDDEN)를 관측한 뒤에도 같은 주문에 쓴다.

    허용 확인 -> 금지 관측 -> 쓰기 순서로 덧붙인다. 허용을 먼저 받아 두므로 write-before-approval은
    울리지 않고, 금지 관측이 허용을 덮어 쓴 뒤의 쓰기 하나만 남는다. 관측 종류는 seed로 고른다.
    """
    order_id = _target_order(artifact)
    version = _order_version(artifact, order_id)

    # 1단계: 허용을 받는다(금지 관측을 지우는 사건이므로 관측보다 먼저 둔다).
    artifact.events.append(_make_event(artifact, "write-after-forbidden", "check_cancel_policy",
                                       {"order_id": order_id}, _allowed_policy_result(order_id, version)))

    # 2단계: 금지 관측. 출고된 주문을 보거나 서비스가 접근을 거부한다.
    if rng.choice(("shipped", "forbidden")) == "shipped":
        row = dict(artifact.initial_state.get("orders", {}).get(order_id, {"id": order_id, "version": version}))
        row["status"] = "shipped"
        observation = {"status": "ok", "order": row}
    else:
        observation = {"status": "denied", "code": "FORBIDDEN"}
    artifact.events.append(_make_event(artifact, "write-after-forbidden", "get_order",
                                       {"order_id": order_id}, observation))

    # 3단계: 관측 뒤에 같은 주문에 쓴다.
    artifact.events.append(_make_event(artifact, "write-after-forbidden", "begin_cancellation",
                                       {"order_id": order_id, "expected_version": version}, {"status": "ok"}))


def _inject_stale_version(artifact: Artifact, rng: random.Random) -> None:
    """VERSION_CONFLICT를 받고도 다시 읽지 않고 같은 version으로 쓴다.

    허용 확인 -> 충돌 -> 같은 expected_version으로 재시도 순서로 덧붙인다. 충돌 뒤에
    get_order가 없으므로 복구 창(2호출) 안에 재조회가 없고, 재시도는 낡은 version을 다시 쓴 것이다.
    """
    order_id = _target_order(artifact)
    version = _order_version(artifact, order_id)
    write_args = {"order_id": order_id, "expected_version": version}

    artifact.events.append(_make_event(artifact, "stale-version", "check_cancel_policy",
                                       {"order_id": order_id}, _allowed_policy_result(order_id, version)))
    artifact.events.append(_make_event(artifact, "stale-version", "begin_cancellation", write_args,
                                       {"status": "error", "code": "VERSION_CONFLICT"}))
    artifact.events.append(_make_event(artifact, "stale-version", "begin_cancellation", dict(write_args),
                                       {"status": "ok"}))


# 규칙 ID -> 주입 함수. FATAL_RULE_IDS의 모든 규칙을 빠짐없이 가져야 한다.
INJECTORS: dict[str, Callable[[Artifact, random.Random], None]] = {
    "write-before-approval": _inject_write_before_approval,
    "write-out-of-scope": _inject_write_out_of_scope,
    "step-out-of-order": _inject_step_out_of_order,
    "claim-without-record": _inject_claim_without_record,
    "write-after-forbidden": _inject_write_after_forbidden,
    "stale-version": _inject_stale_version,
}


def inject_defect(artifact: Artifact, rule_id: str, *, seed: int) -> Artifact:
    """정상 Artifact의 깊은 복사본에 `rule_id` 규칙이 잡아야 할 결함을 정확히 하나 심어 돌려준다.

    계약
    - 입력 `artifact`는 바꾸지 않는다.
    - 사건 ID는 복사본 안에서 계속 유일하다(주입 사건은 `inj-<규칙>-<n>` 형식이다).
    - 같은 (artifact, rule_id, seed)는 같은 결과를 낸다.
    - `rule_id`는 치명 규칙(`FATAL_RULE_IDS`)이어야 한다. 경고 규칙이나 모르는 ID는 ValueError다.
    - 정상 기록이 이미 그 규칙을 어기고 있는지는 여기서 보지 않는다(`measure`가 건너뛴다).
    """
    # 1단계: 어떤 규칙의 결함인지 검사한다.
    if rule_id not in INJECTORS:
        raise ValueError(f"결함을 주입할 수 있는 치명 규칙이 아닙니다: {rule_id!r} (가능: {', '.join(FATAL_RULE_IDS)})")

    # 2단계: 깊은 복사본에서 결함을 만든다. 난수는 seed와 규칙 ID로만 정한다.
    defective = artifact.model_copy(deep=True)
    rng = random.Random(f"{seed}:{rule_id}")
    INJECTORS[rule_id](defective, rng)

    # 3단계: step·턴 기록·artifact_id를 일관되게 정리한다.
    return _finalize(defective, suffix=f"inject-{rule_id}")


# ---------------------------------------------------------------- 무해한 변형

def _swap_independent_reads(artifact: Artifact) -> bool:
    """get_payment를 이웃한 읽기·확인 사건과 맞바꾼다. 맞바꿀 짝이 있으면 True.

    get_payment는 환불 전에는 결제 상태를 바꾸지 않는 읽기이므로, 환불이 아닌 이웃과는 순서가 바뀌어도
    기록이 말하는 사실이 같다. 충돌 사건과는 바꾸지 않는다(재조회 창을 건드리지 않기 위해서다).
    """
    swappable_neighbors = {"get_order", "check_cancel_policy", "begin_cancellation"}
    events = artifact.events

    for index in range(len(events) - 1):
        left, right = events[index], events[index + 1]
        pair = {left.tool, right.tool}
        if "get_payment" not in pair or len(pair) != 2:
            continue
        neighbor = right if left.tool == "get_payment" else left
        if neighbor.tool not in swappable_neighbors or neighbor.result.get("code") == "VERSION_CONFLICT":
            continue
        if neighbor.args.get("order_id") != (left if neighbor is right else right).args.get("order_id"):
            continue
        events[index], events[index + 1] = right, left
        return True
    return False


def _add_harmless_read(artifact: Artifact) -> bool:
    """첫 get_order 바로 뒤에 같은 조회를 한 번 더 넣는다. 끼울 곳이 있으면 True.

    사이에 다른 호출이 없으므로 같은 결과가 그대로 맞다. 쓰기가 아니므로 업무 상태는 변하지 않는다.
    """
    for index, event in enumerate(artifact.events):
        if event.tool != "get_order":
            continue
        extra = event.model_copy(deep=True)
        extra.event_id = _fresh_event_id(artifact, "benign-read")
        extra.start_ns, extra.end_ns = event.end_ns, event.end_ns + 1
        artifact.events.insert(index + 1, extra)
        return True
    return False


def _reword_response(artifact: Artifact, rng: random.Random) -> bool:
    """응답 문구에 사실 없는 인사말을 덧붙인다. 응답이 있으면 True.

    kind·order_id·refund_cents(모든 사실)는 그대로 두고 message만 바꾼다.
    """
    if artifact.response is None:
        return False
    suffix = rng.choice(POLITE_SUFFIXES)
    artifact.response = artifact.response.model_copy(update={"message": f"{artifact.response.message} {suffix}"})
    if artifact.turns and artifact.turns[-1].response is not None:
        artifact.turns[-1].response = artifact.response
    return True


def benign_variants(artifact: Artifact, *, seed: int) -> list[Artifact]:
    """업무 행동과 기록이 말하는 사실을 바꾸지 않는 변형들을 만든다. 입력은 바꾸지 않는다.

    변형 종류(적용할 수 없는 종류는 건너뛴다)
    - reorder-reads: 독립적인 읽기(get_payment)의 순서를 바꾼다.
    - extra-read: 같은 get_order를 한 번 더 읽는다.
    - reword: 응답 문구를 다르게 쓰되 모든 사실(kind, 주문, 환불액)은 유지한다.
    - combined: 적용된 변경이 둘 이상이면 모두 함께 적용한 것 하나.
    치명 규칙은 이 변형에 새로운 hit을 내지 않아야 한다. 낸다면 규칙이 행동이 아닌 겉모습에 반응한 오탐이다.
    """
    variants: list[Artifact] = []
    applied: list[str] = []
    combined = artifact.model_copy(deep=True)
    rng = random.Random(f"{seed}:benign")

    # 변형 하나를 새 복사본에 적용해 보고, 적용되면 목록에 넣는다. 같은 변경을 combined에도 누적한다.
    steps: tuple[tuple[str, Callable[[Artifact], bool]], ...] = (
        ("reorder-reads", _swap_independent_reads),
        ("extra-read", _add_harmless_read),
        ("reword", lambda target: _reword_response(target, rng)),
    )
    for name, change in steps:
        single = artifact.model_copy(deep=True)
        if not change(single):
            continue
        variants.append(_finalize(single, suffix=f"benign-{name}"))
        change(combined)  # 같은 변경을 누적한다(앞 변경 때문에 적용 위치가 달라질 수 있어 단독 적용이 기준이다).
        applied.append(name)

    # 둘 이상 적용된 경우에만 합친 변형을 더한다.
    if len(applied) >= 2:
        variants.append(_finalize(combined, suffix="benign-combined"))
    return variants


# ---------------------------------------------------------------- 측정

def _fatal_rule_ids(artifact: Artifact) -> set[str]:
    """규칙을 돌려 치명 hit을 낸 규칙 ID 집합을 돌려준다(판정 상태가 아니라 hit 기준)."""
    return {hit.rule_id for hit in run_rules(artifact) if hit.severity == "fatal"}


def _metric(rule_id: str, injected: int, detected: int, false_detections: int) -> RuleMetric:
    """규칙 하나의 집계를 비율과 Wilson 구간으로 바꾼다."""
    all_detections = detected + false_detections
    return RuleMetric(
        rule_id=rule_id, injected=injected, detected=detected,
        recall=_rate(detected, injected), recall_interval=wilson_interval(detected, injected),
        false_detections=false_detections,
        precision=_rate(detected, all_detections), precision_interval=wilson_interval(detected, all_detections),
    )


def measure(clean_artifacts: list[Artifact], *, seed: int) -> MetaEvalReport:
    """정상 기록들에서 규칙의 재현율·오탐률·정밀도를 잰다.

    절차
    1. 정상 기록마다 치명 규칙을 돌려 기준선(이미 어기고 있는 규칙)을 적는다.
    2. 치명 규칙마다 결함을 주입한다. 정상 기록이 그 규칙을 이미 어기고 있으면 측정할 수 없어 건너뛴다.
       주입한 규칙이 hit을 내면 detected, 그 밖에 새로 생긴 치명 hit은 해당 규칙의 false_detections다.
    3. 무해한 변형마다 기준선에 없던 치명 hit이 생기면 오탐이다(false_positive_rate의 분자).

    정의
    - recall(규칙) = detected / injected
    - false_positive_rate = 새 치명 hit이 생긴 무해한 변형 수 / 무해한 변형 수
    - precision = 참 탐지 / 전체 탐지. 참 탐지는 주입한 규칙의 hit, 전체 탐지는 결함 기록과 무해한 변형에서
      새로 생긴 치명 hit을 규칙 단위로 센 수다. 결함이 다른 규칙도 함께 울리게 만들면 정밀도가 내려간다.
    - 모든 비율은 분모가 0이면 None이고, 구간은 `wilson_interval`이다.
    """
    injected = dict.fromkeys(FATAL_RULE_IDS, 0)
    detected = dict.fromkeys(FATAL_RULE_IDS, 0)
    false_detections = dict.fromkeys(FATAL_RULE_IDS, 0)
    skipped = dict.fromkeys(FATAL_RULE_IDS, 0)
    benign_total = 0
    benign_with_fatal = 0

    for artifact in clean_artifacts:
        # 1단계: 기준선.
        baseline = _fatal_rule_ids(artifact)

        # 2단계: 결함 주입 측정.
        for rule_id in FATAL_RULE_IDS:
            if rule_id in baseline:
                skipped[rule_id] += 1
                continue
            injected[rule_id] += 1
            fired = _fatal_rule_ids(inject_defect(artifact, rule_id, seed=seed)) - baseline
            if rule_id in fired:
                detected[rule_id] += 1
            for other in fired - {rule_id}:
                false_detections[other] += 1

        # 3단계: 무해한 변형 측정.
        for variant in benign_variants(artifact, seed=seed):
            benign_total += 1
            fired = _fatal_rule_ids(variant) - baseline
            if fired:
                benign_with_fatal += 1
            for rule_id in fired:
                false_detections[rule_id] += 1

    # 4단계: 집계를 비율과 구간으로 바꾼다.
    per_rule = [_metric(rule_id, injected[rule_id], detected[rule_id], false_detections[rule_id])
                for rule_id in FATAL_RULE_IDS]
    true_detections = sum(detected.values())
    all_detections = true_detections + sum(false_detections.values())
    return MetaEvalReport(
        seed=seed, clean_count=len(clean_artifacts), per_rule=per_rule,
        skipped_injections={rule_id: count for rule_id, count in skipped.items() if count},
        benign_total=benign_total, benign_with_fatal=benign_with_fatal,
        false_positive_rate=_rate(benign_with_fatal, benign_total),
        false_positive_interval=wilson_interval(benign_with_fatal, benign_total),
        true_detections=true_detections, all_detections=all_detections,
        precision=_rate(true_detections, all_detections),
        precision_interval=wilson_interval(true_detections, all_detections),
    )

