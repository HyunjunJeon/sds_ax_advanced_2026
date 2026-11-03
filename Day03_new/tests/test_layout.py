"""과정 경계를 지키는지 파일로 확인한다."""
import re
from pathlib import Path

import nbformat
import pytest
from check_notebook import FLOORS, static_problems

DAY03_NEW = Path(__file__).resolve().parents[1]
DAY02_NEW = DAY03_NEW.parent / "Day02_new"


@pytest.mark.parametrize("name", ["corpus.py", "retrieval.py", "evidence.py", "pipeline.py"])
def test_rag_lab_copies_are_byte_identical(name):
    if not DAY02_NEW.exists():
        pytest.skip("Day02_new가 없는 배포본")
    assert (DAY03_NEW / "rag_lab" / name).read_bytes() == (DAY02_NEW / "rag_lab" / name).read_bytes()


def test_modules_stay_readable_in_class():
    sizes = {p.name: sum(bool(line.strip()) for line in p.read_text(encoding="utf-8").splitlines()) for p in (DAY03_NEW / "mas_lab").glob("*.py")}
    assert max(sizes.values()) <= 150, sizes


def test_only_evaluation_module_touches_the_answer_key():
    readers = [p.name for p in (DAY03_NEW / "mas_lab").glob("*.py") if "gold" in p.read_text(encoding="utf-8")]
    assert readers == ["evaluation.py"]
    assert not [p.name for p in (DAY03_NEW / "rag_lab").glob("*.py") if "gold.jsonl" in p.read_text(encoding="utf-8")]


def test_runtime_does_not_import_tests_or_old_assignments():
    for path in [*(DAY03_NEW / "mas_lab").glob("*.py"), *(DAY03_NEW / "rag_lab").glob("*.py")]:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"from (tests|fakes)|import fakes|student_tasks|merge_attempts|select_context|슬라이드|WORKSHEET", text), path.name


@pytest.mark.parametrize("folder", ["refund-case", "credit-case", "insufficient-evidence"])
def test_skills_have_valid_frontmatter(folder):
    text = (DAY03_NEW / "skills" / folder / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---")[1]
    assert f"name: {folder}" in front and "description:" in front


def make_notebook(*cells):
    nb = nbformat.v4.new_notebook()
    table = "# 제목\n\n## 수업 시간표\n\n| 절 | 분 |\n|---|---:|\n| 1 | 60 |\n\n## 호출 규모\n\n약간"
    tail = ["## 직접 해보기\n\n### 해보기 1\n### 해보기 2\n### 해보기 3\n### 해보기 4", "## 정리\n\n끝", "## 확인 질문\n\n1. 가\n2. 나\n3. 다\n4. 라\n5. 마"]
    nb.cells = [nbformat.v4.new_markdown_cell(table), *cells, *map(nbformat.v4.new_markdown_cell, tail)]
    return nb


def good_cells():
    code = [nbformat.v4.new_code_cell("# 실패 재현: 가\nprint(1)") for _ in range(3)] + [nbformat.v4.new_code_cell("print(1)") for _ in range(21)]
    text = "**관찰할 것.** 읽습니다. " * 6 + "**먼저 예측하세요.** 적으세요. " * 3 + "설명 " * 4000
    fill = [nbformat.v4.new_markdown_cell("연결") for _ in range(17)]
    return [*code, nbformat.v4.new_markdown_cell(text), *fill]


def test_good_notebook_passes():
    assert static_problems(make_notebook(*good_cells()), 60, FLOORS[60]) == []


def test_stategraph_is_allowed_here():
    cell = nbformat.v4.new_code_cell("from langgraph.graph import StateGraph\nprint(StateGraph)")
    assert static_problems(make_notebook(*good_cells(), cell), 60, FLOORS[60]) == []


@pytest.mark.parametrize(("source", "expect"), [
    ("from fakes import ScriptedChatModel", "쓰지 않기로"), ("import langgraph_supervisor", "쓰지 않기로"), ("x = 'gold'\nopen('data/gold.jsonl')", "gold"),
    ("# 슬라이드 12", "금지 단어"), ("merge_attempts({}, [])", "쓰지 않기로")])
def test_banned_content_fails(source, expect):
    problems = static_problems(make_notebook(*good_cells(), nbformat.v4.new_code_cell(source)), 60, FLOORS[60])
    assert any(expect in p for p in problems), problems


def test_stored_output_fails():
    cell = nbformat.v4.new_code_cell("print(1)")
    cell.outputs = [nbformat.v4.new_output("stream", text="1")]
    assert any("저장된 출력" in p for p in static_problems(make_notebook(*good_cells(), cell), 60, FLOORS[60]))


def test_paid_cell_without_observation_fails():
    cells = [*good_cells(), nbformat.v4.new_code_cell("announce('x', model_calls=1)")]
    assert any("관찰 문단이 없습니다" in p for p in static_problems(make_notebook(*cells), 60, FLOORS[60]))


def test_floors_fail_when_short():
    problems = static_problems(make_notebook(), 60, FLOORS[60])
    assert any("cells 하한" in p for p in problems) and any("markdown 하한" in p for p in problems)


def test_timetable_sum_fails():
    nb = make_notebook(*good_cells())
    nb.cells[0].source = nb.cells[0].source.replace("| 1 | 60 |", "| 1 | 50 |")
    assert any("분 합계" in p for p in static_problems(nb, 60, FLOORS[60]))


def make_half_notebook(*cells, minutes=30):
    """30분 노트북(분할한 03a, 03b 같은 것)의 뼈대. 시간표 합계만 minutes로 바꾼다."""
    nb = make_notebook(*cells)
    nb.cells[0].source = nb.cells[0].source.replace("| 1 | 60 |", f"| 1 | {minutes} |")
    return nb


def good_half_cells():
    code = [nbformat.v4.new_code_cell("# 실패 재현: 가\nprint(1)")] + [nbformat.v4.new_code_cell("print(1)") for _ in range(11)]
    text = "**관찰할 것.** 읽습니다. " * 3 + "**먼저 예측하세요.** 적으세요. " * 2 + "설명 " * 2000
    return [*code, nbformat.v4.new_markdown_cell(text), *[nbformat.v4.new_markdown_cell("연결") for _ in range(8)]]


def test_good_half_notebook_passes_the_30_minute_floor():
    assert static_problems(make_half_notebook(*good_half_cells()), 30, FLOORS[30]) == []


def test_30_minute_floors_fail_when_short():
    problems = static_problems(make_half_notebook(), 30, FLOORS[30])
    assert any("cells 하한" in p for p in problems) and any("markdown 하한" in p for p in problems)


def test_30_minute_timetable_sum_fails():
    problems = static_problems(make_half_notebook(*good_half_cells(), minutes=60), 30, FLOORS[30])
    assert any("분 합계" in p for p in problems)


def test_half_notebook_does_not_pass_the_60_minute_floor():
    """30분 기준을 더해도 60분 기준은 약해지지 않았다: 절반짜리가 60분 검사를 통과하면 안 된다."""
    problems = static_problems(make_half_notebook(*good_half_cells(), minutes=60), 60, FLOORS[60])
    assert any("cells 하한" in p for p in problems) and any("code 하한" in p for p in problems)
