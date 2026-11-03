"""check_notebook.py의 규칙마다 그 규칙이 잡아야 할 결함을 하나씩 넣어 구체적인 메시지로 잡히는지 본다."""
from __future__ import annotations

import check_notebook
import nbformat
import pytest
from check_notebook import (
    BREAK,
    CHANGE,
    FLOORS,
    FOLLOW,
    MARKER_FLOORS,
    MINE,
    NOTEBOOKS,
    OBSERVE,
    PREDICT,
    check,
    main,
)
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook, new_output

M = 45
PAID_CELL = f"{FOLLOW} 유료 호출\nannounce('평가 한 번', model_calls=3)\nbatch_evaluate(records)"
BREAK_CELL = f"{BREAK} 일부러 실패\nraise RuntimeError('의도된 실패')"
OBSERVE_MD = f"{OBSERVE} 출력의 한 칸만 읽으세요."
PAID_PROBLEM = "셀 3는 유료 호출인데 announce(…, model_calls=정수)가 없습니다."


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
    cells += [new_markdown_cell(f"{OBSERVE_MD} 추가 {n}") for n in range(max(floor["observe"] - per[BREAK], 0))]
    cells += [new_markdown_cell("## 깨뜨리기 절\n\n일부러 실패시킵니다.")] if per[BREAK] else []
    for _ in range(per[BREAK]):
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


def write(tmp_path, cells: list, name: str = "nb.ipynb"):
    path = tmp_path / name
    nbformat.write(new_notebook(cells=cells), path)
    return path


def verdict(tmp_path, cells: list, minutes: int = M) -> list[str]:
    return check(write(tmp_path, cells), minutes)


def index_of(cells: list, text: str) -> int:
    return next(i for i, cell in enumerate(cells) if text in cell.source)


@pytest.mark.parametrize("minutes", sorted(FLOORS))
def test_minimal_notebook_passes_for_each_minutes(tmp_path, minutes):
    assert verdict(tmp_path, build_cells(minutes), minutes) == []


def test_registered_notebooks_and_floor_minutes():
    assert {key: value for key, value in NOTEBOOKS.items()} == {
        "nb00": ("00-Setup.ipynb", 10), "nb01": ("01-Why-Evaluate.ipynb", 40),
        "nb02": ("02-Offline-Golden-Dataset.ipynb", 60), "nb03a": ("03a-Online-Eval-Trace-Selection.ipynb", 45),
        "nb03b": ("03b-Trajectory-Eval.ipynb", 55), "nb04": ("04-Agent-Monitoring.ipynb", 45),
        "nb05": ("05-Continuous-Operation.ipynb", 45), "nb06": ("06-Lab-Self-Improving-Agent.ipynb", 90)}
    assert sorted(FLOORS) == [10, 40, 45, 55, 60, 90]


def test_unreadable_file_is_reported(tmp_path):
    [problem] = check(tmp_path / "missing.ipynb", M)
    assert problem.startswith("노트북을 읽을 수 없습니다:")


def test_invalid_json_is_reported(tmp_path):
    path = tmp_path / "bad.ipynb"
    path.write_text("not json")
    [problem] = check(path, M)
    assert problem.startswith("nbformat 검증 실패:")


def test_saved_output_is_reported_with_its_cell_index(tmp_path):
    cells = build_cells(M)
    cells[2].outputs = [new_output("stream", name="stdout", text="결과")]
    assert verdict(tmp_path, cells) == ["셀 2에 저장된 출력이 있습니다."]


def test_timetable_sum_must_match_minutes(tmp_path):
    cells = build_cells(M)
    cells[0].source = cells[0].source.replace("| 5 |", "| 9 |")
    assert verdict(tmp_path, cells) == ["'수업 시간표'의 분 합계가 49분입니다. 45분이어야 합니다."]


def test_timetable_title_is_required(tmp_path):
    cells = build_cells(M)
    cells[0].source = cells[0].source.replace("수업 시간표", "일정")
    assert verdict(tmp_path, cells) == ["첫 markdown 셀에 '수업 시간표'가 없습니다."]


