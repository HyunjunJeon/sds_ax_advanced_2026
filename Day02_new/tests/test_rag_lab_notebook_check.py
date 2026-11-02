"""check_notebook.py를 CLI로 실행해 거부와 통과를 확인한다."""
import subprocess
import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

CHECKER = Path(__file__).with_name("check_notebook.py")
TIMETABLE = "# 제목\n\n## 수업 시간표\n\n| 절 | 내용 | 분 |\n|---|---|---:|\n| 1 | 준비 | 7 |\n| 2 | 정리 | 3 |\n"
BODY = "## 직접 해보기\n\n## 확인 질문\n\n호출 규모를 적는다.\n\n## 정리\n"


def write_notebook(tmp_path: Path, code: str = "print('ok')", first: str = TIMETABLE, body: str = BODY) -> Path:
    path = tmp_path / "lesson 노트북.ipynb"
    nbformat.write(new_notebook(cells=[new_markdown_cell(first), new_code_cell(code), new_markdown_cell(body)]), path)
    return path


def run_check(path: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECKER), str(path), *flags], capture_output=True, text=True,
                          timeout=120, cwd=path.parent)


def test_accepts_valid_notebook(tmp_path):
    result = run_check(write_notebook(tmp_path), "--minutes", "10")
    assert result.returncode == 0, result.stderr


def test_rejects_wrong_minute_sum(tmp_path):
    result = run_check(write_notebook(tmp_path), "--minutes", "60", "--min-cells", "0", "--min-code", "0", "--min-md", "0")
    assert result.returncode == 1
    assert "분 합계가 10분" in result.stderr


def test_never_executes_cells(tmp_path):
    marker = tmp_path / "실행됨"
    code = f"open({str(marker)!r}, 'w')\nraise ValueError('실행되면 안 된다')"
    assert run_check(write_notebook(tmp_path, code=code), "--minutes", "10").returncode == 0
    assert not marker.exists()


def test_static_rejections_name_the_cause(tmp_path):
    cases = [
        ({"code": "from langgraph.graph import StateGraph"}, "StateGraph"),
        ({"code": "key = 'sk-abcdef1234567890'"}, "소스에 sk- 키"),
        ({"code": "from rag_lab.offline import tool_call"}, "삭제된 이름이 있습니다: rag_lab.offline"),
        ({"code": "live_cell('x')"}, "삭제된 이름이 있습니다: live_cell"),
        ({"code": "from fakes import ScriptedChatModel"}, "삭제된 이름이 있습니다: ScriptedChatModel"),
        ({"code": "OfflineHashEmbeddings()"}, "삭제된 이름이 있습니다: OfflineHashEmbeddings"),
        ({"code": "os.environ['DAY02_OFFLINE'] = '1'"}, "삭제된 이름이 있습니다: DAY02_OFFLINE"),
        ({"code": "print(CONNECTION_CHECK_LABEL)"}, "삭제된 이름이 있습니다: CONNECTION_CHECK_LABEL"),
        ({"code": "rag_script(skill='x', query='y')"}, "삭제된 이름이 있습니다: rag_script"),
        ({"code": "key_status()['OPENROUTER_API_KEY']"}, "삭제된 이름이 있습니다: OPENROUTER_API_KEY"),
        ({"code": "from langchain_openai import ChatOpenAI"}, "삭제된 이름이 있습니다: langchain_openai"),
        ({"first": "# 시간표 없음"}, "수업 시간표"),
        ({"first": "## 수업 시간표\n\n표 없음"}, "표가 없습니다"),
        ({"first": TIMETABLE.replace("| 7 |", "| 약간 |")}, "읽을 수 없습니다"),
        ({"body": "## 확인 질문\n\n호출 규모\n\n## 정리\n"}, "## 직접 해보기"),
        ({"body": "## 직접 해보기\n\n호출 규모\n\n## 정리\n"}, "## 확인 질문"),
        ({"body": "## 직접 해보기\n\n## 확인 질문\n\n호출 규모\n"}, "## 정리"),
        ({"body": "## 직접 해보기\n\n## 확인 질문\n\n## 정리\n"}, "호출 규모"),
    ]
    for kwargs, expected in cases:
        result = run_check(write_notebook(tmp_path, **kwargs), "--minutes", "10")
        assert result.returncode == 1 and expected in result.stderr, (kwargs, result.stderr)


def test_removed_symbol_in_markdown_is_allowed(tmp_path):
    body = BODY + "\n이전 자료의 live_cell은 삭제되었다.\n"
    assert run_check(write_notebook(tmp_path, body=body), "--minutes", "10").returncode == 0


def test_rejects_stored_output(tmp_path):
    path = write_notebook(tmp_path)
    nb = nbformat.read(path, as_version=4)
    nb.cells[1].outputs = [nbformat.v4.new_output("stream", name="stdout", text="남은 출력")]
    nbformat.write(nb, path)
    result = run_check(path, "--minutes", "10")
    assert result.returncode == 1 and "저장된 출력" in result.stderr


def test_floors_default_for_sixty_minutes_and_flags_override(tmp_path):
    table = TIMETABLE.replace("| 7 |", "| 57 |")
    path = write_notebook(tmp_path, first=table)
    result = run_check(path, "--minutes", "60")
    assert result.returncode == 1
    assert "cells 하한 미달: 3 < 36" in result.stderr
    assert "code 하한 미달: 1 < 16" in result.stderr
    assert "markdown 하한 미달" in result.stderr
    assert run_check(write_notebook(tmp_path), "--minutes", "10", "--min-cells", "4").returncode == 1


