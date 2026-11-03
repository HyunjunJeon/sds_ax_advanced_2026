"""채팅 공급자 선택(Anthropic / OpenRouter)과 Claude 응답 처리. 네트워크를 쓰지 않는다."""

from dataclasses import replace
from typing import get_args

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openrouter import ChatOpenRouter

from src.agent.config import (
    CHAT_MODELS,
    Settings,
    chat_model,
    load_settings,
    resolve_provider,
    with_thinking,
)
from src.llm_judge import ClosedAnswers, structured_runnable
from src.middleware.turn_plan import _last_ai_text
from src.schemas import ThinkingEffort

HAIKU = "claude-haiku-5-5"


def _settings(provider: str) -> Settings:
    fast, powerful = CHAT_MODELS[provider]
    return replace(
        load_settings(),
        llm_provider=provider,
        anthropic_api_key="dummy-anthropic",
        openrouter_api_key="dummy-openrouter",
        fast_model=fast,
        powerful_model=powerful,
    )


def _payload(model: ChatAnthropic, **kwargs: object) -> dict:
    """Anthropic API로 나갈 요청 본문. 호출은 하지 않는다(`_get_request_payload`와 같은 타입)."""
    return model._get_request_payload([HumanMessage(content="hi")], **kwargs)


def test_provider_defaults_to_anthropic() -> None:
    assert resolve_provider(None) == "anthropic"
    assert resolve_provider("") == "anthropic"
    assert resolve_provider(' "OpenRouter" ') == "openrouter"


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="LLM_PROVIDER='openai'"):
        resolve_provider("openai")


@pytest.mark.parametrize(
    ("provider", "fast", "powerful", "key_name"),
    [
        ("anthropic", HAIKU, HAIKU, "ANTHROPIC_API_KEY"),
        (
            "openrouter",
            "openai/gpt-5.6-luna",
            "anthropic/claude-sonnet-4.6",
            "OPENROUTER_API_KEY",
        ),
    ],
)
def test_load_settings_follows_llm_provider(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    fast: str,
    powerful: str,
    key_name: str,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", provider)
    settings = load_settings()
    assert settings.llm_provider == provider
    assert (settings.fast_model, settings.powerful_model) == (fast, powerful)
    assert settings.chat_key_name == key_name


def test_anthropic_request_is_haiku_medium_without_temperature() -> None:
    model = chat_model(_settings("anthropic"), HAIKU)
    assert isinstance(model, ChatAnthropic)
    payload = _payload(model)
    assert payload["model"] == HAIKU
    assert payload["output_config"] == {"effort": "medium"}
    assert "temperature" not in payload


@pytest.mark.parametrize("effort", get_args(ThinkingEffort))
def test_anthropic_effort_stays_medium_for_every_turn_plan(effort: str) -> None:
    settings = _settings("anthropic")
    model = with_thinking(chat_model(settings, HAIKU, thinking_effort=effort), effort)
    assert isinstance(model, ChatAnthropic)
    assert _payload(model)["output_config"] == {"effort": "medium"}


def test_openrouter_keeps_turn_plan_effort_and_temperature() -> None:
    settings = _settings("openrouter")
    model = with_thinking(chat_model(settings, settings.fast_model), "high")
    assert isinstance(model, ChatOpenRouter)
    assert model.reasoning == {"effort": "high"}
    assert model.temperature == 0


def test_missing_key_names_the_active_provider() -> None:
    settings = replace(_settings("anthropic"), anthropic_api_key=None)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        chat_model(settings, HAIKU)


def test_claude_judge_forces_tool_call_with_thinking_off() -> None:
    """dict 필드를 지키려고 json_schema가 아니라 강제 tool-call을 쓴다."""
    model = chat_model(_settings("anthropic"), HAIKU)
    binding = structured_runnable(model, ClosedAnswers).first
    kwargs = {k: v for k, v in binding.kwargs.items() if k != "ls_structured_output_format"}
    payload = _payload(binding.bound, **kwargs)
    assert payload["tool_choice"] == {"type": "tool", "name": "ClosedAnswers"}
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["output_config"] == {"effort": "medium"}
    nouls = payload["tools"][0]["input_schema"]["properties"]["nouls"]
    assert nouls["additionalProperties"] == {"type": "number"}


def test_last_ai_text_returns_only_text_blocks() -> None:
    answer = AIMessage(
        content=[
            {"type": "thinking", "thinking": "내부 추론", "signature": "sig"},
            {"type": "text", "text": "최종 답"},
        ]
    )
    state = {"messages": [HumanMessage(content="질문"), answer]}
    assert _last_ai_text(state) == "최종 답"