def test_timetable_table_is_required(tmp_path):
    cells = build_cells(M)
    cells[0].source = "## 수업 시간표\n\n표 없음. 호출 규모"
    assert verdict(tmp_path, cells) == ["'수업 시간표' 아래에 표가 없습니다."]


@pytest.mark.parametrize("heading", ["## 직접 해보기", "## 확인 질문", "## 정리"])
def test_required_heading_is_reported(tmp_path, heading):
    cells = build_cells(M)
    index = index_of(cells, heading)
    cells[index].source = cells[index].source.replace(heading, "### 다른 제목", 1)
    assert f"markdown 제목이 없습니다: {heading}" in verdict(tmp_path, cells)


def test_call_scale_phrase_is_required(tmp_path):
    cells = build_cells(M)
    cells[0].source = cells[0].source.replace("호출 규모", "비용")
    assert verdict(tmp_path, cells) == ["markdown에 '호출 규모' 문구가 없습니다."]


def test_missing_observe_paragraph_before_exercise_heading(tmp_path):
    cells = build_cells(M)
    last_break = max(i for i, cell in enumerate(cells) if cell.source.startswith(BREAK))
    cells[last_break + 1].source = "관찰 문단 대신 다른 문장."
    problems = verdict(tmp_path, cells)
    assert f"셀 {last_break}의 유료 호출·깨뜨리기 뒤에 관찰 문단이 없습니다." in problems
    assert not any("하한 미달" in p for p in problems)


def test_observe_paragraph_must_come_before_the_next_heading(tmp_path):
    cells = build_cells(M)
    first_break = index_of(cells, BREAK)
    cells.insert(first_break + 1, new_markdown_cell("## 중간 제목\n\n관찰 문단이 없습니다."))
    assert verdict(tmp_path, cells) == [f"셀 {first_break}의 유료 호출·깨뜨리기 뒤에 관찰 문단이 없습니다."]


def test_paid_cell_without_observe_paragraph_is_reported(tmp_path):
    cells = build_cells(M)
    paid = index_of(cells, "batch_evaluate")
    cells.insert(paid + 1, new_markdown_cell("## 바로 다음 제목"))
    assert verdict(tmp_path, cells) == [f"셀 {paid}의 유료 호출·깨뜨리기 뒤에 관찰 문단이 없습니다."]


def test_observe_paragraph_after_the_exercise_heading_is_not_checked(tmp_path):
    cells = build_cells(M)
    cells.append(new_code_cell("announce('한 번', model_calls=1)\nrun_round(1)"))
    assert verdict(tmp_path, cells) == []


PAID_SOURCES = ["judge_semantics(x)", "evaluate_records_locally(x)", "batch_evaluate (x)", "run_agent_metrics(x)",
                "propose_candidates(x)", "run_round(x)", "holdout_check(x)", "make_live_session(x)", "run_live(x)",
                "setup(mode='live')", 'setup(mode = "live")', "model.invoke(x)", "await graph.ainvoke(x)",
                "judge.judge(x)"]


@pytest.mark.parametrize("call", PAID_SOURCES)
def test_paid_cell_without_announce_is_reported(tmp_path, call):
    cells = build_cells(M)
    cells.insert(3, new_code_cell(call))
    assert PAID_PROBLEM in verdict(tmp_path, cells)


@pytest.mark.parametrize("call", PAID_SOURCES)
def test_announce_first_with_integer_literal_passes_for_every_paid_call(tmp_path, call):
    cells = build_cells(M)
    cells.insert(3, new_code_cell(f"announce('규모', model_calls=12, jev_calls=2)\n{call}"))
    assert verdict(tmp_path, cells) == []


def test_mode_other_than_live_is_not_a_paid_call(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("setup(mode='fake')\nrun_live_name = 1"))
    assert verdict(tmp_path, cells) == []


def test_announce_needs_an_integer_literal(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("announce('규모', model_calls=n)\nrun_round(c)"))
    assert PAID_PROBLEM in verdict(tmp_path, cells)


