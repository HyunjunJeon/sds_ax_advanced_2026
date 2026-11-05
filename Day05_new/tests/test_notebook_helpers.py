"""노트북 도우미(eval_lab.notebook)의 공개 동작 시험."""
from eval_lab import notebook, settings
from pydantic import BaseModel


def test_announce_names_each_nonzero_part_and_minutes(capsys):
    notebook.announce("시험", model_calls=30, jev_calls=5, judge_calls=4, improver_calls=2, minutes=3)
    assert capsys.readouterr().out.strip() == (
        "[시험] 이 실행은 에이전트 모델 약 30회, Jev 최대 5회, Judge(xhigh) 최대 4회, "
        "개선기 약 2회, 3분 예상입니다. 진행합니다.")


def test_announce_omits_zero_parts(capsys):
    notebook.announce("시험", model_calls=7)
    assert capsys.readouterr().out.strip() == "[시험] 이 실행은 에이전트 모델 약 7회 예상입니다. 진행합니다."


def test_announce_all_zero_says_no_paid_calls(capsys):
    notebook.announce("시험", model_calls=0, minutes=1)
    assert capsys.readouterr().out.strip() == "이 실행은 유료 모델 호출이 없습니다."


def test_output_root_defaults_under_outputs_notebook(monkeypatch):
    monkeypatch.delenv("DAY05_OUTPUT_ROOT", raising=False)
    assert notebook.output_root() == settings.ROOT / "outputs" / "notebook"


def test_new_run_dir_makes_distinct_folders_under_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DAY05_OUTPUT_ROOT", str(tmp_path))
    first, second = notebook.new_run_dir("rsi"), notebook.new_run_dir("rsi")
    assert first != second
    assert first.is_dir() and second.is_dir()
    assert first.parent == tmp_path / "rsi"
    stamp, suffix = first.name.rsplit("-", 1)
    assert stamp.endswith("Z") and len(suffix) == 6


def test_langfuse_or_none_returns_none_without_keys(capsys):
    assert notebook.langfuse_or_none() is None
    assert "Langfuse 키가 미설정이라 로컬 경로로 진행합니다." in capsys.readouterr().out


def test_langfuse_or_none_uses_patched_factory_at_call_time(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(settings, "make_langfuse", lambda given=None: sentinel)
    assert notebook.langfuse_or_none() is sentinel


def test_langfuse_or_none_propagates_other_errors(monkeypatch):
    def broken(given=None):
        raise ValueError("boom")
    monkeypatch.setattr(settings, "make_langfuse", broken)
    try:
        notebook.langfuse_or_none()
    except ValueError as error:
        assert str(error) == "boom"
    else:
        raise AssertionError("ValueError가 전파되지 않았다")


def test_show_keys_never_prints_a_value(tmp_path, capsys):
    secret = "sk-fake-value-12345"
    env_file = tmp_path / "fake.env"
    env_file.write_text(f"ANTHROPIC_API_KEY={secret}\n", encoding="utf-8")
    notebook.show_keys(settings.load_settings(env_file))
    out = capsys.readouterr().out
    assert secret not in out and "12345" not in out
    assert "설정됨" in out and "미설정" in out


def test_show_accepts_dicts_and_models(capsys):
    class Row(BaseModel):
        name: str
        score: int

    notebook.show([{"name": "a", "score": 1}], title="딕셔너리")
    notebook.show([Row(name="b", score=2)], ["name"])
    out = capsys.readouterr().out
    assert "딕셔너리" in out and "a" in out and "b" in out
