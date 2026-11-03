"""03a 노트북의 그림을 만든다. 저장소 루트에서: uv run --no-sync python Day03_new/assets/src/make_03a.py

그림 숫자의 출처
- f1: 03-Four-Flows의 `TASKS`(needs)와 `plan_batches`가 내는 묶음. 숫자 없음.
- f2: `SeqState`의 칸 이름과 `verify`, `billing`, `credit` Node. 숫자 없음.
- f3: 숫자 없음.
- f4: `UNEVEN = {"billing": 0.2, "policy": 0.2, "outage": 1.0}`의 값과 `longest_path`, 합계의 계산. 측정값이 아니다.
"""
from __future__ import annotations

from pathlib import Path

from figlib import TOKENS, Fig

OUT = Path(__file__).resolve().parents[1]  # Day03_new/assets


def f1_task_graph() -> Fig:
    """T-1001 업무 의존 그래프. 묶음(위상 정렬) 5개, 묶음 2가 동시에 돌릴 수 있는 후보."""
    f = Fig("03a-1-task-graph", 960, 416, "T-1001 업무의 선행 조건",
            "verify가 끝나면 billing, policy, outage가 서로 결과 없이 시작할 수 있고, 셋이 모두 끝나야 credit, proposal, gate가 차례로 이어진다.")
    w, h, gap, left = 128, 56, 60, 40
    col = [left + k * (w + gap) for k in range(5)]
    rows = [112, 208, 304]  # 위, 가운데, 아래 줄의 y
    mid = rows[1] + h // 2

    # 묶음 2 영역(동시에 돌릴 수 있는 후보). 강조는 영역 테두리와 라벨, 둘뿐이다.
    f.band(col[1] - 16, rows[0] - 16, w + 32, rows[2] + h - rows[0] + 32, accent=True)
    f.text(col[1] + w / 2, 84, "묶음 2: 동시에 가능한 후보", size=12, weight=600, fill=TOKENS["accent"], layer="front")
    for k, label in [(0, "묶음 1"), (2, "묶음 3"), (3, "묶음 4"), (4, "묶음 5")]:
        f.text(col[k] + w / 2, 84, label, size=12, weight=500, fill=TOKENS["muted"])

    # verify → 세 작업 (한 변에 선 셋: 변 길이 56을 4로 나눈 14, 28, 42 위치)
    v_right = col[0] + w
    xg = v_right + gap // 2
    f.arrow([(v_right, rows[1] + 14), (xg, rows[1] + 14), (xg, rows[0] + h // 2), (col[1], rows[0] + h // 2)])
    f.arrow([(v_right, rows[1] + 28), (col[1], rows[1] + 28)])
    f.arrow([(v_right, rows[1] + 42), (xg, rows[1] + 42), (xg, rows[2] + h // 2), (col[1], rows[2] + h // 2)])

    # 세 작업 → credit (선행 조건이 세 개인 작업)
    t_right = col[1] + w
    xg2 = t_right + gap // 2
    f.arrow([(t_right, rows[0] + h // 2), (xg2, rows[0] + h // 2), (xg2, rows[1] + 14), (col[2], rows[1] + 14)])
    f.arrow([(t_right, rows[1] + 28), (col[2], rows[1] + 28)])
    f.arrow([(t_right, rows[2] + h // 2), (xg2, rows[2] + h // 2), (xg2, rows[1] + 42), (col[2], rows[1] + 42)])

    # 순차 구간
    f.arrow([(col[2] + w, mid), (col[3], mid)])
    f.arrow([(col[3] + w, mid), (col[4], mid)])

    f.node(col[0], rows[1], w, h, "범위 확인", "verify")
    f.node(col[1], rows[0], w, h, "결제 조회", "billing")
    f.node(col[1], rows[1], w, h, "규정 원문 찾기", "policy")
    f.node(col[1], rows[2], w, h, "가용률 조회", "outage")
    f.node(col[2], rows[1], w, h, "크레딧 계산", "credit")
    f.node(col[3], rows[1], w, h, "제안 작성", "proposal")
    f.node(col[4], rows[1], w, h, "코드 게이트", "gate")
    return f


def f2_state_updates() -> Fig:
    """순차 그래프(SeqState)의 stream(updates) 출력과 State 칸. Node는 바뀐 칸만 돌려주고 State에는 칸이 쌓인다."""
    f = Fig("03a-2-state-updates", 960, 376, "순차 그래프에서 State 칸이 쌓이는 모습",
            "verify, billing, credit이 차례로 실행되며 각 Node는 자기가 바꾼 칸 하나만 돌려주고, State에는 그 칸이 하나씩 채워진다.")
    chip_x, chip_w, row_h, pitch, y0 = 32, 80, 44, 64, 72
    stream_x, stream_w = 124, 284
    cell_x, cell_w, cell_pitch = 428, 116, 122
    keys = ["entity", "customer_verified", "billing_facts", "credit"]
    # 단계: (칩 이름, updates 한 줄, 칸별 상태 new/kept/empty, 칸의 값)
    steps = [
        ("START", "{'entity': '알파'}", ["new", "empty", "empty", "empty"], ["알파", "", "", ""]),
        ("verify", "{'verify': {'customer_verified': True}}", ["kept", "new", "empty", "empty"], ["알파", "True", "", ""]),
        ("billing", "{'billing': {'billing_facts': {…}}}", ["kept", "kept", "new", "empty"], ["알파", "True", "{base_fee}", ""]),
        ("credit", "{'credit': {'credit': …}}", ["kept", "kept", "kept", "new"], ["알파", "True", "{base_fee}", "base_fee의 15%"]),
    ]
    f.text(chip_x + chip_w / 2, 52, "단계", size=12, fill=TOKENS["muted"])
    f.text(stream_x + stream_w / 2, 52, "stream(updates)이 내는 한 줄", size=12, fill=TOKENS["muted"])
    for k, key in enumerate(keys):
        f.text(cell_x + k * cell_pitch + cell_w / 2, 52, key, size=11, fill=TOKENS["ink"], mono=True, weight=600)
    for i, (name, line, states, values) in enumerate(steps):
        y = y0 + i * pitch
        if i < len(steps) - 1:  # 고정 간선: 앞 Node → 다음 Node
            f.arrow([(chip_x + chip_w / 2, y + row_h), (chip_x + chip_w / 2, y + pitch)])
        f.node(chip_x, y, chip_w, row_h, name, kind="ghost" if name == "START" else "step")
        f.rect(stream_x, y, stream_w, row_h, fill=TOKENS["paper2"], stroke=TOKENS["rule_solid"], sw=1, rx=6)
        f.text(stream_x + 12, y + row_h / 2 + 4, line, size=11, anchor="start", mono=True, fill=TOKENS["ink"])
        for k, (state, value) in enumerate(zip(states, values)):
            x = cell_x + k * cell_pitch
            if state == "new":
                f.rect(x, y, cell_w, row_h, fill=TOKENS["paper"], stroke=TOKENS["ink"], sw=2, rx=6)
                f.text(x + cell_w / 2, y + row_h / 2 + 4, value, size=12, weight=600)
            elif state == "kept":
                f.rect(x, y, cell_w, row_h, fill=TOKENS["paper2"], stroke=TOKENS["rule_solid"], sw=1, rx=6)
                f.text(x + cell_w / 2, y + row_h / 2 + 4, value, size=12, weight=500, fill=TOKENS["muted"])
            else:
                f.rect(x, y, cell_w, row_h, fill="none", stroke=TOKENS["rule_solid"], sw=1, dashed=True, rx=6)
    # 범례: 아래 가로 띠
    ly = 340
    for x, label, state in [(40, "이번 단계에 쓴 칸", "new"), (228, "앞 단계에서 이어진 칸", "kept"), (448, "아직 비어 있는 칸", "empty")]:
        if state == "new":
            f.rect(x, ly - 12, 20, 16, fill=TOKENS["paper"], stroke=TOKENS["ink"], sw=2, rx=3)
        elif state == "kept":
            f.rect(x, ly - 12, 20, 16, fill=TOKENS["paper2"], stroke=TOKENS["rule_solid"], sw=1, rx=3)
        else:
            f.rect(x, ly - 12, 20, 16, fill="none", stroke=TOKENS["rule_solid"], sw=1, dashed=True, rx=3)
        f.text(x + 28, ly + 1, label, size=12, anchor="start", fill=TOKENS["muted"])
    return f


def f3_send_fanout() -> Fig:
    """dispatch가 Send 세 장을 돌려주고, 같은 work Node가 입력만 바꿔 세 번 돌고, 한 단계가 끝나야 results에 합쳐진다."""
    f = Fig("03a-3-send-fanout", 960, 432, "Send로 같은 Node를 세 번 실행하는 흐름",
            "dispatch가 Send 세 개를 돌려주면 work Node가 입력만 달리해 세 번 실행되고, 한 단계가 모두 끝나면 결과가 reducer가 붙은 results 칸에 합쳐진다.")
    w, h = 224, 56
    rows = [112, 208, 304]
    mid = rows[1] + h // 2
    dx, dw, dh = 40, 176, 72
    wx = 336
    rx_, rw = 696, 224
    d_y = mid - dh // 2
    # 조건부 간선 → work 셋 (dispatch 오른쪽 변에 선 셋: 변 길이 72를 4로 나눈 18, 36, 54)
    xg = dx + dw + 60
    attach = [d_y + 18, d_y + 36, d_y + 54]
    f.arrow([(dx + dw, attach[0]), (xg, attach[0]), (xg, rows[0] + h // 2), (wx, rows[0] + h // 2)])
    f.arrow([(dx + dw, attach[1]), (wx, rows[1] + h // 2)])
    f.arrow([(dx + dw, attach[2]), (xg, attach[2]), (xg, rows[2] + h // 2), (wx, rows[2] + h // 2)])
    # work 셋 → results (한 단계가 끝난 뒤 합침)
    xg2 = wx + w + 40
    r_attach = [d_y + 18, d_y + 36, d_y + 54]
    f.arrow([(wx + w, rows[0] + h // 2), (xg2, rows[0] + h // 2), (xg2, r_attach[0]), (rx_, r_attach[0])])
    f.arrow([(wx + w, rows[1] + h // 2), (rx_, r_attach[1])])
    f.arrow([(wx + w, rows[2] + h // 2), (xg2, rows[2] + h // 2), (xg2, r_attach[2]), (rx_, r_attach[2])])
    # 단계(superstep) 경계
    bx = 648
    f.line(bx, 96, bx, 376, color=TOKENS["muted"], sw=1.25, dashed=True)
    f.text(bx, 404, "점선까지가 한 단계(superstep)입니다. 세 실행이 모두 끝나야 결과가 State에 합쳐집니다.", size=12, fill=TOKENS["muted"])
    for x, label in [(dx + dw / 2, "① 조건부 간선이 작업 표를 만듭니다"), (wx + w / 2, "② 같은 Node를 입력만 바꿔 세 번"), (rx_ + rw / 2, "③ State 칸에 합칩니다")]:
        f.text(x, 84, label, size=12, fill=TOKENS["muted"])
    f.node(dx, d_y, dw, dh, "작업 표 만들기", "dispatch → [Send ×3]")
    for row, task in zip(rows, ["billing", "policy", "outage"]):
        f.node(wx, row, w, h, f"work ({task})", f'task_id="{task}"')
    f.node(rx_, d_y, rw, dh, "results", "Annotated[dict, merge_results]", kind="focal")
    return f


def f4_longest_path() -> Fig:
    """UNEVEN의 계산값. 직렬은 합계, 병렬은 최장 경로. 측정값이 아니라 `longest_path`와 합계의 계산이다."""
    import sys
    sys.path.insert(0, str(OUT.parent))
    from mas_lab.trace import longest_path

    uneven = {"billing": 0.2, "policy": 0.2, "outage": 1.0}
    with_credit = {**uneven, "credit": 0.1}
    parallel, serial = longest_path(uneven, {}), round(sum(uneven.values()), 3)
    chained = longest_path(with_credit, {"credit": list(uneven)})
    assert (parallel, serial, chained) == (1.0, 1.4, 1.1), (parallel, serial, chained)

    f = Fig("03a-4-longest-path", 960, 452, "병렬의 시간은 합계가 아니라 최장 경로",
            "작업 시간이 0.2, 0.2, 1.0초일 때 차례로 돌리면 1.4초이고 동시에 돌리면 가장 긴 1.0초이며, credit이 셋을 기다리면 1.1초다.")
    x0, per = 216, 480  # 시간 0의 x, 1초당 픽셀
    X = lambda t: x0 + round(t * per)
    # 시간 눈금
    f.text(40, 60, "시간(초)", size=12, anchor="start", fill=TOKENS["muted"])
    for k in range(8):
        t = k * 0.2
        f.line(X(t), 72, X(t), 432, color=TOKENS["rule"])
        f.text(X(t), 60, f"{t:.1f}", size=11, mono=True, fill=TOKENS["soft"])

    def bar(t0, t1, y, name, focus=False, named=False):
        """막대 안에는 시간만 쓴다. 이름은 왼쪽 칸에 있다. 한 줄에 여럿이 이어지는 직렬 줄만 막대 안에 이름도 쓴다."""
        f.rect(X(t0), y, X(t1) - X(t0), 22, fill=TOKENS["paper"], stroke=TOKENS["ink"] if focus else TOKENS["muted"], sw=2 if focus else 1.25, rx=4)
        inner = f"{name} {t1 - t0:.1f}" if named else f"{t1 - t0:.1f}"
        f.text((X(t0) + X(t1)) / 2, y + 15, inner, size=11, mono=True, fill=TOKENS["ink"], weight=600 if focus else 500)

    def group(title, y, note):
        f.text(40, y, title, size=12, anchor="start", weight=600)
        f.text(888, y, note, size=12, anchor="end", fill=TOKENS["muted"])

    # 직렬
    group("차례로 돌리면 (max_concurrency=1)", 100, f"합계 {serial}초 = 0.2 + 0.2 + 1.0")
    bar(0.0, 0.2, 110, "billing", named=True)
    bar(0.2, 0.4, 110, "policy", named=True)
    bar(0.4, 1.4, 110, "outage", named=True)
    # 병렬
    group("동시에 돌리면", 176, f"최장 경로 {parallel}초 = max(0.2, 0.2, 1.0)")
    for i, (name, t) in enumerate(uneven.items()):
        y = 186 + i * 28
        f.text(x0 - 12, y + 15, name, size=11, anchor="end", mono=True, fill=TOKENS["soft"])
        bar(0.0, t, y, name, focus=(name == "outage"))
    # 줄어든 시간(강조 둘: 점선 칸과 그 글자)
    f.rect(X(1.0), 242, X(1.4) - X(1.0), 22, fill=TOKENS["accent_tint"], stroke=TOKENS["accent"], sw=1.25, dashed=True, rx=4)
    f.text((X(1.0) + X(1.4)) / 2, 257, "0.4초 짧아짐", size=12, weight=600, fill=TOKENS["accent"])
    # credit이 셋을 기다리는 경우
    group("credit이 셋을 모두 기다리면", 308, f"최장 경로 {chained}초 = 1.0 + 0.1")
    for i, (name, t) in enumerate(with_credit.items()):
        y = 318 + i * 28
        f.text(x0 - 12, y + 15, name, size=11, anchor="end", mono=True, fill=TOKENS["soft"])
        if name == "credit":
            bar(1.0, 1.1, y, name, focus=True)
        else:
            bar(0.0, t, y, name, focus=(name == "outage"))
    return f


FIGURES = [f1_task_graph, f2_state_updates, f3_send_fanout, f4_longest_path]

if __name__ == "__main__":
    for make in FIGURES:
        svg, png = make().save(OUT)
        print(png.relative_to(OUT.parent))
