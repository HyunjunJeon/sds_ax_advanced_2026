"""코퍼스 선택과 원문 스냅샷 무결성. 평가 정답은 이 모듈에서 읽지 않는다.

공개일은 해당 릴리스의 문서를 알 수 있게 된 날이고, 수집일은 파일을 받은 날이다.
해시는 저장한 바이트를 확인할 뿐 내용의 사실성이나 사람의 검수를 보증하지 않는다.
Day03의 vendor/day02에도 같은 파일을 동봉한다.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"코퍼스 경로는 지정된 폴더 내부의 실제 파일이어야 합니다: {relative}")
    return path


@dataclass(frozen=True)
class Corpus:
    root: Path
    name: str

    @property
    def directory(self) -> Path:
        return self.root / "data" / self.name

    @property
    def catalog_path(self) -> Path:
        return self.directory / "catalog.json"

    @property
    def cases_path(self) -> Path:
        return (self.root / "data" if self.name == "business" else self.directory) / "cases.jsonl"

    @property
    def gold_path(self) -> Path:
        # 평가기가 실행 종료 후 읽을 경로만 제공한다.
        return (self.root / "data" if self.name == "business" else self.directory) / "gold.jsonl"

    def catalog(self) -> list[dict]:
        records = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        if not records:
            raise ValueError("빈 코퍼스입니다.")
        ids = [r["metadata"]["doc_id"] for r in records]
        if len(ids) != len(set(ids)):
            raise ValueError("코퍼스 doc_id가 중복됩니다.")
        for record in records:
            inside(self.root, record["path"])
        if self.name != "business":
            self.verify_snapshot(records)
        return records

    def verify_snapshot(self, records: list[dict]) -> dict:
        manifest = json.loads((self.directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest["schema_version"] != 1 or manifest["corpus"] != self.name:
            raise ValueError("코퍼스 manifest의 형식/이름이 다릅니다.")
        cutoff = date.fromisoformat(manifest["as_of"])
        if sha256(self.catalog_path) != manifest["catalog_sha256"]:
            raise ValueError("코퍼스 catalog 해시가 다릅니다.")
        sources = {}
        for source in manifest["sources"]:
            if source["id"] in sources:
                raise ValueError("원문 ID가 중복됩니다.")
            if date.fromisoformat(source["published_at"][:10]) > cutoff:
                raise ValueError("기준일 뒤의 원문이 포함되어 있습니다.")
            datetime.fromisoformat(source["retrieved_at"].replace("Z", "+00:00"))
            path = inside(self.directory, source["path"])
            if sha256(path) != source["sha256"]:
                raise ValueError(f"원문 해시가 다릅니다: {source['id']}")
            sources[source["id"]] = (source, path)
        documents = {d["doc_id"]: d for d in manifest["documents"]}
        if len(documents) != len(manifest["documents"]) or set(documents) != {
            r["metadata"]["doc_id"] for r in records
        }:
            raise ValueError("manifest와 catalog의 문서 집합이 다릅니다.")
        for record in records:
            meta = record["metadata"]
            doc = documents[meta["doc_id"]]
            source, raw_path = sources[doc["source_id"]]
            path = inside(self.root, record["path"])
            expected_path = inside(self.directory, doc["path"])
            if path != expected_path or sha256(path) != doc["sha256"]:
                raise ValueError(f"발췌 문서 해시/경로가 다릅니다: {meta['doc_id']}")
            lines = raw_path.read_bytes().splitlines(keepends=True)
            start, end = doc["start_line"], doc["end_line"]
            if not 1 <= start <= end <= len(lines):
                raise ValueError("원문 행 범위가 잘못되었습니다.")
            if b"".join(lines[start - 1:end]) != path.read_bytes():
                raise ValueError("발췌가 원문 행 범위와 일치하지 않습니다.")
            published = date.fromisoformat(doc["published_at"][:10])
            if published > cutoff or meta["valid_from"] != published.isoformat():
                raise ValueError("문서 공개일/기준일 메타데이터가 다릅니다.")
            if meta["source"] != source["url"] or meta.get("source_sha256") != source["sha256"]:
                raise ValueError("원문 출처 메타데이터가 다릅니다.")
        return manifest

    def provenance(self) -> dict:
        records = self.catalog()
        result = {
            "name": self.name,
            "catalog_sha256": sha256(self.catalog_path),
            "documents": {r["metadata"]["doc_id"]: sha256(inside(self.root, r["path"])) for r in records},
        }
        manifest = self.directory / "manifest.json"
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            result.update(as_of=data["as_of"], manifest_sha256=sha256(manifest))
        return result


def load_corpus(root: Path, name: str = "business") -> Corpus:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise ValueError("코퍼스 이름은 영문 소문자·숫자·하이픈만 사용하세요.")
    corpus = Corpus(Path(root).resolve(), name)
    corpus.catalog()
    return corpus