def test_other_count_keywords_do_not_replace_model_calls(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("announce('규모', jev_calls=2)\nrun_round(c)"))
    assert PAID_PROBLEM in verdict(tmp_path, cells)


def test_announce_after_the_first_paid_call_is_reported(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("run_round(c)\nannounce('규모', model_calls=4)"))
    assert verdict(tmp_path, cells) == ["셀 3의 announce가 첫 유료 호출보다 뒤에 있습니다."]


@pytest.mark.parametrize("name", ["fakes", "FakeChatModel", "FakeDecider", "FakeLangfuse", "NotebookAgentModel",
                                  "GenericFakeChatModel"])
def test_banned_code_name_is_reported_in_code_only(tmp_path, name):
    cells = build_cells(M)
    cells.insert(3, new_code_cell(f"import {name}"))
    assert verdict(tmp_path, cells) == [f"셀 3에 쓰지 않기로 한 이름이 있습니다: {name}"]
    cells[3] = new_markdown_cell(f"{name}은 tests에만 있다.")
    assert verdict(tmp_path, cells) == []


@pytest.mark.parametrize("token", ["not-found", "resume-pending", "fx-not-found", "fx-resume-pending", "hv-a1",
                                   "hv-Z", "incident-hv-"])
def test_holdout_literal_in_code_is_reported_but_not_in_markdown(tmp_path, token):
    cells = build_cells(M)
    cells.insert(3, new_code_cell(f"case = '{token}'"))
    [problem] = verdict(tmp_path, cells)
    assert problem.startswith("셀 3에 쓰지 않기로 한 이름이 있습니다: ")
    cells[3] = new_markdown_cell(f"설명에 {token}을 적었다.")
    assert verdict(tmp_path, cells) == []


@pytest.mark.parametrize("text", ["not-found-error", "my-not-found", "hv-1", "arch-v2", "resume-pending-x"])
def test_holdout_words_inside_other_tokens_are_not_reported(tmp_path, text):
    cells = build_cells(M)
    cells.insert(3, new_code_cell(f"label = '{text}'"))
    assert verdict(tmp_path, cells) == []


@pytest.mark.parametrize("secret", ["sk-abcdefgh12345", "123e4567-e89b-12d3-a456-426614174000"])
def test_key_shaped_string_is_reported_in_any_cell(tmp_path, secret):
    cells = build_cells(M)
    cells[1].source += f"\n\n키는 {secret} 입니다."
    assert verdict(tmp_path, cells) == ["셀 1 소스에 키 형식 문자열이 있습니다."]


def test_short_sk_prefix_is_not_a_key(tmp_path):
    cells = build_cells(M)
    cells[1].source += "\n\nsk-short 는 키가 아닙니다."
    assert verdict(tmp_path, cells) == []


def test_slide_word_is_reported_in_markdown_and_code(tmp_path):
    cells = build_cells(M)
    cells[1].source += "\n\n슬라이드 참고."
    assert verdict(tmp_path, cells) == ["셀 1에 금지 단어가 있습니다: 슬라이드"]
    cells[1].source = cells[1].source.replace("슬라이드", "자료")
    cells.insert(3, new_code_cell("# 슬라이드\nvalue = 1"))
    assert verdict(tmp_path, cells) == ["셀 3에 금지 단어가 있습니다: 슬라이드"]


def test_grading_word_and_own_folder_path_are_allowed(tmp_path):
    cells = build_cells(M)
    cells[1].source += "\n\n트레이스를 채점합니다. 파일은 Day05_new/data/cases.jsonl 입니다."
    assert verdict(tmp_path, cells) == []


@pytest.mark.parametrize("path", ["Day03_new/", "Day04/", "Day05/", "Day02_new/"])
def test_other_day_folder_path_is_reported(tmp_path, path):
    cells = build_cells(M)
    cells[1].source += f"\n\n참고: {path}mas_lab/runner.py"
    assert verdict(tmp_path, cells) == [f"셀 1에 다른 Day 폴더 경로가 있습니다: {path}"]


