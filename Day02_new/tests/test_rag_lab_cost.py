"""cost_report: 기록된 모델별 단가로 비용을 계산한다. 임시 폴더의 사용량 기록으로 확인한다."""
import json
from pathlib import Path

from cost_report import UNKNOWN, read_rows, render


def write_notebook(live: Path, stem: str, lines: list[dict], seconds: float = 10.0) -> None:
    (live / f"{stem}.usage.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    (live / f"{stem}.json").write_text(json.dumps({"total_seconds": seconds}), encoding="utf-8")


def million(model: str, cache: int = 0, write: int = 0) -> dict:
    return {"model": model, "input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_read_tokens": cache,
            "cache_write_tokens": write}


def test_sonnet_and_opus_get_different_correct_costs(tmp_path):
    write_notebook(tmp_path, "a", [million("claude-sonnet-5-5")])
    write_notebook(tmp_path, "b", [million("claude-opus-5-5")])
    costs = {row["notebook"]: row["cost"] for row in read_rows(tmp_path)}
    assert costs == {"a": 12.0, "b": 24.0}


def test_cache_read_tokens_are_billed_at_cache_price_not_input_price(tmp_path):
    write_notebook(tmp_path, "a", [million("claude-sonnet-5-5", cache=1_000_000)])
    assert read_rows(tmp_path)[0]["cost"] == 0.20 + 10.0


def test_unknown_model_prints_unconfirmed_price_and_partial_total(tmp_path):
    write_notebook(tmp_path, "a", [million("claude-sonnet-5-5")])
    write_notebook(tmp_path, "b", [million("claude-미지-9")])
    text = render(read_rows(tmp_path))
    unknown_row = next(line for line in text.splitlines() if "claude-미지-9" in line)
    assert unknown_row.endswith(f"| {UNKNOWN} |")
    total_row = next(line for line in text.splitlines() if "합계" in line and line.startswith("| **"))
    assert "12.0000" in total_row and "부분 합계" in total_row


def test_mixed_models_in_one_notebook_sum_per_model(tmp_path):
    write_notebook(tmp_path, "mix", [million("claude-sonnet-5-5"), million("claude-opus-5-5"),
                                     million("claude-sonnet-5-5")], seconds=7.5)
    rows = read_rows(tmp_path)
    assert {row["model"]: (row["calls"], row["cost"]) for row in rows} == {
        "claude-sonnet-5-5": (2, 24.0), "claude-opus-5-5": (1, 24.0)}
    text = render(rows)
    assert "| **합계** | | 3 | 7.5 |" in text and "**48.0000**" in text and "부분 합계" not in text


def test_cache_write_priced_separately_per_model(tmp_path):
    write_notebook(tmp_path, "a", [million("claude-sonnet-5-5", write=1_000_000)])
    write_notebook(tmp_path, "b", [million("claude-opus-5-5", write=1_000_000)])
    costs = {row["notebook"]: row["cost"] for row in read_rows(tmp_path)}
    assert costs == {"a": 2.50 + 10.0, "b": 5.0 + 20.0}


def test_input_cost_excludes_both_cache_reads_and_writes(tmp_path):
    write_notebook(tmp_path, "a", [million("claude-sonnet-5-5", cache=400_000, write=100_000)])
    # 입력 500k*$2 + 읽기 400k*$0.20 + 쓰기 100k*$2.50 + 출력 $10
    assert read_rows(tmp_path)[0]["cost"] == 1.0 + 0.08 + 0.25 + 10.0


def test_haiku_with_cache_write_is_unconfirmed_but_without_is_priced(tmp_path):
    write_notebook(tmp_path, "a", [million("claude-haiku-5-5", write=10)])
    write_notebook(tmp_path, "b", [million("claude-haiku-5-5")])
    rows = {row["notebook"]: row for row in read_rows(tmp_path)}
    assert rows["a"]["cost"] is None and rows["b"]["cost"] == 0.6
    assert next(l for l in render(list(rows.values())).splitlines() if l.startswith("| a |")).endswith(f"| {UNKNOWN} |")


def test_old_lines_without_cache_write_count_as_zero_with_understate_note(tmp_path):
    old = {"model": "claude-sonnet-5-5", "input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_read_tokens": 0}
    write_notebook(tmp_path, "a", [old])
    rows = read_rows(tmp_path)
    assert rows[0]["cost"] == 12.0 and rows[0]["legacy_lines"] == 1
    assert "실제보다 적게" in render(rows)
    write_notebook(tmp_path, "a", [million("claude-sonnet-5-5")])
    assert "실제보다 적게" not in render(read_rows(tmp_path))


def test_price_table_lists_cache_write_and_source(tmp_path):
    write_notebook(tmp_path, "a", [million("claude-haiku-5-5")])
    text = render(read_rows(tmp_path))
    assert "as of 2026-10" in text and "캐시 쓰기 $2.5" in text and "캐시 쓰기 $5" in text
    assert f"캐시 쓰기 {UNKNOWN}" in text and "cache_write" in text


def million_1h(model: str, one_hour: int, five_minutes: int = 0) -> dict:
    return {**million(model, write=one_hour + five_minutes), "cache_write_1h_tokens": one_hour}


def test_one_hour_writes_priced_at_four_and_eight_dollars(tmp_path):
    write_notebook(tmp_path, "a", [million_1h("claude-sonnet-5-5", 1_000_000)])
    write_notebook(tmp_path, "b", [million_1h("claude-opus-5-5", 1_000_000)])
    costs = {row["notebook"]: row["cost"] for row in read_rows(tmp_path)}
    assert costs == {"a": 4.0 + 10.0, "b": 8.0 + 20.0}


def test_five_minute_part_is_total_minus_one_hour_not_double_counted(tmp_path):
    write_notebook(tmp_path, "a", [million_1h("claude-sonnet-5-5", one_hour=200_000, five_minutes=300_000)])
    # 입력 500k*$2 + 5분 쓰기 300k*$2.50 + 1시간 쓰기 200k*$4 + 출력 $10
    assert read_rows(tmp_path)[0]["cost"] == 1.0 + 0.75 + 0.8 + 10.0


def test_haiku_with_one_hour_write_is_unconfirmed(tmp_path):
    write_notebook(tmp_path, "a", [million_1h("claude-haiku-5-5", 10)])
    assert read_rows(tmp_path)[0]["cost"] is None


def test_optional_run_gets_its_own_row_and_is_excluded_from_class_total(tmp_path):
    write_notebook(tmp_path, "03-Agent-Skills", [million("claude-sonnet-5-5")], seconds=5.0)
    write_notebook(tmp_path, "03-optional-copy", [million("claude-sonnet-5-5"), million("claude-sonnet-5-5")], seconds=9.0)
    lines = render(read_rows(tmp_path)).splitlines()
    total = next(l for l in lines if l.startswith("| **합계**"))
    optional = next(l for l in lines if l.startswith("| **선택 측정**"))
    assert "| 1 | 5.0 |" in total and "**12.0000**" in total
    assert "| 2 | 9.0 |" in optional and "**24.0000**" in optional and "제외" in optional


def test_no_optional_row_when_no_optional_run(tmp_path):
    write_notebook(tmp_path, "03-Agent-Skills", [million("claude-sonnet-5-5")])
    assert "선택 측정" not in render(read_rows(tmp_path))


def test_reported_cost_is_used_even_for_a_model_without_a_price(tmp_path):
    line = {"model": "typesafe/jev-1.13", "input_tokens": 100, "output_tokens": 5, "cost": 0.0123}
    write_notebook(tmp_path, "a", [line, line])
    row = read_rows(tmp_path)[0]
    assert row["cost"] == 0.0246 and row["unpriced"] == 0
    assert "unpriced" not in render([row])


def test_reported_cost_wins_over_the_price_table(tmp_path):
    write_notebook(tmp_path, "a", [{**million("claude-sonnet-5-5"), "cost": 1.5}])
    assert read_rows(tmp_path)[0]["cost"] == 1.5


def test_decision_model_without_cost_or_price_is_counted_as_unpriced_not_zero(tmp_path):
    line = {"model": "gpt-6-luna", "input_tokens": 162, "output_tokens": 0}
    write_notebook(tmp_path, "a", [line, line, {**line, "cost": 0.5}])
    write_notebook(tmp_path, "b", [million("claude-sonnet-5-5")])
    rows = read_rows(tmp_path)
    assert {row["notebook"]: (row["unpriced"], row["cost"]) for row in rows} == {"a": (2, None), "b": (0, 12.0)}
    text = render(rows)
    assert "unpriced: 비용도 단가도 없는 호출 2줄" in text and "부분 합계" in text
    assert next(l for l in text.splitlines() if l.startswith("| a |")).endswith(f"| {UNKNOWN} |")


def test_jev_is_priced_from_input_tokens_at_42_dollars_per_billion_with_free_output(tmp_path):
    line = {"model": "jev-1.14.0", "input_tokens": 1_000_000_000, "output_tokens": 5_000_000}
    write_notebook(tmp_path, "a", [line])
    rows = read_rows(tmp_path)
    assert rows[0]["cost"] == 42.0 and rows[0]["unpriced"] == 0
    text = render(rows)
    assert "$42" in text and "출력은 0" in text and "https://typesafe.ai/" in text


def test_jev_cost_follows_the_prefix_not_one_version(tmp_path):
    write_notebook(tmp_path, "a", [{"model": "jev-2.0.0", "input_tokens": 500_000_000, "output_tokens": 0}])
    assert read_rows(tmp_path)[0]["cost"] == 21.0


def test_cost_by_cell_uses_the_usage_line_ranges(tmp_path):
    from cost_report import cell_costs, render_cells

    jev = {"model": "jev-1.14.0", "input_tokens": 1_000_000_000, "output_tokens": 0}
    write_notebook(tmp_path, "nb", [million("claude-sonnet-5-5"), jev, jev, million("claude-sonnet-5-5")])
    (tmp_path / "nb.json").write_text(json.dumps({"cells": [
        {"index": 1, "usage_lines": [0, 1]}, {"index": 2, "usage_lines": [1, 3]},
        {"index": 4, "usage_lines": [3, 3]}, {"index": 5, "usage_lines": [3, 4]}]}), encoding="utf-8")
    cells = cell_costs(tmp_path, "nb")
    assert [(c["cell"], c["calls"], c["cost"]) for c in cells] == [(1, 1, 12.0), (2, 2, 84.0), (4, 0, 0), (5, 1, 12.0)]
    assert "| **합계** | 4 |" in render_cells("nb", cells) and "**108.0000**" in render_cells("nb", cells)


def test_cost_by_cell_refuses_a_report_without_line_ranges(tmp_path):
    from cost_report import cell_costs

    write_notebook(tmp_path, "old", [million("claude-sonnet-5-5")])
    (tmp_path / "old.json").write_text(json.dumps({"cells": [{"index": 1, "seconds": 1}]}), encoding="utf-8")
    try:
        cell_costs(tmp_path, "old")
    except ValueError as error:
        assert "usage_lines" in str(error)
    else:
        raise AssertionError("usage_lines 없는 보고서를 받아들였다")


def docs_for(tmp_path: Path, rows_text: str) -> tuple[list[dict], Path]:
    write_notebook(tmp_path, "a", [million("claude-sonnet-5-5")])
    write_notebook(tmp_path, "b", [{"model": "jev-1.14.0", "input_tokens": 1_000_000, "output_tokens": 0}])
    rows = read_rows(tmp_path)
    document = tmp_path / "README.md"
    document.write_text("# 문서\n\n" + rows_text + "\n\n뒤의 글\n", encoding="utf-8")
    return rows, document


def test_check_docs_passes_when_the_document_table_equals_the_records(tmp_path):
    from cost_report import check_docs

    rows, document = docs_for(tmp_path, "")
    document.write_text("# 문서\n\n" + render(rows).split("\n\n")[0] + "\n\n뒤의 글\n", encoding="utf-8")
    assert check_docs(rows, [document]) == []


def test_check_docs_names_the_row_with_a_changed_number(tmp_path):
    from cost_report import check_docs

    rows, document = docs_for(tmp_path, "")
    table = render(rows).split("\n\n")[0]
    document.write_text(table.replace("| a | claude-sonnet-5-5 | 1 |", "| a | claude-sonnet-5-5 | 2 |"), encoding="utf-8")
    mismatches = check_docs(rows, [document])
    assert len(mismatches) == 1 and "a / claude-sonnet-5-5" in mismatches[0]


def test_check_docs_fails_when_only_the_total_differs(tmp_path):
    from cost_report import check_docs

    rows, document = docs_for(tmp_path, "")
    table = render(rows).split("\n\n")[0]
    changed = table.replace("**12.0420", "**13.0420")
    assert changed != table
    document.write_text(changed, encoding="utf-8")
    mismatches = check_docs(rows, [document])
    assert len(mismatches) == 1 and "합계" in mismatches[0]


def test_check_docs_reports_missing_and_stale_rows(tmp_path):
    from cost_report import check_docs

    rows, document = docs_for(tmp_path, "")
    lines = render(rows).split("\n\n")[0].splitlines()
    kept = [line for line in lines if not line.startswith("| b |")] + ["| zzz | m | 1 |  | 1 | 1 | 1.0000 |"]
    document.write_text("\n".join(kept), encoding="utf-8")
    text = "\n".join(check_docs(rows, [document]))
    assert "'b / jev-1.14.0' 행이 없습니다" in text and "'zzz / m' 행은 기록에 없습니다" in text
