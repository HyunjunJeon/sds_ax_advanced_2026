"""Decision API 계층. httpx.MockTransport로 요청 본문·주소·응답 해석을 확인한다. 네트워크와 유료 호출은 없다."""
import json

import httpx
import pytest
from rag_lab.decisions import (BACKENDS, AzureOpenAIDecisionsBackend, Choice, DecisionError, Noul, OpenAIDecisionsBackend, OpenRouterBackend, Score,
                               TypeSafeBackend, make_decider)
from rag_lab.settings import Settings

KEY = "sk-test-decision-key-9876543210"
STATE = "환불 기한은 7일이다. 개인정보는 비밀번호 hunter2 이다."
QUESTIONS = [Noul("relevant", "근거가 질문에 답하는가?", "답한다", "답하지 않는다"),
             Choice("kind", "문서 종류는?", {"policy": "정책", "faq": "자주 묻는 질문"}),
             Score("depth", "얼마나 자세한가?", ["한 줄", "한 문단", "상세"])]
NATIVE_ANSWERS = {"relevant": {"type": "noul", "noul": 1},
                  "kind": {"type": "choice", "choice": "policy", "confidence": 0.9, "probabilities": {"policy": 0.9, "faq": 0.1}},
                  "depth": {"type": "score", "score": 1.2, "confidence": 0.6, "legend": {"0": "한 줄"},
                            "probabilities": {"0": 0.1, "1": 0.7, "2": 0.2}}}
OPENAI_ANSWERS = [{"type": "predicate", "name": "relevant", "probability": 0.95},
                  {"type": "choice", "name": "kind", "choice": "faq", "confidence": 0.8,
                   "probabilities": [{"value": "policy", "probability": 0.2}, {"value": "faq", "probability": 0.8}]},
                  {"type": "score", "name": "depth", "score": 1.1, "confidence": 0.55,
                   "probabilities": [{"value": 0, "label": "한 줄", "probability": 0.1}, {"value": 1, "label": "한 문단", "probability": 0.7},
                                     {"value": 2, "label": "상세", "probability": 0.2}]}]


