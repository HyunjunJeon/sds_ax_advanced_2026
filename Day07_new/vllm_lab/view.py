"""표와 그림을 그리는 도구. 그림 글자는 ASCII만 쓴다(글꼴에 한글이 없어도 깨지지 않게).

한국어 설명은 그림 앞뒤 markdown에 쓴다. 시간 값은 teaching model의 toy 값이다.
"""
from __future__ import annotations

import json
import pathlib
from typing import Sequence

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, Rectangle

from vllm_lab import ROOT, VLLM_COMMIT

pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_columns", 40)
pd.set_option("display.width", 200)

TRACE_KEYS = ("step", "actor", "kind", "request_id", "detail")
BLOCK_COLORS = {"null": "#bdbdbd", "free": "#ffffff", "cached": "#9ecae1", "used": "#fdae6b", "shared": "#a1d99b"}
SPAN_COLORS = {"prefill": "#6baed6", "decode": "#fd8d3c", "preempted": "#de2d26",
               "wait": "#d9d9d9", "order": "#74c476", "other": "#bcbddc"}


def _ascii(**texts: str | None) -> None:
    for name, text in texts.items():
        if text is not None and not text.isascii():
            raise ValueError(f"그림 글자는 ASCII만 쓸 수 있습니다. {name}={text!r}")


