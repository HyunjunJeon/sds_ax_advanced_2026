"""05b 노트북의 그림을 만든다. 저장소 루트에서: uv run --no-sync python Day03_new/assets/src/make_05b.py

그림의 근거 (05b-Measure-Compare.ipynb)
- f1: 5절 `call_spans`, `by_kind`의 구분(Supervisor 조정·집계, Worker 합계)과 `longest_path`. 숫자는 쓰지 않고 구조만 그린다.
- f2: 6절 `build_hybrid`(mas_lab/hybrid.py)의 간선. router→fast 또는 worker, worker→join→writer, fast와 writer→validate,
      validate→gate, 그리고 Fast에서 온 부족한 답만 worker로 돌리는 fallback_to_slow.
- f3: 7절 하네스 표. 다섯 구조가 같은 예산, 허용 목록, 응답 형식, 쓰기 게이트를 지난다.
- f4: 8절 선택 순서도. 05a 0절(담당 표), 05a 1절·4절(실패 분류, Skill), 05a 2~3절과 05b 5절(격리·병렬), 02 4절(Handoff)의
      기준을 묻는 순서로 놓는다. 칸 아래 숫자는 절 번호이고 측정값이 아니다.
측정값은 쓰지 않는다.
"""
from __future__ import annotations

from pathlib import Path

from figlib import TOKENS, Fig

OUT = Path(__file__).resolve().parents[1]


