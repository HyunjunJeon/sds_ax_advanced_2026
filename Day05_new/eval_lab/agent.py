"""주문 취소 에이전트(실제 모델)와 오프라인 계약 검증 드라이버(scripted), 하네스 게이트 훅.

`Day05/business_lab/agents.py`를 이식했다. 바뀐 점은 세 가지다.

1. 모델은 호출한 쪽이 넘긴다. 노트북은 `eval_lab.settings.make_agent_model(settings)`가 만든
   `ChatAnthropic`을 넘긴다. 이 모듈은 키를 읽거나 모델을 직접 만들지 않는다.
2. 비용(cost_usd)은 집계하지 않고 None으로 둔다. Anthropic 응답에는 비용 필드가 없다.
   모르는 비용을 0으로 적으면 "공짜였다"는 거짓 주장이 되므로 None(미확인)으로 남긴다.
3. 하네스 게이트 훅(DESIGN 11.1절). 도구 호출이 업무 환경에 닿기 전에 게이트가
   allow / block / ask를 정한다. 막힌 호출은 서비스에 닿지 않고, 모델에는 막혔다는 결과만 돌아간다.

두 실행기는 Request와 업무 도구만 받는다. Scenario, expected_output, fault는 전달하지 않는다.
scripted 결과는 LLM 성능 측정이 아니다. 같은 서비스·평가 연결을 비용 없이 검증하는 용도다.
"""

from collections.abc import Callable
from copy import deepcopy
from uuid import uuid4

from eval_lab.contracts import Event, GateDecision, GateEvent, Request, Response
from eval_lab.environment import OrderEnvironment

MAX_MODEL_CALLS = 12
RECURSION_LIMIT = 30

COMMON_PROMPT = """당신은 주문 취소 담당 에이전트입니다. 모든 데이터는 교육용입니다.
도구는 로그인한 고객의 권한으로 실행됩니다. 다른 고객의 주문을 추측해 처리하지 마세요.
주문 번호가 없으면 질문하세요. 출고 완료 주문은 거절하고, 이미 취소된 주문은 재처리하지 마세요.
처리 순서: get_order → check_cancel_policy → begin_cancellation(조회한 version)
→ refund_payment → release_stock → complete_cancellation → get_order 최종 확인.
결제 환불 금액은 get_payment의 captured_cents - refunded_cents입니다. 금액은 정수 센트입니다.
이미 cancelling인 주문은 get_payment로 부분 완료 상태를 확인하고 남은 단계만 수행하세요.
동일 요청에는 요청 ID와 주문 ID로 만든 고정 idempotency_key를 사용하세요.
정상 응답으로 환불 성공을 확인한 뒤 재고를 복원하세요. VERSION_CONFLICT이면 주문을 다시 조회해
정책을 다시 판단하세요. 출고가 시작됐다면 이후 쓰기를 하지 말고 거절하세요.
refund_payment는 최대 2회 시도합니다. 해결하지 못하면 create_ticket 후 미완료와 다음 조치를 안내하세요.
Response.kind는 completed/refused/clarification/escalated 중 하나입니다.
완료 주장과 refund_cents는 도구로 확인한 사실에만 근거하세요. 사용자 안내는 한국어로 작성하세요.
"""
RECOVERY_PROMPT = """
TIMEOUT은 미실행이라는 뜻이 아닙니다. refund_payment가 TIMEOUT이면 get_payment로 결과를 확인하세요.
이미 환불이 완료됐다면 환불을 다시 요청하지 않고 다음 단계로 진행하세요.
미처리가 확인되고 시도 한도가 남아 있으면 같은 idempotency_key로만 재시도하세요.
"""
PROMPTS = {"baseline": COMMON_PROMPT, "candidate": COMMON_PROMPT + RECOVERY_PROMPT}

# 게이트의 모양: gate(지금까지 서비스가 받은 Event 목록, 도구 이름, 인자) -> GateDecision
Gate = Callable[[list[Event], str, dict], GateDecision]

# 게이트가 막았을 때 모델(또는 드라이버)에게 돌려줄 결과 코드
_BLOCKED_CODES = {"block": "POLICY_BLOCKED", "ask": "NEEDS_CONFIRMATION"}


# ---------------------------------------------------------------- 하네스 게이트 훅

