"""시험 전용 가짜. 이 파일은 시험(tests)과, tests/run_fake.py가 노트북 임시 사본에 넣는 주입 셀만 import한다.

실행 경로(eval_lab)와 저장된 노트북은 이 파일을 import하지 않는다.

- FakeChatModel, FakeDecider: 단위 시험용 대본 모델과 Decision API.
- NotebookAgentModel, NotebookJudgeModel, NOTEBOOK_DECIDER_SCRIPT, FakeLangfuse: run_fake가 노트북을
  키·네트워크 없이 끝까지 돌릴 때 settings·decisions의 factory 자리에 넣는 가짜.
"""
from __future__ import annotations

import json
import operator
import re
import statistics
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from urllib.parse import unquote
from uuid import uuid4

from eval_lab.contracts import Response
from eval_lab.decisions import (
    Choice,
    DecisionError,
    Judgment,
    Noul,
    Question,
    Score,
    UsageCallback,
    Verdict,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langfuse import Langfuse
from langfuse.api import (
    AnnotationQueue,
    AnnotationQueueItem,
    AnnotationQueueObjectType,
    AnnotationQueueStatus,
    Dataset,
    DatasetItem,
    DatasetRunItem,
    DatasetStatus,
    MetricsV2Response,
    ObservationLevel,
    ObservationsView,
    Organization,
    PaginatedAnnotationQueues,
    PaginatedDatasetItems,
    Project,
    Projects,
    Usage,
)
from langfuse.api.commons.types.observation_v2 import ObservationV2
from langfuse.api.core.request_options import RequestOptions
from langfuse.api.legacy.observations_v1.types.observations_views import (
    ObservationsViews,
)
from langfuse.api.observations.types.observations_v2meta import ObservationsV2Meta
from langfuse.api.observations.types.observations_v2response import (
    ObservationsV2Response,
)
from langfuse.api.utils.pagination.types.meta_response import MetaResponse
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import Field, JsonValue


def _tool_name(tool: object) -> str:
    """bind_tools에 넘어오는 str, dict, 도구 객체, 함수에서 이름을 꺼낸다."""
    if isinstance(tool, str):
        return tool
    if isinstance(tool, dict):
        return tool.get("name") or tool["function"]["name"]
    return getattr(tool, "name", None) or tool.__name__


class FakeChatModel(GenericFakeChatModel):
    """미리 쓴 AIMessage(tool_calls 포함)를 차례로 돌려주고, bind_tools 호출마다 도구 이름을 기록한다."""

    bound_tools: list[list[str]] = Field(default_factory=list)

    @classmethod
    def scripted(cls, messages: Iterable[AIMessage]) -> FakeChatModel:
        return cls(messages=iter(list(messages)))

    def bind_tools(self, tools: Sequence[object], **kwargs: object) -> FakeChatModel:
        self.bound_tools.append([_tool_name(tool) for tool in tools])
        return self


class FakeDecider:
    """DecisionBackend 프로토콜을 따르는 가짜. script는 {질문 이름: Noul 확률, Score 점수, Choice 라벨}이다.

    script에 없는 질문은 refused 판정이 된다. error를 주면 judge가 그 오류를 낸다.
    on_usage를 주면 judge 한 번마다 실제 공급자처럼 사용량 한 줄(토큰 0)을 넘긴다.
    """

    name = "fake"

    def __init__(self, script: dict[str, float | str] | None = None, *, error: DecisionError | None = None,
                 on_usage: UsageCallback | None = None) -> None:
        self.script = script or {}
        self.error = error
        self.on_usage = on_usage
        self.calls: list[tuple[str, list[str]]] = []

    def judge(self, state: str, questions: list[Question]) -> Judgment:
        self.calls.append((state, [q.name for q in questions]))
        if self.error:
            raise self.error
        if self.on_usage:
            self.on_usage({"model": "fake-decider", "input_tokens": 0, "output_tokens": 0})
        return Judgment({q.name: self._verdict(q) for q in questions}, self.name, "fake-decider")

    def _verdict(self, question: Question) -> Verdict:
        if question.name not in self.script:
            return Verdict(question.name, question.kind, refused=True)
        value = self.script[question.name]
        if isinstance(question, Noul):
            return Verdict(question.name, question.kind, probability=float(value))
        if isinstance(question, Score):
            return Verdict(question.name, question.kind, score=float(value))
        assert isinstance(question, Choice)
        return Verdict(question.name, question.kind, choice=str(value))


# ---------------------------------------------------------------- run_fake: 에이전트·Judge·Jev 가짜

# run_fake의 Jev 대본. 이름은 eval_lab.judges.JEV_QUESTIONS와 같다(test_run_fake가 확인한다).
# judges의 T_LO=0.2, T_HI=0.8 기준으로 0.9는 Jev 확신 통과, 0.5는 불확실 구간이라 Judge로 넘어가고, 0.1은 Jev 확신 실패다.
NOTEBOOK_DECIDER_SCRIPT: dict[str, float | str] = {
    "message_consistent": 0.9,
    "next_step_clear": 0.5,
    "clarify_when_needed": 0.1,
}

# 가짜 모델은 토큰을 쓰지 않는다. 실제 ChatAnthropic처럼 usage_metadata는 늘 붙여 토큰 합계가 숫자로 남게 한다.
_ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
# ToolStrategy(Response)는 스키마 클래스 이름으로 구조화 응답 도구를 묶는다(langchain 1.4.7 OutputToolBinding).
_RESPONSE_TOOL = Response.__name__
_ORDER_ID = re.compile(r"\border-[A-Za-z0-9-]+")
JUDGE_REASON = "기록과 응답이 서로 맞습니다(가짜 Judge)."


def _order_id_in(text: str) -> str | None:
    """사람 메시지에서 주문 번호를 꺼낸다. 에이전트는 Request JSON을 보내고, 직접 쓴 문장에서는 order-… 패턴을 찾는다."""
    try:
        request = json.loads(text)
    except ValueError:
        match = _ORDER_ID.search(text)
        return match.group(0) if match else None
    return request.get("order_id") if isinstance(request, dict) else None


def _final_response(order_id: str | None) -> Response:
    """마지막 구조화 응답. 주문 번호가 없으면 되묻고, 있으면 담당자에게 넘긴다."""
    if order_id is None:
        return Response(kind="clarification", message="취소할 주문 번호를 알려 주세요.", order_id=None)
    return Response(kind="escalated", order_id=order_id,
                    message=f"주문 {order_id}을 확인했습니다. 담당자가 취소와 환불 가능 여부를 이어서 확인하도록 넘겼습니다.")


def _chat_result(message: AIMessage) -> ChatResult:
    return ChatResult(generations=[ChatGeneration(message=message)])


class NotebookAgentModel(BaseChatModel):
    """run_fake가 make_agent_model 자리에 넣는 결정적 가짜 Claude. 같은 대화에는 늘 같은 답을 한다.

    마지막 사람 메시지를 기준으로 답한다.
    1. 묶인 도구가 없으면 짧은 한국어 문장으로 답한다.
    2. get_order가 묶여 있고, 요청에 주문 번호가 있고, 그 요청 뒤에 ToolMessage가 아직 없으면 get_order를 한 번 부른다.
    3. 그 밖에는 ToolStrategy가 묶은 Response 구조화 도구를 한 번 부른다. 주문 번호가 없으면
       kind=clarification, 있으면 kind=escalated다. Response 도구가 묶이지 않았으면 문장으로 답한다.
    calls는 응답한 횟수, bound_tools는 bind_tools마다 받은 도구 이름 목록이다.
    """

    model_name: str = "run-fake-agent"  # LangChain이 ls_model_name으로 넘겨 Langfuse가 모델 이름을 읽는다.
    calls: int = 0
    bound_tools: list[list[str]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "run-fake-agent"

    def bind_tools(self, tools: Sequence[object], **kwargs: object):
        """도구 이름만 기록해 _generate에 넘긴다. tool_choice 같은 선택은 받기만 한다(가짜는 정해진 도구를 부른다)."""
        names = [_tool_name(tool) for tool in tools]
        self.bound_tools.append(names)
        return self.bind(tool_names=names)

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, run_manager=None, *,
                  tool_names: Sequence[str] = (), **kwargs: object) -> ChatResult:
        self.calls += 1
        return _chat_result(self._reply(messages, tool_names))

    def _reply(self, messages: list[BaseMessage], tool_names: Sequence[str]) -> AIMessage:
        if not tool_names:
            return AIMessage(content="가짜 에이전트 응답입니다. 실제 모델은 부르지 않았습니다.", usage_metadata=_ZERO_USAGE)
        human = [index for index, message in enumerate(messages) if isinstance(message, HumanMessage)]
        start = human[-1] if human else len(messages)
        order_id = _order_id_in(messages[start].text) if human else None
        looked_up = any(isinstance(message, ToolMessage) for message in messages[start + 1:])
        if "get_order" in tool_names and order_id and not looked_up:
            return self._tool_call("get_order", {"order_id": order_id})
        if _RESPONSE_TOOL in tool_names:
            return self._tool_call(_RESPONSE_TOOL, _final_response(order_id).model_dump())
        return AIMessage(content=_final_response(order_id).message, usage_metadata=_ZERO_USAGE)

    def _tool_call(self, name: str, args: dict[str, JsonValue]) -> AIMessage:
        call = {"name": name, "args": args, "id": f"run-fake-call-{self.calls}", "type": "tool_call"}
        return AIMessage(content="", tool_calls=[call], usage_metadata=_ZERO_USAGE)


_SCALAR_EXAMPLES: dict[str, JsonValue] = {"string": "가짜 Judge 문장입니다.", "number": 1.0, "integer": 1, "boolean": True}


def _schema_example(schema: dict[str, JsonValue], defs: dict[str, JsonValue]) -> JsonValue:
    """JSON 스키마를 채운 값. $ref, const, enum(첫 값), anyOf/oneOf/allOf(null 아닌 첫 갈래), object, array, 기본 타입을 다룬다.

    배열은 minItems만큼(보통 0개) 채운다. 타입이 없는 스키마는 None이다.
    """
    if "$ref" in schema:
        return _schema_example(defs[schema["$ref"].rsplit("/", 1)[-1]], defs)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            options = [option for option in schema[key] if option.get("type") != "null"] or schema[key]
            return _schema_example(options[0], defs)
    kind = schema.get("type")
    if kind == "object":
        return {name: _schema_example(sub, defs) for name, sub in schema.get("properties", {}).items()}
    if kind == "array":
        return [_schema_example(schema.get("items", {}), defs) for _ in range(schema.get("minItems", 0))]
    return _SCALAR_EXAMPLES.get(kind)


def _trailing_schema(prompt: str) -> dict[str, JsonValue] | None:
    """DeepEvalAnthropic이 프롬프트 끝 문단에 붙인 JSON 스키마(judges._schema_prompt)를 읽는다. 없으면 None."""
    try:
        tail = json.loads(prompt.rsplit("\n\n", 1)[-1])
    except ValueError:
        return None
    return tail if isinstance(tail, dict) and "properties" in tail else None


def judge_reply(prompt: str) -> str:
    """가짜 Judge의 답 문자열. 스키마 프롬프트면 스키마를 채운 JSON, 판정 질문이면 PASS JSON, 그 밖에는 문장이다."""
    schema = _trailing_schema(prompt)
    if schema is not None:
        return json.dumps(_schema_example(schema, schema.get("$defs", {})), ensure_ascii=False)
    if "[판정 질문]" in prompt:
        return json.dumps({"verdict": "PASS", "reason": JUDGE_REASON}, ensure_ascii=False)
    return "가짜 Judge 응답입니다. 실제 모델은 부르지 않았습니다."


class NotebookJudgeModel(BaseChatModel):
    """run_fake가 make_judge_model 자리에 넣는 결정적 가짜 Judge. 마지막 메시지의 모양으로 답을 고른다(judge_reply).

    - judges._judge_prompt('[판정 질문]' 포함): {"verdict": "PASS", "reason": JUDGE_REASON}.
    - judges.DeepEvalAnthropic의 스키마 프롬프트(끝 문단이 JSON 스키마): 스키마를 채운 JSON.
    - 그 밖: 짧은 한국어 문장. calls는 응답한 횟수다.
    """

    model_name: str = "run-fake-judge"  # LangChain이 ls_model_name으로 넘겨 Langfuse가 모델 이름을 읽는다.
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "run-fake-judge"

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, run_manager=None,
                  **kwargs: object) -> ChatResult:
        self.calls += 1
        return _chat_result(AIMessage(content=judge_reply(messages[-1].text), usage_metadata=_ZERO_USAGE))


