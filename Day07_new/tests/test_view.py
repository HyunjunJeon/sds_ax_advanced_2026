from __future__ import annotations

import json

import pandas as pd
import pytest
from matplotlib.figure import Figure

import vllm_lab
from vllm_lab import view

SHA = "5df63a7203cdb9328d824a27b682e77c7b9928be"


def test_constants():
    assert vllm_lab.VLLM_VERSION == "0.32.0" and vllm_lab.VLLM_COMMIT == SHA
    assert vllm_lab.DEFAULT_BLOCK_SIZE == 16
    assert vllm_lab.ROOT.name == "Day07_new" and vllm_lab.DATA_DIR == vllm_lab.ROOT / "data"


def test_pandas_options_set_on_import():
    assert pd.get_option("display.max_colwidth") is None and pd.get_option("display.max_rows") == 200
    assert pd.get_option("display.max_columns") == 40 and pd.get_option("display.width") == 200


def test_table_keeps_every_row_and_column_order():
    rows = [{"a": 1, "b": 2}, {"a": 3}, {"b": 4, "a": 5}]
    frame = view.table(rows)
    assert len(frame) == 3 and frame["a"].tolist() == [1, 3, 5]
    assert list(view.table(rows, ["b", "a"]).columns) == ["b", "a"]


def test_table_unknown_column_is_korean_error():
    with pytest.raises(ValueError, match="없는 열"):
        view.table([{"a": 1}], ["zz"])


def test_table_empty_rows_with_columns():
    assert list(view.table([], ["x", "y"]).columns) == ["x", "y"]


def test_table_dataframe_input_is_not_mutated():
    src = pd.DataFrame({"a": [1]})
    copy = view.table(src, ["a"])
    copy.loc[0, "a"] = 9
    assert src["a"].tolist() == [1]


def test_trace_table_serializes_detail_without_ascii_escape():
    events = [{"step": 1, "actor": "BlockPool", "kind": "alloc", "request_id": "doc", "detail": {"블록": [3, 4]}},
              {"step": 2, "actor": "KVManagerSim", "kind": "hit", "request_id": None, "detail": {}}]
    frame = view.trace_table(events)
    assert list(frame.columns) == ["step", "actor", "kind", "request_id", "detail"]
    assert frame.loc[0, "detail"] == json.dumps({"블록": [3, 4]}, ensure_ascii=False) == '{"블록": [3, 4]}'
    assert frame.loc[1, "detail"] == "{}"


def test_trace_table_rejects_wrong_keys_and_accepts_empty():
    with pytest.raises(ValueError, match="키"):
        view.trace_table([{"step": 1}])
    assert list(view.trace_table([]).columns) == ["step", "actor", "kind", "request_id", "detail"]


def test_permalink_and_cite():
    url = view.permalink("vllm/v1/core/sched/scheduler.py", 42)
    assert url == f"https://github.com/vllm-project/vllm/blob/{SHA}/vllm/v1/core/sched/scheduler.py#L42"
    assert view.cite("a/b.py", 7) == f"[a/b.py:7]({view.permalink('a/b.py', 7)})"
    assert view.cite("a/b.py", 7, "여기").startswith("[여기](")


@pytest.mark.parametrize("path,line", [("/abs/x.py", 3), ("x.py", 0), ("x.py", -1)])
def test_permalink_rejects_bad_input(path, line):
    with pytest.raises(ValueError):
        view.permalink(path, line)


CELLS = [{"block_id": i, "state": s, "label": f"b{i}"} for i, s in enumerate(["null", "free", "cached", "used", "shared"])]


def test_block_grid_returns_closed_figure():
    fig = view.block_grid(CELLS, ncols=3, title="pool", mark={1: "hit"})
    assert isinstance(fig, Figure)
    texts = {t.get_text() for t in fig.axes[0].texts}
    assert "#1\nb1\nhit" in texts and "#0\nb0" in texts
    import matplotlib.pyplot as plt
    assert plt.get_fignums() == []


def test_block_grid_rejects_unknown_state_and_non_ascii():
    with pytest.raises(ValueError, match="state"):
        view.block_grid([{"block_id": 0, "state": "weird", "label": "x"}])
    with pytest.raises(ValueError, match="ASCII"):
        view.block_grid([{"block_id": 0, "state": "free", "label": "블록"}])
    with pytest.raises(ValueError, match="ASCII"):
        view.block_grid(CELLS, title="제목")
    with pytest.raises(ValueError, match="ASCII"):
        view.block_grid(CELLS, mark={0: "적중"})


SPANS = [{"lane": "doc", "start": 0, "end": 3, "label": "p", "kind": "prefill"},
         {"lane": "faq", "start": 1, "end": 2, "label": "d", "kind": "decode"},
         {"lane": "doc", "start": 3, "end": 4, "label": "d", "kind": "decode"}]


def test_timeline_lanes_in_first_seen_order_and_note_shown():
    fig = view.timeline(SPANS, title="t")
    ax = fig.axes[0]
    assert [t.get_text() for t in ax.get_yticklabels()] == ["doc", "faq"]
    assert "teaching model, not measured" in [t.get_text() for t in fig.texts]


def test_timeline_rejects_non_ascii_and_bad_kind():
    with pytest.raises(ValueError, match="ASCII"):
        view.timeline(SPANS, note="측정 아님")
    with pytest.raises(ValueError, match="ASCII"):
        view.timeline([{**SPANS[0], "lane": "문서"}])
    with pytest.raises(ValueError, match="kind"):
        view.timeline([{**SPANS[0], "kind": "nap"}])


