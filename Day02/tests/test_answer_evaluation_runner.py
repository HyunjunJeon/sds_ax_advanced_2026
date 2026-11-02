"""실제 네트워크 없이 평가 실행기의 결과 보존·세션·비용 계약을 검증한다."""
import importlib.util
import json
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest

from day02.evaluation import AnswerQuality


@pytest.fixture
def runner(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "answer_runner", Path(__file__).resolve().parents[1] / "scripts/evaluate_answers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    corpus = module.load_corpus(module.ROOT, module.CORPUS)
    monkeypatch.setattr(module, "load_corpus", lambda *_: corpus)
    day = tmp_path / "Day02"
    day.mkdir()
    monkeypatch.setattr(module, "ROOT", day)
    (tmp_path / "uv.lock").write_text("offline fixture")
    monkeypatch.setattr(module.Settings, "load", lambda: SimpleNamespace(
        model="fake", require_model_key=lambda: None))
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("network forbidden"))
    return module


def output(module):
    folder, = (module.ROOT / "outputs/answer-evaluation").iterdir()
    rows = [json.loads(line) for line in (folder / "runs.jsonl").read_text().splitlines()]
    return rows, json.loads((folder / "summary.json").read_text())


def answered(question, **kwargs):
    budget = kwargs["budget"]
    budget.consume("model")
    budget.consume("usage", usage={"input_tokens": 7, "output_tokens": 3})
    return {"status": "answered", "question": question, "answer": {"sections": []},
            "trace": budget.report()}


def test_auth_failure_keeps_all_rows_trace_and_skips_judge(runner, monkeypatch):
    class AuthenticationError(Exception):
        pass

    def fail(*args, **kwargs):
        kwargs["budget"].consume("model")
        raise AuthenticationError("do not persist exception secrets")

    monkeypatch.setattr(runner, "ask", fail)
    monkeypatch.setattr(runner, "make_model", lambda *_: pytest.fail("judge must not be built"))
    assert runner.main() == 1
    rows, summary = output(runner)
    assert len(rows) == 2 and summary["errors"] == 2
    assert summary["model_calls"] == 2
    assert summary["usage_missing_runs"] == 2 and summary["agent_input_tokens"] is None
    assert summary["judge_coverage"] == 0 and summary["judged_accuracy"] is None
    assert all(r["evaluation"]["observed_abstention"] is None for r in rows)
    assert "do not persist" not in json.dumps(rows)


@pytest.mark.parametrize("phase", ["construct", "invoke", "parse"])
def test_judge_failures_preserve_successful_agent_rows(runner, monkeypatch, phase):
    monkeypatch.setattr(runner, "ask", lambda settings, question, **kw: answered(question, **kw))

    class Judge:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, _):
            if phase == "invoke":
                raise RuntimeError("judge unavailable")
            return {"raw": SimpleNamespace(usage_metadata={"input_tokens": 5, "output_tokens": 1}),
                    "parsed": None, "parsing_error": ValueError("bad JSON")}

    def make(*_):
        if phase == "construct":
            raise RuntimeError("configuration failure")
        return Judge()

    monkeypatch.setattr(runner, "make_model", make)
    assert runner.main() == 1
    rows, summary = output(runner)
    assert all(r["run"]["status"] == "answered" for r in rows)
    assert summary["errors"] == 0 and summary["judge_errors"] == 2
    assert summary["judge_coverage"] == 0
    assert summary["agent_input_tokens"] == 14
    if phase == "parse":
        assert all(r["evaluation"]["judge_usage"]["input_tokens"] == 5 for r in rows)


def test_followup_final_turn_only_with_session_isolation(runner, monkeypatch):
    monkeypatch.setattr(runner, "CASE_IDS", ["tech-followup", "tech-blob"])
    monkeypatch.setattr(runner, "REPEATS", 2)
    sessions, judged = [], []

    def ask(settings, question, **kwargs):
        sessions.append(kwargs["session"])
        return answered(question, **kwargs)

    class Judge:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            judged.append(json.loads(messages[-1]["content"])["question"])
            return {"raw": SimpleNamespace(usage_metadata={"input_tokens": 5, "output_tokens": 1}),
                    "parsed": AnswerQuality(correct=True, supported=True, appropriate_abstention=True,
                                            missing_facts=[], unsupported_claims=[], reason="mock"),
                    "parsing_error": None}

    monkeypatch.setattr(runner, "ask", ask)
    monkeypatch.setattr(runner, "make_model", lambda *_: Judge())
    assert runner.main() == 0
    rows, summary = output(runner)
    assert len(rows) == 6 and summary["final_turns"] == 4 and len(judged) == 4
    assert sessions[0] == sessions[1] and sessions[3] == sessions[4]
    assert len(set(sessions)) == 4
    assert "evaluation" not in rows[0] and "evaluation" not in rows[3]
    assert summary["model_calls"] == 6 and summary["agent_input_tokens"] == 42
    assert summary["agent_output_tokens"] == 18 and summary["judge_coverage"] == 1


def test_partial_usage_is_unknown_and_judge_disabled(runner, monkeypatch):
    monkeypatch.setattr(runner, "JUDGE", False)
    count = 0

    def ask(settings, question, **kwargs):
        nonlocal count
        count += 1
        if count == 1:
            return answered(question, **kwargs)
        kwargs["budget"].consume("model")
        return {"status": "insufficient", "trace": kwargs["budget"].report()}

    monkeypatch.setattr(runner, "ask", ask)
    monkeypatch.setattr(runner, "make_model", lambda *_: pytest.fail("judge disabled"))
    assert runner.main() == 0
    rows, summary = output(runner)
    assert summary["usage_observed_runs"] == 1 and summary["usage_missing_runs"] == 1
    assert summary["agent_input_tokens"] is None and summary["agent_output_tokens"] is None
    assert rows[1]["evaluation"]["observed_abstention"] is True
    assert summary["judge_coverage"] == 0
