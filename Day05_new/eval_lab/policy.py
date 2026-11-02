"""선언형 하네스 정책: 명세(JSON)를 검증하고, 고정된 해석기로 도구 호출을 allow·block·ask로 가른다.

정책은 데이터다. 개선기 모델은 이 모듈이 아는 네 가지 규칙 모양만 만들 수 있고 코드는 만들지 못한다.
명세에 해석기 밖의 키·도구 이름·규칙 종류가 있으면 PolicyRejected로 형식 단계에서 거부한다.
문턱값·예산·Dataset·파일 경로 같은 평가 쪽 키도 같은 이유로 거부된다(PREREG P7).
이 모듈은 외부 호출을 하지 않는다.

결정은 호출 시점 앞까지의 서비스 Event(prefix_events)만 보고 내린다.
"""

import json
from collections.abc import Callable
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from eval_lab.contracts import Event, GateDecision
from eval_lab.environment import TOOL_NAMES

# 에이전트 게이트의 모양: gate(prefix_events, tool, args) -> GateDecision
PolicyGate = Callable[[list[Event], str, dict], GateDecision]


class PolicyRejected(Exception):
    """정책 명세가 형식 검사를 통과하지 못했다. reason에 한국어 이유가 들어 있다."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _check_tool_name(name: str) -> str:
    """도구 이름이 업무 환경의 도구 목록에 있는지 확인한다."""
    if name not in TOOL_NAMES:
        raise ValueError(f"알 수 없는 도구 이름입니다: {name!r} (허용: {', '.join(sorted(TOOL_NAMES))})")
    return name


class _Rule(BaseModel):
    """모든 규칙의 공통 부분. 모르는 키는 거부하고, 위반 시 행동은 block(기본) 또는 ask다."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["block", "ask"] = "block"


class RequireBefore(_Rule):
    """tool을 부르기 전에 requires_tool 성공 호출이 앞서 있어야 한다(기본은 같은 주문)."""

    kind: Literal["require_before"]
    tool: str
    requires_tool: str
    same_order: bool = True

    @field_validator("tool", "requires_tool")
    @classmethod
    def known_tool(cls, value: str) -> str:
        return _check_tool_name(value)


class BlockAfter(_Rule):
    """같은 주문에서 on_code 결과를 관측한 뒤에는 tools를 막는다.

    on_code는 결과의 status('denied'), code('FORBIDDEN'), 또는 get_order가 본 주문 상태('shipped')와 비교한다.
    """

    kind: Literal["block_after"]
    on_code: str = Field(min_length=1)
    tools: list[str] = Field(min_length=1)

    @field_validator("tools")
    @classmethod
    def known_tools(cls, values: list[str]) -> list[str]:
        return [_check_tool_name(value) for value in values]


class MaxAttempts(_Rule):
    """같은 주문에서 tool을 부른 횟수가 limit에 이르면 다음 호출을 막는다."""

    kind: Literal["max_attempts"]
    tool: str
    limit: int = Field(ge=1)

    @field_validator("tool")
    @classmethod
    def known_tool(cls, value: str) -> str:
        return _check_tool_name(value)


class RequireCheckAfterTimeout(_Rule):
    """같은 주문에서 tool이 TIMEOUT을 낸 뒤, check_tool을 부르기 전에는 tool 재호출을 막는다."""

    kind: Literal["require_check_after_timeout"]
    tool: str
    check_tool: str

    @field_validator("tool", "check_tool")
    @classmethod
    def known_tool(cls, value: str) -> str:
        return _check_tool_name(value)


Rule = Annotated[RequireBefore | BlockAfter | MaxAttempts | RequireCheckAfterTimeout, Field(discriminator="kind")]


