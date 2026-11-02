"""check_sources.py 공개 CLI(main, 명령줄)로 검사 규칙을 확인한다.

블로그 본문은 쓰지 않는다. 각 테스트가 tmp_path에 지어낸 블로그를 만든다.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import check_sources

SCRIPT = Path(check_sources.__file__)

# 30자 안팎이라 연속 일치(41자)에는 걸리지 않고 문장 유사도로만 잡힌다.
SENTENCE = "블록 풀은 해시 값으로 이미 계산된 블록을 다시 찾아낸다"
LONG_SENTENCE = "스케줄러는 매 step마다 대기 중인 요청과 실행 중인 요청을 함께 살펴보고 순서를 정한다"
CODE_LINE = "self.scheduler.schedule(request_queue, max_num_batched_tokens=8192) # run once"
TITLE = "Inside vLLM: 서버 시작부터 KV cache까지 소스 코드 톺아보기"


@pytest.fixture
def blog(tmp_path: Path) -> Path:
    path = tmp_path / "blog.txt"
    path.write_text(f"{SENTENCE}.\n{LONG_SENTENCE}.\n{CODE_LINE}\n{TITLE}\n", encoding="utf-8")
    return path


def run(blog: Path, *targets: Path) -> int:
    return check_sources.main(["--blog", str(blog), *map(str, targets)])


def write(tmp_path: Path, text: str, name: str = "ledger.md") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_copied_sentence_is_reported_with_path_line_and_ratio(blog, tmp_path, capsys):
    ledger = write(tmp_path, f"# 제목\n\n- 근거: {SENTENCE}\n")
    assert run(blog, ledger) == 1
    line = capsys.readouterr().out.strip()
    assert line.startswith(f"{ledger}:3 ratio=")
    assert SENTENCE in line


def test_rewritten_sentence_with_same_facts_passes(blog, tmp_path):
    ledger = write(tmp_path, "- 근거: 이미 계산이 끝난 블록은 해시로 조회되어 블록 풀이 재사용한다\n")
    assert run(blog, ledger) == 0


def test_blog_section_column_is_skipped_but_other_columns_are_not(blog, tmp_path, capsys):
    skipped = write(
        tmp_path,
        f"| ID | 주장 | 블로그 절 |\n|---|---|---|\n| A-01 | 다른 서술이다 | {SENTENCE} |\n",
        "skipped.md",
    )
    assert run(blog, skipped) == 0
    caught = write(
        tmp_path,
        f"| ID | 주장 | 블로그 절 |\n|---|---|---|\n| A-01 | {SENTENCE} | 큰 그림 |\n",
        "caught.md",
    )
    assert run(blog, caught) == 1
    assert "caught.md:3" in capsys.readouterr().out


def test_run_of_41_characters_is_caught_but_40_is_not(blog, tmp_path, capsys):
    tail = " 그 밖의 설명은 전혀 다른 내용이고 길이만 충분히 길게 이어 적은 문장이다 abc"
    run41 = write(tmp_path, LONG_SENTENCE[:41] + tail + "\n", "run41.md")
    assert run(blog, run41) == 1
    assert "run>40" in capsys.readouterr().out
    run40 = write(tmp_path, LONG_SENTENCE[:40] + "X" + tail + "\n", "run40.md")
    assert run(blog, run40) == 0


def test_code_only_line_passes_even_when_identical_to_blog(blog, tmp_path):
    ledger = write(tmp_path, CODE_LINE + "\n")
    assert run(blog, ledger) == 0


def test_allowed_title_is_not_reported(blog, tmp_path):
    ledger = write(tmp_path, f"블로그 제목은 {TITLE}이다.\n")
    assert run(blog, ledger) == 0


def test_code_piece_in_a_prose_line_is_not_reported(blog, tmp_path):
    ledger = write(tmp_path, f"전혀 다른 설명을 한글로 길게 적은 칸이다 | {CODE_LINE}\n")
    assert run(blog, ledger) == 0


def test_backticks_do_not_hide_a_copied_run(blog, tmp_path):
    ticked = LONG_SENTENCE[:50].replace(" ", " `", 3)  # 단어 사이에 백틱을 끼운 41자 넘는 복사
    ledger = write(tmp_path, ticked + " 그 밖의 설명은 전혀 다른 내용이고 길이만 충분히 길게 이어 적은 문장이다 abc\n")
    assert run(blog, ledger) == 1


def test_notebook_markdown_is_read_and_code_cells_are_ignored(blog, tmp_path, capsys):
    def notebook(cells):
        return {"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}

    markdown = {"cell_type": "markdown", "metadata": {}, "source": ["# 메모\n", f"{SENTENCE}\n"]}
    code = {"cell_type": "code", "metadata": {}, "outputs": [], "source": [f"print('{SENTENCE}')"]}
    with_markdown = write(tmp_path, json.dumps(notebook([markdown])), "md.ipynb")
    assert run(blog, with_markdown) == 1
    assert "md.ipynb:2" in capsys.readouterr().out
    only_code = write(tmp_path, json.dumps(notebook([code])), "code.ipynb")
    assert run(blog, only_code) == 0


def test_missing_blog_exits_2(tmp_path):
    ledger = write(tmp_path, "아무 내용이나 적은 대장 문장이다 충분히 길게\n")
    assert run(tmp_path / "없음.txt", ledger) == 2


def test_empty_blog_exits_2(tmp_path):
    empty = write(tmp_path, " \n\t\n", "empty.txt")
    ledger = write(tmp_path, SENTENCE + "\n")
    assert run(empty, ledger) == 2


def test_missing_target_exits_2(blog, tmp_path):
    assert run(blog, tmp_path / "없음.md") == 2


def test_command_line_exit_code_for_missing_blog(tmp_path):
    ledger = write(tmp_path, SENTENCE + "\n")
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "--blog", str(tmp_path / "없음.txt"), str(ledger)],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 2
    assert "입력 오류" in done.stderr