# ---------------------------------------------------------------- run_fake: Langfuse 가짜

OFFLINE_PUBLIC_KEY = "pk-lf-offline-placeholder"
OFFLINE_SECRET_KEY = "sk-lf-offline-placeholder"
# 루프백의 discard 포트. 가짜가 놓친 실제 API 호출이 있어도 밖으로 나가지 않고 연결 실패로 드러난다.
OFFLINE_BASE_URL = "http://127.0.0.1:9"
OFFLINE_PROJECT_ID = "offline-project"
# 비용·토큰은 가짜 기록에 없다. Metrics API에서 이 측정값은 0이 아니라 None(미확인)으로 답한다.
_UNKNOWN_MEASURES = frozenset({"inputTokens", "outputTokens", "totalTokens", "inputCost", "outputCost", "totalCost"})
_PERCENTILES = {"p50": 50, "p75": 75, "p90": 90, "p95": 95, "p99": 99}


class OfflineLangfuseError(NotImplementedError):
    """FakeLangfuse가 흉내 내지 않는 API를 불렀다. 메시지에 메서드 또는 값 이름이 있다."""


def _now() -> datetime:
    return datetime.now(UTC)


def _as_datetime(value: str | datetime) -> datetime:
    """필터의 ISO 시각을 UTC datetime으로 읽는다. 시간대가 없으면 UTC로 본다."""
    moment = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _json_attribute(attributes: dict[str, JsonValue], key: str) -> JsonValue:
    """Langfuse가 span 속성에 JSON 문자열로 넣은 입출력을 되읽는다. JSON이 아니면 문자열 그대로다."""
    raw = attributes.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw


