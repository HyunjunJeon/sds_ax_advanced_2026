"""audit_report가 셀의 예고(announce)를 상한으로 지키는지 공개 함수로 확인한다. audit_report 시험은 파일을 읽지 않고,
main 시험은 tmp_path에 만든 기록만 읽는다."""
import json
from pathlib import Path

import nbformat
import pytest
from audit_live import audit_report, main

STEM = "99-Probe"


def report_with(index: int, model_calls: int, announced: bool) -> dict:
    cell = {"index": index, "model_calls": model_calls, "announced": announced, "has_output": True}
    return {"finished": True, "errors": [], "cells": [cell]}


def announce_source(*calls: int) -> str:
    return "\n".join(f'announce("조사 {n}", model_calls={n})' for n in calls)


def test_measured_below_announce_passes():
    problems = audit_report(report_with(4, model_calls=3, announced=True), {4: announce_source(5)}, STEM)
    assert problems == []


def test_measured_equal_to_announce_passes():
    problems = audit_report(report_with(4, model_calls=5, announced=True), {4: announce_source(5)}, STEM)
    assert problems == []


def test_cell_without_model_calls_passes_whatever_it_announced():
    problems = audit_report(report_with(4, model_calls=0, announced=True), {4: announce_source(5)}, STEM)
    assert problems == []


@pytest.mark.parametrize("announce, measured", [(8, 9), (160, 277)])
def test_measured_above_announce_fails_naming_cell_announce_and_measured(announce, measured):
    problems = audit_report(report_with(12, model_calls=measured, announced=True), {12: announce_source(announce)}, STEM)
    assert len(problems) == 1
    message = problems[0]
    assert message.startswith(f"{STEM}: 셀 12")
    assert f"예고 {announce}회" in message
    assert f"실측 {measured}회" in message


def test_measured_without_announce_fails_as_unannounced():
    problems = audit_report(report_with(4, model_calls=2, announced=False), {4: "print('모델을 부르지만 고지가 없습니다')"}, STEM)
    assert problems == [f"{STEM}: 셀 4가 고지 없이 모델을 2회 불렀습니다."]


def test_two_announces_in_one_cell_use_their_sum_as_the_bound():
    source = announce_source(3, 4)
    assert audit_report(report_with(4, model_calls=7, announced=True), {4: source}, STEM) == []
    problems = audit_report(report_with(4, model_calls=8, announced=True), {4: source}, STEM)
    assert len(problems) == 1
    assert "예고 7회" in problems[0]
    assert "실측 8회" in problems[0]


@pytest.mark.parametrize("source", ['announce("검색", exa_calls=3)', 'announce("조사", model_calls=len(topics))'])
def test_announced_cell_without_model_calls_number_fails_as_not_comparable(source):
    problems = audit_report(report_with(7, model_calls=2, announced=True), {7: source}, STEM)
    assert len(problems) == 1
    message = problems[0]
    assert message.startswith(f"{STEM}: 셀 7")
    assert "실측 2회" in message
    assert "model_calls 숫자가 없" in message


def test_cell_without_model_calls_passes_when_its_announce_has_no_model_calls_number():
    problems = audit_report(report_with(7, model_calls=0, announced=True), {7: 'announce("검색", exa_calls=3)'}, STEM)
    assert problems == []


def write_record(live: Path, cell_count: int) -> None:
    cells = [{"index": i, "model_calls": 2, "announced": True, "has_output": True} for i in range(cell_count)]
    record = {
        "notebook": f"{STEM}.ipynb", "finished": True, "errors": [], "cells": cells,
        "model_calls": 2 * cell_count, "input_tokens": 100, "output_tokens": 10, "total_seconds": 1.0,
    }
    (live / f"{STEM}.json").write_text(json.dumps(record), encoding="utf-8")


def test_main_fails_once_per_stem_when_executed_notebook_is_missing(tmp_path, capsys):
    write_record(tmp_path, cell_count=3)
    assert main([STEM], live=tmp_path) == 1
    captured = capsys.readouterr()
    failures = [line for line in captured.err.splitlines() if line.startswith("FAIL")]
    assert len(failures) == 1
    assert failures[0].startswith(f"FAIL {STEM}:")
    assert "실행본" in failures[0]
    assert "비교할 수 없" in failures[0]
    assert captured.out.splitlines()[-1] == "AUDIT FAIL 1건"


def test_main_passes_when_executed_notebook_is_present(tmp_path, capsys):
    write_record(tmp_path, cell_count=1)
    executed = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(announce_source(2))])
    nbformat.write(executed, tmp_path / f"{STEM}.executed.ipynb")
    assert main([STEM], live=tmp_path) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "AUDIT OK"
