from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import nbformat
import pytest
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

import check_notebook as cn

SHA = "5df63a7203cdb9328d824a27b682e77c7b9928be"
TIMETABLE = "# 제목\n\n## 수업 시간표\n\n| 순서 | 내용 | 분 |\n|---|---|---|\n| 1 | 도입 | {a} |\n| 2 | 실습 | {b} |\n"


@pytest.fixture
def world(tmp_path: Path):
    source = tmp_path / "vllm_src"
    (source / "vllm" / "v1").mkdir(parents=True)
    (source / "vllm" / "v1" / "sched.py").write_text("\n".join(f"line {i}" for i in range(1, 11)) + "\n")
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    (ledger / "part1.md").write_text(
        "| ID | 주장 | 상태 |\n|---|---|---|\n| P1-01 | 확인된 주장 | 일치 |\n| P1-02 | 모르는 주장 | 미확인 |\n"
        "\n| ID | 내용 | 판정 |\n|---|---|---|\n| D-01 | 문서 차이 | 일치 |\n| D-02 | 모름 | 미확인 |\n", encoding="utf-8")
    return source, ledger


def make_nb(minutes=40, *, cells=30, code=12, observe=4, predict=2, exercises=2, questions=5,
            failures=1, md_chars=9200, a=None, extra_md=(), extra_code=(), headings=True):
    """기본값은 40분 노트북의 하한과 정확히 같다. 인자를 하나씩 낮추면 경계가 된다."""
    a = 10 if a is None else a
    first = TIMETABLE.format(a=a, b=minutes - 10)
    body = [new_markdown_cell(first)]
    body.append(new_markdown_cell("\n".join([cn.OBSERVE] * observe + [cn.PREDICT] * predict)))
    tail = []
    if headings:
        tail = [new_markdown_cell("## 직접 해보기\n" + "".join(f"### 해보기 {i + 1}\n" for i in range(exercises))),
                new_markdown_cell("## 확인 질문\n" + "".join(f"{i + 1}. 질문\n" for i in range(questions))),
                new_markdown_cell("## 정리\n끝"), new_markdown_cell("## 참고한 근거\n없음")]
    codes = [new_code_cell(f"# 실패 재현: {i}\nx = {i}" if i < failures else f"x = {i}") for i in range(code)]
    codes += [new_code_cell(src) for src in extra_code]
    md = body + tail + [new_markdown_cell(src) for src in extra_md]
    used = sum(len(c.source) for c in md)
    filler_count = max(0, cells - len(md) - len(codes))
    fillers = [new_markdown_cell("f") for _ in range(filler_count)]
    used += filler_count
    pad = max(0, md_chars - used)
    if filler_count:
        fillers[0].source = "f" * (pad + 1)
    else:
        body[1].source += "f" * pad
    return new_notebook(cells=md + fillers + codes)


def problems(nb, world, minutes=40):
    source, ledger = world
    return cn.static_problems(nb, minutes, source, ledger)


def has(found, text):
    return any(text in p for p in found)


def test_baseline_notebook_passes(world):
    assert problems(make_nb(), world) == []


@pytest.mark.parametrize("override,word", [
    ({"cells": 29}, "cells 하한"), ({"code": 11}, "code 하한"), ({"md_chars": 9199}, "markdown 하한"),
    ({"observe": 3}, "observe 하한"), ({"predict": 1}, "predict 하한"), ({"exercises": 1}, "exercise 하한"),
    ({"questions": 4}, "questions 하한"), ({"failures": 0}, "failure 하한")])
def test_floor_one_below_boundary_fails(world, override, word):
    assert has(problems(make_nb(**override), world), word)


def test_short_class_uses_relaxed_floors(world):
    nb = make_nb(10, cells=9, code=3, observe=1, predict=1, exercises=1, questions=2, failures=0, md_chars=2300)
    assert problems(nb, world, 10) == []
    assert has(problems(make_nb(10, cells=9, code=2, observe=1, predict=1, exercises=1, questions=2, failures=0,
                                md_chars=2300), world, 10), "code 하한")


