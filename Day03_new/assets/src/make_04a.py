"""04a 노트북의 그림을 만든다. 저장소 루트에서: uv run --no-sync python Day03_new/assets/src/make_04a.py

그림의 근거 (04a-Graph-Contracts-Budget.ipynb)
- f1: 3절 "실패 재현" 셀의 표. 네 결과는 그 셀의 `bad_results`이고, 거절한 층은 같은 셀의 `거절한 층` 열과 같다
      (없는 status는 Pydantic 스키마, 없는 근거 ID와 근거 없는 complete는 validate_result, 틀린 사실은 어느 층도 거절하지 않음).
- f2: 3절 `payloads`의 세 전달물과 `trim_payload`의 줄이는 순서(원문, 그다음 사실. 근거 참조와 불확실성은 끝까지 남김).
- f3: 4절 `Budget(max_model_calls=5)`와 `consumer`(스레드 3개, 시도 3번). 허용 건수가 한도와 같아야 한다.
측정값은 쓰지 않는다.
"""
from __future__ import annotations

from pathlib import Path

from figlib import TOKENS, Fig

OUT = Path(__file__).resolve().parents[1]


def f1_check_layers() -> Fig:
    f = Fig("04a-1-check-layers", 960, 392, "잘못된 Worker 결과를 거르는 층",
            "네 가지 잘못된 결과가 Pydantic 스키마, validate_result 근거 검증을 차례로 지난다. 없는 status는 스키마가, 없는 근거 ID와 근거 없는 complete는 근거 검증이 거절하고, 틀린 사실은 어느 층도 거절하지 않는다.")
    heads = [(288, 170, "Pydantic 스키마"), (506, 170, "validate_result"), (724, 170, "다음 단계로")]
    f.text(40, 36, "잘못된 결과", size=13, weight=600, anchor="start")
    for x, w, name in heads:
        f.text(x + w / 2, 36, name, size=13, weight=600, fill=TOKENS["muted"])
    rows = [("없는 status", "status가 \"done\"", 0), ("없는 근거 ID", "\"lookup_outage: 8월 장애\"", 1),
            ("근거 없는 complete", "evidence_refs가 비어 있음", 1), ("실제 근거에 틀린 사실", "근거 ID는 진짜, 사실이 틀림", 2)]
    h, step, top = 48, 76, 60
    for k, (name, sub, stop) in enumerate(rows):
        y = top + k * step
        mid = y + h // 2
        f.node(40, y, 200, h, name)
        f.text(40, y + h + 16, sub, size=11, anchor="start", fill=TOKENS["soft"])
        xs = [x for x, _, _ in heads]
        ws = [w for _, w, _ in heads]
        f.arrow([(240, mid), (xs[0], mid)])
        for s in range(2):
            if s < stop or (stop == 2):
                f.arrow([(xs[s] + ws[s], mid), (xs[s + 1], mid)])
        for s in range(3):
            if s < stop:
                f.node(xs[s], y, ws[s], h, "통과", kind="ghost")
            elif s == stop and stop < 2:
                f.node(xs[s], y, ws[s], h, "여기서 거절", kind="focal")
            elif s == 2 and stop == 2:
                f.node(xs[s], y, ws[s], h, "거절 없이 통과", kind="focal")
            else:
                f.node(xs[s], y, ws[s], h, "도달하지 않음", kind="ghost")
    f.text(40, 376, "근거 검증은 인용이 이번 실행에 있었는지를 봅니다. 문장이 근거와 뜻이 같은지는 사람이 원문과 대조합니다.", size=12, anchor="start", weight=600, fill=TOKENS["accent"])
    return f


