"""03b 노트북의 그림을 만든다. 저장소 루트에서: uv run --no-sync python Day03_new/assets/src/make_03b.py

그림의 근거 (03b-Branch-Loop-Patterns.ipynb)
- f1: 4절의 `rule_route`(다른 고객 이름 → out_of_scope, 자료 종류 둘 이상 → slow, 그 밖 → fast)와 `fallback_app`
      (fast → check_kinds → 부족한 자료 종류가 있으면 slow, 없으면 END, slow → END). 4절 표의 비용(낮음, 높음, 없음).
- f2: 5절 `build_retry_loop`의 `check`. 판정 순서는 complete, same_failure, retry_limit, 그 밖(다시)이다.
- f3: 6절 `build_orchestrator`의 간선과 `FLOW_OF_NODE`(plan 순차, worker 병렬, aggregate 순차, validate 분기, replan 루프).
- f4: 6절 `build_agent_loop`의 간선. START → model, model → tools 또는 END(`tools_condition`), tools → model.
숫자는 쓰지 않는다.
"""
from __future__ import annotations

from pathlib import Path

from figlib import TOKENS, Fig

OUT = Path(__file__).resolve().parents[1]


def chip(f: Fig, cx, y, text, accent=False):
    """흐름 이름표. 노드 위나 아래에 붙는 작은 칸."""
    w = 56
    stroke = TOKENS["accent"] if accent else TOKENS["rule_solid"]
    f.rect(cx - w / 2, y, w, 20, fill=TOKENS["accent_tint"] if accent else TOKENS["paper2"], stroke=stroke, sw=1, rx=2)
    f.text(cx, y + 14.5, text, size=12, weight=600, fill=TOKENS["accent"] if accent else TOKENS["muted"])


