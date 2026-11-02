"""check_secrets CLI 시험. 임시 폴더의 가짜 값만 쓰고 실제 .env는 열지 않는다."""
from pathlib import Path

from check_secrets import main

FAKE_VALUE = "fake-secret-value-0123456789"


def _write_env(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_clean_tree_exits_zero(tmp_path, capsys):
    env = _write_env(tmp_path / ".env", f"ANTHROPIC_API_KEY={FAKE_VALUE}\n")
    root = tmp_path / "tree"
    root.mkdir()
    (root / "a.txt").write_text("아무 비밀도 없는 파일", encoding="utf-8")

    code = main(["--env", str(env), "--root", str(root)])

    assert code == 0
    assert "secret scan: files=1 values=1 skipped_short=0 leaks=0" in capsys.readouterr().out


def test_leak_exits_one_and_hides_value(tmp_path, capsys):
    env = _write_env(tmp_path / ".env", f"TYPESAFE_API_KEY={FAKE_VALUE}\n")
    root = tmp_path / "tree"
    root.mkdir()
    (root / "notes.md").write_text(f"실수로 붙여 넣음: {FAKE_VALUE}", encoding="utf-8")

    code = main(["--env", str(env), "--root", str(root)])

    out = capsys.readouterr().out
    assert code == 1
    assert "notes.md" in out and "TYPESAFE_API_KEY" in out
    assert "leaks=1" in out
    assert FAKE_VALUE not in out and FAKE_VALUE[:8] not in out


def test_missing_env_exits_zero_with_message(tmp_path, capsys):
    code = main(["--env", str(tmp_path / "no.env"), "--root", str(tmp_path)])

    out = capsys.readouterr().out
    assert code == 0
    assert "secret scan: .env 없음" in out
    assert "values=0" in out


def test_short_values_are_skipped_and_counted(tmp_path, capsys):
    env = _write_env(tmp_path / ".env", "OPENAI_API_KEY=short\n")
    (tmp_path / "x.txt").write_text("short", encoding="utf-8")

    code = main(["--env", str(env), "--root", str(tmp_path)])

    assert code == 0
    assert "values=0 skipped_short=1 leaks=0" in capsys.readouterr().out


def test_env_file_and_excluded_folders_are_not_scanned(tmp_path, capsys):
    env = _write_env(tmp_path / ".env", f"LANGFUSE_SECRET_KEY={FAKE_VALUE}\n")
    for folder in (".venv", "__pycache__", ".git"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "f.txt").write_text(FAKE_VALUE, encoding="utf-8")

    code = main(["--env", str(env), "--root", str(tmp_path)])

    assert code == 0
    assert "files=0 values=1" in capsys.readouterr().out


def test_non_key_names_are_not_checked(tmp_path, capsys):
    env = _write_env(tmp_path / ".env", f"DAY05_MODEL={FAKE_VALUE}\n")
    (tmp_path / "a.txt").write_text(FAKE_VALUE, encoding="utf-8")

    code = main(["--env", str(env), "--root", str(tmp_path)])

    assert code == 0
    assert "values=0" in capsys.readouterr().out
