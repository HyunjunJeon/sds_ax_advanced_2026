"""업무 문서와 평가 사례를 읽고 조각으로 나눈다. 정답표는 여기서 읽지 않는다."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from rag_lab.settings import ROOT

_COMMON_ENTITY = "공통"


@dataclass(frozen=True)
class Scope:
    entity: str
    as_of: date
    domain: str | None = None


def _scope_json(scope: Scope) -> dict[str, str | None]:
    return {"entity": scope.entity, "as_of": scope.as_of.isoformat(), "domain": scope.domain}


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    source: str
    domain: str
    entity: str
    version: str
    valid_from: date
    valid_until: date | None
    status: str
    owner: str
    family: str | None
    text: str

    def applies(self, scope: Scope) -> bool:
        """승인됨, 고객 일치, 기준일이 유효 기간 안, 도메인 일치를 모두 요구한다. valid_until은 그날 제외다."""
        return (self.status == "approved"
                and self.entity in {scope.entity, _COMMON_ENTITY}
                and self.valid_from <= scope.as_of
                and (self.valid_until is None or scope.as_of < self.valid_until)
                and (scope.domain is None or self.domain == scope.domain))


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    heading: str
    text: str
    start: int       # 원문 문자 위치, 끝 미포함
    end: int
    start_line: int  # 원문 행 번호, 1부터
    end_line: int


def load_corpus() -> dict[str, Document]:
    documents = {}
    for record in json.loads((ROOT / "data/business/catalog.json").read_text(encoding="utf-8")):
        meta = record["metadata"]
        until = meta["valid_until"]
        documents[meta["doc_id"]] = Document(
            doc_id=meta["doc_id"], title=meta["title"], source=meta["source"], domain=meta["domain"],
            entity=meta["entity"], version=meta["version"], valid_from=date.fromisoformat(meta["valid_from"]),
            valid_until=date.fromisoformat(until) if until else None, status=meta["status"],
            owner=meta["owner"], family=meta.get("family"),
            text=(ROOT / record["path"]).read_text(encoding="utf-8"),
        )
    return documents


def load_cases(path: Path | None = None) -> list[dict]:
    lines = (path or ROOT / "data/cases.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _chunk(doc: Document, index: int, start: int, end: int, heading: str) -> Chunk:
    start_line = doc.text.count("\n", 0, start) + 1
    end_line = start_line + doc.text.count("\n", start, max(start, end - 1))
    return Chunk(f"{doc.doc_id}#{index}", doc.doc_id, heading, doc.text[start:end], start, end, start_line, end_line)


def fixed_chunks(doc: Document, size: int = 400, overlap: int = 80) -> list[Chunk]:
    """문자 단위로 자른다. 표를 고려하지 않는 비교 대상이다."""
    if not 0 <= overlap < size:
        raise ValueError("overlap은 0 이상이고 size보다 작아야 합니다.")
    chunks = []
    for start in range(0, len(doc.text), size - overlap):
        end = min(start + size, len(doc.text))
        chunks.append(_chunk(doc, len(chunks), start, end, ""))
        if end == len(doc.text):
            break
    return chunks


def _only_headings(piece: str) -> bool:
    return all(line.startswith("#") or not line.strip() for line in piece.splitlines())


def section_chunks(doc: Document) -> list[Chunk]:
    """`## ` 제목에서 나눈다. 제목만 있는 조각은 다음 절에 붙이고, 절이 커도 표를 나누지 않는다."""
    starts = [0, *(m.start() for m in re.finditer(r"^## ", doc.text, re.MULTILINE) if m.start() > 0)]
    chunks: list[Chunk] = []
    begin = 0
    for start, end in zip(starts, [*starts[1:], len(doc.text)], strict=True):
        if end < len(doc.text) and _only_headings(doc.text[begin:end]):
            continue
        heading = re.match(r"#+ (.+)", doc.text[start:end])
        chunks.append(_chunk(doc, len(chunks), begin, end, heading.group(1) if heading else ""))
        begin = end
    return chunks


def count_cut_tables(doc: Document, chunks: list[Chunk]) -> int:
    """`|`로 시작하는 연속 행을 표 하나로 보고, 전체를 담은 조각이 없는 표의 수를 센다."""
    spans = []
    position = 0
    table_start = None
    for line in doc.text.splitlines(keepends=True):
        if line.startswith("|"):
            table_start = position if table_start is None else table_start
        elif table_start is not None:
            spans.append((table_start, position))
            table_start = None
        position += len(line)
    if table_start is not None:
        spans.append((table_start, position))
    return sum(not any(c.start <= start and end <= c.end for c in chunks) for start, end in spans)