@dataclass(frozen=True)
class CapturedObservation:
    """메모리 exporter에 모인 span 하나를 Langfuse observation 모양으로 다시 읽은 것."""

    id: str
    trace_id: str
    parent_observation_id: str | None
    name: str
    type: str
    start_time: datetime
    end_time: datetime
    input: JsonValue
    output: JsonValue
    version: str | None
    environment: str

    @classmethod
    def from_span(cls, span: ReadableSpan) -> CapturedObservation:
        attributes = dict(span.attributes or {})
        return cls(
            id=format(span.context.span_id, "016x"),
            trace_id=format(span.context.trace_id, "032x"),
            parent_observation_id=format(span.parent.span_id, "016x") if span.parent is not None else None,
            name=span.name,
            type=str(attributes.get("langfuse.observation.type", "span")).upper(),
            start_time=datetime.fromtimestamp(span.start_time / 1e9, UTC),
            end_time=datetime.fromtimestamp(span.end_time / 1e9, UTC),
            input=_json_attribute(attributes, "langfuse.observation.input"),
            output=_json_attribute(attributes, "langfuse.observation.output"),
            version=attributes.get("langfuse.version"),
            environment=attributes.get("langfuse.environment") or "default",
        )

    @property
    def latency_ms(self) -> float:
        return (self.end_time - self.start_time).total_seconds() * 1000

    def as_view(self) -> ObservationsView:
        """관측 목록 v1(run_batched_evaluation이 읽는 쪽) 모양."""
        return ObservationsView(
            id=self.id, trace_id=self.trace_id, parent_observation_id=self.parent_observation_id, name=self.name,
            type=self.type, start_time=self.start_time, end_time=self.end_time, input=self.input, output=self.output,
            version=self.version, environment=self.environment, metadata={}, model_parameters={},
            usage=Usage(input=0, output=0, total=0), level=ObservationLevel.DEFAULT, usage_details={},
            cost_details={}, latency=self.latency_ms / 1000,
        )

    def as_v2(self) -> ObservationV2:
        """관측 목록 v2(api.observations.get_many) 모양."""
        return ObservationV2(
            id=self.id, trace_id=self.trace_id, parent_observation_id=self.parent_observation_id, name=self.name,
            type=self.type, start_time=self.start_time, end_time=self.end_time, input=self.input, output=self.output,
            version=self.version, environment=self.environment, project_id=OFFLINE_PROJECT_ID,
            is_root_observation=self.parent_observation_id is None, latency=self.latency_ms / 1000,
        )


