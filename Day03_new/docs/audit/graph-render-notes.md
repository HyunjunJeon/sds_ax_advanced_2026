# Graph render notes (node graph-render, run dag_mvxjjtgg_181ytn)

P = <P>

## 1. Verdict

The real `build_hybrid` graph renders correctly the way the 04 notebook shows it. All 13 nodes and all 19 edges are drawn and readable. Nothing overlaps (text boxes) and no error text is drawn. No network is needed to draw it.

Deliverable: P/graph-render.png (read with the Read tool; cropped JupyterLab view of the cell, the diagram and the 19-row edge table, 2x scale).

## 2. What was rendered and how

Where the picture comes from: `Day03_new/04-Graph-Engineering.ipynb`, code cell index 51 (it also calls `inspect.getsource(build_hybrid)` and defines `NODE_LAYERS`):

    hybrid_shape = build_hybrid(make_desk(case, label="shape"), model)
    show_graph(hybrid_shape)

`show_graph` (`Day03_new/mas_lab/view.py:30-34`) displays a dict `{"text/vnd.mermaid": app.get_graph(xray=False).draw_mermaid(), "text/plain": "(그래프 그림은 JupyterLab에서 보입니다)"}` with `raw=True`, then `show_table` of every edge (출발, 도착, 조건부) as a pandas HTML table.

Steps (all scripts and intermediates are under P/graph-render/):
1. `make_graph.py` (run with `.venv/bin/python -B`, cwd P/graph-render): same case as the notebook (`complex-double-pay` from `Day03_new/data/cases.jsonl`), `make_desk(case, label="shape")`, `ParsedChatModel(steps=[])` from `Day03_new/tests/fakes.py` only to construct the graph, then the real `show_graph` with IPython display output captured (`InteractiveShell.instance()` + `capture_output`). Fake model `calls` after the run: 0. Captured two display outputs: mermaid bundle (`text/vnd.mermaid`, `text/plain`) and the edge table (`text/html`, `text/plain`).
2. Those two outputs were saved as the outputs of one code cell in a scratch notebook P/graph-render/hybrid_shape.ipynb (same two code lines as cell 51). No cell was executed in a kernel; the cell shows `[ ]:` in the picture.
3. `run_shot_offline.sh`: starts JupyterLab 4.6.5 (the repo root `.venv`, port 8918, 127.0.0.1, random token, all Jupyter config/data/runtime/workspace dirs under P/graph-render/jup) rooted at P/graph-render, opens `/lab/tree/hybrid_shape.ipynb` in headless Chrome 156.0.8078.80 (`--headless=new --force-device-scale-factor=2 --window-size=1400,1800 --virtual-time-budget=40000`), screenshots, then kills the server. The final PNG is the 2x screenshot P/graph-render/shot3_offline_2x_tall.png cropped to x 570-1800, y 0-3250.
4. Earlier shots kept as evidence: shot1.png (scale 1, 1600x2400, network not blocked), shot2_offline_2x.png (scale 2, network blocked), zoom_middle.png and zoom_bottom.png (crops of shot2 used to check edge ends).

Renderer: the mermaid extension in JupyterLab core (DESIGN section 12 says mermaid 11.16.1; I did not re-read the bundled version).

## 3. Network dependency

None for drawing. The offline shots (shot2, shot3 and the final PNG) ran Chrome with `--host-resolver-rules="MAP * ~NOTFOUND , EXCLUDE 127.0.0.1"`, so every name except 127.0.0.1 failed to resolve. Control: with the same flag, Chrome navigating to https://example.com logged `ERR_NAME_NOT_RESOLVED` (P/graph-render/blocktest.err), so the block is real. The diagram and table still drew in full. This matches the `show_graph` docstring ("외부 렌더링 서비스를 쓰지 않는다").

Not part of drawing: JupyterLab shows a "Would you like to get notified about official Jupyter news?" prompt in the corner (in shot1, shot2 and shot3, with or without network). It is a UI consent prompt, not an error, and it is cropped out of graph-render.png. A classroom with no internet sees the same drawing.

The picture needs a front end that renders `text/vnd.mermaid`. JupyterLab 4.6.5 does. Not tested: Notebook 7 (7.6.4 is installed), VS Code, other browsers, dark theme. Where the mermaid mimetype is not rendered, the reader sees the `text/plain` line "(그래프 그림은 JupyterLab에서 보입니다)" and the edge table, which is the designed fallback.

## 4. Nodes and edges: `get_graph()` next to what the picture shows

Source: `.venv/bin/python` output saved in P/graph-render/nodes_edges.json and graph.mmd. The topology is static in `Day03_new/mas_lab/hybrid.py:160-177`; the model object is only used inside node bodies, so the fake model builds the same graph as the notebook's real model.