class PolicySpec(BaseModel):
    """정책 명세 전체. rules는 앞에서부터 보고 처음 걸린 규칙이 이긴다."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    rules: list[Rule]


# 시작 정책 r0: 규칙이 없으므로 모든 호출을 허용한다.
EMPTY_POLICY = PolicySpec(version="r0", rules=[])


# ---------------------------------------------------------------- 검증

def _korean_reason(error: ValidationError) -> str:
    """pydantic 오류를 한국어 이유 한 덩어리로 바꾼다."""
    parts = []
    for item in error.errors():
        where = ".".join(str(p) for p in item["loc"]) or "(최상위)"
        kind = item["type"]
        if kind == "extra_forbidden":
            parts.append(f"{where}: 해석기가 모르는 키입니다. 허용된 키만 쓸 수 있습니다.")
        elif kind in {"union_tag_invalid", "union_tag_not_found"}:
            parts.append(f"{where}: 허용되지 않는 규칙 종류입니다. "
                         "require_before, block_after, max_attempts, require_check_after_timeout만 쓸 수 있습니다.")
        elif kind == "value_error":
            parts.append(f"{where}: {item['ctx']['error']!s}")
        else:
            parts.append(f"{where}: 형식이 맞지 않습니다({item['msg']}).")
    return " / ".join(parts)


def validate_spec(obj: dict | str) -> PolicySpec:
    """JSON 문자열 또는 dict를 PolicySpec으로 검증한다. 형식이 틀리면 PolicyRejected(한국어 이유)를 낸다."""
    # 1단계: 문자열이면 JSON으로 읽는다.
    if isinstance(obj, str):
        try:
            obj = json.loads(obj)
        except json.JSONDecodeError as exc:
            raise PolicyRejected(f"JSON으로 읽을 수 없습니다: {exc.msg}") from exc
    if not isinstance(obj, dict):
        raise PolicyRejected("정책 명세는 JSON 객체여야 합니다.")

    # 2단계: 모델 검증. 모르는 키·도구·규칙 종류는 여기서 거부된다.
    try:
        return PolicySpec.model_validate(obj)
    except ValidationError as exc:
        raise PolicyRejected(_korean_reason(exc)) from exc


# ---------------------------------------------------------------- 해석기

def _order_of(args: dict) -> Any:
    """호출 인자에서 주문 ID를 꺼낸다. 없으면 None."""
    return args.get("order_id")


def _same_order(event: Event, order_id: Any) -> bool:
    """서비스 Event가 같은 주문에 대한 것인지 본다."""
    return _order_of(event.args) == order_id


def _observed(event: Event, on_code: str) -> bool:
    """결과가 on_code를 담고 있는지 본다: status, code, 또는 get_order가 본 주문 상태."""
    result = event.result
    order = result.get("order")
    order_status = order.get("status") if isinstance(order, dict) else None
    return on_code in (result.get("status"), result.get("code"), order_status)


def _violation(rule: _Rule, prefix_events: list[Event], tool: str, args: dict) -> tuple[str, str] | None:
    """규칙 하나가 이 호출을 막아야 하면 (rule_id, 이유)를 돌려주고, 아니면 None."""
    order_id = _order_of(args)

    if isinstance(rule, RequireBefore):
        if tool != rule.tool:
            return None
        # 앞선 requires_tool 성공 호출이 있으면 통과한다.
        for event in prefix_events:
            if event.tool == rule.requires_tool and event.result.get("status") == "ok" \
                    and (not rule.same_order or _same_order(event, order_id)):
                return None
        scope = "같은 주문에서 " if rule.same_order else ""
        return (f"require_before:{rule.tool}<-{rule.requires_tool}",
                f"{rule.tool} 전에 {scope}{rule.requires_tool} 성공이 필요합니다.")

    if isinstance(rule, BlockAfter):
        if tool not in rule.tools:
            return None
        for event in prefix_events:
            if _same_order(event, order_id) and _observed(event, rule.on_code):
                return (f"block_after:{rule.on_code}->{tool}",
                        f"같은 주문에서 {rule.on_code} 결과를 관측한 뒤에는 {tool}을 쓸 수 없습니다.")
        return None

    if isinstance(rule, MaxAttempts):
        if tool != rule.tool:
            return None
        attempts = sum(1 for e in prefix_events if e.tool == rule.tool and _same_order(e, order_id))
        if attempts >= rule.limit:
            return (f"max_attempts:{rule.tool}<={rule.limit}",
                    f"같은 주문에서 {rule.tool} 시도가 한도 {rule.limit}회에 도달했습니다.")
        return None

    if isinstance(rule, RequireCheckAfterTimeout):
        if tool != rule.tool:
            return None
        # 마지막 TIMEOUT 위치를 찾고, 그 뒤에 확인 도구 호출이 있었는지 본다.
        mine = [(i, e) for i, e in enumerate(prefix_events) if _same_order(e, order_id)]
        timeouts = [i for i, e in mine if e.tool == rule.tool and e.result.get("code") == "TIMEOUT"]
        if not timeouts:
            return None
        checked = any(i > timeouts[-1] and e.tool == rule.check_tool for i, e in mine)
        if checked:
            return None
        return (f"require_check_after_timeout:{rule.tool}<-{rule.check_tool}",
                f"{rule.tool}이 TIMEOUT을 낸 뒤에는 {rule.check_tool}로 확인하기 전에 다시 부를 수 없습니다.")

    raise TypeError(f"알 수 없는 규칙 객체: {type(rule).__name__}")


def decide(spec: PolicySpec, prefix_events: list[Event], tool: str, args: dict) -> GateDecision:
    """prefix_events(이 호출 직전까지의 서비스 Event)만 보고 결정한다. 처음 걸린 규칙이 이긴다."""
    for rule in spec.rules:
        found = _violation(rule, prefix_events, tool, args)
        if found is not None:
            rule_id, reason = found
            return GateDecision(action=rule.action, rule_id=rule_id, reason=reason)
    return GateDecision(action="allow")


def as_gate(spec: PolicySpec) -> PolicyGate:
    """spec을 에이전트 게이트 모양 gate(prefix_events, tool, args) -> GateDecision으로 감싼다."""

    def gate(prefix_events: list[Event], tool: str, args: dict) -> GateDecision:
        return decide(spec, prefix_events, tool, args)

    return gate


def describe(spec: PolicySpec) -> str:
    """정책을 한국어로 설명한다. 규칙마다 한 줄이다."""
    if not spec.rules:
        return f"정책 {spec.version}: 규칙 없음(모두 허용)"
    lines = []
    for rule in spec.rules:
        verb = "차단" if rule.action == "block" else "확인 요청"
        if isinstance(rule, RequireBefore):
            scope = "같은 주문에서 " if rule.same_order else ""
            lines.append(f"{rule.tool} 전에 {scope}{rule.requires_tool} 성공이 없으면 {verb}")
        elif isinstance(rule, BlockAfter):
            lines.append(f"같은 주문에서 {rule.on_code} 관측 뒤 {', '.join(rule.tools)}을 {verb}")
        elif isinstance(rule, MaxAttempts):
            lines.append(f"같은 주문에서 {rule.tool}을 {rule.limit}회 부른 뒤에는 {verb}")
        else:
            lines.append(f"{rule.tool}이 TIMEOUT을 낸 뒤 {rule.check_tool} 호출 전에는 {rule.tool} 재호출을 {verb}")
    return "\n".join(lines)