# 필터 열 이름 -> observation 값. v1 관측 목록 필터와 Metrics API 필터가 같이 쓴다.
_COLUMNS: dict[str, Callable[[CapturedObservation], JsonValue | datetime]] = {
    "environment": lambda o: o.environment,
    "name": lambda o: o.name,
    "version": lambda o: o.version,
    "type": lambda o: o.type,
    "traceId": lambda o: o.trace_id,
    "parentObservationId": lambda o: o.parent_observation_id,
    "isRootObservation": lambda o: o.parent_observation_id is None,
    "start_time": lambda o: o.start_time,
    "startTime": lambda o: o.start_time,
}
_OPERATORS: dict[str, Callable[[JsonValue | datetime, JsonValue | datetime], bool]] = {
    "=": operator.eq, "<>": operator.ne, ">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le,
    "any of": lambda value, options: value in options, "none of": lambda value, options: value not in options,
}


def _column(observation: CapturedObservation, column: str) -> JsonValue | datetime:
    if column not in _COLUMNS:
        raise OfflineLangfuseError(f"FakeLangfuse 필터·차원: 열 {column!r}는 지원하지 않습니다. 지원: {', '.join(_COLUMNS)}")
    return _COLUMNS[column](observation)


def _holds(observation: CapturedObservation, condition: dict[str, JsonValue]) -> bool:
    """필터 조건 하나(type, column, operator, value). 모르는 열·연산자는 이름을 대며 멈춘다."""
    operator_name = condition["operator"]
    if operator_name not in _OPERATORS:
        raise OfflineLangfuseError(f"FakeLangfuse 필터: 연산자 {operator_name!r}는 지원하지 않습니다.")
    expected = _as_datetime(condition["value"]) if condition.get("type") == "datetime" else condition["value"]
    return _OPERATORS[operator_name](_column(observation, condition["column"]), expected)