def test_other_day_folder_path_is_reported_in_code_cells_too(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("open('../Day02/data/a.txt')"))
    assert verdict(tmp_path, cells) == ["셀 3에 다른 Day 폴더 경로가 있습니다: Day02/"]


def test_switch_cell_with_both_false_passes(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("RUN_EXERCISE = False\nRUN_OPTIONAL = False"))
    cells.insert(4, new_code_cell("if RUN_EXERCISE:\n    value = 1"))
    assert verdict(tmp_path, cells) == []


def test_switch_used_without_definition_is_reported(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("if RUN_EXERCISE:\n    value = 1"))
    assert verdict(tmp_path, cells) == ["RUN_EXERCISE·RUN_OPTIONAL을 쓰지만 정의하는 스위치 셀이 없습니다."]


@pytest.mark.parametrize("source, missing", [
    ("RUN_EXERCISE = False", "RUN_OPTIONAL"),
    ("RUN_OPTIONAL = False", "RUN_EXERCISE"),
    ("RUN_EXERCISE = True\nRUN_OPTIONAL = False", "RUN_EXERCISE"),
    ("RUN_EXERCISE = False\nRUN_OPTIONAL = 0", "RUN_OPTIONAL"),
])
def test_switch_cell_must_set_both_to_false(tmp_path, source, missing):
    cells = build_cells(M)
    cells.insert(3, new_code_cell(source))
    assert verdict(tmp_path, cells) == [f"셀 3의 스위치 셀에 {missing} = False가 없습니다."]


def test_code_floor_is_reported(tmp_path):
    cells = build_cells(M)
    cells.pop(index_of(cells, "x = 0"))
    assert f"code 하한 미달: {FLOORS[M]['code'] - 1} < {FLOORS[M]['code']}" in verdict(tmp_path, cells)


def test_markdown_floor_is_reported(tmp_path):
    cells = build_cells(M)
    cells[1].source = "## 앞 절"
    [problem] = [p for p in verdict(tmp_path, cells) if p.startswith("markdown 하한")]
    assert problem.endswith(f"< {FLOORS[M]['markdown']}")


def test_predict_and_observe_floors_are_reported(tmp_path):
    cells = build_cells(M)
    for cell in cells:
        cell.source = cell.source.replace(PREDICT, "예측").replace(OBSERVE, "관찰")
    problems = verdict(tmp_path, cells)
    assert f"predict 하한 미달: 0 < {FLOORS[M]['predict']}" in problems
    assert f"observe 하한 미달: 0 < {FLOORS[M]['observe']}" in problems


def test_exercise_and_question_floors_count_only_their_own_section(tmp_path):
    cells = build_cells(M)
    cells[index_of(cells, "## 직접 해보기")].source = "## 직접 해보기\n\n해보기 없음"
    cells[index_of(cells, "## 확인 질문")].source = "## 확인 질문\n\n- 항목\n"
    cells[1].source += "\n\n### 해보기 9\n\n1. 다른 곳의 항목\n"
    problems = verdict(tmp_path, cells)
    assert f"exercise 하한 미달: 0 < {FLOORS[M]['exercise']}" in problems
    assert f"questions 하한 미달: 0 < {FLOORS[M]['questions']}" in problems


def test_break_and_marker_floors_are_reported_per_marker(tmp_path):
    cells = build_cells(M)
    for cell in cells:
        if cell.source.startswith(BREAK):
            cell.source = cell.source.replace(BREAK, "# 일반")
    problems = verdict(tmp_path, cells)
    assert f"breaks 하한 미달: 0 < {FLOORS[M]['breaks']}" in problems
    assert f"{BREAK} 표지 셀 하한 미달: 0 < {MARKER_FLOORS[M][BREAK]}" in problems
    assert any(p.startswith("marked 하한 미달") for p in problems)
    assert not any(p.startswith(f"{CHANGE} 표지") for p in problems)


