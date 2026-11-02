"""근거 대장이 블로그 문장을 옮겨 적지 않았는지 검사한다 (표준 라이브러리만 사용).

사용법:
    python Day07_new/tests/check_sources.py --blog <blog.txt> <파일> [<파일> ...]

종료 코드: 0 = 발견 없음, 1 = 발견 있음(한 줄에 하나), 2 = 입력 오류(블로그나 대상 파일이
없음, 블로그가 비어 있음). 입력이 없는 상태가 통과처럼 보이지 않게 하려고 2를 따로 둔다.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

RUN_LIMIT = 40  # 이 길이를 넘는 연속 일치는 옮겨 적은 것으로 본다
SENTENCE_MIN = 15  # 이 길이 이상인 조각만 문장으로 비교한다
SIMILARITY = 0.80
MIN_HANGUL = 5  # 한글이 이보다 적은 조각은 산문이 아니라 코드로 본다
BLOG_COLUMN = "블로그 절"
MASK = "\x00"  # 제외한 부분을 지운 자리. 이 글자를 건너는 일치는 만들어지지 않는다

# 제외는 이 목록과 한글 5자 미만 조각, '블로그 절' 열뿐이다.
ALLOWED_RUNS = (
    "Inside vLLM: 서버 시작부터 KV cache까지 소스 코드 톺아보기",
    "5. 멀티턴 대화: prefix caching을 통한 이전 턴 KV 재사용",
    "shape은 [num_blocks, num_kv_heads, block_size, 2 * head_size]",
    "* block_size * num_kv_heads * head_size * dtype 크기",
    "VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS",
    "SchedulerOutput.scheduled_spec_decode_tokens",
    "WAITING_FOR_STRUCTURED_OUTPUT_GRAMMAR",
    "EAGLE3와 MTP는 0, draft model은 1, DFlash는 K",
)

_HANGUL = re.compile(r"[가-힣]")
_PIECE_SPLIT = re.compile(r"[.|\n]")
_PIECE_KEEP_DELIMITERS = re.compile(r"([.|])")


class InputError(Exception):
    """블로그나 대상 파일을 읽을 수 없을 때."""


def normalize(text: str) -> str:
    return " ".join(text.replace("`", "").split())


def split_pieces(text: str) -> list[str]:
    """'.', '|', 줄바꿈으로 자른 뒤 15자 이상인 조각만 남긴다."""
    pieces = (normalize(p) for p in _PIECE_SPLIT.split(text))
    return [p for p in pieces if len(p) >= SENTENCE_MIN]


def mask_allowed(text: str) -> str:
    for allowed in ALLOWED_RUNS:
        text = text.replace(allowed, MASK)
    return text


def read_text(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"읽을 수 없는 파일: {path} ({exc.strerror})") from exc
    except UnicodeDecodeError as exc:
        raise InputError(f"UTF-8이 아닌 파일: {path}") from exc
    if path.suffix != ".ipynb":
        return raw
    try:
        cells = json.loads(raw)["cells"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise InputError(f"노트북 형식이 아님: {path}") from exc
    sources = (
        c["source"] if isinstance(c["source"], str) else "".join(c["source"])
        for c in cells
        if c.get("cell_type") == "markdown"
    )
    return "\n".join(sources)


def _cells(line: str) -> list[str]:
    return line.strip().strip("|").split("|")


def target_lines(text: str) -> list[tuple[int, str]]:
    """(줄 번호, 검사할 글) 목록. '블로그 절' 열의 칸은 지워서 돌려준다."""
    result: list[tuple[int, str]] = []
    skip_column: int | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            skip_column = None
            result.append((number, line))
            continue
        cells = _cells(line)
        names = [c.strip() for c in cells]
        if BLOG_COLUMN in names:
            skip_column = names.index(BLOG_COLUMN)
        elif skip_column is not None and skip_column < len(cells):
            cells[skip_column] = MASK
        result.append((number, "|".join(cells)))
    return result


def mask_code_pieces(line: str) -> str:
    """한글이 5자 미만인 조각(코드)을 지운다. 구분자('.', '|')는 그대로 둔다."""
    parts = _PIECE_KEEP_DELIMITERS.split(line)
    return "".join(
        part if part in (".", "|") or len(_HANGUL.findall(part)) >= MIN_HANGUL else MASK
        for part in parts
    )


def longest_run(line: str, blog_grams: set[str]) -> int:
    """line과 블로그가 공유하는 가장 긴 연속 부분 문자열의 길이.

    41자 창 하나가 블로그에 있으면 40자 초과 일치다. 그 창을 양쪽으로 넓혀 길이를 잰다.
    """
    width = RUN_LIMIT + 1
    best = 0
    for start in range(len(line) - width + 1):
        if line[start : start + width] in blog_grams:
            best = max(best, width)
    return best


def check(blog_text: str, targets: list[Path]) -> list[str]:
    blog = normalize(blog_text)
    width = RUN_LIMIT + 1
    blog_grams = {blog[i : i + width] for i in range(len(blog) - width + 1)}
    blog_sentences = sorted(set(split_pieces(blog_text)))
    matcher = difflib.SequenceMatcher(autojunk=False)
    findings: list[str] = []
    for path in targets:
        for number, raw_line in target_lines(read_text(path)):
            shown = normalize(raw_line)
            # 백틱을 걷어낸 뒤에야 허용 목록과 맞는다
            line = mask_code_pieces(mask_allowed(shown))
            run = longest_run(line, blog_grams)
            if run:
                findings.append(f"{path}:{number} run>{RUN_LIMIT} {shown}")
                continue
            for piece in split_pieces(line):
                ratio = best_ratio(matcher, piece, blog_sentences)
                if ratio >= SIMILARITY:
                    findings.append(f"{path}:{number} ratio={ratio:.2f} {piece}")
                    break
    return findings


def best_ratio(matcher: difflib.SequenceMatcher, piece: str, blog_sentences: list[str]) -> float:
    matcher.set_seq2(piece)  # seq2 통계를 한 번만 계산해 재사용한다
    best = 0.0
    for sentence in blog_sentences:
        matcher.set_seq1(sentence)
        if matcher.real_quick_ratio() < SIMILARITY or matcher.quick_ratio() < SIMILARITY:
            continue
        best = max(best, matcher.ratio())
    return best


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="근거 대장이 블로그 문장을 옮겼는지 검사한다.")
    parser.add_argument("--blog", required=True, type=Path, help="블로그 본문 텍스트 파일")
    parser.add_argument("files", nargs="+", type=Path, help="검사할 .md 또는 .ipynb 파일")
    args = parser.parse_args(argv)
    try:
        for path in args.files:
            if path.suffix not in (".md", ".ipynb"):
                raise InputError(f"지원하지 않는 확장자: {path}")
        blog_text = read_text(args.blog)
        if not normalize(blog_text):
            raise InputError(f"블로그 본문이 비어 있음: {args.blog}")
        findings = check(blog_text, args.files)
    except InputError as exc:
        print(f"입력 오류: {exc}", file=sys.stderr)
        return 2
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
