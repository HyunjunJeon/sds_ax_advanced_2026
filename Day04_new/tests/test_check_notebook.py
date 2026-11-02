"""check_notebook.py의 규칙마다 그 규칙이 잡아야 할 결함을 하나씩 넣어 구체적인 메시지로 잡히는지 본다."""
from __future__ import annotations

import nbformat
import pytest
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from check_notebook import BREAK, CHANGE, FLOORS, FOLLOW, MARKER_FLOORS, MINE, NOTEBOOKS, OBSERVE, PREDICT, check, main

PAID_CELL = f"{FOLLOW} 유료 호출\nannounce('에이전트 한 번', model_calls=3)\nagent.invoke('질문')"
BREAK_CELL = f"{BREAK} 일부러 실패\nraise RuntimeError('의도된 실패')"
OBSERVE_MD = f"{OBSERVE} 출력의 한 칸만 읽으세요."


def timetable(minutes: int) -> str:
    return (f"# 제목\n\n## 수업 시간표\n\n| 구간 | 분 |\n|---|---|\n| 앞부분 | {minutes - 5} |\n| 뒷부분 | 5 |\n\n"
            "호출 규모는 셀마다 알립니다.\n")


def build_cells(minutes: int) -> list:
    """분에 맞는 하한을 모두 겨우 넘기는 노트북. 마지막 깨뜨리기 뒤 관찰 문단이 직접 해보기 바로 앞에 온다."""
    floor, per = FLOORS[minutes], dict(MARKER_FLOORS[minutes])
    per[FOLLOW] += max(floor["marked"] - sum(per.values()), 0)
    cells = [new_markdown_cell(timetable(minutes)), new_markdown_cell("## 앞 절\n\n설명입니다.")]
    cells += [new_code_cell(PAID_CELL), new_markdown_cell(OBSERVE_MD)]
    cells += [new_code_cell(f"{FOLLOW} 따라하기 {n}\nvalue = {n}") for n in range(per[FOLLOW] - 1)]
    cells += [new_code_cell(f"{CHANGE} 바꿔보기 {n}\nvalue = {n}") for n in range(per[CHANGE])]
    cells += [new_code_cell(f"{MINE} 내 것 {n}\nvalue = {n}") for n in range(per[MINE])]
    cells += [new_markdown_cell(f"{PREDICT} 어떻게 나올까요? {n}") for n in range(floor["predict"])]
    cells += [new_markdown_cell(f"{OBSERVE_MD} 추가 {n}") for n in range(max(floor["observe"] + 1 - 1 - per[BREAK], 0))]
    cells += [new_markdown_cell("## 깨뜨리기 절\n\n일부러 실패시킵니다.")] if per[BREAK] else []
    for n in range(per[BREAK]):
        cells += [new_code_cell(BREAK_CELL), new_markdown_cell(OBSERVE_MD)]
    exercises = "".join(f"### 해보기 {n}\n\n값 하나만 바꿉니다.\n\n" for n in range(1, floor["exercise"] + 1))
    questions = "".join(f"{n}. 질문 {n}\n" for n in range(1, floor["questions"] + 1))
    tail = [new_markdown_cell(f"## 직접 해보기\n\n{exercises}"), new_markdown_cell(f"## 확인 질문\n\n{questions}"),
            new_markdown_cell("## 정리\n\n끝.")]
    padding_code = max(floor["code"] - sum(c.cell_type == "code" for c in cells), 0)
    cells += [new_code_cell(f"x = {n}") for n in range(padding_code)]
    cells += [new_markdown_cell("문단입니다.") for _ in range(max(floor["cells"] - len(cells) - len(tail), 0))]
    cells += tail
    shortfall = floor["markdown"] + 100 - sum(len(c.source) for c in cells if c.cell_type == "markdown")
    cells[1].source += "\n\n" + "가" * max(shortfall, 0)
    return cells


def verdict(tmp_path, cells: list, minutes: int) -> list[str]:
    path = tmp_path / "nb.ipynb"
    nbformat.write(new_notebook(cells=cells), path)
    return check(path, minutes)


def index_of(cells: list, text: str) -> int:
    return next(i for i, cell in enumerate(cells) if text in cell.source)


@pytest.mark.parametrize("minutes", sorted(FLOORS))
def test_minimal_notebook_passes_for_each_minutes(tmp_path, minutes):
    assert verdict(tmp_path, build_cells(minutes), minutes) == []