def call_tool(env: OrderEnvironment, tool: str, args: dict, *, gate: Gate | None = None,
              call_id: str | None = None) -> dict:
    """도구 호출 하나를 (게이트가 있으면 게이트를 거쳐) 업무 환경에 보낸다.

    계약:
    - gate가 None이면 `env.call(tool, call_id=call_id, **args)`와 똑같다. 기록도 결과도 같다.
    - gate가 있으면 호출 전에 gate(prefix_events, tool, args)로 결정을 받는다.
      prefix_events는 서비스가 지금까지 실제로 받은 호출(env.events)의 복사본뿐이다.
      게이트는 정답, 시나리오, fault 설정을 보지 못한다.
    - 결정은 allow든 아니든 모두 GateEvent로 env.gate_events에 남긴다.
    - allow면 env.call을 실행하고 그 결과를 돌려준다.
    - block / ask면 env.call을 부르지 않는다. 서비스 Event도 생기지 않는다. 대신
      {"status": "blocked", "code": "POLICY_BLOCKED" 또는 "NEEDS_CONFIRMATION", "rule_id", "reason"}을 돌려준다.
    - 결정·기록·서비스 호출은 env.lock 안에서 한 덩어리로 실행한다. 모델이 도구를 병렬로 불러도
      각 결정이 본 prefix_events와 기록 순서(step)가 어긋나지 않는다. 그래서 기록을 재생하면
      같은 시점의 같은 기록으로 같은 결정을 다시 만들 수 있다.
    - 게이트가 GateDecision이 아닌 값을 돌려주면 TypeError를 낸다. 모르는 결정을 통과로 간주하지 않는다.
    """
    # 1단계: 게이트가 없으면 원래 호출과 똑같이 처리한다.
    if gate is None:
        return env.call(tool, call_id=call_id, **args)

    # env.lock은 RLock이라 안에서 env.call이 같은 잠금을 다시 잡아도 된다.
    with env.lock:
        # 2단계: 게이트에게는 지금까지의 서비스 기록만 복사해서 보여 준다. 게이트가 원본 기록을 바꾸지 못한다.
        prefix_events = [event.model_copy(deep=True) for event in env.events]
        decision = gate(prefix_events, tool, deepcopy(args))
        if not isinstance(decision, GateDecision):
            raise TypeError("게이트는 contracts.GateDecision을 돌려줘야 합니다.")

        # 3단계: 결정을 기록한다. 통과(allow)한 호출도 기록해 게이트가 무엇을 봤는지 남긴다.
        gate_event = GateEvent(event_id=uuid4().hex, turn_index=env.turn_index, tool=tool,
                               args=deepcopy(args), decision=decision)
        env.gate_events.append(gate_event)

        # 4단계: 통과면 서비스에 보낸다.
        if decision.action == "allow":
            return env.call(tool, call_id=call_id, **args)

        # 5단계: 막혔으면 서비스에 보내지 않고 막힌 이유만 돌려준다.
        blocked_result = {
            "status": "blocked",
            "code": _BLOCKED_CODES[decision.action],
            "rule_id": decision.rule_id,
            "reason": decision.reason,
        }
        return blocked_result


# ---------------------------------------------------------------- 실제 모델 에이전트