def _matches(observation: CapturedObservation, conditions: list[dict[str, JsonValue]]) -> bool:
    return all(_holds(observation, condition) for condition in conditions)


def _page_meta(page: int, limit: int, total: int) -> MetaResponse:
    return MetaResponse(page=page, limit=limit, total_items=total, total_pages=max(1, -(-total // limit)))


def _aggregate(measure: str, aggregation: str, members: list[CapturedObservation]) -> float | int | None:
    """Metrics API 측정값 하나. count와 latency(ms)만 계산하고, 비용·토큰은 None, 나머지는 멈춘다."""
    if measure in _UNKNOWN_MEASURES:
        return None
    if measure == "count":
        return len(members)
    if measure != "latency":
        raise OfflineLangfuseError(f"FakeLangfuse Metrics: 측정값 {measure!r}는 지원하지 않습니다(count, latency, 비용·토큰=None).")
    values = [member.latency_ms for member in members]
    if aggregation == "count":
        return len(values)
    if not values:
        return None
    if aggregation in _PERCENTILES:
        return statistics.quantiles(values, n=100, method="inclusive")[_PERCENTILES[aggregation] - 1]
    reducers = {"sum": sum, "avg": statistics.fmean, "max": max, "min": min}
    if aggregation not in reducers:
        raise OfflineLangfuseError(f"FakeLangfuse Metrics: 집계 {aggregation!r}는 지원하지 않습니다.")
    return reducers[aggregation](values)


class _OfflineResource:
    """api 아래 자원 하나. 정의하지 않은 메서드를 부르면 그 이름을 대며 OfflineLangfuseError를 낸다."""

    def __init__(self, client: FakeLangfuse, path: str) -> None:
        self._client = client
        self._path = path

    def __getattr__(self, name: str):
        if name.startswith("__"):
            raise AttributeError(name)
        raise OfflineLangfuseError(f"FakeLangfuse.{self._path}.{name}는 오프라인 가짜가 지원하지 않습니다.")


class _Projects(_OfflineResource):
    def get(self, *, request_options: RequestOptions | None = None) -> Projects:
        """auth_check와 get_trace_url이 읽는 프로젝트 목록. 프로젝트 하나를 돌려준다."""
        organization = Organization(id="offline-organization", name="offline")
        return Projects(data=[Project(id=OFFLINE_PROJECT_ID, name="day05-offline", organization=organization, metadata={})])


class _Datasets(_OfflineResource):
    def create(self, *, name: str, description: str | None = None, metadata: JsonValue = None,
               input_schema: JsonValue = None, expected_output_schema: JsonValue = None,
               request_options: RequestOptions | None = None) -> Dataset:
        """이름이 같은 Dataset이 있으면 그것을 돌려준다(서버의 upsert와 같다)."""
        if name not in self._client.datasets:
            now = _now()
            self._client.datasets[name] = Dataset(
                id=f"offline-dataset-{len(self._client.datasets) + 1}", name=name, description=description,
                metadata=metadata, input_schema=input_schema, expected_output_schema=expected_output_schema,
                project_id=OFFLINE_PROJECT_ID, created_at=now, updated_at=now)
            self._client.dataset_items[name] = {}
        return self._client.datasets[name]

    def get(self, dataset_name: str, *, request_options: RequestOptions | None = None) -> Dataset:
        name = unquote(dataset_name)
        if name not in self._client.datasets:
            raise LookupError(f"FakeLangfuse: Dataset {name!r}가 없습니다.")
        return self._client.datasets[name]


class _DatasetItems(_OfflineResource):
    def create(self, *, dataset_name: str, input: JsonValue = None, expected_output: JsonValue = None,
               metadata: JsonValue = None, source_trace_id: str | None = None, source_observation_id: str | None = None,
               id: str | None = None, status: DatasetStatus | None = None, request_options: RequestOptions | None = None) -> DatasetItem:
        """같은 id면 덮어쓴다(서버의 upsert와 같다). Dataset이 없으면 멈춘다."""
        dataset = self._client.api.datasets.get(dataset_name)
        now = _now()
        item = DatasetItem(
            id=id or uuid4().hex, status=status or DatasetStatus.ACTIVE, input=input, expected_output=expected_output,
            metadata=metadata, source_trace_id=source_trace_id, source_observation_id=source_observation_id,
            dataset_id=dataset.id, dataset_name=dataset.name, created_at=now, updated_at=now, media_references=[])
        self._client.dataset_items[dataset.name][item.id] = item
        return item

    def list(self, *, dataset_name: str, page: int = 1, limit: int = 50, version: datetime | None = None,
             request_options: RequestOptions | None = None) -> PaginatedDatasetItems:
        """get_dataset이 쪽마다 부른다. 과거 시점(version) 조회는 흉내 내지 않는다."""
        if version is not None:
            raise OfflineLangfuseError("FakeLangfuse.api.dataset_items.list(version=...)는 오프라인 가짜가 지원하지 않습니다.")
        items = list(self._client.dataset_items[self._client.api.datasets.get(dataset_name).name].values())
        return PaginatedDatasetItems(data=items[(page - 1) * limit: page * limit], meta=_page_meta(page, limit, len(items)))


class _DatasetRunItems(_OfflineResource):
    def create(self, *, run_name: str, dataset_item_id: str, trace_id: str | None = None,
               observation_id: str | None = None, run_description: str | None = None, metadata: JsonValue = None,
               dataset_version: datetime | None = None, request_options: RequestOptions | None = None) -> DatasetRunItem:
        """run_experiment가 Dataset 항목마다 부른다. 기록만 한다."""
        now = _now()
        run_item = DatasetRunItem(
            id=uuid4().hex, dataset_run_id=f"offline-run-{run_name}", dataset_run_name=run_name,
            dataset_item_id=dataset_item_id, trace_id=trace_id or "", observation_id=observation_id,
            created_at=now, updated_at=now)
        self._client.dataset_run_items.append(run_item)
        return run_item


class _Observations(_OfflineResource):
    def get_many(self, *, trace_id: str | None = None, limit: int | None = None, cursor: str | None = None,
                 from_start_time: datetime | None = None, to_start_time: datetime | None = None,
                 fields: str | None = None, request_options: RequestOptions | None = None) -> ObservationsV2Response:
        """관측 목록 v2. 조건에 맞는 observation을 한 쪽에 모두 담고 cursor는 None이다."""
        found = [o.as_v2() for o in self._client.captured_observations()
                 if (trace_id is None or o.trace_id == trace_id)
                 and (from_start_time is None or o.start_time >= _as_datetime(from_start_time))
                 and (to_start_time is None or o.start_time <= _as_datetime(to_start_time))]
        return ObservationsV2Response(data=found, meta=ObservationsV2Meta(cursor=None))


class _ObservationsV1(_OfflineResource):
    def get_many(self, *, page: int = 1, limit: int = 50, filter: str | None = None,
                 request_options: RequestOptions | None = None) -> ObservationsViews:
        """관측 목록 v1. 실제 run_batched_evaluation(scope='observations')이 이 메서드로 항목을 읽는다."""
        conditions = json.loads(filter) if filter else []
        found = [o.as_view() for o in self._client.captured_observations() if _matches(o, conditions)]
        return ObservationsViews(data=found[(page - 1) * limit: page * limit], meta=_page_meta(page, limit, len(found)))


class _Metrics(_OfflineResource):
    def metrics(self, *, query: str, request_options: RequestOptions | None = None) -> MetricsV2Response:
        """Metrics API v2의 observations view. 차원별로 묶어 '<집계>_<측정값>' 열을 계산한다."""
        request = json.loads(query)
        self._client.metrics_queries.append(request)
        if request["view"] != "observations":
            raise OfflineLangfuseError(f"FakeLangfuse Metrics: view {request['view']!r}는 지원하지 않습니다(observations만).")
        start, end = _as_datetime(request["fromTimestamp"]), _as_datetime(request["toTimestamp"])
        dimensions = [dimension["field"] for dimension in request.get("dimensions", [])]
        groups: dict[tuple, list[CapturedObservation]] = defaultdict(list)
        if not dimensions:
            groups[()] = []
        for observation in self._client.captured_observations():
            if start <= observation.start_time <= end and _matches(observation, request.get("filters", [])):
                groups[tuple(_column(observation, field) for field in dimensions)].append(observation)
        rows = []
        for key in sorted(groups, key=str):
            row = dict(zip(dimensions, key))
            for metric in request["metrics"]:
                row[f"{metric['aggregation']}_{metric['measure']}"] = _aggregate(
                    metric["measure"], metric["aggregation"], groups[key])
            rows.append(row)
        return MetricsV2Response(data=rows)


class _AnnotationQueues(_OfflineResource):
    def list_queues(self, *, page: int = 1, limit: int = 50, request_options: RequestOptions | None = None) -> PaginatedAnnotationQueues:
        queues = self._client.annotation_queues
        return PaginatedAnnotationQueues(data=queues[(page - 1) * limit: page * limit],
                                         meta=_page_meta(page, limit, len(queues)))

    def create_queue(self, *, name: str, score_config_ids: list[str], description: str | None = None,
                     request_options: RequestOptions | None = None) -> AnnotationQueue:
        now = _now()
        queue = AnnotationQueue(id=f"offline-queue-{len(self._client.annotation_queues) + 1}", name=name,
                                description=description, score_config_ids=score_config_ids, created_at=now, updated_at=now)
        self._client.annotation_queues.append(queue)
        return queue

    def create_queue_item(self, queue_id: str, *, object_id: str, object_type: AnnotationQueueObjectType,
                          status: AnnotationQueueStatus | None = None, request_options: RequestOptions | None = None) -> AnnotationQueueItem:
        if queue_id not in {queue.id for queue in self._client.annotation_queues}:
            raise LookupError(f"FakeLangfuse: annotation queue {queue_id!r}가 없습니다.")
        now = _now()
        item = AnnotationQueueItem(id=uuid4().hex, queue_id=queue_id, object_id=object_id, object_type=object_type,
                                   status=status or AnnotationQueueStatus.PENDING, created_at=now, updated_at=now)
        self._client.annotation_queue_items.append(item)
        return item


class _EvaluationRules(_OfflineResource):
    def create(self, *, name: str, enabled: bool, evaluator_assignments: list, sampling: float | None = None,
               filter: list | None = None, request_options: RequestOptions | None = None) -> SimpleNamespace:
        """서버 쪽 평가 Rule 초안. 기록만 하고 실행하지 않는다."""
        rule = SimpleNamespace(id=f"offline-rule-{len(self._client.evaluation_rules) + 1}", name=name, enabled=enabled,
                               evaluator_assignments=evaluator_assignments, sampling=sampling, filter=filter)
        self._client.evaluation_rules.append(rule)
        return rule


class OfflineLangfuseAPI(_OfflineResource):
    """FakeLangfuse.api. 아래 자원과 메서드만 흉내 내고, 나머지 자원은 이름을 대며 멈춘다.

    projects.get, datasets.create/get, dataset_items.create/list, dataset_run_items.create,
    observations.get_many(v2), legacy.observations_v1.get_many, metrics.metrics,
    annotation_queues.list_queues/create_queue/create_queue_item, evaluation_rules.create.
    """

    def __init__(self, client: FakeLangfuse) -> None:
        super().__init__(client, "api")
        self.projects = _Projects(client, "api.projects")
        self.datasets = _Datasets(client, "api.datasets")
        self.dataset_items = _DatasetItems(client, "api.dataset_items")
        self.dataset_run_items = _DatasetRunItems(client, "api.dataset_run_items")
        self.observations = _Observations(client, "api.observations")
        self.legacy = _OfflineResource(client, "api.legacy")
        self.legacy.observations_v1 = _ObservationsV1(client, "api.legacy.observations_v1")
        self.metrics = _Metrics(client, "api.metrics")
        self.annotation_queues = _AnnotationQueues(client, "api.annotation_queues")
        self.evaluation_rules = _EvaluationRules(client, "api.evaluation_rules")


class FakeLangfuse(Langfuse):
    """네트워크 없이 도는 실제 langfuse.Langfuse(SDK 4.15.1). run_fake가 make_langfuse 자리에 넣는다.

    - 추적은 실제 SDK 그대로다(start_as_current_observation, propagate_attributes, get_current_trace_id,
      LangChain CallbackHandler). span은 OTel InMemorySpanExporter에 모인다.
    - api는 OfflineLangfuseAPI다. run_batched_evaluation, auth_check, create_dataset, create_dataset_item,
      get_dataset, run_experiment는 실제 SDK 코드가 이 api를 거쳐 돈다. run_batched_evaluation은
      메모리 span에서 다시 만든 observation(root output = Episode 요약)에 mapper와 평가기를 돌린다.
    - create_score는 보내지 않고 scores에 쌓는다. flush는 span을 메모리 exporter로 밀어내기만 하고,
      shutdown은 flush와 같다(자원을 닫지 않는다). async_api와 흉내 내지 않은 API는 이름을 대며 멈춘다.
    - Langfuse 자원은 public_key마다 하나다. 같은 프로세스에서 다시 만들면 먼저 만든 exporter를 함께 쓴다.
    """

    def __init__(self) -> None:
        super().__init__(public_key=OFFLINE_PUBLIC_KEY, secret_key=OFFLINE_SECRET_KEY, base_url=OFFLINE_BASE_URL,
                         span_exporter=InMemorySpanExporter(), tracer_provider=TracerProvider())
        self.scores: list[dict[str, JsonValue]] = []
        self.datasets: dict[str, Dataset] = {}
        self.dataset_items: dict[str, dict[str, DatasetItem]] = {}
        self.dataset_run_items: list[DatasetRunItem] = []
        self.annotation_queues: list[AnnotationQueue] = []
        self.annotation_queue_items: list[AnnotationQueueItem] = []
        self.evaluation_rules: list[SimpleNamespace] = []
        self.metrics_queries: list[dict[str, JsonValue]] = []
        self._offline_api = OfflineLangfuseAPI(self)

    @property
    def api(self) -> OfflineLangfuseAPI:
        return self._offline_api

    @property
    def async_api(self):
        raise OfflineLangfuseError("FakeLangfuse.async_api는 오프라인 가짜가 지원하지 않습니다.")

    def create_score(self, **score: JsonValue) -> None:
        """점수를 보내지 않고 scores에 그대로 쌓는다. 실제 create_score처럼 None을 돌려준다."""
        self.scores.append(score)

    def _create_trace_tags_via_ingestion(self, **kwargs: JsonValue) -> None:
        raise OfflineLangfuseError("FakeLangfuse._create_trace_tags_via_ingestion는 오프라인 가짜가 지원하지 않습니다.")

    def flush(self) -> None:
        """끝난 span을 메모리 exporter로 밀어낸다. 네트워크 전송은 없다."""
        self._resources.tracer_provider.force_flush()

    def shutdown(self) -> None:
        """자원을 닫지 않고 flush만 한다. 같은 커널의 다음 셀이 계속 기록할 수 있게 한다."""
        self.flush()

    def captured_observations(self) -> list[CapturedObservation]:
        """지금까지 끝난 span을 시작 시각 순서의 observation으로 돌려준다. 읽기 전에 flush한다."""
        self.flush()
        spans = self._resources.span_exporter.get_finished_spans()
        return sorted((CapturedObservation.from_span(span) for span in spans), key=lambda o: (o.start_time, o.id))