def test_notebooks_table_names_all_eight_files():
    assert {key: value[1] for key, value in NOTEBOOKS.items()} == {
        "nb00": 10, "nb01": 50, "nb02": 50, "nb03": 50, "nb04": 50, "nb05": 50, "nb06": 60, "nb07": 70}
    assert NOTEBOOKS["nb07"][0] == "07-Lab-Improvement.ipynb"


def test_unreadable_file_is_reported(tmp_path):
    [problem] = check(tmp_path / "missing.ipynb", 50)
    assert problem.startswith("노트북을 읽을 수 없습니다:")


def test_invalid_json_is_reported(tmp_path):
    path = tmp_path / "bad.ipynb"
    path.write_text("not json")
    [problem] = check(path, 50)
    assert problem.startswith("nbformat 검증 실패:")


def test_saved_output_is_reported_with_its_cell_index(tmp_path):
    cells = build_cells(50)
    cells[2].outputs = [nbformat.v4.new_output("stream", name="stdout", text="결과")]
    assert verdict(tmp_path, cells, 50) == ["셀 2에 저장된 출력이 있습니다."]


def test_timetable_sum_must_match_minutes(tmp_path):
    cells = build_cells(50)
    cells[0].source = cells[0].source.replace("| 5 |", "| 9 |")
    assert verdict(tmp_path, cells, 50) == ["'수업 시간표'의 분 합계가 54분입니다. 50분이어야 합니다."]


def test_timetable_title_is_required(tmp_path):
    cells = build_cells(50)
    cells[0].source = cells[0].source.replace("수업 시간표", "일정")
    assert verdict(tmp_path, cells, 50) == ["첫 markdown 셀에 '수업 시간표'가 없습니다."]


def test_timetable_table_is_required(tmp_path):
    cells = build_cells(50)
    cells[0].source = "## 수업 시간표\n\n표 없음. 호출 규모"
    assert verdict(tmp_path, cells, 50) == ["'수업 시간표' 아래에 표가 없습니다."]


@pytest.mark.parametrize("heading", ["## 직접 해보기", "## 확인 질문", "## 정리"])
def test_required_heading_is_reported(tmp_path, heading):
    cells = build_cells(50)
    index = index_of(cells, heading)
    cells[index].source = cells[index].source.replace(heading, "### 다른 제목", 1)
    assert f"markdown 제목이 없습니다: {heading}" in verdict(tmp_path, cells, 50)


def test_call_scale_phrase_is_required(tmp_path):
    cells = build_cells(50)
    cells[0].source = cells[0].source.replace("호출 규모", "비용")
    assert verdict(tmp_path, cells, 50) == ["markdown에 '호출 규모' 문구가 없습니다."]


def test_missing_observe_paragraph_before_exercise_heading(tmp_path):
    cells = build_cells(50)
    last_break = max(i for i, cell in enumerate(cells) if cell.source.startswith(BREAK))
    cells[last_break + 1].source = "관찰 문단 대신 다른 문장."
    problems = verdict(tmp_path, cells, 50)
    assert f"셀 {last_break}의 유료 호출·깨뜨리기 뒤에 관찰 문단이 없습니다." in problems
    assert not any("하한 미달" in p for p in problems)


def test_observe_paragraph_must_come_before_the_next_heading(tmp_path):
    cells = build_cells(50)
    first_break = index_of(cells, BREAK)
    cells.insert(first_break + 1, new_markdown_cell("## 중간 제목\n\n관찰 문단이 없습니다."))
    assert verdict(tmp_path, cells, 50) == [f"셀 {first_break}의 유료 호출·깨뜨리기 뒤에 관찰 문단이 없습니다."]


def test_paid_cell_without_observe_paragraph_is_reported(tmp_path):
    cells = build_cells(50)
    paid = index_of(cells, "agent.invoke")
    cells.insert(paid + 1, new_markdown_cell("## 바로 다음 제목"))
    assert verdict(tmp_path, cells, 50) == [f"셀 {paid}의 유료 호출·깨뜨리기 뒤에 관찰 문단이 없습니다."]


def test_observe_paragraph_after_the_exercise_heading_is_not_checked(tmp_path):
    cells = build_cells(50)
    cells.append(new_code_cell("announce('한 번', model_calls=1)\nrun_case(1)"))
    assert verdict(tmp_path, cells, 50) == []


@pytest.mark.parametrize("call", ["agent = build_agent(x)", "run_case(c)", "run_experiment(c)", "run_small_compare(c)",
                                  "model.invoke(x)", "await graph.ainvoke(x)", "judge.judge(x)"])