def test_rejects_invalid_and_missing_files(tmp_path):
    broken = tmp_path / "broken.ipynb"
    broken.write_text("{ 이건 JSON이 아니다", encoding="utf-8")
    invalid = tmp_path / "invalid.ipynb"
    invalid.write_text('{"cells": "문자열", "metadata": {}, "nbformat": 4, "nbformat_minor": 5}', encoding="utf-8")
    for path, expected in [(broken, "nbformat 검증 실패"), (invalid, "nbformat 검증 실패"), (tmp_path / "없음.ipynb", "읽을 수 없습니다")]:
        result = run_check(path, "--minutes", "10")
        assert result.returncode == 1 and expected in result.stderr, result.stderr


def sixty_minute_notebook(tmp_path: Path, codes: list[str], filler: int = 0) -> Path:
    first = TIMETABLE.replace("| 7 |", "| 57 |") + "가" * filler
    nb = new_notebook(cells=[new_markdown_cell(first), *map(new_code_cell, codes), new_markdown_cell(BODY)])
    path = tmp_path / "sixty.ipynb"
    nbformat.write(nb, path)
    return path


def sixty(tmp_path: Path, codes: list[str], filler: int = 0) -> subprocess.CompletedProcess:
    return run_check(sixty_minute_notebook(tmp_path, codes, filler), "--minutes", "60",
                     "--min-cells", "0", "--min-code", "0", "--min-md", "0")


GOOD_CELLS = ["# [따라하기] 무료\nprint(1)", *["# [따라하기] 무료\nprint(1)"] * 5, *["# [바꿔보기] 무료\nprint(2)"] * 4,
              *["# [깨뜨리기] 무료\nprint(3)"] * 2, *["# [내 것 만들기] 무료\nprint(4)"] * 2]


def test_marker_rules_accept_good_notebook(tmp_path):
    result = sixty(tmp_path, GOOD_CELLS)
    assert len(GOOD_CELLS) == 14 and result.returncode == 0, result.stderr


def test_marker_rules_reject_each_violation(tmp_path):
    only_follow = ["# [따라하기] 무료"] * 12
    cases = [
        (GOOD_CELLS[:11], "표지 셀이 11개"),
        ([c for c in GOOD_CELLS if not c.startswith("# [바꿔보기]")] + ["# [바꿔보기] 무료"] * 3, "# [바꿔보기] 표지 셀이 3개입니다. 4개"),
        ([c for c in GOOD_CELLS if not c.startswith("# [깨뜨리기]")] + ["# [깨뜨리기] 무료"], "# [깨뜨리기] 표지 셀이 1개입니다. 2개"),
        ([c for c in GOOD_CELLS if not c.startswith("# [내 것 만들기]")] + ["# [내 것 만들기] 무료"] * 1 + ["print(5)"], "# [내 것 만들기] 표지 셀이 1개입니다. 2개"),
        ([c for c in GOOD_CELLS if not c.startswith("# [따라하기]")] + ["# [따라하기] 무료"] * 1, "# [따라하기] 표지 셀이 1개입니다. 2개"),
        (only_follow, "# [바꿔보기] 표지 셀이 없습니다"),
        ([c for c in GOOD_CELLS if not c.startswith("# [깨뜨리기]")] + ["print(5)"] * 2, "# [깨뜨리기] 표지 셀이 없습니다"),
        ([c for c in GOOD_CELLS if not c.startswith("# [내 것 만들기]")] + ["print(5)"] * 2, "# [내 것 만들기] 표지 셀이 없습니다"),
    ]
    for codes, expected in cases:
        result = sixty(tmp_path, codes)
        assert result.returncode == 1 and expected in result.stderr, (expected, result.stderr)
    only_marker_not_first_line = ["x = 1\n# [따라하기] 둘째 줄이라 세지 않는다"] * 12
    result = sixty(tmp_path, only_marker_not_first_line)
    assert result.returncode == 1 and "표지 셀이 0개" in result.stderr


def test_first_follow_along_cell_rejects_forbidden_names(tmp_path):
    for name in ["load_corpus", "ask(", "build_rag_agent", "retriever", "data/business"]:
        codes = [f"# [따라하기] 무료\nx = {name}", *GOOD_CELLS[1:]]
        result = sixty(tmp_path, codes)
        assert result.returncode == 1 and f"금지된 이름이 있습니다: {name}" in result.stderr, (name, result.stderr)


def test_forbidden_names_allowed_after_first_follow_along(tmp_path):
    codes = [*GOOD_CELLS, "# [따라하기] 유료\nask('q')\nload_corpus()"]
    assert sixty(tmp_path, codes).returncode == 0


def test_markdown_limit_is_ten_thousand_chars(tmp_path):
    base = len(TIMETABLE.replace("| 7 |", "| 57 |")) + len(BODY)
    assert sixty(tmp_path, GOOD_CELLS, filler=10000 - base).returncode == 0
    result = sixty(tmp_path, GOOD_CELLS, filler=10001 - base)
    assert result.returncode == 1 and "markdown이 너무 깁니다: 10001" in result.stderr


def test_marker_rules_skip_ten_minute_notebooks(tmp_path):
    assert run_check(write_notebook(tmp_path, code="print(1)"), "--minutes", "10").returncode == 0