def test_timetable_sum_must_equal_minutes(world):
    assert has(problems(make_nb(a=11), world), "분 합계가 41분")


def test_timetable_missing_fails(world):
    nb = make_nb()
    nb.cells[0].source = "# 제목만"
    assert has(problems(nb, world), "수업 시간표")


def test_unreadable_minute_cell_fails(world):
    nb = make_nb()
    nb.cells[0].source = nb.cells[0].source.replace("| 10 |", "| 약간 |")
    assert has(problems(nb, world), "읽을 수 없습니다")


@pytest.mark.parametrize("heading", cn.REQUIRED_HEADINGS)
def test_each_required_heading(world, heading):
    nb = make_nb()
    for cell in nb.cells:
        cell.source = cell.source.replace(heading, heading.replace("## ", "### "))
    assert has(problems(nb, world), f"제목이 없습니다: {heading}")


def link(sha=SHA, path="vllm/v1/sched.py", frag="L5"):
    return f"[a](https://github.com/vllm-project/vllm/blob/{sha}/{path}#{frag})"


def test_valid_permalink_passes(world):
    assert problems(make_nb(extra_md=[link(frag="L10"), link(frag="L2-L10")]), world) == []


@pytest.mark.parametrize("kwargs,word", [
    ({"sha": "main"}, "고정 커밋이 아닙니다"), ({"sha": SHA[:7]}, "고정 커밋이 아닙니다"),
    ({"path": "vllm/v1/none.py"}, "소스에 없습니다"), ({"frag": "L11"}, "줄 범위"),
    ({"frag": "L0"}, "줄 범위"), ({"frag": "L3-L11"}, "줄 범위"), ({"frag": "L6-L3"}, "줄 범위")])
def test_bad_permalink_fails(world, kwargs, word):
    assert has(problems(make_nb(extra_md=[link(**kwargs)]), world), word)


@pytest.mark.parametrize("text,word", [
    ("키 sk-abcdefgh12345678", "키 형식"), ("hf_" + "a" * 24, "키 형식"),
    ("https://abcd1234efgh-8000.proxy.runpod.net/v1", "Pod 호스트"),
    ("https://www.runpod.io/console/pods/abcd1234efgh", "Pod ID")])
def test_secret_like_text_fails_in_markdown_and_code(world, text, word):
    assert has(problems(make_nb(extra_md=[text]), world), word)
    assert has(problems(make_nb(extra_code=[f"x = '{text}'"]), world), word)


def test_placeholder_host_is_allowed(world):
    assert problems(make_nb(extra_md=["https://<pod-id>-8000.proxy.runpod.net/v1"]), world) == []


def test_ledger_ids_exist_and_known_ids_pass(world):
    assert problems(make_nb(extra_md=["P1-01 과 D-01 은 확인됨"]), world) == []
    for missing in ("P1-09", "D-09", "R-01"):
        assert has(problems(make_nb(extra_md=[f"{missing} 근거"]), world), f"{missing}가 대장에 없습니다")


def test_part7_and_part8_ids_are_read_from_the_ledger_and_checked(world):
    _, ledger = world
    (ledger / "part7.md").write_text(
        "| ID | 주장 | 상태 |\n|---|---|---|\n| P7-01 | 확인 | 일치 |\n| P7-47 | 재현 안 됨 | 미확인 |\n"
        "| P8-01 | 코드 | 자기 보고 |\n", encoding="utf-8")
    assert problems(make_nb(extra_md=["P7-01 과 P8-01 근거"]), world) == []
    assert has(problems(make_nb(extra_md=["P7-09 근거"]), world), "P7-09가 대장에 없습니다")
    assert has(problems(make_nb(extra_md=["P8-99 근거"]), world), "P8-99가 대장에 없습니다")
    assert has(problems(make_nb(extra_md=["P7-47 는 사실이다"]), world), "P7-47는 대장에서 미확인")


@pytest.mark.parametrize("outside", ["P0-01", "P9-01"])
def test_part_numbers_outside_one_to_eight_are_not_ledger_ids(world, outside):
    assert problems(make_nb(extra_md=[f"{outside} 는 ID가 아니다"]), world) == []