def test_paid_cell_without_announce_is_reported(tmp_path, call):
    cells = build_cells(50)
    cells.insert(3, new_code_cell(call))
    problems = verdict(tmp_path, cells, 50)
    assert "셀 3는 유료 호출인데 announce(…, model_calls=정수)가 없습니다." in problems


def test_announce_needs_an_integer_literal(tmp_path):
    cells = build_cells(50)
    cells.insert(3, new_code_cell("announce('규모', model_calls=n)\nrun_case(c)"))
    assert "셀 3는 유료 호출인데 announce(…, model_calls=정수)가 없습니다." in verdict(tmp_path, cells, 50)


def test_announce_with_integer_literal_passes_the_paid_rule(tmp_path):
    cells = build_cells(50)
    cells.insert(3, new_code_cell("announce('규모', model_calls=12)\nrun_case(c)"))
    assert verdict(tmp_path, cells, 50) == []


@pytest.mark.parametrize("name", ["fakes", "FakeDecider", "FakeChatModel", "DAY04_ALLOW_FAKE_DECIDER",
                                  "DAY04_FAKE_DECIDER", "gate_labels"])
def test_banned_code_name_is_reported(tmp_path, name):
    cells = build_cells(50)
    cells.insert(3, new_code_cell(f"import {name}"))
    assert verdict(tmp_path, cells, 50) == [f"셀 3에 쓰지 않기로 한 이름이 있습니다: {name}"]


def test_gate_labels_is_reported_in_markdown_cells_too(tmp_path):
    cells = build_cells(50)
    cells.insert(3, new_markdown_cell("라벨 파일 gate_labels는 저자만 읽는다."))
    assert verdict(tmp_path, cells, 50) == ["셀 3에 쓰지 않기로 한 이름이 있습니다: gate_labels"]


@pytest.mark.parametrize("text", ["`cases.jsonl`을 읽지 않는다.", "FakeChatModel은 tests에만 있다."])
def test_other_banned_names_stay_code_only(tmp_path, text):
    cells = build_cells(50)
    cells.insert(3, new_markdown_cell(text))
    assert verdict(tmp_path, cells, 50) == []


def test_holdout_id_in_code_is_reported_but_not_in_markdown(tmp_path):
    cells = build_cells(50)
    cells.insert(3, new_code_cell("case = 'ho-01'"))
    assert verdict(tmp_path, cells, 50) == ["셀 3에 쓰지 않기로 한 이름이 있습니다: ho-01"]
    cells[3] = new_markdown_cell("설명에 ho-01을 적었다.")
    assert verdict(tmp_path, cells, 50) == []


def test_word_ho_inside_another_word_is_not_a_holdout_id(tmp_path):
    cells = build_cells(50)
    cells.insert(3, new_code_cell("path = 'echo-12'"))
    assert verdict(tmp_path, cells, 50) == []


@pytest.mark.parametrize("secret", ["sk-abcdefgh12345", "123e4567-e89b-12d3-a456-426614174000"])
def test_key_shaped_string_is_reported_in_any_cell(tmp_path, secret):
    cells = build_cells(50)
    cells[1].source += f"\n\n키는 {secret} 입니다."
    assert verdict(tmp_path, cells, 50) == ["셀 1 소스에 키 형식 문자열이 있습니다."]


def test_short_sk_prefix_is_not_a_key(tmp_path):
    cells = build_cells(50)
    cells[1].source += "\n\nsk-short 는 키가 아닙니다."
    assert verdict(tmp_path, cells, 50) == []


@pytest.mark.parametrize("word", ["슬라이드", "채점"])
def test_banned_word_is_reported_in_markdown(tmp_path, word):
    cells = build_cells(50)
    cells[1].source += f"\n\n{word} 참고."
    assert verdict(tmp_path, cells, 50) == [f"셀 1에 금지 단어가 있습니다: {word}"]


def test_other_day_folder_path_is_reported_but_day04_new_passes(tmp_path):
    cells = build_cells(50)
    cells[1].source += "\n\n파일은 Day04_new/data/cases.jsonl 입니다."
    assert verdict(tmp_path, cells, 50) == []
    cells[1].source += "\n\n참고: Day03_new/mas_lab/runner.py"
    assert verdict(tmp_path, cells, 50) == ["셀 1에 다른 Day 폴더 경로가 있습니다: Day03_new/"]
    cells[1].source = cells[1].source.replace("Day03_new/", "Day04/")
    assert verdict(tmp_path, cells, 50) == ["셀 1에 다른 Day 폴더 경로가 있습니다: Day04/"]


