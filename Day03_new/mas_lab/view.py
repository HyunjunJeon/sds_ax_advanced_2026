"""실행 결과를 읽는 표와 그림, 그리고 설계 기록."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from IPython.display import display

from rag_lab.settings import ROOT


def message_table(messages: list) -> list[dict]:
    """메시지를 한 줄씩 펼친다. 대화에서 무슨 일이 있었는지 읽는 기본 표다."""
    rows = []
    for index, message in enumerate(messages):
        calls = getattr(message, "tool_calls", None) or []
        text = message.text if hasattr(message, "text") else str(message.content)
        rows.append({"순번": index, "종류": type(message).__name__.removesuffix("Message"),
                     "도구": ", ".join(c["name"] for c in calls) or getattr(message, "name", "") or "",
                     "인자": ", ".join(json.dumps(c["args"], ensure_ascii=False)[:60] for c in calls),
                     "내용": str(text)[:70].replace("\n", " ")})
    return rows


def _edges(app, xray: bool) -> list:
    return app.get_graph(xray=xray).edges


def show_graph(app, *, xray: bool = False) -> None:
    """그림은 JupyterLab의 mermaid로, 표는 렌더러가 없어도 읽히게 함께 낸다. 외부 렌더링 서비스를 쓰지 않는다."""
    source = app.get_graph(xray=xray).draw_mermaid()
    display({"text/vnd.mermaid": source, "text/plain": "(그래프 그림은 JupyterLab에서 보입니다)"}, raw=True)
    show_table([{"출발": e.source, "도착": e.target, "조건부": e.conditional} for e in _edges(app, xray)])


def flows_of(app) -> dict:
    """조건부 간선과 순환을 센다. 분석이지 판결이 아니다. Send 병렬은 실행 trace로 확인한다."""
    edges = _edges(app, False)
    nodes = {e.source for e in edges} | {e.target for e in edges}
    follows = {n: [e.target for e in edges if e.source == n] for n in nodes}

    def reaches(start: str, goal: str, seen: set[str]) -> bool:
        return any(n == goal or (n not in seen and reaches(n, goal, seen | {n})) for n in follows[start])

    return {"노드": len(nodes - {"__start__", "__end__"}), "간선": len(edges),
            "조건부 간선": sum(e.conditional for e in edges), "순환": any(reaches(n, n, {n}) for n in nodes)}


def show_table(rows: list[dict], columns: list[str] | None = None) -> None:
    """행을 빠뜨리지 않고 표로 낸다."""
    with pd.option_context("display.max_colwidth", 80, "display.max_rows", 200, "display.max_columns", 40,
                           "display.width", 200):
        display(pd.DataFrame(rows, columns=columns))


def bars(values: dict[str, float], width: int = 32) -> str:
    """글꼴 문제가 없는 문자 막대."""
    top = max(values.values(), default=0) or 1
    label = max((len(k) for k in values), default=0)
    return "\n".join(f"{k:<{label}} {'#' * int(v / top * width):<{width}} {v:,.0f}" for k, v in values.items())


def read_design_log() -> dict:
    path = ROOT / "outputs" / "design_log.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_design_log(question: str, answer: str) -> Path:
    """각 노트북 끝의 설계 기록. 06이 모아 읽는다."""
    path = ROOT / "outputs" / "design_log.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**read_design_log(), question: answer}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