def test_unconfirmed_id_needs_the_word_in_same_cell(world):
    assert has(problems(make_nb(extra_md=["P1-02 는 사실이다"]), world), "P1-02는 대장에서 미확인")
    assert has(problems(make_nb(extra_md=["D-02 는 사실이다"]), world), "D-02는 대장에서 미확인")
    assert problems(make_nb(extra_md=["P1-02(미확인)"]), world) == []
    assert has(problems(make_nb(extra_md=["P1-02 사실", "다른 셀 미확인"]), world), "P1-02는")


GUARDED = "RUN_POD = False"
CALL = "if RUN_POD:\n    url = read_env_value('RUNPOD_BASE_URL')\n"


def test_run_pod_guarded_cell_passes(world):
    assert problems(make_nb(extra_code=[GUARDED, CALL]), world) == []


def test_run_pod_cell_without_switch_cell_fails(world):
    assert has(problems(make_nb(extra_code=[CALL]), world), "RUN_POD = False 셀 없이")


def test_server_url_outside_guard_fails(world):
    unguarded = "url = 'http://127.0.0.1:8000/v1'"
    assert has(problems(make_nb(extra_code=[GUARDED, unguarded]), world), "'if RUN_POD:' 안에 있지 않습니다")
    before_guard = "url = read_env_value('RUNPOD_BASE_URL')\nif RUN_POD:\n    print(url)\n"
    assert has(problems(make_nb(extra_code=[GUARDED, before_guard]), world), "'if RUN_POD:' 안에")


def test_run_pod_true_fails(world):
    assert has(problems(make_nb(extra_code=["RUN_POD = True"]), world), "False가 아닌 값")


@pytest.mark.parametrize("line", ["import vllm", "from vllm.v1 import x", "import torch", "from torch import nn",
                                  "    import torch.nn"])
def test_forbidden_imports_fail(world, line):
    assert has(problems(make_nb(extra_code=[line]), world), "import합니다")


def test_vllm_lab_import_is_allowed(world):
    assert problems(make_nb(extra_code=["from vllm_lab import view\nimport torchvision_like"]), world) == []


def test_saved_outputs_are_allowed(world):
    nb = make_nb()
    nb.cells[-1].outputs = [nbformat.v4.new_output("stream", name="stdout", text="ok")]
    assert problems(nb, world) == []


def test_command_line_ok_and_fail(world, tmp_path):
    source, ledger = world
    path = tmp_path / "ok.ipynb"
    nbformat.write(make_nb(), path)
    script = Path(cn.__file__)
    base = [sys.executable, str(script), str(path), "--source", str(source), "--ledger", str(ledger)]
    ok = subprocess.run([*base, "--minutes", "40"], capture_output=True, text=True)
    assert ok.returncode == 0 and ok.stdout.startswith("OK")
    bad = subprocess.run([*base, "--minutes", "41"], capture_output=True, text=True)
    assert bad.returncode == 1 and "FAIL" in bad.stderr


def test_unreadable_notebook_reports(world, tmp_path):
    source, ledger = world
    assert cn.check(tmp_path / "missing.ipynb", 40, source, ledger)[0].startswith("노트북을 읽을 수 없습니다")


def placeholder_problems(world, *sources):
    return [p for p in problems(make_nb(extra_md=sources), world) if "자리표시자" in p]


def test_unrendered_placeholder_names_cell_and_placeholder(world):
    nb = make_nb(extra_md=["본문 {paged_path} 입니다"])
    index = next(i for i, c in enumerate(nb.cells) if "{paged_path}" in c.source)
    found = [p for p in problems(nb, world) if "자리표시자" in p]
    assert len(found) == 1 and f"셀 {index}" in found[0] and "{paged_path}" in found[0]


def test_every_placeholder_in_a_cell_is_reported(world):
    found = placeholder_problems(world, "{paged_path} 와 {paged_warn}")
    assert any("{paged_path}" in p for p in found) and any("{paged_warn}" in p for p in found)