ROWS = [{"x": 1, "y": 2.0, "z": 1.0}, {"x": 2, "y": 3.0, "z": 0.5}]


def test_sweep_chart_draws_one_line_per_y_and_shows_note():
    fig = view.sweep_chart(ROWS, "x", ["y", "z"], note="toy values", title="s")
    assert len(fig.axes[0].lines) == 2 and "toy values" in [t.get_text() for t in fig.texts]


@pytest.mark.parametrize("note", ["", "   "])
def test_sweep_chart_requires_note(note):
    with pytest.raises(ValueError, match="note"):
        view.sweep_chart(ROWS, "x", ["y"], note=note)


def test_sweep_chart_rejects_non_ascii_note():
    with pytest.raises(ValueError, match="ASCII"):
        view.sweep_chart(ROWS, "x", ["y"], note="장난감")


def test_bar_chart_keeps_key_order_top_to_bottom():
    fig = view.bar_chart({"b": 1.0, "a": 2.0, "c": 3.0}, unit="blocks")
    assert [t.get_text() for t in fig.axes[0].get_yticklabels()] == ["b", "a", "c"]
    with pytest.raises(ValueError, match="ASCII"):
        view.bar_chart({"키": 1.0})


def test_lane_diagram_draws_boxes_and_checks_arrows():
    lanes = {"client": ["req"], "engine": ["sched", "model"]}
    fig = view.lane_diagram(lanes, [("req", "sched", "send"), ("sched", "model", "run")], title="flow")
    texts = {t.get_text() for t in fig.axes[0].texts}
    assert {"req", "sched", "model", "send", "run", "client", "engine"} <= texts
    with pytest.raises(ValueError, match="nope"):
        view.lane_diagram(lanes, [("req", "nope", "x")])
    with pytest.raises(ValueError, match="ASCII"):
        view.lane_diagram({"층": ["a"]})


def test_env_status_reads_only_the_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    monkeypatch.setenv("RUNPOD_BASE_URL", "http://from-environ")
    assert view.env_status("RUNPOD_BASE_URL", env) == "미설정"
    assert view.read_env_value("RUNPOD_BASE_URL", env) is None
    env.write_text("# RUNPOD_BASE_URL=commented\nOTHER=1\nRUNPOD_BASE_URL=\n")
    assert view.env_status("RUNPOD_BASE_URL", env) == "미설정"
    env.write_text("# c\nexport RUNPOD_BASE_URL='http://x/v1'\n")
    assert view.env_status("RUNPOD_BASE_URL", env) == "설정됨"
    assert view.read_env_value("RUNPOD_BASE_URL", env) == "http://x/v1"
    assert view.env_status("NOT_THERE", env) == "미설정"


def test_table_shows_missing_cells_as_dash_only_in_columns_that_have_them():
    frame = view.table([{"a": 1, "b": 2.5, "c": "x"}, {"a": 2, "c": None}, {"a": 3, "b": float("nan"), "c": "z"}])
    assert frame["b"].tolist() == [2.5, "-", "-"]
    assert frame["c"].tolist() == ["x", "-", "z"]
    assert frame["a"].tolist() == [1, 2, 3] and frame["a"].dtype.kind == "i"


def test_table_dash_applies_to_selected_columns_and_leaves_input_frame_alone():
    src = pd.DataFrame({"a": [1.0, None], "b": [1, 2]})
    frame = view.table(src, ["b", "a"])
    assert list(frame.columns) == ["b", "a"] and frame["a"].tolist() == [1.0, "-"]
    assert frame["b"].dtype.kind == "i"
    assert src["a"].isna().tolist() == [False, True] and list(src.columns) == ["a", "b"]


def test_lane_diagram_same_lane_arrow_runs_between_box_edges():
    fig = view.lane_diagram({"engine": ["sched", "model"]}, [("sched", "model", "run")])
    ax = fig.axes[0]
    arrow = next(p for p in ax.patches if p.__class__.__name__ == "FancyArrowPatch")
    xs = arrow.get_path().vertices[:, 0]
    start, end = (xs.min(), 0), (xs.max(), 0)  # 화살촉 끝이 가장 오른쪽
    boxes = {t.get_text(): t.get_position()[0] for t in ax.texts}
    assert start[0] == pytest.approx(boxes["sched"] + 0.95, abs=0.05)
    assert end[0] == pytest.approx(boxes["model"] - 0.95, abs=0.05)
    label = next(t for t in ax.texts if t.get_text() == "run")
    assert label.get_position()[1] > 0.35


def test_trace_table_shows_missing_request_id_as_dash():
    frame = view.trace_table([{"step": 1, "actor": "a", "kind": "k", "request_id": None, "detail": {}}])
    assert frame.loc[0, "request_id"] == "-"


def test_lane_diagram_box_fits_its_label_and_arrow_label_has_white_background():
    name = "BlockPool.free_blocks"
    fig = view.lane_diagram({"Pool": [name, "x"], "Mgr": ["KVCacheManager.free"]}, [(name, "KVCacheManager.free", "drop")])
    fig.canvas.draw()
    ax = fig.axes[0]
    box_text = next(t for t in ax.texts if t.get_text() == name)
    rect = next(p for p in ax.patches if p.__class__.__name__ == "Rectangle"
                and p.get_window_extent().x0 < box_text.get_window_extent().x0 + 1 < p.get_window_extent().x1)
    assert rect.get_window_extent().x0 <= box_text.get_window_extent().x0
    assert box_text.get_window_extent().x1 <= rect.get_window_extent().x1
    label = next(t for t in ax.texts if t.get_text() == "drop")
    assert label.get_bbox_patch().get_facecolor()[:3] == (1.0, 1.0, 1.0)
