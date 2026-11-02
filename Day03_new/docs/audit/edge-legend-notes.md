# Edge legend notes (node edge-legend-note, run dag_mvxokk3e_pg8nz6)

P = <P>

## Confirmed before editing

`grep -rn -i -e 점선 -e dotted -e 실선 -e dashed` over `Day03_new` (`*.ipynb`, `*.md`, `*.py`, `rag_lab` excluded) found no match. No notebook told students what a dotted line means.

Fact behind the sentences: for a LangGraph graph, `draw_mermaid()` draws a conditional edge as `-.->` and a plain edge as `-->`. A 4-node test graph (START -> verify, verify conditional to interpret and END, interpret -> END) printed `verify -.-> __end__`, `verify -.-> interpret`, `__start__ --> verify`, `interpret --> __end__`. No model call. The hybrid render in P/graph-render.png showed 12 dotted and 7 solid edges, and `get_graph()` lists 12 conditional and 7 plain.

## The two sentences (exact text, as written into the notebooks)

01-Workflow-vs-Agent.ipynb, markdown cell id `ee66ca62` (file line 451), inserted after "등록되지 않은 고객이면 비용을 쓰기 전에 끝냅니다." and before "Day01에서 ...":

> 그려진 그림에서는 점선이 조건부 간선이고 실선이 고정 간선입니다.

04-Graph-Engineering.ipynb, markdown cell id `cbb1a6e8` (the cell right before the `show_graph(hybrid_shape)` code cell; the paragraph is file line 1216), appended at the end of the paragraph, after "아래 표는 각 노드를 1절의 층에 대응시킵니다.":

> 그림의 점선은 조건부 간선인데 어떤 조건에서 어느 갈래로 가는지는 그림에 적혀 있지 않으므로, 갈림 조건은 아래 셀이 출력하는 `build_hybrid` 소스에서 찾거나 그림 아래 간선 표의 `조건부` 열이 `True`인 행을 찾아 그 간선을 고르는 라우팅 함수에서 읽어야 합니다.

Placement choices:
- 01: the cell also holds the `**먼저 예측하세요.**` paragraph, which was not touched. The new sentence sits in the explanation paragraph before it and answers nothing it asks (time per node, effect of a missing role, model call count).
- 04: the cell has no `**먼저 예측하세요.**` and no `**관찰할 것.**` (the `**관찰할 것.**` cell `37e57846` comes after the run cells and was not touched). The sentence names no condition, so it does not answer the cell's own questions ("`after_join`은 어떤 조건에서 `retry`로 갈까요?").

## Diffs (pre-edit copy against edited file, `diff` output saved)

| notebook | diff file | diff lines | removed (`<`) | added (`>`) | cells changed |
|---|---|---:|---:|---:|---:|
| 01-Workflow-vs-Agent.ipynb | P/edge-legend/01.diff | 4 | 1 | 1 | 1 (markdown, index 20, +37 chars) |
| 04-Graph-Engineering.ipynb | P/edge-legend/04.diff | 4 | 1 | 1 | 1 (markdown, index 50, +158 chars) |

Attempt 2 correction (04 only): the first attempt wrote `이 셀이 출력하는`, but that markdown cell prints nothing; the code cell right after it (`aaa85b65`, `print(inspect.getsource(build_hybrid))`) prints the source. Changed that one phrase to `아래 셀이 출력하는` by raw text replace (one match asserted). The 04.diff above was regenerated against 04-pre.ipynb after the fix. 01 was not touched in attempt 2; its sentence is still at line 451.

Pre-edit copies: P/edge-legend/01-pre.ipynb, P/edge-legend/04-pre.ipynb. Edit script (raw text replace, one match asserted per file): P/edge-legend/apply.py.

A JSON comparison of pre and edited files showed the same `metadata`, the same cell count, the same ids, and every other cell equal. Every code cell has `outputs == []`.

## Checks

- `.venv/bin/python Day03_new/tests/check_notebook.py Day03_new/01-Workflow-vs-Agent.ipynb --minutes 60` printed `OK Day03_new/01-Workflow-vs-Agent.ipynb`, exit 0.
- `.venv/bin/python Day03_new/tests/check_notebook.py Day03_new/04-Graph-Engineering.ipynb --minutes 60` printed `OK Day03_new/04-Graph-Engineering.ipynb`, exit 0.
- `점선` count: 1 in each notebook.
- No model or EXA call was made. No other file was edited.

Edge legend: done
