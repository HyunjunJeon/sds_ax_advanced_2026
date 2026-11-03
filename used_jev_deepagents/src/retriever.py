"""로컬 코퍼스를 읽고 BM25 숏리스트를 만든다.

임베딩 없이 영문 단어와 한글 글자 바이그램으로 색인한다.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi

from src.schemas import Passage


def tokenize(text: str) -> list[str]:
    """영문 단어와 한글 글자 바이그램으로 나눈다."""
    pieces = re.findall(r"[a-zA-Z0-9]+|[가-힣]+", text.lower())
    tokens: list[str] = []
    for piece in pieces:
        tokens.append(piece)
        # 공백 없는 한글은 어절만으로는 매칭이 약해서 글자 쌍을 더한다.
        if re.fullmatch(r"[가-힣]{2,}", piece):
            tokens.extend(
                piece[index : index + 2] for index in range(len(piece) - 1)
            )
    return tokens


class CorpusIndex:
    """청크된 마크다운 파일의 인메모리 BM25 색인."""

    def __init__(self, corpus_dir: Path) -> None:
        self.passages = load_corpus(corpus_dir)
        self._bm25 = BM25Okapi([tokenize(item.text) for item in self.passages])

    def search(self, query: str, k: int = 8) -> list[Passage]:
        """``query``에 대한 상위 k개 패시지를 돌려준다."""
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(
            zip(scores, self.passages, strict=True),
            key=lambda pair: (-float(pair[0]), pair[1].doc_id),
        )
        hits: list[Passage] = []
        for score, passage in ranked[:k]:
            hits.append(
                Passage(
                    doc_id=passage.doc_id,
                    title=passage.title,
                    source=passage.source,
                    source_type=passage.source_type,
                    text=passage.text,
                    bm25=round(float(score), 4),
                )
            )
        return hits


def load_corpus(corpus_dir: Path) -> list[Passage]:
    """``corpus_dir``의 마크다운을 패시지로 쪼갠다."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    passages: list[Passage] = []
    for path in sorted(corpus_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        source_type = _source_type(path.name, raw)
        title = _first_heading(raw) or path.stem
        for index, chunk in enumerate(splitter.split_text(raw), start=1):
            passages.append(
                Passage(
                    doc_id=f"{path.stem}-{index:02d}",
                    title=title,
                    source=f"corpus/{path.name}",
                    source_type=source_type,
                    text=chunk.strip(),
                )
            )
    if not passages:
        raise RuntimeError(f"코퍼스가 비어 있습니다: {corpus_dir}")
    return passages


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _source_type(filename: str, text: str) -> str:
    # 시연용 포럼 주입 문서는 공식 문서로 취급하지 않는다.
    if "injection" in filename or "Ignore all previous" in text:
        return "community_forum"
    if filename.startswith("sds-"):
        return "internal_policy"
    return "official_documentation"