Nodes (13 in `get_graph().nodes`) vs picture: `__start__` (rounded, outlined), scope, router, fast, worker, retry, join, writer, validate, gate, approve, execute, `__end__` (rounded, filled purple). 13 of 13 drawn, each label fully inside its box.

Edges (19 in `get_graph().edges`; table rows 0-18 in the picture match them one to one, order included). Dotted line = conditional (12), solid = plain (7):

| # | edge | conditional in get_graph | style seen in picture |
|---|---|---|---|
| 0 | `__start__` -> scope | no | solid, arrow at scope |
| 1 | approve -> execute | no | solid |
| 2 | fast -> validate | no | solid |
| 3 | gate -> `__end__` | yes | dotted, left of the gate column, arrow at `__end__` |
| 4 | gate -> approve | yes | dotted, straight down |
| 5 | gate -> execute | yes | dotted, right side, arrow at execute |
| 6 | join -> retry | yes | dotted, short |
| 7 | join -> writer | yes | dotted, diagonal |
| 8 | retry -> join | no | solid, arrow at join |
| 9 | router -> fast | yes | dotted |
| 10 | router -> worker | yes | dotted, long on the left, arrow at worker |
| 11 | scope -> `__end__` | yes | dotted, longest line, right of the main column |
| 12 | scope -> router | yes | dotted |
| 13 | validate -> gate | yes | dotted, to the right |
| 14 | validate -> worker | yes | dotted, lower left |
| 15 | validate -> writer | yes | dotted, straight down |
| 16 | worker -> join | no | solid |
| 17 | writer -> validate | no | solid, goes up on the right of the dotted validate -> writer line, arrow at validate |
| 18 | execute -> `__end__` | no | solid, arrow at `__end__` |

Counts: 12 dotted and 7 solid lines in the picture, equal to 12 conditional and 7 plain edges in `get_graph()`. Each of the 19 arrowheads is at the right node (checked on zoom_middle.png and zoom_bottom.png).

## 5. Checks asked for

- Every node and conditional edge appears: yes (section 4).
- Labels readable: yes, at the 1400 px-wide window with 2x scale and also at scale 1 (shot1.png); node names are about the size of body text.
- Nothing overlaps: no text or box overlaps another. Line crossings exist and are normal for this graph: the long scope -> `__end__` dotted line crosses validate -> gate and gate -> `__end__`; two dotted lines (scope -> `__end__`, gate -> `__end__`) run side by side close to each other near `__end__` but stay separate with two separate arrowheads. validate <-> writer is drawn as two distinct lines (dotted down, solid up).
- No error text drawn: no mermaid "Syntax error" box, no traceback; jupyter-server.log has no error lines.

## 6. Defects and observations

No drawing defect. Minor observations, none of them a failure of the check:
1. The conditional edges carry no labels (the `path_map` is a plain list in `hybrid.py:162-174`), so the picture shows that a branch exists but not which condition takes it. The table has a 조건부 column but also no condition. Neither the 00 nor the 04 notebook, nor README, says that a dotted line means conditional (grep of "점선" gives 0 hits), so a student has to infer it or read the 조건부 column.
2. The saved `outputs` of 04 cell 51 are empty at the time of this check (`outputs: []`), so the repo notebook itself does not yet carry this picture. Another node reruns the notebooks; I did not touch them.
3. Scope of this evidence: `show_graph` ran in a plain Python process, not in a kernel, and its captured output was drawn by JupyterLab. A kernel would send the same display data, but I did not run the cell in a kernel.

DESIGN.md section 12 row "`show_graph`의 mermaid 표시" says "실제 Day03_new 그래프는 그리지 않았다". This run did draw it (JupyterLab 4.6.5, Chrome 156.0.8078.80, 2026-11-01). I did not edit DESIGN.md; documentation refresh is outside this run.

## 7. Side effects and scope

- Model calls: 0. EXA calls: 0. No .env content printed or read into any output.
- Project files: none written by me. `find` for files newer than P/graph-render/start-marker (excluding .git, .venv, .claude/dag) listed only `Day03_new/outputs/live/01-Workflow-vs-Agent.{json,usage.jsonl}` and three `Day03_new/outputs/runs/*.json`: these belong to the parallel paid rerun of notebook 01 (an `ipykernel_launcher` process, PID 17490, started 17:03:39 with cwd Day03_new, before my server started; I left it alone).
- Outside P: `InteractiveShell.instance()` in make_graph.py touched `~/.ipython/profile_default/history.sqlite` (IPYTHONDIR was not set for that one run; another session's IPython could also have written it). It is not a project file.
- My JupyterLab servers and their kernels were stopped (`pgrep jupyter-lab` shows none).

Graph render: done
