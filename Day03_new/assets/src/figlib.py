"""Day03_new 노트북 그림 생성 도우미.

diagram-design 스킬의 기본 스킨(색, 노드 모양, 연결선 규칙)을 따라 SVG를 쓰고, macOS의 qlmanage로 PNG를 만든다.
- 색 토큰은 TOKENS 한 곳에만 있다. 스킨을 바꾸려면 여기만 고치고 `make_03a.py`를 다시 돌린다.
- 글꼴은 시스템 글꼴 묶음이다(스킬의 system 글꼴 방식). Hangul은 Apple SD Gothic Neo로 그려진다.
- 연결선은 직각 꺾임(r=8)만 쓴다. 한 변에 여러 선이 붙으면 변의 길이 L을 N+1로 나눈 위치에 따로 붙인다.
- 그림의 숫자는 노트북 코드의 상수나 계산식에서 나온 값만 쓴다. 측정값을 그림에 넣지 않는다.

PNG는 이 폴더 밖의 도구 없이 `uv run python Day03_new/assets/src/make_03a.py`로 다시 만들 수 있다(macOS 전용).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from html import escape
from pathlib import Path

from PIL import Image

TOKENS = {
    "paper": "#f5f5f5", "paper2": "#ececec", "ink": "#2d3142", "muted": "#4f5d75", "soft": "#5a6580",
    "rule": "rgba(45,49,66,0.12)", "rule_solid": "#bfc0c0", "accent": "#bf4520", "accent_tint": "rgba(191,69,32,0.08)", "link": "#2e5aa8",
}
SANS = "'Geist','Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',sans-serif"
MONO = "'Geist Mono','SF Mono',Menlo,monospace"


class Fig:
    """SVG 하나를 쌓는다. 화살표는 먼저 그리고 노드는 나중에 그려서 선이 노드 뒤로 간다."""

    def __init__(self, slug: str, width: int, height: int, title: str, desc: str):
        assert width % 4 == 0 and height % 4 == 0, "viewBox는 4의 배수여야 한다"
        self.slug, self.w, self.h, self.title, self.desc = slug, width, height, title, desc
        self.back: list[str] = []   # 영역, 연결선
        self.front: list[str] = []  # 노드, 글자, 마스크

    # --- 글자 -----------------------------------------------------------------
    def text(self, x, y, s, size=14, weight=500, fill=None, anchor="middle", mono=False, layer="front"):
        family = MONO if mono else SANS
        fill = fill or TOKENS["ink"]
        el = (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
              f'fill="{fill}">{escape(s)}</text>')
        (self.back if layer == "back" else self.front).append(el)

    # --- 노드 -----------------------------------------------------------------
    def node(self, x, y, w, h, name, sub=None, kind="step"):
        stroke, fill, sw = TOKENS["ink"], TOKENS["paper"], 1.5
        if kind == "focal":
            stroke, fill = TOKENS["accent"], TOKENS["accent_tint"]
        elif kind == "store":
            stroke, fill = TOKENS["muted"], TOKENS["paper2"]
        elif kind == "ghost":
            stroke, fill, sw = TOKENS["rule_solid"], TOKENS["paper"], 1
        # 선이 노드 안으로 비치지 않게 불투명 마스크를 먼저 깐다.
        self.front.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{TOKENS["paper"]}"/>')
        self.front.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        if sub:
            self.text(x + w / 2, y + h / 2 - 2, name, size=14, weight=600)
            self.text(x + w / 2, y + h / 2 + 16, sub, size=11, weight=500, fill=TOKENS["soft"], mono=True)
        else:
            self.text(x + w / 2, y + h / 2 + 5, name, size=14, weight=600)

    # --- 일반 도형 ---------------------------------------------------------------
    def rect(self, x, y, w, h, fill="none", stroke=None, sw=1, dashed=False, rx=4, layer="front"):
        stroke_attr = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        el = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{stroke_attr}{dash}/>'
        (self.back if layer == "back" else self.front).append(el)

    def line(self, x0, y0, x1, y1, color=None, sw=1, dashed=False):
        assert x0 == x1 or y0 == y1, "대각선은 쓰지 않는다"
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        self.back.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{color or TOKENS["rule"]}" stroke-width="{sw}"{dash}/>')

    # --- 영역(묶음) -------------------------------------------------------------
    def band(self, x, y, w, h, accent=False, dashed=True):
        stroke = TOKENS["accent"] if accent else TOKENS["rule_solid"]
        fill = TOKENS["accent_tint"] if accent else "none"
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        self.back.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.25"{dash}/>')

    # --- 연결선 -----------------------------------------------------------------
    def arrow(self, pts, kind="default", dashed=False, r=8):
        """pts는 직각 꺾임 경로의 꼭짓점. 마지막 점이 화살촉 끝이다."""
        color = {"default": TOKENS["muted"], "accent": TOKENS["accent"], "link": TOKENS["link"]}[kind]
        marker = {"default": "arr", "accent": "arr-a", "link": "arr-l"}[kind]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            assert x0 == x1 or y0 == y1, f"대각선 연결선은 쓰지 않는다: {(x0, y0)}→{(x1, y1)}"
        d = f"M{pts[0][0]},{pts[0][1]}"
        for i in range(1, len(pts) - 1):
            (px, py), (cx, cy), (nx, ny) = pts[i - 1], pts[i], pts[i + 1]
            rr = min(r, abs(cx - px) + abs(cy - py), abs(nx - cx) + abs(ny - cy))
            bx, by = cx - rr * _sign(cx - px), cy - rr * _sign(cy - py)
            ax, ay = cx + rr * _sign(nx - cx), cy + rr * _sign(ny - cy)
            d += f" L{bx},{by} Q{cx},{cy} {ax},{ay}"
        d += f" L{pts[-1][0]},{pts[-1][1]}"
        dash = ' stroke-dasharray="5,4"' if dashed else ""
        self.back.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{dash} marker-end="url(#{self.slug}-{marker})"/>')

    def label(self, cx, cy, s, size=12, fill=None, weight=500):
        """연결선 위 라벨. 글자 폭만큼 불투명 마스크를 깐다(한글은 글자당 1em)."""
        width = sum(size if ord(ch) > 0x2E80 else size * 0.6 for ch in s) + 12
        width = -(-width // 4) * 4
        self.front.append(f'<rect x="{cx - width / 2}" y="{cy - 10}" width="{width}" height="20" fill="{TOKENS["paper"]}"/>')
        self.text(cx, cy + 4, s, size=size, weight=weight, fill=fill or TOKENS["muted"])

    # --- 출력 -----------------------------------------------------------------
    def svg(self) -> str:
        s = self.slug
        markers = "".join(
            f'<marker id="{s}-{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            for mid, color in [("arr", TOKENS["muted"]), ("arr-a", TOKENS["accent"]), ("arr-l", TOKENS["link"])])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
                f'role="img" aria-labelledby="{s}-title {s}-desc">\n'
                f'<title id="{s}-title">{escape(self.title)}</title>\n<desc id="{s}-desc">{escape(self.desc)}</desc>\n'
                f'<defs>{markers}</defs>\n<rect width="{self.w}" height="{self.h}" fill="{TOKENS["paper"]}"/>\n'
                + "\n".join(self.back) + "\n" + "\n".join(self.front) + "\n</svg>\n")

    def save(self, out_dir: Path, scale: int = 2) -> tuple[Path, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        svg_path = out_dir / f"{self.slug}.svg"
        svg_path.write_text(self.svg(), encoding="utf-8")
        return svg_path, render_png(svg_path, out_dir / f"{self.slug}.png", self.w, self.h, scale)


def _sign(v: float) -> int:
    return (v > 0) - (v < 0)


def render_png(svg_path: Path, png_path: Path, w: int, h: int, scale: int = 2) -> Path:
    """qlmanage는 정사각 캔버스에 그림을 왼쪽 위부터 그린다. 그림 영역만 잘라 불투명 PNG로 저장한다."""
    if not shutil.which("qlmanage"):
        raise RuntimeError("qlmanage가 없습니다. 이 도우미는 macOS에서만 PNG를 만듭니다.")
    # qlmanage는 가로세로가 다른 SVG에서 배율이 흔들린다(시험: 960x416을 s=1920으로 그리면 2.5배). 정사각 캔버스로 감싸면 배율이 정확히 s/N이다.
    n = max(w, h)
    body = svg_path.read_text(encoding="utf-8")
    wrapper = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="{n}" height="{n}">'
               f'<rect width="{n}" height="{n}" fill="#ffffff"/><svg x="0" y="0" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
               f'{body.split("?>", 1)[-1]}</svg></svg>')
    with tempfile.TemporaryDirectory() as tmp:
        wrapped = Path(tmp) / "wrapped.svg"
        wrapped.write_text(wrapper, encoding="utf-8")
        subprocess.run(["qlmanage", "-t", "-s", str(n * scale), "-o", tmp, str(wrapped)], check=True, capture_output=True)
        raw = Path(tmp) / "wrapped.svg.png"
        with Image.open(raw) as image:
            image.convert("RGB").crop((0, 0, w * scale, h * scale)).save(png_path, optimize=True)
    return png_path
