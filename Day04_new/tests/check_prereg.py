"""DESIGN.md의 사전 등록 절(PREREG 블록)이 기록된 sha256과 같은지 확인한다.

종료 코드: 0 일치, 1 불일치(절이 바뀜), 2 확인 불가(파일 또는 표식 없음).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

BEGIN = "<!-- PREREG:BEGIN -->\n"
END = "<!-- PREREG:END -->"
DOCS = Path(__file__).resolve().parent.parent / "docs"


def main() -> int:
    parser = argparse.ArgumentParser(description="사전 등록 절의 sha256을 기록과 대조한다.")
    parser.add_argument("--design", type=Path, default=DOCS / "DESIGN.md")
    parser.add_argument("--hash", type=Path, default=DOCS / "prereg.sha256")
    args = parser.parse_args()

    try:
        text = args.design.read_text(encoding="utf-8")
        expected = args.hash.read_text(encoding="utf-8").strip()
    except OSError as error:
        print(f"확인 불가: 파일을 읽을 수 없습니다 ({error})")
        return 2
    if BEGIN not in text:
        print(f"확인 불가: 시작 표식 {BEGIN.strip()} 이 없습니다")
        return 2
    tail = text.split(BEGIN, 1)[1]
    if END not in tail:
        print(f"확인 불가: 끝 표식 {END} 이 없습니다")
        return 2
    block = tail.split(END, 1)[0]
    actual = hashlib.sha256(block.encode("utf-8")).hexdigest()
    if actual != expected:
        print(f"사전 등록 절이 바뀌었습니다 (기록 {expected}, 현재 {actual})")
        return 1
    print(f"사전 등록 일치: {actual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