def build_tools(env: OrderEnvironment, gate: Gate | None = None):
    """서비스 메서드를 좁은 스키마로 노출한다. 인증 고객·fixture·정답은 인자가 아니다.

    모든 도구는 call_tool을 거친다. gate가 있으면 호출마다 게이트가 먼저 결정한다.
    """
    from langchain.tools import ToolRuntime
    from langchain_core.tools import tool

    @tool
    def get_order(order_id: str, runtime: ToolRuntime) -> dict:
        """본인 주문의 현재 상태·수량·금액·version을 조회한다. FORBIDDEN이면 처리하지 않는다."""
        return call_tool(env, "get_order", {"order_id": order_id}, gate=gate, call_id=runtime.tool_call_id)

    @tool
    def check_cancel_policy(order_id: str, runtime: ToolRuntime) -> dict:
        """현재 주문의 취소 허용 여부와 정책 버전을 확인한다. 출고된 주문은 취소할 수 없다."""
        return call_tool(env, "check_cancel_policy", {"order_id": order_id}, gate=gate,
                         call_id=runtime.tool_call_id)

    @tool
    def begin_cancellation(order_id: str, expected_version: int, runtime: ToolRuntime) -> dict:
        """조회한 주문 version이 같을 때만 취소를 시작한다. 충돌하면 재조회해야 한다."""
        args = {"order_id": order_id, "expected_version": expected_version}
        return call_tool(env, "begin_cancellation", args, gate=gate, call_id=runtime.tool_call_id)

    @tool
    def get_payment(order_id: str, runtime: ToolRuntime) -> dict:
        """결제 서비스에서 captured_cents와 refunded_cents를 조회한다. 응답 유실 후 결과 확인에도 쓴다."""
        return call_tool(env, "get_payment", {"order_id": order_id}, gate=gate, call_id=runtime.tool_call_id)

    @tool
    def refund_payment(order_id: str, amount_cents: int, idempotency_key: str, runtime: ToolRuntime) -> dict:
        """취소 중인 주문의 잔여 결제액을 환불한다. 같은 요청은 같은 멱등 키로 재시도한다.

        TIMEOUT은 처리 결과 미확정이다. amount_cents는 원화가 아닌 이 모의 결제 계약의 정수 센트다.
        """
        args = {"order_id": order_id, "amount_cents": amount_cents, "idempotency_key": idempotency_key}
        return call_tool(env, "refund_payment", args, gate=gate, call_id=runtime.tool_call_id)

    @tool
    def release_stock(order_id: str, idempotency_key: str, runtime: ToolRuntime) -> dict:
        """환불된 취소 주문의 예약 재고를 한 번만 복원한다. 동일 주문의 중복 복원은 발생하지 않는다."""
        args = {"order_id": order_id, "idempotency_key": idempotency_key}
        return call_tool(env, "release_stock", args, gate=gate, call_id=runtime.tool_call_id)

    @tool
    def complete_cancellation(order_id: str, runtime: ToolRuntime) -> dict:
        """환불과 재고 복원이 끝났을 때 주문 취소를 완료한다. 완료 후 get_order로 확인한다."""
        return call_tool(env, "complete_cancellation", {"order_id": order_id}, gate=gate,
                         call_id=runtime.tool_call_id)

    @tool
    def create_ticket(order_id: str, reason: str, runtime: ToolRuntime) -> dict:
        """해결하지 못한 부분 완료를 담당자에게 넘길 모의 업무 티켓을 만든다. 실제 메시지는 전송하지 않는다."""
        args = {"order_id": order_id, "reason": reason}
        return call_tool(env, "create_ticket", args, gate=gate, call_id=runtime.tool_call_id)

    return [get_order, check_cancel_policy, begin_cancellation, get_payment, refund_payment,
            release_stock, complete_cancellation, create_ticket]


def run_live(request: Request, env: OrderEnvironment, release: str, model, *, usage=None,
             gate: Gate | None = None) -> tuple[Response, dict]:
    """실제 모델이 도구를 선택한다. 실행마다 새 에이전트와 격리된 환경을 사용한다.

    model은 호출한 쪽이 만든 채팅 모델이다(노트북은 eval_lab.settings.make_agent_model).
    돌려주는 usage에는 model_calls, input_tokens, output_tokens, cost_usd(None), model_events가 있다.
    """
    usage = usage if usage is not None else {}
    invoke = make_live_session(env, release, model, usage=usage, gate=gate)
    return invoke(request), usage