@pytest.mark.parametrize("text", [
    "코드 `{paged_path}` 는 그대로",
    "```python\nprint({paged_path})\n```",
    '요청 본문 {"method":"mtp","num_speculative_tokens":5} 입니다',
    "빈 중괄호 {} 와 { 공백 } 와 {1+2}",
])
def test_literal_braces_are_not_placeholders(world, text):
    assert placeholder_problems(world, text) == []


def test_placeholder_in_code_cell_is_not_checked(world):
    nb = make_nb(extra_code=["d = {name}"])
    assert not [p for p in problems(nb, world) if "자리표시자" in p]


VLLM_URL = f"https://github.com/vllm-project/vllm/blob/{SHA}/vllm/v1/sched.py"
LMCACHE_URL = "https://github.com/LMCache/LMCache/blob/3e11e10812b448142c6cdb177a3058652bd826fa/lmcache/a.py"


def rule_problems(world, rule, *sources):
    return [p for p in problems(make_nb(extra_md=sources), world) if rule in p]


def test_lone_tilde_pair_on_one_line_is_reported_with_cell_index(world):
    nb = make_nb(extra_md=["식 1~2, P7-09)는 대략 1.5~2배 줍니다"])
    index = next(i for i, c in enumerate(nb.cells) if "1.5~2배" in c.source)
    found = [p for p in problems(nb, world) if "LONE_TILDE" in p]
    assert len(found) == 1 and f"셀 {index}" in found[0]


@pytest.mark.parametrize("text", [
    "범위 1~2 하나뿐",
    "두 줄에 하나씩 1~2\n그리고 3~4",
    "취소선 ~~지움~~ 은 정상",
    "코드 `1~2` 와 `3~4` 는 그대로",
    "```\na~b c~d\n```",
    "공백이 붙은 ~ 와 ~ 는 취소선이 아님",
])
def test_lone_tilde_ignores_single_tilde_strikethrough_and_code(world, text):
    assert rule_problems(world, "LONE_TILDE", text) == []


@pytest.mark.parametrize("particle", list("은는이가을를과와"))
def test_link_followed_by_particle_is_reported(world, particle):
    found = rule_problems(world, "LINK_SUBJECT", f"[`sched.py:3`]({VLLM_URL}#L3){particle} 한 block을 만듭니다")
    assert len(found) == 1 and "셀 " in found[0]


def test_lmcache_link_followed_by_particle_is_reported(world):
    assert len(rule_problems(world, "LINK_SUBJECT", f"[a.py:3]({LMCACHE_URL}#L3)가 저장합니다")) == 1


@pytest.mark.parametrize("text", [
    f"`hash_block_tokens`([`sched.py:3`]({VLLM_URL}#L3))가 만듭니다",
    f"[`sched.py:3`]({VLLM_URL}#L3) 줄을 봅니다",
    f"[`sched.py:3`]({VLLM_URL}#L3)가능성은 따로 봅니다",
    f"[문서](https://example.com/a)는 영향이 없습니다",
])
def test_link_with_symbol_or_without_particle_passes(world, text):
    assert rule_problems(world, "LINK_SUBJECT", text) == []


@pytest.mark.parametrize("label,anchor", [("sched.py:3", "L4"), ("`sched.py:3-5`", "L3-L6"), ("sched.py:3-5", "L3")])
def test_label_number_must_match_anchor(world, label, anchor):
    found = rule_problems(world, "LABEL_LINE", f"봅니다 [{label}]({VLLM_URL}#{anchor}) 참고")
    assert len(found) == 1 and "셀 " in found[0]


@pytest.mark.parametrize("label,anchor", [("sched.py:3", "L3"), ("`sched.py:3-5`", "L3-L5"), ("scheduler 코드", "L9")])
def test_matching_or_unnumbered_label_passes(world, label, anchor):
    assert rule_problems(world, "LABEL_LINE", f"봅니다 [{label}]({VLLM_URL}#{anchor}) 참고") == []


def test_recipe_line_reference_is_reported(world):
    assert len(rule_problems(world, "RECIPE_LINE", "레시피 22줄에 있습니다")) == 1
    assert rule_problems(world, "RECIPE_LINE", "레시피 명령과 `레시피 22`는 코드") == []