def test_other_day_folder_path_is_reported_in_code_cells_too(tmp_path):
    cells = build_cells(50)
    cells.insert(3, new_code_cell("open('../Day02/data/a.txt')"))
    assert verdict(tmp_path, cells, 50) == ["셀 3에 다른 Day 폴더 경로가 있습니다: Day02/"]


def test_code_floor_is_reported(tmp_path):
    cells = build_cells(50)
    cells.pop(index_of(cells, "x = 0"))
    problems = verdict(tmp_path, cells, 50)
    assert f"code 하한 미달: {FLOORS[50]['code'] - 1} < {FLOORS[50]['code']}" in problems


def test_markdown_floor_is_reported(tmp_path):
    cells = build_cells(50)
    cells[1].source = "## 앞 절"
    [problem] = [p for p in verdict(tmp_path, cells, 50) if p.startswith("markdown 하한")]
    assert problem.endswith(f"< {FLOORS[50]['markdown']}")


def test_predict_and_observe_floors_are_reported(tmp_path):
    cells = build_cells(50)
    for cell in cells:
        cell.source = cell.source.replace(PREDICT, "예측").replace(OBSERVE, "관찰")
    problems = verdict(tmp_path, cells, 50)
    assert f"predict 하한 미달: 0 < {FLOORS[50]['predict']}" in problems
    assert f"observe 하한 미달: 0 < {FLOORS[50]['observe']}" in problems


def test_exercise_and_question_floors_count_only_their_own_section(tmp_path):
    cells = build_cells(50)
    cells[index_of(cells, "## 직접 해보기")].source = "## 직접 해보기\n\n해보기 없음"
    cells[index_of(cells, "## 확인 질문")].source = "## 확인 질문\n\n- 항목\n"
    cells[1].source += "\n\n### 해보기 9\n\n1. 다른 곳의 항목\n"
    problems = verdict(tmp_path, cells, 50)
    assert f"exercise 하한 미달: 0 < {FLOORS[50]['exercise']}" in problems
    assert f"questions 하한 미달: 0 < {FLOORS[50]['questions']}" in problems


def test_break_and_marker_floors_are_reported_per_marker(tmp_path):
    cells = build_cells(50)
    for cell in cells:
        if cell.source.startswith(BREAK):
            cell.source = cell.source.replace(BREAK, "# 일반")
    problems = verdict(tmp_path, cells, 50)
    assert f"breaks 하한 미달: 0 < {FLOORS[50]['breaks']}" in problems
    assert f"{BREAK} 표지 셀 하한 미달: 0 < {MARKER_FLOORS[50][BREAK]}" in problems
    assert any(p.startswith("marked 하한 미달") for p in problems)
    assert not any(p.startswith(f"{CHANGE} 표지") for p in problems)


def test_marker_must_be_the_first_line_of_a_code_cell(tmp_path):
    cells = build_cells(50)
    first_change = index_of(cells, CHANGE)
    cells[first_change].source = "pass\n" + cells[first_change].source
    problems = verdict(tmp_path, cells, 50)
    assert f"{CHANGE} 표지 셀 하한 미달: {MARKER_FLOORS[50][CHANGE] - 1} < {MARKER_FLOORS[50][CHANGE]}" in problems


def test_cells_floor_is_reported(tmp_path):
    cells = build_cells(50)
    cells.pop(index_of(cells, "문단입니다."))
    assert f"cells 하한 미달: {len(cells)} < {FLOORS[50]['cells']}" in verdict(tmp_path, cells, 50)


def test_cli_prints_ok_and_exits_zero(tmp_path, capsys):
    path = tmp_path / "nb.ipynb"
    nbformat.write(new_notebook(cells=build_cells(10)), path)
    assert main([str(path), "--minutes", "10"]) == 0
    assert capsys.readouterr().out == f"OK {path}\n"


def test_cli_prints_fail_lines_to_stderr_and_exits_one(tmp_path, capsys):
    path = tmp_path / "nb.ipynb"
    cells = build_cells(10)
    cells[0].source = cells[0].source.replace("| 5 |", "| 6 |")
    nbformat.write(new_notebook(cells=cells), path)
    assert main([str(path), "--minutes", "10"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"FAIL {path}: '수업 시간표'의 분 합계가 12분입니다. 10분이어야 합니다.\n"


def test_cli_rejects_unknown_minutes(tmp_path):
    with pytest.raises(SystemExit) as stop:
        main([str(tmp_path / "nb.ipynb"), "--minutes", "30"])
    assert stop.value.code == 2