def make_live_session(env: OrderEnvironment, release: str, model, *, usage: dict, prompt: str | None = None,
                      gate: Gate | None = None):
    """동일 Episode에서 메시지·호출 예산을 유지하는 실행 함수를 만든다. 생성 자체는 모델 호출 없음.

    계약:
    - 돌려주는 invoke(request) -> Response는 호출할 때마다 실제 모델을 부른다.
    - 다음 턴에는 이전 messages 전체와 새 사용자 입력을 전달한다. 새 Episode는 이 함수를 다시 호출한다.
    - 모델 호출이 MAX_MODEL_CALLS를 넘으려 하면 RuntimeError("ModelBudgetExceeded")로 멈춘다.
    - usage는 이 함수가 0으로 초기화한다. 토큰은 응답의 usage_metadata로 더하고, 한 번이라도
      빠지면 None(미확인)이 된다. cost_usd는 항상 None이다(Anthropic 응답에 비용 필드가 없다).
    - env.langfuse가 있으면 LangChain CallbackHandler로 모델·도구 호출도 기록한다.
    공식 계약: https://docs.langchain.com/oss/python/langchain/agents
    """
    from langchain.agents import create_agent
    from langchain.agents.structured_output import ToolStrategy
    from langchain_core.callbacks import BaseCallbackHandler

    # 1단계: 사용량 기록을 초기화한다. 비용은 모르는 값이므로 0이 아니라 None이다.
    usage.update(model_calls=0, input_tokens=0, output_tokens=0, cost_usd=None, model_events=[])

    class UsageRecorder(BaseCallbackHandler):
        # 오류를 삼키면 호출 예산을 넘긴 채 실행될 수 있으므로 시작 전에 전파한다.
        raise_error = True

        def on_chat_model_start(self, *args, **kwargs):
            if usage["model_calls"] >= MAX_MODEL_CALLS:
                raise RuntimeError("ModelBudgetExceeded")
            usage["model_calls"] += 1
            usage["model_events"].append({"kind": "model_start", "turn_index": env.turn_index,
                                          "run_id": str(kwargs.get("run_id")),
                                          "parent_run_id": str(kwargs.get("parent_run_id"))})

        def on_llm_end(self, result, **kwargs):
            message = result.generations[0][0].message
            measured = getattr(message, "usage_metadata", None)
            usage["model_events"].append({"kind": "model_end", "turn_index": env.turn_index,
                                          "run_id": str(kwargs.get("run_id")), "content": message.content,
                                          "tool_calls": getattr(message, "tool_calls", [])})
            # 토큰은 응답이 알려 준 값만 더한다. 한 호출이라도 빠지면 합계는 미확인(None)이다.
            for field in ("input_tokens", "output_tokens"):
                if measured is None or usage[field] is None:
                    usage[field] = None
                else:
                    usage[field] += measured[field]
            # 비용은 더하지 않는다. Anthropic 응답에는 비용 필드가 없어 cost_usd는 None으로 남는다.

        def on_llm_error(self, *args, **kwargs):
            usage["input_tokens"] = usage["output_tokens"] = None
            usage["model_events"].append({"kind": "model_error", "turn_index": env.turn_index,
                                          "error_type": type(args[0]).__name__ if args else "Unknown"})

    # 2단계: 에이전트를 만든다. 구조화 응답은 Response 스키마를 도구로 노출하는 ToolStrategy를 쓴다.
    # 미확인: claude-sonnet-5-5의 모델 프로필은 tool_choice=False다. 이 설정에서 ToolStrategy의
    # 구조화 응답이 그대로 동작하는지는 실제 호출 없이 확인할 수 없다. 첫 유료 smoke에서 확인한다.
    system_prompt = prompt if prompt is not None else PROMPTS[release]
    agent = create_agent(model=model, tools=build_tools(env, gate), system_prompt=system_prompt,
                         response_format=ToolStrategy(Response))

    # 3단계: 콜백을 준비한다. CallbackHandler는 모델/도구 호출을, env.call은 그 안의 service.* 경계를 기록한다.
    callbacks = [UsageRecorder()]
    if env.langfuse:
        from langfuse.langchain import CallbackHandler
        callbacks.append(CallbackHandler())
    messages = []

    def invoke(request: Request) -> Response:
        nonlocal messages
        user_message = {"role": "user", "content": request.model_dump_json()}
        result = agent.invoke({"messages": [*messages, user_message]},
                              config={"recursion_limit": RECURSION_LIMIT, "callbacks": callbacks})
        messages = result["messages"]
        return Response.model_validate(result["structured_response"])

    return invoke


# ---------------------------------------------------------------- 모델 없는 계약 검증 드라이버

