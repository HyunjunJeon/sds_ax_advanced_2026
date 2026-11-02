"""노트북 04용 표본 PDF를 만든다: 글자층이 없고 막대 차트가 이미지로만 들어 있는 한 쪽짜리 PDF.

수치는 채점 자료(data/business)와 무관하게 지어낸 예시다. 실행: uv run --no-sync python Day02_new/benchmarks/make_sample_pdf.py
"""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib
import pymupdf
from matplotlib import font_manager, pyplot

matplotlib.use("Agg")

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "pdf" / "credit-trend-chart.pdf"
FONT_CANDIDATES = (
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)
TITLE = "분기별 서비스 크레딧 신청 건수(예시 자료)"
COUNTS = {"Q1": 12, "Q2": 18, "Q3": 9, "Q4": 21}


def find_font() -> str:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit(f"한글 글꼴이 없습니다. 다음 중 하나가 필요합니다: {FONT_CANDIDATES}")


def render_chart_png(font_path: str) -> bytes:
    font_manager.fontManager.addfont(font_path)
    family = font_manager.FontProperties(fname=font_path).get_name()
    pyplot.rcParams["font.family"] = family
    figure, axes = pyplot.subplots(figsize=(7, 4.5), dpi=150)
    bars = axes.bar(list(COUNTS), list(COUNTS.values()), color="#4472c4")
    axes.bar_label(bars)
    axes.set_title(TITLE)
    axes.set_xlabel("분기")
    axes.set_ylabel("신청 건수(건)")
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png")
    pyplot.close(figure)
    return buffer.getvalue()


def main() -> None:
    png = render_chart_png(find_font())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as document:
        page = document.new_page(width=595, height=842)
        page.insert_image(pymupdf.Rect(40, 100, 555, 100 + 515 * 4.5 / 7), stream=png)
        document.save(OUTPUT, deflate=True)
    print(f"{OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
