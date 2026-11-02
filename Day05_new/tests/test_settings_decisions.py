"""설정과 Decision API 계층. httpx.MockTransport로 요청과 응답 해석을 확인한다. 네트워크와 유료 호출은 없다."""
import json
import socket

import httpx
import pytest
from eval_lab.decisions import (
    BACKENDS,
    Choice,
    DecisionError,
    Noul,
    Score,
    TypeSafeBackend,
    make_decider,
)
from eval_lab.settings import (
    ALL_ENV_NAMES,
    Settings,
    key_status,
    load_settings,
    make_agent_model,
    make_improver_model,
    make_judge_model,
    make_langfuse,
    require,
)
from fakes import FakeChatModel, FakeDecider
from langchain_core.messages import AIMessage

KEY = "sk-test-decision-key-9876543210"
STATE = "주문 취소는 배송 전에만 된다."
QUESTIONS = [Noul("relevant", "근거가 질문에 답하는가?", "답한다", "답하지 않는다"),
             Choice("kind", "문서 종류는?", {"policy": "정책", "faq": "자주 묻는 질문"}),
             Score("depth", "얼마나 자세한가?", ["한 줄", "한 문단", "상세"])]
ANSWERS = {"relevant": {"type": "noul", "noul": 1},
           "kind": {"type": "choice", "choice": "policy", "confidence": 0.9, "probabilities": {"policy": 0.9, "faq": 0.1}},
           "depth": {"type": "score", "score": 1.2, "confidence": 0.6, "probabilities": {"0": 0.1, "1": 0.7, "2": 0.2}}}