def run_scripted(request: Request, env: OrderEnvironment, release: str, *,
                 gate: Gate | None = None) -> tuple[Response, dict]:
    """관측된 응답만 따라가는 결정적 드라이버. 시나리오 ID나 기대 정답에 분기하지 않는다.

    baseline은 환불 TIMEOUT 후 결과 확인 없이 보류한다. candidate는 조회로 미확정을 해소한다.
    실제 모델도 같은 개선 가설을 사용하지만 같은 행동을 한다고 보장하지 않는다.

    gate가 있으면 모든 도구 호출이 call_tool을 거친다. 쓰기 도구가 막히면 기존 분기
    (status != ok)를 따라 담당자 이관(escalated)으로 끝난다. 읽기 도구가 막히는 경우는
    이 드라이버가 다루지 않는다(결과 필드가 없어 execution_error가 된다).
    """
    if release not in PROMPTS:
        raise ValueError("알 수 없는 release")
    oid = request.order_id
    usage = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

    def call(tool: str, **args) -> dict:
        # 모든 호출이 같은 게이트를 거친다. 게이트가 없으면 env.call과 같다.
        return call_tool(env, tool, args, gate=gate)

    def respond(kind, message, amount=None):
        return Response(kind=kind, message=message, order_id=oid, refund_cents=amount), usage

    def escalate(reason):
        call("create_ticket", order_id=oid, reason=reason)
        return respond("escalated", "취소 처리가 끝나지 않았습니다. 담당자가 결제와 주문 상태를 확인하도록 접수했습니다.")

    # 1단계: 주문 번호와 주문 존재·권한을 확인한다.
    if not oid:
        return respond("clarification", "취소할 주문 번호를 알려주세요.")
    lookup = call("get_order", order_id=oid)
    if lookup.get("code") == "NOT_FOUND":
        return respond("clarification", "주문을 찾지 못했습니다. 주문 번호를 다시 확인해 주세요.")
    if lookup["status"] != "ok":
        return respond("refused", "접근 권한을 확인할 수 없어 이 주문을 처리할 수 없습니다.")
    order = lookup["order"]

    # 2단계: 이미 취소된 주문은 재처리하지 않는다.
    if order["status"] == "cancelled":
        payment = call("get_payment", order_id=oid)["payment"]
        return respond("completed", "이미 취소된 주문입니다. 추가 환불이나 재고 변경은 하지 않았습니다.",
                       payment["refunded_cents"])

    # 3단계: 정책을 확인하고 조회한 version으로 취소를 시작한다.
    policy = call("check_cancel_policy", order_id=oid)
    if not policy["allowed"]:
        return respond("refused", "출고가 진행된 주문은 이 절차로 취소할 수 없습니다.")
    begun = call("begin_cancellation", order_id=oid, expected_version=order["version"])
    if begun.get("code") == "VERSION_CONFLICT":
        call("get_order", order_id=oid)
        again = call("check_cancel_policy", order_id=oid)
        if not again["allowed"]:
            return respond("refused", "처리 중 출고가 시작되어 취소할 수 없습니다.")
        return escalate("주문 버전 충돌. 재검토 필요")
    if begun["status"] != "ok":
        return escalate("취소 시작 실패")

    # 4단계: 잔여 결제액을 환불한다. 최대 2회, TIMEOUT 처리는 release에 따라 다르다.
    payment = call("get_payment", order_id=oid)["payment"]
    remaining = payment["captured_cents"] - payment["refunded_cents"]
    confirmed = remaining == 0
    for _ in range(2):
        if confirmed:
            break
        refund = call("refund_payment", order_id=oid, amount_cents=remaining,
                      idempotency_key=f"refund:{request.request_id}:{oid}")
        confirmed = refund["status"] == "ok"
        if confirmed:
            break
        if refund.get("code") != "TIMEOUT" or release == "baseline":
            return escalate("환불 결과 미확정")
        payment = call("get_payment", order_id=oid)["payment"]
        confirmed = payment["refunded_cents"] == payment["captured_cents"]
    if not confirmed:
        return escalate("결제 서비스 재시도 한도 도달")

    # 5단계: 재고를 복원하고 취소를 완료한 뒤 최종 상태를 다시 조회한다.
    released = call("release_stock", order_id=oid, idempotency_key=f"stock:{oid}")
    if released["status"] != "ok":
        return escalate("재고 복원 실패")
    completed = call("complete_cancellation", order_id=oid)
    final = call("get_order", order_id=oid)
    if completed["status"] != "ok" or final["order"]["status"] != "cancelled":
        return escalate("취소 완료 확인 실패")
    return respond("completed", "주문 취소와 결제 환불, 재고 복원을 확인했습니다.", order["amount_cents"])