def f2_payload_fields() -> Fig:
    f = Fig("04a-2-payload-fields", 960, 384, "전달물 세 가지에 들어가는 칸",
            "1줄 요약은 첫 사실만 담고, 사실+근거+불확실성은 status, facts, evidence_refs, uncertainty, error를 담고, 원문 포함은 거기에 quotes를 더한다. 줄일 때는 quotes, facts 순으로 빼고 evidence_refs와 uncertainty는 끝까지 남긴다.")
    cols = ["status", "facts", "evidence_refs", "uncertainty", "error", "quotes"]
    x0, cw, rh, top = 248, 112, 52, 72
    f.text(40, 52, "전달물", size=13, weight=600, anchor="start")
    for k, c in enumerate(cols):
        f.text(x0 + k * cw + cw / 2, 52, c, size=12, weight=600, fill=TOKENS["muted"], mono=True)
    rows = [("1줄 요약", ["빠짐", "첫 사실만", "빠짐", "빠짐", "빠짐", "빠짐"]),
            ("사실+근거+불확실성", ["있음", "있음", "있음", "있음", "있음", "빠짐"]),
            ("원문 포함", ["있음"] * 6)]
    for r, (name, cells) in enumerate(rows):
        y = top + r * (rh + 8)
        f.text(40, y + rh / 2 + 5, name, size=14, weight=600, anchor="start")
        for k, val in enumerate(cells):
            on = val != "빠짐"
            f.rect(x0 + k * cw + 4, y, cw - 8, rh, fill=TOKENS["accent_tint"] if on else TOKENS["paper"],
                   stroke=TOKENS["accent"] if on else TOKENS["rule_solid"], sw=1.25 if on else 1, rx=4)
            f.text(x0 + k * cw + cw / 2, y + rh / 2 + 5, val, size=13, weight=600 if on else 500,
                   fill=TOKENS["ink"] if on else TOKENS["soft"])
    # 줄이는 순서
    y = 276
    f.line(40, y - 24, 920, y - 24, color=TOKENS["rule_solid"])
    f.text(40, y, "trim_payload가 예산에 맞춰 줄이는 순서", size=13, weight=600, anchor="start")
    w, h, yy = 168, 48, y + 24
    f.node(40, yy, w, h, "① 원문 빼기", "quotes")
    f.node(40 + w + 56, yy, w, h, "② 사실 빼기", "facts")
    f.node(40 + 2 * (w + 56), yy, 2 * w // 1 - 40, h, "끝까지 남김", "evidence_refs, uncertainty", kind="focal")
    f.arrow([(40 + w, yy + h // 2), (40 + w + 56, yy + h // 2)])
    f.arrow([(40 + 2 * w + 56, yy + h // 2), (40 + 2 * (w + 56), yy + h // 2)])
    f.text(40, yy + h + 22, "항목 단위로 빼고, 뺀 항목을 dropped에 기록합니다. 바이트에서 그냥 자르면 예외 문장이 사라집니다.", size=12, anchor="start", fill=TOKENS["muted"])
    return f


def f3_shared_budget() -> Fig:
    f = Fig("04a-3-shared-budget", 960, 308, "Worker 셋이 공유하는 하나의 예산",
            "billing, policy, outage 스레드가 각자 consume을 부르면 잠금이 있는 Budget 카운터 하나가 세고, 한도 안이면 허용하고 한도를 넘으면 BudgetExceeded를 낸다.")
    w, h = 160, 48
    ys = [48, 120, 192]
    bx, bw, bh = 400, 200, 96
    by = 120 + h // 2 - bh // 2
    # Budget 왼쪽 변: 선 셋 (변 길이 96을 4로 나눈 24, 48, 72)
    att = [by + 24, by + 48, by + 72]
    for y, a, name in zip(ys, att, ["billing", "policy", "outage"]):
        f.node(40, y, w, h, name, "스레드")
        mid = y + h // 2
        if mid == a:
            f.arrow([(200, mid), (bx, mid)])
        else:
            f.arrow([(200, mid), (300, mid), (300, a), (bx, a)])
    f.node(bx, by, bw, bh, "Budget", "max_model_calls=5", kind="focal")
    f.text(bx + bw / 2, by - 12, "잠금이 있는 카운터 하나", size=12, weight=600, fill=TOKENS["accent"])
    ox = 720
    f.arrow([(bx + bw, by + 24), (ox, by + 24)])
    f.arrow([(bx + bw, by + 72), (ox, by + 72)])
    f.node(ox, by + 2, 200, 44, "허용", "한도 이하")
    f.node(ox, by + 50, 200, 44, "BudgetExceeded", "한도 초과", kind="ghost")
    f.text(40, 284, "스레드 3개가 각각 3번씩 시도하고 한도는 5입니다. 허용 건수는 한도와 같아야 합니다.", size=12, anchor="start", fill=TOKENS["muted"])
    return f


FIGURES = [f1_check_layers, f2_payload_fields, f3_shared_budget]

if __name__ == "__main__":
    for make in FIGURES:
        svg, png = make().save(OUT)
        print(png.relative_to(OUT.parent))