def f1_branch_placement() -> Fig:
    f = Fig("03b-1-branch-placement", 960, 484, "분기를 어디에 두는가",
            "위는 요청을 보고 먼저 경로를 고르는 규칙 라우터이고, 아래는 먼저 Fast를 돌려 보고 자료 종류가 부족하면 Slow로 보내는 복구 간선이다.")
    # ① 먼저 고르기
    f.text(40, 36, "① 먼저 고르기: 규칙 라우터", size=13, weight=600, anchor="start")
    w, h = 160, 56
    rows = [72, 144, 216]
    cx_, cw, ch = 40, 160, 72
    c_y = rows[1] + h // 2 - ch // 2
    tx = 424
    xg = 240
    att = [c_y + 18, c_y + 36, c_y + 54]
    mids = [r + h // 2 for r in rows]
    f.arrow([(cx_ + cw, att[0]), (xg, att[0]), (xg, mids[0]), (tx, mids[0])])
    f.arrow([(cx_ + cw, att[1]), (tx, mids[1])])
    f.arrow([(cx_ + cw, att[2]), (xg, att[2]), (xg, mids[2]), (tx, mids[2])])
    f.node(cx_, c_y, cw, ch, "분류", "classify")
    for y, (name, sub, cost, cond) in zip(rows, [("범위 밖", "out_of_scope", "비용 없음", "다른 고객 이름"), ("느린 경로", "slow", "비용 높음", "자료 종류 둘 이상"),
                                                 ("빠른 경로", "fast", "비용 낮음", "그 밖")]):
        f.node(tx, y, w, h, name, sub)
        f.text(tx + w + 16, y + h // 2 + 4, cost, size=12, anchor="start", fill=TOKENS["muted"])
        f.label(332, y + h // 2, cond)
    f.line(40, 296, 920, 296, color=TOKENS["rule_solid"])
    # ② 돌려 보고 정하기
    f.text(40, 332, "② 돌려 보고 정하기: 복구 간선", size=13, weight=600, anchor="start")
    y = 376
    mid = y + h // 2
    f.arrow([(200, mid), (272, mid)])
    f.arrow([(432, mid), (504, mid)])
    f.arrow([(664, mid), (736, mid)])
    f.arrow([(352, y), (352, y - 22), (808, y - 22), (808, y)])
    f.label(460, mid, "부족함")
    f.text(580, y - 30, "충분함", size=12, fill=TOKENS["muted"])
    f.node(40, y, w, h, "빠른 경로", "fast")
    f.node(272, y, w, h, "자료 종류 확인", "check_kinds")
    f.node(504, y, w, h, "느린 경로", "slow")
    f.node(736, y, 144, h, "종료", "END", kind="ghost")
    f.text(40, 468, "복구 간선의 비용: 먼저 돌린 fast의 검색은 버려집니다.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f2_loop_exits() -> Fig:
    f = Fig("03b-2-loop-exits", 960, 376, "루프가 멈추는 길과 계속하는 길",
            "check가 시도 결과를 위에서 아래로 판정해 누락이 없으면 complete, 같은 누락이 반복되면 same_failure, 시도 상한이면 retry_limit으로 멈추고, 그 밖에는 attempt로 되돌아간다.")
    ay, ah = 144, 64
    mid = ay + ah // 2
    f.arrow([(200, mid), (272, mid)])
    # check의 오른쪽 변: 선 셋 (변 길이 64를 4로 나눈 16, 32, 48)
    att = [ay + 16, ay + 32, ay + 48]
    bw, bh, bx = 344, 80, 576
    ys = [40, 136, 232]
    xg = 504
    f.arrow([(432, att[0]), (xg, att[0]), (xg, ys[0] + bh // 2), (bx, ys[0] + bh // 2)])
    f.arrow([(432, att[1]), (bx, ys[1] + bh // 2)])
    f.arrow([(432, att[2]), (xg, att[2]), (xg, ys[2] + bh // 2), (bx, ys[2] + bh // 2)])
    # 계속하는 길: check 아래로 나가 attempt로 되돌아간다. 이 그림의 강조는 이 선과 글자다.
    f.arrow([(352, ay + ah), (352, 336), (120, 336), (120, ay + ah)], kind="accent")
    f.text(236, 322, "④ 그 밖: attempt로 되돌아갑니다", size=12, weight=600, fill=TOKENS["accent"])
    f.node(40, ay, 160, ah, "시도", "attempt")
    f.node(272, ay, 160, ah, "검사", "check")
    for y, (name, sub, cond) in zip(ys, [("① 통과", "complete", "누락 항목이 없다"), ("② 같은 실패 반복", "same_failure", "같은 누락이 same_limit번 연속"),
                                       ("③ 상한 도달", "retry_limit", "시도 수가 max_attempts 이상")]):
        f.node(bx, y, bw, bh, name, sub, kind="ghost")
        f.text(bx + bw / 2, y + bh - 8, cond, size=12, fill=TOKENS["muted"])
    return f


def f3_orchestrator_flows() -> Fig:
    f = Fig("03b-3-orchestrator-flows", 960, 412, "Orchestrator-Worker 조립에서 네 흐름이 있는 자리",
            "plan이 작업을 나누고 worker가 Send로 병렬 실행하고 aggregate가 합친 뒤 validate가 통과면 종료, 문제가 있으면 replan이 실패한 작업만 worker로 되돌려 보낸다.")
    w, h, gap, left = 128, 64, 60, 40
    col = [left + k * (w + gap) for k in range(5)]
    y = 120
    mid = y + h // 2
    names = [("작업 분해", "plan", "순차"), ("작업 실행", "worker", "병렬"), ("결과 합치기", "aggregate", "순차"), ("검증", "validate", "분기")]
    for k in range(3):
        f.arrow([(col[k] + w, mid), (col[k + 1], mid)])
    f.label(col[0] + w + gap / 2, mid - 22, "Send", size=11)  # plan → worker 간선 위(마스크 없이 윗줄에 둔다)
    f.arrow([(col[3] + w, mid), (col[4], mid)])
    # validate → replan → worker (루프). 강조는 이 두 선뿐이다.
    ry = 272
    vx = col[3] + w // 2
    f.arrow([(vx, y + h), (vx, ry)], kind="accent")
    f.text(vx + 12, y + h + 40, "문제 있음, 재계획 한도 안", size=12, anchor="start", weight=600, fill=TOKENS["muted"])
    wx = col[1] + w // 2
    ax = col[2] + w // 2
    up, down = ry + 21, ry + 43  # replan 왼쪽 변에 선 둘: 변 길이 64를 3으로 나눈 위치
    f.arrow([(col[3], down), (wx, down), (wx, y + h)], kind="accent")
    f.text((wx + col[3]) / 2, down + 20, "실패한 작업만 새 키로 다시 Send", size=12, weight=600, fill=TOKENS["muted"])
    # 다시 보낼 작업이 없으면 worker를 거치지 않고 aggregate로 간다(send_tasks의 `or "aggregate"`).
    f.arrow([(col[3], up), (ax, up), (ax, y + h)], dashed=True)
    f.text((ax + col[3]) / 2, up - 10, "보낼 작업이 없으면", size=12, fill=TOKENS["muted"])
    for k, (name, sub, flow) in enumerate(names):
        f.node(col[k], y, w, h, name, sub)
        chip(f, col[k] + w / 2, y - 32, flow)
    f.node(col[4], y, w, h, "종료", "END", kind="ghost")
    f.node(col[3], ry, w, h, "재계획", "replan")
    chip(f, vx, ry + h + 12, "루프")
    f.text(col[4] + w / 2, ry + 36, "validate가 문제 없음이거나", size=12, fill=TOKENS["muted"])
    f.text(col[4] + w / 2, ry + 54, "한도에 닿으면 종료합니다", size=12, fill=TOKENS["muted"])
    return f


def f4_agent_loop() -> Fig:
    f = Fig("03b-4-agent-loop", 960, 288, "Agent Loop 안의 분기와 루프",
            "START에서 model로 가고, model의 응답에 도구 호출이 있으면 tools로, 없으면 END로 간다(분기). tools는 실행 결과를 들고 다시 model로 돌아간다(루프).")
    f.node(40, 54, 96, 48, "시작", "START", kind="ghost")
    f.node(200, 46, 176, 64, "model", "다음 행동을 고름", kind="focal")
    f.node(744, 54, 176, 48, "끝", "END", kind="ghost")
    f.node(472, 156, 176, 64, "tools", "고른 도구를 실행")
    f.arrow([(136, 78), (200, 78)])
    f.arrow([(376, 78), (744, 78)])
    f.label(560, 78, "도구 호출이 없으면", size=12)
    f.arrow([(336, 110), (336, 176), (472, 176)])
    f.text(348, 166, "도구 호출이 있으면", size=12, anchor="start", fill=TOKENS["muted"])
    f.arrow([(472, 204), (240, 204), (240, 110)], kind="accent")
    f.text(356, 226, "도구 결과를 들고 돌아감", size=12, weight=600, fill=TOKENS["accent"])
    chip(f, 432, 44, "분기")
    chip(f, 196, 184, "루프", accent=True)
    f.text(40, 272, "분기 하나(tools_condition)와 루프 하나(tools → model)가 Agent Loop의 전부입니다. 끝낼지는 모델이 정하고, 코드는 재귀 한도로만 멈춥니다.",
           size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


FIGURES = [f1_branch_placement, f2_loop_exits, f3_orchestrator_flows, f4_agent_loop]

if __name__ == "__main__":
    for make in FIGURES:
        svg, png = make().save(OUT)
        print(png.relative_to(OUT.parent))