def table(rows: list[dict] | pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """행을 빠뜨리지 않고 DataFrame으로 돌려준다. display를 호출하지 않는다."""
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
    if columns is not None:
        missing = [name for name in columns if name not in frame.columns and len(frame) > 0]
        if missing:
            raise ValueError(f"없는 열이 있습니다: {missing}. 있는 열: {list(frame.columns)}")
        frame = frame.reindex(columns=columns)
    for name in frame.columns[frame.isna().any()]:
        frame[name] = frame[name].astype(object).where(frame[name].notna(), "-")
    return frame


def trace_table(events: list[dict]) -> pd.DataFrame:
    """열 step, actor, kind, request_id, detail. detail은 json.dumps(ensure_ascii=False) 문자열."""
    out = []
    for index, event in enumerate(events):
        if set(event) != set(TRACE_KEYS):
            raise ValueError(f"event {index}의 키가 {sorted(event)}입니다. {sorted(TRACE_KEYS)}여야 합니다.")
        out.append({**{key: event[key] for key in TRACE_KEYS[:-1]},
                    "detail": json.dumps(event["detail"], ensure_ascii=False)})
    return table(out, list(TRACE_KEYS))


def permalink(path: str, line: int) -> str:
    """https://github.com/vllm-project/vllm/blob/<VLLM_COMMIT>/<path>#L<line>."""
    if path.startswith("/"):
        raise ValueError(f"절대 경로는 쓸 수 없습니다: {path}")
    if line < 1:
        raise ValueError(f"줄 번호는 1 이상이어야 합니다: {line}")
    return f"https://github.com/vllm-project/vllm/blob/{VLLM_COMMIT}/{path}#L{line}"


def cite(path: str, line: int, label: str | None = None) -> str:
    """markdown 링크 문자열 '[label](permalink)'."""
    return f"[{label or f'{path}:{line}'}]({permalink(path, line)})"


def _finish(fig: Figure) -> Figure:
    plt.close(fig)
    return fig


def block_grid(cells: list[dict], *, ncols: int = 8, title: str | None = None,
               mark: dict[int, str] | None = None) -> Figure:
    """cells[i]: {"block_id", "state", "label"}. state는 null, free, cached, used, shared."""
    mark = mark or {}
    _ascii(title=title, **{f"mark[{k}]": v for k, v in mark.items()},
           **{f"label[{i}]": c["label"] for i, c in enumerate(cells)})
    for cell in cells:
        if cell["state"] not in BLOCK_COLORS:
            raise ValueError(f"알 수 없는 state {cell['state']!r}. {sorted(BLOCK_COLORS)} 중 하나여야 합니다.")
    nrows = max(1, -(-len(cells) // ncols))
    fig, ax = plt.subplots(figsize=(1.1 * ncols, 1.0 * nrows + 0.8))
    for i, cell in enumerate(cells):
        row, col = divmod(i, ncols)
        ax.add_patch(Rectangle((col, -row), 0.95, 0.9, facecolor=BLOCK_COLORS[cell["state"]], edgecolor="black"))
        text = f"#{cell['block_id']}\n{cell['label']}"
        extra = mark.get(cell["block_id"])
        ax.text(col + 0.475, -row + 0.45, text + (f"\n{extra}" if extra else ""), ha="center", va="center", fontsize=7)
    ax.set_xlim(-0.1, ncols)
    ax.set_ylim(-nrows + 0.8, 1.0)
    ax.axis("off")
    ax.legend(handles=[Rectangle((0, 0), 1, 1, facecolor=c, edgecolor="black") for c in BLOCK_COLORS.values()],
              labels=list(BLOCK_COLORS), loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=len(BLOCK_COLORS), fontsize=7)
    if title:
        ax.set_title(title)
    return _finish(fig)


def timeline(spans: list[dict], *, title: str | None = None, x_label: str = "toy ms",
             note: str = "teaching model, not measured") -> Figure:
    """spans[i]: {"lane", "start", "end", "label", "kind"}. lane은 처음 나온 순서로 위에서 아래로."""
    _ascii(title=title, x_label=x_label, note=note,
           **{f"span[{i}]": f"{s['lane']}{s['label']}" for i, s in enumerate(spans)})
    for span in spans:
        if span["kind"] not in SPAN_COLORS:
            raise ValueError(f"알 수 없는 kind {span['kind']!r}. {sorted(SPAN_COLORS)} 중 하나여야 합니다.")
    lanes = list(dict.fromkeys(s["lane"] for s in spans))
    fig, ax = plt.subplots(figsize=(8, 0.7 * len(lanes) + 1.6))
    for span in spans:
        y = lanes.index(span["lane"])
        ax.barh(y, span["end"] - span["start"], left=span["start"], color=SPAN_COLORS[span["kind"]], edgecolor="black")
        ax.text((span["start"] + span["end"]) / 2, y, span["label"], ha="center", va="center", fontsize=7)
    ax.set_yticks(range(len(lanes)), labels=lanes)
    ax.invert_yaxis()
    ax.set_xlabel(x_label)
    ax.legend(handles=[Rectangle((0, 0), 1, 1, facecolor=c) for c in SPAN_COLORS.values()],
              labels=list(SPAN_COLORS), fontsize=7, loc="upper right", ncol=len(SPAN_COLORS))
    fig.text(0.5, 0.01, note, ha="center", fontsize=8, style="italic")
    if title:
        ax.set_title(title)
    return _finish(fig)


def sweep_chart(rows: list[dict], x: str, ys: list[str], *, note: str, title: str | None = None) -> Figure:
    """x축 x, 선 ys. note가 비면 ValueError(측정이 아니라는 문구를 그림 안에 강제한다)."""
    if not note.strip():
        raise ValueError("note가 비었습니다. 측정이 아니라는 문구를 넣어야 합니다.")
    _ascii(x=x, note=note, title=title, **{f"ys[{i}]": y for i, y in enumerate(ys)})
    fig, ax = plt.subplots(figsize=(7, 4))
    for y in ys:
        ax.plot([r[x] for r in rows], [r[y] for r in rows], marker="o", label=y)
    ax.set_xlabel(x)
    ax.legend()
    fig.text(0.5, 0.01, note, ha="center", fontsize=8, style="italic")
    if title:
        ax.set_title(title)
    fig.subplots_adjust(bottom=0.2)
    return _finish(fig)


def bar_chart(values: dict[str, float], *, unit: str = "", note: str = "", title: str | None = None) -> Figure:
    """가로 막대. 키 순서 유지."""
    _ascii(unit=unit, note=note, title=title, **{f"key[{i}]": k for i, k in enumerate(values)})
    fig, ax = plt.subplots(figsize=(7, 0.5 * len(values) + 1.5))
    ax.barh(list(values), list(values.values()), color="#6baed6", edgecolor="black")
    ax.invert_yaxis()
    ax.set_xlabel(unit)
    if note:
        fig.text(0.5, 0.01, note, ha="center", fontsize=8, style="italic")
        fig.subplots_adjust(bottom=0.25)
    if title:
        ax.set_title(title)
    return _finish(fig)


# 가로 1단위를 그림 0.6인치 * 0.775(axes 비율)로 고정하므로 7pt 글자 한 자(약 0.06인치)는 약 0.13단위다.
_INCH_PER_UNIT = 0.6
_CHAR_UNITS = 0.13


def lane_diagram(lanes: dict[str, list[str]], arrows: Sequence[tuple[str, str, str]] = (),
                 *, title: str | None = None) -> Figure:
    """lane별 상자. arrows는 (출발 상자, 도착 상자, 글자). 없는 상자 이름이면 ValueError."""
    _ascii(title=title, **{f"lane[{n}]": f"{n} {' '.join(b)}" for n, b in lanes.items()})
    # 상자 반폭은 글자 수에 맞춘다(7pt 글자 하나를 _CHAR_UNITS로 잡는다). 열 간격은 가장 넓은 상자 기준이다.
    half = {box: max(0.95, _CHAR_UNITS * len(box) / 2 + 0.15) for boxes in lanes.values() for box in boxes}
    pitch = 2 * max(half.values(), default=0.95) + 0.3
    centers: dict[str, tuple[float, float]] = {}
    for row, boxes in enumerate(lanes.values()):
        for col, box in enumerate(boxes):
            centers[box] = (col * pitch + pitch / 2, -row * 1.6)
    for src, dst, text in arrows:
        _ascii(arrow=text)
        for name in (src, dst):
            if name not in centers:
                raise ValueError(f"없는 상자 이름입니다: {name!r}. 있는 상자: {sorted(centers)}")
    width = max((len(b) for b in lanes.values()), default=1)
    fig, ax = plt.subplots(figsize=(max(_INCH_PER_UNIT * (pitch * width + 3.5), 0.1 * len(title or "") + 0.5), 1.6 * len(lanes) + 1))
    label_box = {"facecolor": "white", "edgecolor": "none", "pad": 1.5}
    for row, (lane, boxes) in enumerate(lanes.items()):
        ax.text(-0.2, -row * 1.6, lane, ha="right", va="center", fontsize=9, weight="bold")
        for box in boxes:
            cx, cy = centers[box]
            ax.add_patch(Rectangle((cx - half[box], cy - 0.35), 2 * half[box], 0.7, facecolor="#deebf7",
                                   edgecolor="black"))
            ax.text(cx, cy, box, ha="center", va="center", fontsize=7)
    for src, dst, text in arrows:
        (x1, y1), (x2, y2) = centers[src], centers[dst]
        if y1 == y2 and x1 != x2:
            # 같은 lane: 상자 가장자리끼리 잇고 글자는 틈 위쪽에 둔다.
            sign = 1 if x2 > x1 else -1
            ax.add_patch(FancyArrowPatch((x1 + sign * half[src], y1), (x2 - sign * half[dst], y2), arrowstyle="->",
                                         mutation_scale=12, shrinkA=0, shrinkB=0))
            ax.text((x1 + x2) / 2, y1 + 0.45, text, ha="center", fontsize=7, color="#08519c", bbox=label_box)
            continue
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="->", mutation_scale=12, shrinkA=14, shrinkB=14))
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, text, ha="center", fontsize=7, color="#08519c",
                bbox=label_box if text else None, zorder=3)
    ax.set_xlim(-3, pitch * width + 0.5)
    ax.set_ylim(-1.6 * len(lanes) + 0.6, 0.9)
    ax.axis("off")
    if title:
        ax.set_title(title)
    return _finish(fig)


def read_env_value(name: str, env_path: pathlib.Path | None = None) -> str | None:
    """Day07_new/.env에서만 값을 돌려준다(os.environ은 읽지 않는다). 출력과 로그를 하지 않는다."""
    path = env_path or ROOT / ".env"
    if not path.is_file():
        return None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().removeprefix("export ").strip()
        key, sep, value = line.partition("=")
        if not sep or line.startswith("#") or key.strip() != name:
            continue
        value = value.strip().strip("'\"")
        return value or None
    return None


def env_status(name: str, env_path: pathlib.Path | None = None) -> str:
    """'설정됨' 또는 '미설정'. 값이 비었거나 파일이 없으면 미설정."""
    return "설정됨" if read_env_value(name, env_path) else "미설정"
