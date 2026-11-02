"""단위 시험 전용 가짜. 비용 없이 경계를 시험하려고 둔다. rag_lab, mas_lab과 노트북은 이 파일을 import하지 않는다."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, Field, SkipValidation, ValidationError


class ScriptExhausted(RuntimeError):
    """대본을 다 썼는데 모델이 또 불렸다."""


class ScriptedChatModel(BaseChatModel):
    """steps를 차례로 돌려준다. callable 단계는 그때까지의 메시지를 받아 응답을 만든다."""
    steps: SkipValidation[list[AIMessage | Callable[[list[BaseMessage]], AIMessage]]]
    calls: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tool_names: list[str] = Field(default_factory=list)
    bound_kwargs: dict = Field(default_factory=dict)
    structured_methods: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Sequence[dict | type[BaseModel] | Callable | BaseTool],
                   **kwargs: object) -> ScriptedChatModel:
        self.bound_tool_names = [convert_to_openai_tool(t)["function"]["name"] for t in tools]
        self.bound_kwargs = kwargs
        return self

    def with_structured_output(self, schema: type[BaseModel], *, include_raw: bool = False,
                               method: str = "function_calling") -> Runnable:
        """실제 ChatAnthropic의 method="json_schema"처럼 응답 본문의 JSON을 읽는다."""
        self.structured_methods.append(method)

        def parse(raw: AIMessage) -> dict:
            try:
                return {"raw": raw, "parsed": schema.model_validate_json(raw.text), "parsing_error": None}
            except ValidationError as error:
                return {"raw": raw, "parsed": None, "parsing_error": error}

        return self | RunnableLambda(parse)

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None,
                  run_manager: object = None, **kwargs: object) -> ChatResult:
        index = len(self.calls)
        self.calls.append(list(messages))
        if index >= len(self.steps):
            raise ScriptExhausted(f"대본은 {len(self.steps)}단계인데 {index + 1}번째 호출이 왔습니다.")
        step = self.steps[index]
        message = step if isinstance(step, AIMessage) else step(messages)
        return ChatResult(generations=[ChatGeneration(message=message)])


class ParsedChatModel(ScriptedChatModel):
    """파싱된 객체를 바로 받는 코드(hybrid Router, 리서치 synth)용이다. 기반 클래스의 with_structured_output은 raw와 parsed를 담은 dict를 돌려준다."""
    schemas: list[type[BaseModel]] = Field(default_factory=list)

    def with_structured_output(self, schema: type[BaseModel], **_options: object) -> Runnable:
        self.schemas.append(schema)
        return self | RunnableLambda(lambda raw: schema.model_validate_json(raw.text))


def tool_call(name: str, args: dict, call_id: str | None = None) -> AIMessage:
    return AIMessage(content="", tool_calls=[
        {"name": name, "args": args, "id": call_id or f"call-{uuid4().hex[:8]}", "type": "tool_call"}])
