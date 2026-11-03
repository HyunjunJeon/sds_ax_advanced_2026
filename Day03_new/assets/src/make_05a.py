"""05a 노트북의 그림을 만든다. 저장소 루트에서: uv run --no-sync python Day03_new/assets/src/make_05a.py

그림의 근거 (05a-Single-First.ipynb)
- f1: 1절 표의 네 칸(정보가 부족함, 도구를 잘못 고름, Context가 너무 큼, 단계 의존성이 강함)과 `먼저 점검할 것`, `분리를 검토할 근거` 열.
      같은 절의 `DIAGNOSIS` 주석이 말하는 두 칸(자동 검사 문제, 실패 아님)도 함께 둔다.
- f2: 3절의 Persona와 Context 분리 실험. 마지막 셀의 `같은 Desk`, `같은 원장` 열과 `ROLE_TOOLS`.
- f3: 4절 마지막 판단표(절차 재사용, Context 분리, 도구·권한 분리, 병렬 필요 × Skill, SubAgent, 코드).
측정값은 쓰지 않는다.
"""
from __future__ import annotations

from pathlib import Path

from figlib import TOKENS, Fig

OUT = Path(__file__).resolve().parents[1]


def f1_failure_first() -> Fig:
    f = Fig("05a-1-failure-first", 960, 396, "나누기 전에 Single의 실패를 분류하는 순서",
            "Single 실행의 자동 검사와 신호표를 읽어 실패를 네 칸(정보 부족, 도구 선택, Context 크기, 단계 의존성)과 자동 검사 문제, 실패 아님으로 분류하고, 먼저 점검할 것을 고친 뒤에도 남는 실패와 비용만 분리의 근거로 삼는다.")
    f.node(40, 148, 160, 72, "Single 실행", "네 사례, 각 1회")
    f.node(280, 148, 160, 72, "표 두 개 읽기", "자동 검사 · 신호표")
    f.arrow([(200, 184), (280, 184)])
    rows = [("정보가 부족함", "검색어, 코퍼스, not_found 처리"), ("도구를 잘못 고름", "도구 설명, 프롬프트 지침"),
            ("Context가 너무 큼", "도구 결과 크기, 필요한 원문만 읽기"), ("단계 의존성이 강함", "코드로 순서 고정(03의 순차)")]
    x1, y0, h, step = 520, 40, 48, 64
    att = [148 + 18 + 12 * k for k in range(4)]  # 표 노드 오른쪽 변에 선 넷
    f.text(x1, y0 - 12, "점검할 칸 → 먼저 점검할 것", size=12, anchor="start", weight=600, fill=TOKENS["muted"])
    for k, (name, sub) in enumerate(rows):
        y = y0 + k * step
        mid = y + h // 2
        xg = 480
        f.arrow([(440, att[k]), (xg, att[k]), (xg, mid), (x1, mid)])
        f.node(x1, y, 200, h, name)
        f.text(x1 + 216, mid + 4, sub, size=12, anchor="start", fill=TOKENS["muted"])
    f.arrow([(360, 220), (360, 316), (520, 316)])
    f.node(520, 292, 200, 48, "자동 검사 문제 · 실패 아님", kind="ghost")
    f.text(736, 320, "이 두 칸은 분리의 근거가 아닙니다", size=12, anchor="start", fill=TOKENS["muted"])
    f.text(40, 380, "먼저 점검할 것을 고친 뒤에도 남는 실패나 비용이 분리를 검토할 근거입니다. 단계 의존성은 대개 근거가 못 됩니다.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f2_persona_vs_context() -> Fig:
    f = Fig("05a-2-persona-vs-context", 960, 372, "역할 이름만 다른 Worker와 도구 범위가 다른 Worker",
            "위쪽 Persona는 이름만 다른 Worker 셋이 모든 도구를 보고 같은 Desk와 원장에 닿는다. 아래쪽 Context 분리는 ROLE_TOOLS로 Worker마다 보이는 도구가 다르지만 같은 Desk와 원장에 닿는 점은 같아서 보안 격리는 아니다.")
    lanes = [("Persona: 이름만 다름", 56, ["결제 담당", "규정 담당", "장애 담당"], "모든 도구가 보임", False),
             ("Context 분리: 도구 범위가 다름", 204, ["billing", "policy", "outage"], "ROLE_TOOLS로 보이는 도구만", True)]
    for title, y, names, tool_text, good in lanes:
        f.text(40, y - 16, title, size=13, weight=600, anchor="start", fill=TOKENS["ink"] if good else TOKENS["accent"])
        for k, name in enumerate(names):
            f.node(40 + k * 148, y, 128, 56, name, "Worker")
        xt = 520
        mid = y + 28
        f.arrow([(40 + 2 * 148 + 128, mid), (xt, mid)], kind="default" if good else "accent")
        f.node(xt, y, 176, 56, "도구", tool_text, kind="step" if good else "focal")
        f.arrow([(xt + 176, mid), (760, mid)])
        f.node(760, y, 160, 56, "같은 Desk, 같은 원장", kind="store")
    f.text(40, 330, "줄어드는 것은 보이는 도구와 넘기는 Context입니다. 두 경우 모두 같은 프로세스의 같은 객체에 닿으므로 Context 분리는 보안 격리가 아닙니다.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f3_skill_subagent() -> Fig:
    f = Fig("05a-3-skill-subagent", 960, 340, "Skill, SubAgent, 코드의 판단 기준",
            "절차 재사용, Context 분리, 도구·권한 분리, 병렬 필요라는 네 기준에서 Skill, SubAgent, 코드가 각각 어떻게 다른지 비교한 판단표.")
    cols = ["Skill", "SubAgent", "코드"]
    rows = [("절차 재사용", ["적합", "가능하지만 과함", "판단 없는 절차는 코드"]),
            ("Context 분리", ["없음", "있음", "해당 없음"]),
            ("도구·권한 분리", ["없음", "Worker마다 허용 목록", "게이트처럼 강제"]),
            ("병렬 필요", ["없음", "task 여러 개로 가능", "Send로 코드가 정함"])]
    x0, cw, rh, top = 224, 232, 48, 64
    for k, c in enumerate(cols):
        f.text(x0 + k * cw + cw / 2, 44, c, size=13, weight=600, fill=TOKENS["muted"])
    for r, (name, cells) in enumerate(rows):
        y = top + r * (rh + 8)
        f.text(40, y + rh / 2 + 5, name, size=13, weight=600, anchor="start")
        for k, val in enumerate(cells):
            f.rect(x0 + k * cw + 4, y, cw - 8, rh, fill=TOKENS["paper"], stroke=TOKENS["rule_solid"], sw=1, rx=4)
            f.text(x0 + k * cw + cw / 2, y + rh / 2 + 5, val, size=13)
    f.text(40, 324, "기준을 정리한 표입니다. 위 실행 표의 수치가 어느 칸을 뒷받침하는지는 직접 대조하세요.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


FIGURES = [f1_failure_first, f2_persona_vs_context, f3_skill_subagent]

if __name__ == "__main__":
    for make in FIGURES:
        svg, png = make().save(OUT)
        print(png.relative_to(OUT.parent))
