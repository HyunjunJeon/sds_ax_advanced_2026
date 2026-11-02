"""키 처리와 모델 생성. 실제 .env를 건드리지 않도록 가짜 값이나 임시 복사본으로 확인한다."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage
from rag_lab import settings as settings_module
from rag_lab.settings import Settings, UsageLog, announce, key_status, load_settings, make_embeddings, make_model, make_reranker, require_key

FAKE_KEY = "sk-test-not-a-real-key-1234567890"
SOURCE = Path(__file__).resolve().parents[1] / "rag_lab"
EXAMPLE = SOURCE.parent / ".env.example"
FORBIDDEN_FOR_OPUS_5_5 = {"temperature", "top_p", "top_k"}


def run_in_copy(tmp_path: Path, code: str, env_file: str | None, **env: str) -> str:
    """임시 Day02_new/rag_lab에서 code를 실행한다. ROOT는 임시 폴더가 된다."""
    root = tmp_path / "copy" / "Day02_new"
    shutil.copytree(SOURCE, root / "rag_lab", ignore=shutil.ignore_patterns("__pycache__"))
    if env_file is not None:
        (root / ".env").write_text(env_file, encoding="utf-8")
    done = subprocess.run([sys.executable, "-c", code], cwd=root, env=os.environ | env,
                          capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return done.stdout


@pytest.fixture
def empty_dotenv(monkeypatch):
    """실제 .env 대신 빈 값을 읽게 한다. 수강생이 아직 키를 채우지 않은 상태다."""
    monkeypatch.setattr(settings_module, "dotenv_values", lambda path: {})


def test_key_status_and_repr_never_contain_the_key():
    settings = Settings(api_key=FAKE_KEY)
    status = key_status(settings)
    text = json.dumps(status, ensure_ascii=False) + repr(settings) + str(settings)
    assert status["ANTHROPIC_API_KEY"] == "설정됨"
    assert FAKE_KEY not in text and FAKE_KEY[:6] not in text and str(len(FAKE_KEY)) not in text


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_key_counts_as_unset(value):
    assert key_status(Settings(api_key=value))["ANTHROPIC_API_KEY"] == "미설정"


@pytest.mark.parametrize("fail", [require_key, make_model])
def test_missing_key_fails_fast_with_korean_instruction(empty_dotenv, fail):
    with pytest.raises(RuntimeError) as caught:
        fail()
    assert ".env.example을 .env로 복사" in str(caught.value) and "직접 채우세요" in str(caught.value)


def test_require_key_returns_the_settings_when_key_exists():
    settings = Settings(api_key=FAKE_KEY)
    assert require_key(settings) is settings


def test_defaults_without_env_file(empty_dotenv):
    assert key_status(load_settings()) == {
        "ANTHROPIC_API_KEY": "미설정", "DAY02_MODEL": "claude-sonnet-5-5", "DAY02_EFFORT": "medium",
        "DAY02_EMBEDDING_MODEL": "intfloat/multilingual-e5-small",
        "DAY02_RERANK_MODEL": "BAAI/bge-reranker-v2-m3", "TYPESAFE_API_KEY": "미설정",
        "OPENROUTER_API_KEY": "미설정", "OPENAI_API_KEY": "미설정", "AZURE_OPENAI_API_KEY": "미설정", "DAY02_DECISION_BACKEND": ""}


def test_announce_prints_one_line_scale_notice(capsys):
    announce("연결 시험", model_calls=3)
    assert capsys.readouterr().out == "[연결 시험] 이 실행은 모델 호출 약 3회입니다. 진행합니다.\n"


def test_request_avoids_parameters_opus_5_5_rejects():
    payload = make_model(Settings(api_key=FAKE_KEY))._get_request_payload("안녕")
    assert not FORBIDDEN_FOR_OPUS_5_5 & payload.keys()
    assert payload.get("thinking", {}).get("type") != "disabled"
    assert payload["model"] == "claude-sonnet-5-5" and payload["output_config"]["effort"] == "medium"
    assert payload["max_tokens"] == 16000


def test_request_opts_into_server_side_fallback():
    payload = make_model(Settings(api_key=FAKE_KEY))._get_request_payload("안녕")
    assert payload["fallbacks"] == "default" and payload["betas"] == ["server-side-fallback-2026-07-01"]


def test_sdk_retries_are_off_so_budget_sees_every_call():
    assert make_model(Settings(api_key=FAKE_KEY)).max_retries == 0


def test_model_ignores_base_url_from_shell(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://다른곳.example")
    assert "example" not in make_model(Settings(api_key=FAKE_KEY)).anthropic_api_url


def test_embeddings_need_no_key_and_load_lazily():
    assert make_embeddings(Settings(api_key="")).model_name == "intfloat/multilingual-e5-small"


def test_reranker_needs_no_key_and_loads_lazily():
    assert make_reranker(Settings(api_key="")).model_name == "BAAI/bge-reranker-v2-m3"


def usage_model() -> ScriptedChatModel:
    reply = AIMessage(content="적으면 안 되는 답변", response_metadata={"model": "시험-모델"},
                      usage_metadata={"input_tokens": 12, "output_tokens": 5, "total_tokens": 17,
                                      "input_token_details": {"cache_read": 7, "cache_creation": 3}})
    return ScriptedChatModel(steps=[reply, reply], callbacks=[UsageLog()])


def test_usage_log_appends_tokens_without_content(tmp_path, monkeypatch):
    path = tmp_path / "새 폴더" / "사용량.jsonl"
    monkeypatch.setenv("DAY02_USAGE_LOG", str(path))
    model = usage_model()
    model.invoke("질문")
    model.invoke("질문")
    expected = {"model": "시험-모델", "input_tokens": 12, "output_tokens": 5, "cache_read_tokens": 7,
                "cache_write_tokens": 3}
    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [expected, expected]


# 실제 Anthropic 호출(2026-11-01, claude-sonnet-5-5)에서 langchain-anthropic이 만든 input_token_details 모양이다.
# 쓰기가 있으면 cache_creation은 0이고 TTL별 키에 들어간다.
REAL_WRITE_DETAILS = {"cache_read": 0, "cache_creation": 0, "ephemeral_5m_input_tokens": 18032,
                      "ephemeral_1h_input_tokens": 0}


def logged(tmp_path, monkeypatch, details: dict) -> dict:
    path = tmp_path / f"u{len(list(tmp_path.iterdir()))}.jsonl"
    monkeypatch.setenv("DAY02_USAGE_LOG", str(path))
    reply = AIMessage(content="x", response_metadata={"model": "m"},
                      usage_metadata={"input_tokens": 18054, "output_tokens": 4, "total_tokens": 18058,
                                      "input_token_details": details})
    ScriptedChatModel(steps=[reply], callbacks=[UsageLog()]).invoke("q")
    return json.loads(path.read_text(encoding="utf-8"))


def test_usage_log_records_five_minute_writes_from_real_shape(tmp_path, monkeypatch):
    line = logged(tmp_path, monkeypatch, REAL_WRITE_DETAILS)
    assert line["cache_write_tokens"] == 18032 and "cache_write_1h_tokens" not in line


def test_usage_log_records_one_hour_part_without_double_counting(tmp_path, monkeypatch):
    details = {**REAL_WRITE_DETAILS, "ephemeral_5m_input_tokens": 300, "ephemeral_1h_input_tokens": 200}
    line = logged(tmp_path, monkeypatch, details)
    assert line["cache_write_tokens"] == 500 and line["cache_write_1h_tokens"] == 200
    # cache_creation이 TTL 합과 같은 값으로 함께 와도 두 번 세지 않는다.
    assert logged(tmp_path, monkeypatch, {**details, "cache_creation": 500})["cache_write_tokens"] == 500


def test_usage_log_is_silent_when_env_is_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("DAY02_USAGE_LOG", raising=False)
    monkeypatch.chdir(tmp_path)
    usage_model().invoke("질문")
    assert list(tmp_path.iterdir()) == []


def test_env_example_lists_the_anthropic_settings_without_a_value():
    text = EXAMPLE.read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY=\n" in text and "DAY02_MODEL=claude-sonnet-5-5\n" in text
    assert "DAY02_EFFORT=medium\n" in text and "DAY02_EMBEDDING_MODEL=intfloat/multilingual-e5-small\n" in text
    assert all(f"{name}=\n" in text for name in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"))
    assert "DAY02_DECISION_BACKEND=\n" in text and "하나는 반드시" in text


def test_load_settings_ignores_exported_key_and_parent_env(tmp_path):
    (tmp_path / "copy").mkdir()
    (tmp_path / "copy" / ".env").write_text(f"ANTHROPIC_API_KEY={FAKE_KEY}\n", encoding="utf-8")
    code = "from rag_lab.settings import key_status; print(key_status()['ANTHROPIC_API_KEY'])"
    output = run_in_copy(tmp_path, code, None, ANTHROPIC_API_KEY=FAKE_KEY)
    assert output.strip() == "미설정"


def test_load_settings_reads_only_its_own_env_file(tmp_path):
    code = "from rag_lab.settings import key_status; s = key_status(); print(s['ANTHROPIC_API_KEY'], s['DAY02_MODEL'])"
    output = run_in_copy(tmp_path, code, f"ANTHROPIC_API_KEY={FAKE_KEY}\nDAY02_MODEL=시험-모델\n")
    assert output.strip() == "설정됨 시험-모델"
    assert FAKE_KEY not in output


def test_run_record_redacts_key_value(tmp_path):
    code = ("from rag_lab.agent import write_run_record\n"
            f"path = write_run_record({{'run_id': 'r1', 'errors': ['Bearer {FAKE_KEY} 거부됨']}})\n"
            "print(path.read_text(encoding='utf-8'))")
    output = run_in_copy(tmp_path, code, f"ANTHROPIC_API_KEY={FAKE_KEY}\n")
    assert FAKE_KEY not in output and "Bearer *** 거부됨" in output


def test_decision_keys_report_only_set_or_unset_and_stay_out_of_repr():
    settings = Settings(api_key="", typesafe_api_key=FAKE_KEY, decision_backend="openai")
    status = key_status(settings)
    text = json.dumps(status, ensure_ascii=False) + repr(settings)
    assert (status["TYPESAFE_API_KEY"], status["OPENROUTER_API_KEY"], status["OPENAI_API_KEY"]) == ("설정됨", "미설정", "미설정")
    assert status["DAY02_DECISION_BACKEND"] == "openai" and FAKE_KEY not in text


def test_load_settings_reads_decision_keys_from_its_own_env_only(tmp_path):
    code = ("from rag_lab.settings import load_settings; s = load_settings()\n"
            "print(bool(s.typesafe_api_key), bool(s.openrouter_api_key), bool(s.openai_api_key), s.decision_backend)")
    env = f"OPENROUTER_API_KEY={FAKE_KEY}\nDAY02_DECISION_BACKEND= OpenRouter \n"
    assert run_in_copy(tmp_path, code, env, TYPESAFE_API_KEY=FAKE_KEY).strip() == "False True False openrouter"


def test_azure_key_reports_only_set_or_unset_and_stays_out_of_repr():
    settings = Settings(api_key="", azure_openai_api_key=FAKE_KEY, azure_endpoint="https://r.openai.azure.com")
    assert key_status(settings)["AZURE_OPENAI_API_KEY"] == "설정됨" and FAKE_KEY not in json.dumps(key_status(settings)) + repr(settings)


def test_load_settings_reads_azure_and_openrouter_model_from_its_own_env(tmp_path):
    code = ("from rag_lab.settings import load_settings; s = load_settings()\n"
            "print(bool(s.azure_openai_api_key), s.azure_endpoint, s.azure_deployment, s.openrouter_model)")
    env = (f"AZURE_OPENAI_API_KEY={FAKE_KEY}\nDAY02_AZURE_ENDPOINT= https://r.openai.azure.com \n"
           "DAY02_AZURE_DEPLOYMENT=dep\nDAY02_OPENROUTER_MODEL=typesafe/jev-9.9\n")
    assert run_in_copy(tmp_path, code, env).strip() == "True https://r.openai.azure.com dep typesafe/jev-9.9"


@pytest.mark.parametrize("name", ["TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY"])
def test_run_record_redacts_decision_keys(tmp_path, name):
    code = ("from rag_lab.agent import write_run_record\n"
            f"print(write_run_record({{'run_id': 'r3', 'errors': ['Bearer {FAKE_KEY} 거부됨']}}).read_text(encoding='utf-8'))")
    output = run_in_copy(tmp_path, code, f"{name}={FAKE_KEY}\n")
    assert FAKE_KEY not in output and "Bearer *** 거부됨" in output


def test_run_record_without_key_is_not_corrupted(tmp_path):
    code = ("from rag_lab.agent import write_run_record\n"
            "print(write_run_record({'run_id': 'r2', 'label': '그대로'}).read_text(encoding='utf-8'))")
    assert json.loads(run_in_copy(tmp_path, code, None)) == {"run_id": "r2", "label": "그대로"}