def f1_critical_path() -> Fig:
    f = Fig("05b-1-critical-path", 960, 356, "지연은 Agent 수가 아니라 가장 긴 경로",
            "Supervisor가 Worker 셋에게 위임하고 결과를 받아 집계할 때 Worker는 병렬로 돌지만, 경로는 Supervisor 호출, 가장 느린 Worker, Supervisor 집계 호출을 지난다.")
    w, h = 144, 48
    f.node(40, 140, w, 64, "Supervisor", "위임 호출")
    ys = [48, 148, 232]
    names = ["billing", "policy", "outage"]
    att = [140 + 16, 140 + 32, 140 + 48]
    xg = 248
    for y, n, a in zip(ys, names, att):
        mid = y + h // 2
        f.node(344, y, w, h, n, "Worker 호출")
        if mid == a:
            f.arrow([(40 + w, a), (344, a)])
        else:
            f.arrow([(40 + w, a), (xg, a), (xg, mid), (344, mid)])
        ex = 648
        if mid == 140 + 32:
            f.arrow([(344 + w, mid), (ex, mid)])
        else:
            f.arrow([(344 + w, mid), (600, mid), (600, 140 + (16 if y < 140 else 48)), (ex, 140 + (16 if y < 140 else 48))])
    f.node(648, 140, 144, 64, "Supervisor", "집계 호출", kind="focal")
    f.text(344 + w / 2, 304, "Worker끼리는 겹쳐서 돕니다", size=12, fill=TOKENS["muted"])
    f.text(720, 120, "나누면서 새로 생긴 시간", size=12, weight=600, fill=TOKENS["accent"])
    f.text(40, 340, "경로 = Supervisor 호출 + 가장 느린 Worker + Supervisor 집계 호출. 직렬 합과 최장 경로의 차이가 병렬이 줄인 시간의 상한입니다.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f2_fast_slow() -> Fig:
    f = Fig("05b-2-fast-slow", 960, 340, "hybrid의 Fast와 Slow 경로",
            "Router가 Fast 또는 Worker 병렬로 보내고, Worker 결과는 join과 writer를 거쳐 validate로, Fast의 답은 바로 validate로 모인 뒤 gate로 간다. Fast에서 온 답이 근거 부족이면 validate가 worker로 되돌려 Slow로 전환한다.")
    w, h = 104, 56
    x = [40, 188, 336, 484, 632, 780]
    f.node(x[0], 120, w, h, "라우터", "router")
    f.node(x[1], 60, w, h, "빠른 경로", "fast")
    f.node(x[1], 180, w, h, "작업 실행", "worker")
    f.node(x[2], 180, w, h, "합치기", "join")
    f.node(x[3], 180, w, h, "합성", "writer")
    f.node(x[4], 120, w, h, "검증", "validate")
    f.node(x[5], 120, w, h, "게이트", "gate")
    f.arrow([(x[0] + w, 132), (166, 132), (166, 88), (x[1], 88)])
    f.arrow([(x[0] + w, 164), (166, 164), (166, 208), (x[1], 208)])
    f.arrow([(x[1] + w, 88), (x[4] + 52, 88), (x[4] + 52, 120)])
    f.arrow([(x[1] + w, 208), (x[2], 208)])
    f.arrow([(x[2] + w, 208), (x[3], 208)])
    f.arrow([(x[3] + w, 208), (x[4] + 28, 208), (x[4] + 28, 176)])
    f.arrow([(x[4] + w, 148), (x[5], 148)])
    f.arrow([(x[4] + 78, 176), (x[4] + 78, 272), (x[1] + 52, 272), (x[1] + 52, 236)], kind="accent", dashed=True)
    f.label(400, 272, "Fast에서 온 부족한 답만", size=12, fill=TOKENS["accent"])
    f.text(x[5] + w / 2, 200, "승인 대기 또는", size=12, fill=TOKENS["muted"])
    f.text(x[5] + w / 2, 218, "execute로 실행", size=12, fill=TOKENS["muted"])
    f.text(40, 316, "Fast와 Slow 모두 같은 validate와 gate를 지납니다. Fast가 건너뛰는 것은 조사의 폭이지 검증이 아닙니다.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f3_same_harness() -> Fig:
    f = Fig("05b-3-same-harness", 960, 356, "다섯 구조가 지나는 같은 하네스",
            "single, single_skills, supervisor, handoff, hybrid 다섯 구조는 조립만 다르고 같은 예산, 도구 허용 목록, 응답 형식, 쓰기 게이트 하네스를 지난다.")
    names = [("single", None), ("single_skills", None), ("supervisor", None), ("handoff", None), ("hybrid", None)]
    sx, sw, sh, top, step = 40, 176, 44, 44, 56
    bx, bw = 328, 360
    f.band(bx, 24, bw, 288, accent=True, dashed=False)
    f.text(bx + bw / 2, 52, "같은 하네스", size=13, weight=600, fill=TOKENS["accent"])
    items = [("예산", "Desk의 Budget, FIXED_BUDGET"), ("도구 허용 목록", "allowlist_middleware"), ("응답 형식", "FinalAnswer"), ("쓰기 게이트", "gate_answer")]
    for k, (n, s) in enumerate(items):
        f.node(bx + 32, 72 + k * 60, bw - 64, 48, n, s)
    for k, (n, _) in enumerate(names):
        y = top + k * step
        f.node(sx, y, sw, sh, n)
        f.arrow([(sx + sw, y + sh // 2), (bx, y + sh // 2)])
    f.node(760, 140, 160, 64, "결과 행", "같은 칸의 실행 행")
    f.arrow([(bx + bw, 172), (760, 172)])
    f.text(40, 340, "바뀌는 변수는 구조 하나뿐이어서 표의 차이를 구조 탓으로 읽을 수 있습니다. general-purpose Worker는 이 하네스 밖이라 끕니다.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f4_decision_flow() -> Fig:
    f = Fig("05b-4-decision-flow", 960, 400, "흩어진 선택 기준을 묻는 순서",
            "코드로 정해지나, Single로 고쳐지나, 격리나 병렬이 필요한가, 주도권이 넘어가나를 차례로 묻는다. 예이면 아래 칸의 구조에서 멈추고, 모두 아니오이면 나누지 않는다. 어느 칸이든 돈을 움직이는 쓰기는 코드 게이트 하나를 지난다.")
    w, h, gap = 144, 64, 48
    xs = [40 + k * (w + gap) for k in range(5)]
    qy, oy = 56, 208
    questions = [("코드로 정해지나?", "05a 0절"), ("Single로 고쳐지나?", "05a 1절, 4절"), ("격리·병렬이 필요?", "05a 2~3절, 05b 5절"),
                 ("주도권이 넘어가나?", "02 4절")]
    outcomes = [("코드 노드", "Workflow", "step"), ("Single", "+ Skill", "step"), ("Supervisor·Send", "분해는 누가?", "focal"),
                ("Handoff", "owner 전환", "step")]
    for k, (name, sub) in enumerate(questions):
        f.node(xs[k], qy, w, h, name, sub)
    f.node(xs[4], qy, w, h, "나누지 않음", "더 재고 기록", kind="ghost")
    for k in range(4):
        y = qy + h // 2
        f.arrow([(xs[k] + w, y), (xs[k + 1], y)])
        f.text(xs[k] + w + gap / 2, y - 10, "아니오", size=11, fill=TOKENS["muted"])
        name, sub, kind = outcomes[k]
        cx = xs[k] + w // 2
        f.node(xs[k], oy, w, h, name, sub, kind=kind)
        f.arrow([(cx, qy + h), (cx, oy)])
        f.text(cx + 10, (qy + h + oy) / 2 + 4, "예", size=12, anchor="start", fill=TOKENS["muted"])
    f.text(xs[2] + w // 2, oy + h + 24, "Worker가 늘고 걸러 낼 판단이 생기면 Hierarchical", size=11, fill=TOKENS["soft"])
    f.band(40, 324, 912, 56, accent=True, dashed=False)
    f.text(56, 348, "어느 칸에서 끝나든 돈을 움직이는 쓰기는 코드 게이트 하나(gate_answer)를 지납니다.", size=13, anchor="start", weight=600, fill=TOKENS["accent"])
    f.text(56, 368, "나누기 쉬운 것은 읽기(조사)이고, 쓰기와 결정은 한 곳에 모읍니다. 셋째와 넷째 질문은 다른 축이라 둘 다 예일 수 있습니다.", size=12, anchor="start", fill=TOKENS["ink"])
    return f


FIGURES = [f1_critical_path, f2_fast_slow, f3_same_harness, f4_decision_flow]

if __name__ == "__main__":
    for make in FIGURES:
        svg, png = make().save(OUT)
        print(png.relative_to(OUT.parent))