def test_marker_must_be_the_first_line_of_a_code_cell(tmp_path):
    cells = build_cells(M)
    first_change = index_of(cells, CHANGE)
    cells[first_change].source = "pass\n" + cells[first_change].source
    floor = MARKER_FLOORS[M][CHANGE]
    assert f"{CHANGE} 표지 셀 하한 미달: {floor - 1} < {floor}" in verdict(tmp_path, cells)


def test_cells_floor_is_reported(tmp_path):
    cells = build_cells(M)
    cells.pop(index_of(cells, "문단입니다."))
    assert f"cells 하한 미달: {len(cells)} < {FLOORS[M]['cells']}" in verdict(tmp_path, cells)


def test_cli_prints_pass_line_with_file_name_and_exits_zero(tmp_path, capsys):
    path = write(tmp_path, build_cells(10))
    assert main([str(path), "--minutes", "10"]) == 0
    assert capsys.readouterr().out == "구조 검사 통과: nb.ipynb\n"


def test_cli_prints_fail_lines_to_stderr_and_exits_one(tmp_path, capsys):
    cells = build_cells(10)
    cells[0].source = cells[0].source.replace("| 5 |", "| 6 |")
    path = write(tmp_path, cells)
    assert main([str(path), "--minutes", "10"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "FAIL nb.ipynb: '수업 시간표'의 분 합계가 12분입니다. 10분이어야 합니다.\n"


def test_cli_rejects_unknown_minutes(tmp_path):
    with pytest.raises(SystemExit) as stop:
        main([str(tmp_path / "nb.ipynb"), "--minutes", "30"])
    assert stop.value.code == 2


def test_cli_needs_minutes_or_all(tmp_path):
    with pytest.raises(SystemExit) as stop:
        main([str(tmp_path / "nb.ipynb")])
    assert stop.value.code == 2


def test_all_exits_one_and_names_every_missing_notebook(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(check_notebook, "DAY05_ROOT", tmp_path)
    assert main(["--all"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    for name, _ in NOTEBOOKS.values():
        assert f"FAIL {name}: 노트북을 읽을 수 없습니다:" in captured.err


def test_all_exits_zero_when_every_registered_notebook_passes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(check_notebook, "DAY05_ROOT", tmp_path)
    for name, minutes in NOTEBOOKS.values():
        write(tmp_path, build_cells(minutes), name)
    assert main(["--all"]) == 0
    assert capsys.readouterr().out.splitlines() == [f"구조 검사 통과: {name}" for name, _ in NOTEBOOKS.values()]


def deepeval_problem(index: int) -> str:
    return f"셀 {index}이 eval_lab보다 먼저 deepeval을 import합니다. eval_lab이 DeepEval 텔레메트리를 먼저 꺼야 합니다."


def test_deepeval_in_an_earlier_cell_than_eval_lab_is_reported(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("from deepeval.metrics import GEval"))
    cells.insert(4, new_code_cell("from eval_lab import settings"))
    assert verdict(tmp_path, cells) == [deepeval_problem(3)]


def test_deepeval_line_before_eval_lab_line_in_the_same_cell_is_reported(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("import deepeval\n    import eval_lab"))
    assert verdict(tmp_path, cells) == [deepeval_problem(3)]


def test_eval_lab_before_deepeval_passes(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("import eval_lab\nfrom deepeval.metrics import GEval"))
    cells.insert(4, new_code_cell("    import deepeval"))
    assert verdict(tmp_path, cells) == []


def test_deepeval_without_eval_lab_is_reported(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("x = 1\nimport deepeval"))
    assert verdict(tmp_path, cells) == [deepeval_problem(3)]


def test_notebook_without_deepeval_import_passes(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("from eval_lab import settings"))
    assert verdict(tmp_path, cells) == []


def test_deepeval_in_comment_or_markdown_does_not_count(tmp_path):
    cells = build_cells(M)
    cells.insert(3, new_code_cell("# import deepeval\nvalue = 1"))
    cells.insert(4, new_markdown_cell("import deepeval 은 eval_lab 뒤에 한다."))
    assert verdict(tmp_path, cells) == []