def serve(reply: dict | None = None, status: int = 200):
    """(client, 받은 요청 목록)을 돌려준다."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=reply)

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_key_status_reports_only_set_or_unset_never_a_value():
    secret = "test-anthropic-very-secret-value"
    status = key_status(Settings(anthropic_api_key=secret, langfuse_secret_key="lf-secret-value"))
    assert status["ANTHROPIC_API_KEY"] == "설정됨" and status["LANGFUSE_SECRET_KEY"] == "설정됨"
    assert status["TYPESAFE_API_KEY"] == "미설정"
    assert set(status.values()) == {"설정됨", "미설정"}
    assert secret not in json.dumps(status, ensure_ascii=False)


def test_settings_repr_hides_key_values():
    assert "test-anthropic-secret" not in repr(Settings(anthropic_api_key="test-anthropic-secret", typesafe_api_key="ts-secret"))


def test_require_names_missing_variables_without_values():
    with pytest.raises(RuntimeError) as caught:
        require(Settings(openai_api_key="set-secret"), "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LANGFUSE_SECRET_KEY")
    message = str(caught.value)
    assert "ANTHROPIC_API_KEY" in message and "LANGFUSE_SECRET_KEY" in message
    assert "OPENAI_API_KEY" not in message and "set-secret" not in message
    assert "Day05_new/.env.example을 .env로 복사한 뒤 본인의 키를 직접 채우세요" in message


def test_require_passes_through_settings_when_keys_are_present():
    settings = Settings(anthropic_api_key="a")
    assert require(settings, "ANTHROPIC_API_KEY") is settings


def test_load_settings_ignores_the_real_dotenv_under_the_conftest_fixture():
    settings = load_settings()
    assert settings == Settings()
    assert all(value == "미설정" for value in key_status(settings).values())


def test_settings_defaults():
    settings = Settings()
    assert (settings.model, settings.effort) == ("claude-sonnet-5-5", "medium")
    assert (settings.judge_model, settings.judge_effort) == ("claude-sonnet-5-5", "xhigh")
    assert (settings.improver_effort, settings.langfuse_environment) == ("high", "day05_new")


def test_load_settings_reads_an_explicit_file_with_defaults_and_overrides(tmp_path):
    env = tmp_path / "custom.env"
    env.write_text("ANTHROPIC_API_KEY=abc\nDAY05_EFFORT=high\nDAY05_DECISION_BACKEND= OpenAI \nLANGFUSE_HOST=https://lf.example\n", encoding="utf-8")
    settings = load_settings(env)
    assert (settings.anthropic_api_key, settings.effort, settings.model) == ("abc", "high", "claude-sonnet-5-5")
    assert (settings.decision_backend, settings.langfuse_host, settings.langfuse_environment) == ("openai", "https://lf.example", "day05_new")


def test_judge_effort_override_through_day05_env_file(tmp_path, monkeypatch):
    env = tmp_path / "judge.env"
    env.write_text("ANTHROPIC_API_KEY=k\nDAY05_JUDGE_EFFORT=max\nDAY05_IMPROVER_EFFORT=low\n", encoding="utf-8")
    monkeypatch.setenv("DAY05_ENV_FILE", str(env))
    settings = load_settings()
    assert (settings.judge_effort, settings.improver_effort) == ("max", "low")
    assert make_judge_model(settings).effort == "max"


def test_load_settings_ignores_shell_environment_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-shell")
    assert load_settings().anthropic_api_key == ""


def test_judge_model_uses_xhigh_and_large_token_budget():
    model = make_judge_model(Settings(anthropic_api_key="sk-test"))
    assert (model.model, model.effort, model.max_tokens) == ("claude-sonnet-5-5", "xhigh", 32000)
    assert (model.temperature, model.thinking, model.max_retries) == (None, None, 0)


def test_agent_and_improver_models_use_their_own_effort():
    settings = Settings(anthropic_api_key="sk-test")
    agent = make_agent_model(settings)
    improver = make_improver_model(settings)
    assert (agent.effort, agent.max_tokens) == ("medium", 16000)
    assert (improver.effort, improver.max_tokens) == ("high", 16000)
    assert (agent.temperature, agent.thinking, agent.max_retries) == (None, None, 0)


@pytest.mark.parametrize("factory", [make_agent_model, make_judge_model, make_improver_model])
def test_model_factories_require_the_anthropic_key(factory):
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        factory(Settings())


def test_make_langfuse_requires_both_keys_and_uses_host():
    with pytest.raises(RuntimeError) as caught:
        make_langfuse(Settings(langfuse_public_key="pk-x"))
    assert "LANGFUSE_SECRET_KEY" in str(caught.value) and "LANGFUSE_PUBLIC_KEY" not in str(caught.value)


def test_make_decider_picks_backends_in_order():
    keys = {"azure_openai_api_key": "d", "openai_api_key": "c", "openrouter_api_key": "b", "typesafe_api_key": "a"}
    azure = {"azure_endpoint": "https://r.example", "azure_deployment": "dep"}
    assert make_decider(Settings(**keys)).name == "typesafe"
    del keys["typesafe_api_key"]
    assert make_decider(Settings(**keys)).name == "openrouter"
    del keys["openrouter_api_key"]
    assert make_decider(Settings(**keys)).name == "openai"
    del keys["openai_api_key"]
    assert make_decider(Settings(**keys, **azure)).name == "azure"


def test_make_decider_without_any_key_names_the_variables_and_env_example():
    with pytest.raises(RuntimeError) as caught:
        make_decider(Settings(anthropic_api_key="only-claude"))
    message = str(caught.value)
    assert all(name in message for name in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY"))
    assert "Day05_new/.env.example을 .env로 복사" in message and "only-claude" not in message


def test_azure_key_without_endpoint_names_day05_variables():
    with pytest.raises(RuntimeError) as caught:
        make_decider(Settings(azure_openai_api_key="a"))
    assert "DAY05_AZURE_ENDPOINT" in str(caught.value) and "DAY05_AZURE_DEPLOYMENT" in str(caught.value)


def test_unknown_backend_name_is_rejected():
    with pytest.raises(RuntimeError, match="DAY05_DECISION_BACKEND"):
        make_decider(Settings(decision_backend="nope", typesafe_api_key="a"))


def test_typesafe_posts_native_body_with_bearer_and_parses_verdicts():
    client, seen = serve({"model": "jev-1.14.0", "answers": ANSWERS, "usage": {"input_tokens": 40, "output_tokens": 3}})
    judgment = TypeSafeBackend(KEY, client=client).judge(STATE, QUESTIONS)
    request = seen[0]
    assert str(request.url) == "https://api.typesafe.ai/v1/systemone" and request.headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(request.content) == {"model": "jev-latest", "state": STATE, "questions": {
        "relevant": {"type": "noul", "instructions": "근거가 질문에 답하는가?", "criteria": {"true": "답한다", "false": "답하지 않는다"}},
        "kind": {"type": "choice", "instructions": "문서 종류는?", "criteria": {"policy": "정책", "faq": "자주 묻는 질문"}},
        "depth": {"type": "score", "instructions": "얼마나 자세한가?", "criteria": ["한 줄", "한 문단", "상세"]}}}
    relevant, kind, depth = (judgment.verdicts[q.name] for q in QUESTIONS)
    assert (relevant.probability, kind.choice, depth.score) == (1.0, "policy", 1.2)
    assert (judgment.backend, judgment.model, judgment.input_tokens, judgment.output_tokens) == ("typesafe", "jev-1.14.0", 40, 3)


def test_missing_answer_becomes_a_refused_verdict():
    client, _ = serve({"answers": {"relevant": ANSWERS["relevant"]}})
    verdicts = TypeSafeBackend(KEY, client=client).judge(STATE, QUESTIONS).verdicts
    assert [verdicts[n].refused for n in ("relevant", "kind", "depth")] == [False, True, True]


@pytest.mark.parametrize("backend", list(BACKENDS.values()))
def test_http_500_raises_decision_error_without_key_or_state(backend):
    client, _ = serve({"error": f"bad key {KEY}"}, status=500)
    with pytest.raises(DecisionError) as caught:
        backend(KEY, base_url="https://gateway.example", client=client).judge(STATE, QUESTIONS)
    message = str(caught.value)
    assert "HTTP 500" in message and KEY not in message and STATE not in message


def test_transport_failure_message_has_no_key():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach with {KEY}")

    client = httpx.Client(transport=httpx.MockTransport(boom))
    with pytest.raises(DecisionError) as caught:
        TypeSafeBackend(KEY, client=client).judge(STATE, QUESTIONS)
    assert KEY not in str(caught.value) and "전송 실패" in str(caught.value)


def test_on_usage_receives_token_counts_and_cost_only_when_reported():
    usages: list[dict] = []
    reply = {"model": "jev-1.14.0", "answers": ANSWERS, "usage": {"input_tokens": 40, "output_tokens": 3}}
    TypeSafeBackend(KEY, client=serve(reply)[0], on_usage=usages.append).judge(STATE, QUESTIONS)
    reply["usage"]["cost"] = 0.002
    TypeSafeBackend(KEY, client=serve(reply)[0], on_usage=usages.append).judge(STATE, QUESTIONS)
    assert usages == [{"model": "jev-1.14.0", "input_tokens": 40, "output_tokens": 3},
                      {"model": "jev-1.14.0", "input_tokens": 40, "output_tokens": 3, "cost": 0.002}]


def test_fake_decider_returns_scripted_verdicts_and_records_calls():
    decider = FakeDecider({"relevant": 0.9, "depth": 2, "kind": "faq"})
    judgment = decider.judge(STATE, QUESTIONS)
    assert (judgment.verdicts["relevant"].probability, judgment.verdicts["depth"].score, judgment.verdicts["kind"].choice) == (0.9, 2.0, "faq")
    decider.judge("다른 근거", QUESTIONS[:1])
    assert decider.calls == [(STATE, ["relevant", "kind", "depth"]), ("다른 근거", ["relevant"])]


def test_fake_decider_marks_unscripted_questions_refused_and_can_raise():
    assert FakeDecider({}).judge(STATE, QUESTIONS[:1]).verdicts["relevant"].refused
    failing = FakeDecider(error=DecisionError("fake: HTTP 500"))
    with pytest.raises(DecisionError, match="HTTP 500"):
        failing.judge(STATE, QUESTIONS)
    assert len(failing.calls) == 1


def test_fake_chat_model_replays_scripted_tool_calls_and_records_bound_tool_names():
    call = {"name": "search", "args": {"q": "취소"}, "id": "call-1"}
    model = FakeChatModel.scripted([AIMessage(content="", tool_calls=[call]), AIMessage(content="끝")])
    bound = model.bind_tools([{"name": "search"}, {"name": "read"}])
    assert bound is model and model.bound_tools == [["search", "read"]]
    first = bound.invoke("질문")
    assert first.tool_calls[0]["name"] == "search" and bound.invoke("다음").content == "끝"


def test_conftest_clears_every_environment_variable_it_lists():
    import os
    assert not any(name in os.environ for name in ALL_ENV_NAMES)
    assert os.environ["DAY05_ENV_FILE"].endswith("no-such.env")


@pytest.mark.parametrize("family, address", [(socket.AF_INET, ("127.0.0.1", 9)), (socket.AF_INET6, ("::1", 9, 0, 0))])
def test_real_network_connect_raises_the_conftest_error(family, address):
    with socket.socket(family, socket.SOCK_STREAM) as sock, pytest.raises(RuntimeError, match="tests must not use the network"):
        sock.connect(address)


def test_unix_socket_and_subprocess_pipes_still_work():
    import subprocess
    import sys
    left, right = socket.socketpair()
    left.sendall(b"ok")
    assert right.recv(2) == b"ok"
    left.close(), right.close()
    out = subprocess.run([sys.executable, "-c", "print('pipe')"], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "pipe"
