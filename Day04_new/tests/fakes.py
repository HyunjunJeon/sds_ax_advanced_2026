"""단위 시험 전용 가짜. 실행 경로(cap_lab)와 노트북은 이 파일을 import하지 않는다."""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from pydantic import Field

from cap_lab.decisions import Choice, DecisionError, Judgment, Noul, Question, Score, Verdict


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
    """

    name = "fake"

    def __init__(self, script: dict[str, float | str] | None = None, *, error: DecisionError | None = None) -> None:
        self.script = script or {}
        self.error = error
        self.calls: list[tuple[str, list[str]]] = []

    def judge(self, state: str, questions: list[Question]) -> Judgment:
        self.calls.append((state, [q.name for q in questions]))
        if self.error:
            raise self.error
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
