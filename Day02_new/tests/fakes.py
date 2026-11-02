"""단위 시험 전용 가짜. 비용 없이 경계를 시험하려고 둔다. rag_lab과 노트북은 이 파일을 import하지 않는다."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from uuid import uuid4

import numpy as np
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, Field, SkipValidation, ValidationError
from rag_lab.decisions import DecisionError, Judgment, Noul, Question, Verdict
from rag_lab.retrieval import tokenize


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


def tool_call(name: str, args: dict, call_id: str | None = None) -> AIMessage:
    return AIMessage(content="", tool_calls=[
        {"name": name, "args": args, "id": call_id or f"call-{uuid4().hex[:8]}", "type": "tool_call"}])


def _last_tool_output(messages: list[BaseMessage], name: str) -> str:
    outputs = [m.text for m in messages if isinstance(m, ToolMessage) and m.name == name]
    return outputs[-1] if outputs else ""


def rag_script(*, skill: str, query: str, answer_text: str = "검색된 근거를 인용한 시험 문장입니다.") -> list:
    """Skill 읽기, output.json 읽기, 검색, 답변의 네 단계. 인용 ID는 내용 해시라 답변 단계에서 메시지로 만든다."""
    def answer(messages: list[BaseMessage]) -> AIMessage:
        headings = re.findall(r'"heading":\s*"([^"]+)"', _last_tool_output(messages, "read_file"))
        found = json.loads(_last_tool_output(messages, "search_knowledge") or "{}").get("evidence", [])
        items = [{"text": answer_text, "evidence_ids": [found[0]["evidence_id"]]}] if found else []
        insufficient = skill == "insufficient-evidence"
        return AIMessage(content=json.dumps({
            "skill": skill, "status": "insufficient" if insufficient else "answered",
            "sections": [{"heading": heading, "items": items} for heading in headings],
            "missing": ["시험용 부족 사항"] if insufficient else [],
        }, ensure_ascii=False))

    return [tool_call("read_file", {"file_path": f"/{skill}/SKILL.md", "limit": 1000}),
            tool_call("read_file", {"file_path": f"/{skill}/output.json", "limit": 1000}),
            tool_call("search_knowledge", {"query": query}),
            answer]


# 질문 하나의 대본. 숫자는 확률, None은 거절, DecisionError는 judge 전체의 실패, callable은 질문을 받아 위 값 중 하나를 돌려준다.
Reply = float | None | DecisionError | Callable[[Noul], float | None]


class ScriptedDecider:
    """질문 이름의 접두사별 대본으로 답하는 Decision 공급자. list 대본은 호출마다 앞에서 하나씩 쓴다.

    기본 대본은 분해 안 함, 추가 확인 안 함, 인용 모두 관련 있음이다. 받은 (state, questions)를 calls에 남긴다."""
    name, model = "fake-backend", "fake-model"

    def __init__(self, *, decompose: Reply | list[Reply] = 0.1, follow_up: Reply | list[Reply] = 0.1,
                 citation: Reply | list[Reply] = 0.9) -> None:
        self.script = {"decompose": decompose, "follow_up": follow_up, "citation": citation}
        self.calls: list[tuple[str, list[Question]]] = []

    def _reply(self, question: Noul) -> float | None:
        key = question.name.split("_")[0] if question.name.startswith("citation") else question.name
        reply = self.script[key]
        if isinstance(reply, list):
            reply = reply.pop(0)
        if isinstance(reply, DecisionError):
            raise reply
        return reply(question) if callable(reply) else reply

    def judge(self, state: str, questions: list[Question]) -> Judgment:
        self.calls.append((state, questions))
        replies = {question.name: self._reply(question) for question in questions}
        verdicts = {name: Verdict(name, "noul", probability=reply, refused=reply is None) for name, reply in replies.items()}
        return Judgment(verdicts, self.name, self.model)


class HashEmbeddings(Embeddings):
    """토큰을 칸에 부호 해시하는 결정적 임베딩. 어휘 일치일 뿐이라 색인 경계 시험에만 쓴다."""
    def __init__(self, dim: int = 256):
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vector = np.zeros(self.dim)
        for token in tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dim] += 1 if digest[4] & 1 else -1
        norm = np.linalg.norm(vector)
        return (vector / norm if norm else vector).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
