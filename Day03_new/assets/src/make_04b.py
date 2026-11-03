"""04b 노트북의 그림을 만든다. 저장소 루트에서: uv run --no-sync python Day03_new/assets/src/make_04b.py

그림의 근거 (04b-Graph-Failure-Approval.ipynb)
- f1: 5절 `next_action`. 표의 값은 이 스크립트가 `mas_lab.contracts.next_action`을 직접 불러 얻는다(재시도 남음·예산 남음, 재시도 0, 예산 없음 세 조건).
- f2: 6절 `silent_join`(complete만 모아 넘김)과 `join_results`/`after_visible_join`(작업별 상태를 드러내고 failed만 새 키로 다시 Send).
- f3: 7절 `build_approval`의 간선(propose→gate, gate→execute/approve/END, approve→gate/execute/END, execute→verify→END).
측정값은 쓰지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

from figlib import TOKENS, Fig

OUT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OUT.parent))
from mas_lab.contracts import FailureKind, next_action  # noqa: E402


def f1_failure_actions() -> Fig:
    f = Fig("04b-1-failure-actions", 960, 372, "실패 종류에 따른 다음 행동",
            "next_action이 실패 종류와 재시도 기회, 예산 여부에 따라 respond, reinvestigate, retry, escalate, stop_with_reason 중 하나를 고른다. 다시 부르는 행동은 reinvestigate와 retry뿐이다.")
    conds = [("재시도 남음 · 예산 남음", 1, True), ("재시도 0", 0, True), ("예산 없음", 1, False)]
    x0, cw, rh, top, lw = 248, 224, 48, 64, 200
    f.text(40, 44, "실패 종류", size=13, weight=600, anchor="start")
    for k, (name, _, _) in enumerate(conds):
        f.text(x0 + k * cw + cw / 2, 44, name, size=13, weight=600, fill=TOKENS["muted"])
    for r, kind in enumerate(FailureKind):
        y = top + r * (rh + 8)
        f.text(40, y + rh / 2 + 5, kind.value, size=13, weight=600, anchor="start", mono=True)
        for k, (_, retries, left) in enumerate(conds):
            act = next_action(kind, retries_left=retries, budget_left=left)
            again = act in {"retry", "reinvestigate"}
            f.rect(x0 + k * cw + 4, y, cw - 8, rh, fill=TOKENS["accent_tint"] if again else TOKENS["paper"],
                   stroke=TOKENS["accent"] if again else TOKENS["rule_solid"], sw=1.25 if again else 1, rx=4)
            f.text(x0 + k * cw + cw / 2, y + rh / 2 + 5, act, size=13, weight=600 if again else 500, mono=True,
                   fill=TOKENS["ink"] if again else TOKENS["soft"])
    f.text(40, 356, "강조한 칸만 다시 부릅니다. 분류와 다음 행동은 모델이 아니라 코드가 정합니다.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f2_join_visibility() -> Fig:
    f = Fig("04b-2-join-visibility", 960, 340, "조용한 합류와 드러내는 합류",
            "위쪽 silent_join은 complete인 결과만 작성 노드에 넘겨 실패가 사라진다. 아래쪽 join_results는 작업별 상태를 드러내고 failed인 작업만 새 키로 다시 Send한다.")
    w, h = 200, 64
    xs = [40, 300, 560]
    lanes = [("조용한 합류", 64, "worker 셋", "outage 하나가 failed", "silent_join", "complete만 모읍니다", "작성 노드의 입력", "outage가 없습니다", False),
             ("드러내는 합류", 208, "worker 셋", "outage 하나가 failed", "join_results", "작업별 상태 표", "after_visible_join", "failed만 새 키로 Send", True)]
    for title, y, a, asub, b, bsub, c, csub, good in lanes:
        f.text(40, y - 14, title, size=13, weight=600, anchor="start", fill=TOKENS["accent"] if not good else TOKENS["ink"])
        mid = y + h // 2
        f.node(xs[0], y, w, h, a, asub)
        f.node(xs[1], y, w, h, b, bsub)
        f.node(xs[2], y, w, h, c, csub, kind="focal" if not good else "step")
        f.arrow([(xs[0] + w, mid), (xs[1], mid)])
        f.arrow([(xs[1] + w, mid), (xs[2], mid)], kind="accent" if not good else "default")
    # 아래 레인: 새 키 재시도가 worker로 되돌아간다
    y = 208
    f.arrow([(xs[2] + w // 2, y + h), (xs[2] + w // 2, y + h + 28), (xs[0] + w // 2, y + h + 28), (xs[0] + w // 2, y + h)])
    f.text((xs[0] + xs[2] + w) / 2 - 20, y + h + 48, "outage#2만 다시 실행하고 billing, policy 결과는 그대로 둡니다", size=12, fill=TOKENS["muted"])
    f.text(xs[2] + w + 16, 64 + h // 2 + 4, "실패의 흔적 없음", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f3_approval_graph() -> Fig:
    f = Fig("04b-3-approval-graph", 960, 340, "승인 그래프에서 부작용이 있는 자리",
            "propose 뒤 gate가 검사하고 allow면 execute, needs_approval이면 approve에서 interrupt로 사람을 기다린다. approve는 승인되면 execute로, 금액이 바뀌면 gate로 돌아간다. 원장에 쓰는 일은 execute 한 곳뿐이고 verify가 원장을 다시 읽는다.")
    w, h, y = 140, 56, 160
    mid = y + h // 2
    px, gx, ex, vx, endx = 40, 240, 520, 700, 880
    ax, ay = 380, 48
    f.node(px, y, w, h, "제안", "propose")
    f.node(gx, y, w, h, "게이트", "gate")
    f.node(ax, ay, w, h, "사람 승인", "approve")
    f.node(ex, y, w, h, "실행", "execute", kind="focal")
    f.node(vx, y, 120, h, "확인", "verify")
    f.node(endx - 0, y, 40, h, "끝", kind="ghost")
    f.arrow([(px + w, mid), (gx, mid)])
    f.arrow([(gx + w, mid + 14), (ex, mid + 14)])
    f.label(450, mid + 14, "allow", size=11)
    f.arrow([(gx + 2 * w // 3, y), (gx + 2 * w // 3, ay + h // 3), (ax, ay + h // 3)])
    f.arrow([(ax, ay + 2 * h // 3), (gx + w // 3, ay + 2 * h // 3), (gx + w // 3, y)], dashed=True)
    f.text(gx + w // 3 - 6, ay + 2 * h // 3 - 8, "금액 수정", size=11, anchor="end", fill=TOKENS["muted"])
    f.text(gx + 2 * w // 3 + 8, y - 40, "needs_approval", size=11, anchor="start", fill=TOKENS["muted"])
    f.arrow([(ax + w, ay + h // 2), (ex + w // 2, ay + h // 2), (ex + w // 2, y)])
    f.text(ex + w // 2 + 8, y - 30, "승인", size=11, anchor="start", fill=TOKENS["muted"])
    f.arrow([(ex + w, mid), (vx, mid)])
    f.arrow([(vx + 120, mid), (endx, mid)])
    f.text(ax + w // 2, ay - 12, "interrupt: 재개하면 노드를 처음부터 다시 돕니다", size=12, weight=600, fill=TOKENS["accent"])
    f.text(ex + w // 2, y + h + 24, "원장에 쓰는 곳은 여기뿐", size=12, weight=600, fill=TOKENS["accent"])
    f.text(vx + 60, y + h + 24, "원장을 다시 읽음", size=12, fill=TOKENS["muted"])
    f.text(40, 300, "gate가 거절이거나 사람이 거절하면 execute를 거치지 않고 끝납니다. 멱등 키는 gate가 정합니다.", size=12, anchor="start", fill=TOKENS["muted"])
    return f


FIGURES = [f1_failure_actions, f2_join_visibility, f3_approval_graph]

if __name__ == "__main__":
    for make in FIGURES:
        svg, png = make().save(OUT)
        print(png.relative_to(OUT.parent))