def serve(reply: dict | list | None = None, status: int = 200, raw: bytes | None = None):
    """(client, 받은 요청 목록)을 돌려준다. reply는 JSON 본문이다."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, content=raw) if raw is not None else httpx.Response(status, json=reply)

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def native_reply(**extra) -> dict:
    return {"model": "jev-1.14.0", "answers": NATIVE_ANSWERS, "usage": {"input_tokens": 40, "output_tokens": 3}, **extra}


def openai_reply(answers=None) -> dict:
    return {"model": "gpt-6-luna", "answers": OPENAI_ANSWERS if answers is None else answers,
            "usage": {"input_tokens": 162, "output_tokens": 0, "total_tokens": 162}}


def test_typesafe_sends_native_body_to_systemone_with_bearer():
    client, seen = serve(native_reply())
    TypeSafeBackend(KEY, client=client).judge(STATE, QUESTIONS)
    request = seen[0]
    assert str(request.url) == "https://api.typesafe.ai/v1/systemone" and request.headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(request.content) == {"model": "jev-latest", "state": STATE, "questions": {
        "relevant": {"type": "noul", "instructions": "근거가 질문에 답하는가?", "criteria": {"true": "답한다", "false": "답하지 않는다"}},
        "kind": {"type": "choice", "instructions": "문서 종류는?", "criteria": {"policy": "정책", "faq": "자주 묻는 질문"}},
        "depth": {"type": "score", "instructions": "얼마나 자세한가?", "criteria": ["한 줄", "한 문단", "상세"]}}}


def test_openrouter_uses_alpha_decisions_path_and_pinned_model():
    client, seen = serve(native_reply())
    OpenRouterBackend(KEY, client=client).judge(STATE, QUESTIONS[:1])
    assert str(seen[0].url) == "https://openrouter.ai/api/alpha/decisions"
    assert json.loads(seen[0].content)["model"] == "typesafe/jev-1.13"


def test_openai_sends_list_of_typed_questions_and_folds_criteria_into_instructions():
    client, seen = serve(openai_reply())
    OpenAIDecisionsBackend(KEY, client=client).judge(STATE, QUESTIONS)
    assert str(seen[0].url) == "https://api.openai.com/v1/decisions" and seen[0].headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(seen[0].content) == {"model": "gpt-6-luna", "input": STATE, "questions": [
        {"type": "predicate", "name": "relevant", "instructions": "근거가 질문에 답하는가?\n참이면: 답한다\n거짓이면: 답하지 않는다"},
        {"type": "choice", "name": "kind", "instructions": "문서 종류는?",
         "choices": [{"value": "policy", "description": "정책"}, {"value": "faq", "description": "자주 묻는 질문"}]},
        {"type": "score", "name": "depth", "instructions": "얼마나 자세한가?",
         "levels": [{"label": "한 줄", "description": "한 줄"}, {"label": "한 문단", "description": "한 문단"},
                    {"label": "상세", "description": "상세"}]}]}


def test_base_url_override_lets_another_host_reuse_the_openai_dialect():
    client, seen = serve(openai_reply())
    OpenAIDecisionsBackend(KEY, base_url="https://gateway.example/openai/", client=client).judge(STATE, QUESTIONS[:1])
    assert str(seen[0].url) == "https://gateway.example/openai/v1/decisions"


ENDPOINT = "https://my-resource.openai.azure.com"
# learn.microsoft.com/azure/foundry/openai/how-to/decisions (2026-10-23)의 응답 모양: OpenAI와 같고 refusal의 name은 null일 수 있다.
AZURE_REFUSAL = [{"type": "refusal", "name": None, "refusal": "요청을 처리할 수 없습니다."}]


def azure(client: httpx.Client) -> AzureOpenAIDecisionsBackend:
    return AzureOpenAIDecisionsBackend(KEY, ENDPOINT + "/", client=client, model="my-deployment")


def test_azure_posts_openai_body_to_resource_path_with_api_key_header_and_deployment_as_model():
    client, seen = serve(openai_reply())
    azure(client).judge(STATE, QUESTIONS)
    request = seen[0]
    assert str(request.url) == f"{ENDPOINT}/openai/v1/decisions"
    assert request.headers["api-key"] == KEY and "authorization" not in request.headers
    body = json.loads(request.content)
    assert body["model"] == "my-deployment" and body["input"] == STATE and [q["type"] for q in body["questions"]] == ["predicate", "choice", "score"]


def test_azure_parses_predicate_choice_and_score_answers_and_usage():
    judgment = azure(serve(openai_reply())[0]).judge(STATE, QUESTIONS)
    verdicts = judgment.verdicts
    assert verdicts["relevant"].probability == 0.95 and verdicts["kind"].choice == "faq" and verdicts["depth"].score == 1.1
    assert (judgment.backend, judgment.input_tokens, judgment.output_tokens) == ("azure", 162, 0)


def test_azure_refusal_with_null_name_marks_every_unanswered_question_refused():
    verdicts = azure(serve(openai_reply(AZURE_REFUSAL + [OPENAI_ANSWERS[1]]))[0]).judge(STATE, QUESTIONS).verdicts
    assert [verdicts[n].refused for n in ("relevant", "kind", "depth")] == [True, False, True]
    assert all(v.refused for v in azure(serve(openai_reply(AZURE_REFUSAL))[0]).judge(STATE, QUESTIONS).verdicts.values())


def test_native_answers_map_to_verdicts_and_usage():
    client, _ = serve(native_reply(usage={"input_tokens": 40, "output_tokens": 3, "cost": 0.002}))
    judgment = OpenRouterBackend(KEY, client=client).judge(STATE, QUESTIONS)
    relevant, kind, depth = (judgment.verdicts[q.name] for q in QUESTIONS)
    assert (relevant.probability, relevant.refused) == (1.0, False)
    assert (kind.choice, kind.confidence, kind.probabilities) == ("policy", 0.9, {"policy": 0.9, "faq": 0.1})
    assert (depth.score, depth.probabilities["1"]) == (1.2, 0.7)
    assert (judgment.backend, judgment.model, judgment.input_tokens, judgment.output_tokens, judgment.cost) == ("openrouter", "jev-1.14.0", 40, 3, 0.002)


def test_openai_answers_map_by_name_with_probabilities_keyed_by_value_or_label():
    client, _ = serve(openai_reply())
    verdicts = OpenAIDecisionsBackend(KEY, client=client).judge(STATE, QUESTIONS).verdicts
    assert verdicts["relevant"].probability == 0.95 and verdicts["relevant"].kind == "noul"
    assert (verdicts["kind"].choice, verdicts["kind"].probabilities) == ("faq", {"policy": 0.2, "faq": 0.8})
    assert (verdicts["depth"].score, verdicts["depth"].probabilities["한 문단"]) == (1.1, 0.7)


def test_openai_refusal_and_missing_answer_become_refused_verdicts_not_errors():
    answers = [{"type": "refusal", "name": "relevant"}, OPENAI_ANSWERS[1]]  # depth는 아예 빠졌다
    client, _ = serve(openai_reply(answers))
    verdicts = OpenAIDecisionsBackend(KEY, client=client).judge(STATE, QUESTIONS).verdicts
    assert [verdicts[n].refused for n in ("relevant", "kind", "depth")] == [True, False, True]
    assert verdicts["relevant"].probability is None and verdicts["depth"].score is None


def test_native_missing_answer_is_refused():
    client, _ = serve({"answers": {"relevant": NATIVE_ANSWERS["relevant"]}})
    verdicts = TypeSafeBackend(KEY, client=client).judge(STATE, QUESTIONS).verdicts
    assert [verdicts[n].refused for n in ("relevant", "kind", "depth")] == [False, True, True]


def failing_client(kind: str) -> httpx.Client:
    if kind == "timeout":
        def boom(request):
            raise httpx.ReadTimeout(f"{request.url} Bearer {KEY}")
        return httpx.Client(transport=httpx.MockTransport(boom))
    return serve(raw=b"{not json", status=200)[0] if kind == "json" else serve({"error": f"bad key {KEY}"}, status=400)[0]


@pytest.mark.parametrize("backend", list(BACKENDS.values()))
@pytest.mark.parametrize("kind, expected", [("http", "HTTP 400"), ("timeout", "ReadTimeout"), ("json", "응답 형식")])
def test_failures_raise_decision_error_without_key_or_state(backend, kind, expected):
    with pytest.raises(DecisionError) as caught:
        backend(KEY, base_url="https://gateway.example", client=failing_client(kind)).judge(STATE, QUESTIONS)
    message = str(caught.value)
    assert expected in message and KEY not in message and "hunter2" not in message
    assert caught.value.__cause__ is None and (caught.value.__context__ is None or caught.value.__suppress_context__)


@pytest.mark.parametrize("reply", [[1, 2], {"answers": "x"}, {"answers": None}])
def test_unexpected_body_shapes_are_decision_errors(reply):
    with pytest.raises(DecisionError):
        TypeSafeBackend(KEY, client=serve(reply)[0]).judge(STATE, QUESTIONS)


def settings(**keys: str) -> Settings:
    return Settings(api_key="", **keys)


def test_make_decider_picks_first_key_in_typesafe_openrouter_openai_order():
    assert make_decider(settings(openai_api_key="a", openrouter_api_key="b")).name == "openrouter"
    assert make_decider(settings(openai_api_key="a", openrouter_api_key="b", typesafe_api_key="c")).name == "typesafe"
    assert make_decider(settings(openai_api_key="a")).name == "openai"


AZURE = {"azure_openai_api_key": "a", "azure_endpoint": ENDPOINT, "azure_deployment": "my-deployment"}


def test_azure_is_last_in_auto_order_and_configured_from_settings():
    assert make_decider(settings(**AZURE)).name == "azure"
    assert make_decider(settings(openai_api_key="b", **AZURE)).name == "openai"
    assert make_decider(settings(decision_backend="azure", openai_api_key="b", **AZURE)).model == "my-deployment"


@pytest.mark.parametrize("missing", ["azure_endpoint", "azure_deployment"])
def test_azure_key_without_endpoint_or_deployment_stops_with_korean_message(missing):
    with pytest.raises(RuntimeError) as caught:
        make_decider(settings(**{**AZURE, missing: "  "}))
    message = str(caught.value)
    assert "DAY02_AZURE_ENDPOINT" in message and "DAY02_AZURE_DEPLOYMENT" in message and ".env" in message


def test_openrouter_model_setting_overrides_the_pin_and_blank_keeps_it():
    assert make_decider(settings(openrouter_api_key="b", openrouter_model="typesafe/jev-9.9")).model == "typesafe/jev-9.9"
    assert make_decider(settings(openrouter_api_key="b")).model == "typesafe/jev-1.13"


def test_make_decider_honours_explicit_backend_and_does_not_fall_back_when_its_key_is_missing():
    assert make_decider(settings(typesafe_api_key="a", openai_api_key="b", decision_backend="openai")).name == "openai"
    with pytest.raises(RuntimeError) as caught:
        make_decider(settings(typesafe_api_key="a", decision_backend="openai"))
    assert "OPENAI_API_KEY" in str(caught.value) and "TYPESAFE" not in str(caught.value)


def test_make_decider_rejects_unknown_backend_name():
    with pytest.raises(RuntimeError, match="typesafe, openrouter, openai, azure"):
        make_decider(settings(typesafe_api_key="a", decision_backend="claude"))


@pytest.mark.parametrize("keys", [{}, {"typesafe_api_key": "  "}])
def test_missing_key_stops_with_korean_message_naming_variables_and_no_claude_fallback(keys):
    with pytest.raises(RuntimeError) as caught:
        make_decider(Settings(api_key="sk-ant-only-anthropic", **keys))
    message = str(caught.value)
    assert all(name in message for name in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY"))
    assert ".env.example을 .env로 복사" in message and "직접 채우세요" in message


def test_each_judgment_appends_one_usage_line_with_cost_only_when_reported(tmp_path, monkeypatch):
    path = tmp_path / "새 폴더" / "u.jsonl"
    monkeypatch.setenv("DAY02_USAGE_LOG", str(path))
    OpenRouterBackend(KEY, client=serve(native_reply(usage={"input_tokens": 40, "output_tokens": 3, "cost": 0.002}))[0]).judge(STATE, QUESTIONS)
    OpenAIDecisionsBackend(KEY, client=serve(openai_reply())[0]).judge(STATE, QUESTIONS)
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert lines == [{"model": "jev-1.14.0", "input_tokens": 40, "output_tokens": 3, "cost": 0.002},
                     {"model": "gpt-6-luna", "input_tokens": 162, "output_tokens": 0}]
    assert STATE not in path.read_text(encoding="utf-8") and KEY not in path.read_text(encoding="utf-8")


def test_failed_call_writes_no_usage_line(tmp_path, monkeypatch):
    monkeypatch.setenv("DAY02_USAGE_LOG", str(tmp_path / "u.jsonl"))
    with pytest.raises(DecisionError):
        TypeSafeBackend(KEY, client=serve({}, status=500)[0]).judge(STATE, QUESTIONS)
    assert not (tmp_path / "u.jsonl").exists()


def test_a_new_decision_api_is_one_small_class():
    class EchoBackend(TypeSafeBackend):
        name, key_env, base_url, path, model = "echo", "ECHO_API_KEY", "https://echo.example", "/judge", "echo-1"

    client, seen = serve(native_reply())
    assert EchoBackend(KEY, client=client).judge(STATE, QUESTIONS[:1]).backend == "echo"
    assert str(seen[0].url) == "https://echo.example/judge"


def test_real_typesafe_reply_recorded_2026_11_has_no_cost_and_index_keyed_score_probabilities():
    # api.typesafe.ai/v1/systemone 실제 응답(jev-1.14.0). 요청의 model은 jev-latest이고 응답이 실제 버전을 알려 주며 usage에 cost가 없다.
    real = {"model": "jev-1.14.0",
            "answers": {"rel": {"type": "noul", "noul": 0.98},
                        "depth": {"type": "score", "score": 1.25, "confidence": 0.62, "legend": {"0": "none", "1": "partial", "2": "full"},
                                  "probabilities": {"0": 0.0, "1": 0.75, "2": 0.25}}},
            "usage": {"input_tokens": 403, "output_tokens": 61}}
    judgment = TypeSafeBackend(KEY, client=serve(real)[0]).judge(STATE, [Noul("rel", "i", "t", "f"), Score("depth", "i", ["none", "partial", "full"])])
    assert (judgment.model, judgment.cost, judgment.verdicts["rel"].probability) == ("jev-1.14.0", None, 0.98)
    assert judgment.verdicts["depth"].probabilities == {"0": 0.0, "1": 0.75, "2": 0.25}
