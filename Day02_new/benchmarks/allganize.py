"""올거나이즈 RAG-Evaluation-Dataset-KO를 받아 검색 측정에 쓰는 도구. 수업 노트북은 이 모듈을 쓰지 않는다.

문항 CSV는 MIT 라이선스이지만 PDF는 각 기관 원본이라 저장소에 넣지 않고 원본 위치에서 받는다.
받은 PDF는 documents.csv의 페이지 수와 같을 때만 인정하고, 못 받은 파일과 그 문항 수를 숨기지 않는다.

    uv run --no-sync python Day02_new/benchmarks/allganize.py fetch
    uv run --no-sync python Day02_new/benchmarks/allganize.py status
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
import urllib.parse as up
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import httpx
import pymupdf

_REVISION = "35db50ff8739d78b11ee68b6f4ef04a95862a504"
_DATASET = f"https://huggingface.co/datasets/allganize/RAG-Evaluation-Dataset-KO/resolve/{_REVISION}/"
_COURT_DOWNLOAD = "https://file.scourt.go.kr//AttachDownload"  # 대법원 게시판의 다운로드 버튼이 보내는 양식
_ATTACHMENT = re.compile(r'''href=["']([^"']*(?:\.pdf|down\.do|download|filedown|getfile)[^"']*)["']''', re.I)
_COURT_LINK = re.compile(r"javascript:download\('([^']+\.pdf)','([^']*)'\)", re.I)
_MAX_ATTACHMENTS = 15
_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36"

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent / "outputs" / "benchmarks" / "allganize"
PINNED = HERE / "allganize_pinned.json"  # 측정에 쓴 PDF의 파일별 sha256


@dataclass(frozen=True)
class Page:
    file: str
    page_no: int  # 1부터. 정답표의 target_page_no와 같은 기준이다.
    text: str


@dataclass(frozen=True)
class Case:
    case_id: str
    domain: str
    question: str
    answer: str
    file: str
    page_no: int
    context_type: str
    split: str  # tune은 조정용, hold는 구성을 고정한 뒤 한 번만 읽는다.


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _pdf_path(root: Path, file: str) -> Path:
    return root / "pdf" / Path(file.replace("/", "_")).name  # CSV의 이름이 폴더 밖을 가리키지 못하게 한다.


def _page_count(data: bytes) -> int | None:
    if data[:5] != b"%PDF-":
        return None
    try:
        return pymupdf.open(stream=data, filetype="pdf").page_count
    except (pymupdf.FileDataError, ValueError):
        return None


def _get(client: httpx.Client, url: str, **params) -> httpx.Response | None:
    """한 경로의 시간 초과가 다음 경로를 막지 않게 네트워크 실패를 None으로 돌려준다."""
    try:
        return client.get(url, **params)
    except httpx.HTTPError:
        return None


def _attempts(client: httpx.Client, url: str):
    """원본 → 게시판 첨부 → 웹 아카이브 순서로 응답 내용을 내놓는다. 쓸 수 있는지는 호출자가 판단한다."""
    page = _get(client, url)
    if page is not None:
        yield "direct", page.content
        html = page.content.decode("euc-kr", errors="ignore") if "scourt.go.kr" in str(page.url) else page.text
        for file, name in _COURT_LINK.findall(html):
            try:
                yield "court", client.post(_COURT_DOWNLOAD, data={
                    "file": file, "path": "003", "downFile": name.encode("euc-kr", errors="ignore")}).content
            except httpx.HTTPError:
                continue
        for link in list(dict.fromkeys(_ATTACHMENT.findall(html)))[:_MAX_ATTACHMENTS]:
            time.sleep(0.3)
            attachment = _get(client, up.urljoin(str(page.url), link.replace("&amp;", "&")))
            if attachment is not None:
                yield "attachment", attachment.content
    snapshots = _get(client, "https://web.archive.org/cdx/search/cdx", params={
        "url": url.split("#")[0], "output": "json", "filter": "statuscode:200", "collapse": "digest", "limit": "8"})
    if snapshots is None or snapshots.status_code != 200 or not snapshots.text.strip():
        return
    for row in snapshots.json()[1:]:
        archived = _get(client, f"https://web.archive.org/web/{row[1]}id_/{row[2]}")
        if archived is not None:
            yield "wayback", archived.content


def resolve_pdf(client: httpx.Client, url: str, pages: int) -> tuple[bytes | None, str]:
    """페이지 수가 맞는 첫 PDF를 돌려준다. 실패하면 (None, 이유)다. 다른 판본을 정답 페이지와 맞추지 않기 위해서다."""
    reason = "pdf_not_found"
    for route, data in _attempts(client, url):
        count = _page_count(data)
        if count == pages:
            return data, route
        if count is not None:
            reason = f"page_count_mismatch:{count}"
    return None, reason


def fetch(root: Path = DEFAULT_ROOT, client: httpx.Client | None = None) -> dict:
    """이어받기가 된다. 결과는 root/manifest.json에 파일별로 남는다."""
    client = client or httpx.Client(follow_redirects=True, timeout=60, headers={"User-Agent": _USER_AGENT})
    (root / "pdf").mkdir(parents=True, exist_ok=True)
    for local, remote in (("documents.csv", "documents.csv"), ("qa.csv", "rag_evaluation_result.csv")):
        if not (root / local).exists():
            (root / local).write_bytes(client.get(_DATASET + remote).raise_for_status().content)
    pinned = json.loads(PINNED.read_text(encoding="utf-8")) if PINNED.exists() else {}
    manifest = {}
    for row in _rows(root / "documents.csv"):
        path, pages = _pdf_path(root, row["file_name"]), int(row["pages"])
        data, route = (path.read_bytes(), "cached") if path.exists() else resolve_pdf(client, row["url"], pages)
        if data is None:
            manifest[row["file_name"]] = {"status": "missing", "reason": route, "url": row["url"]}
        else:
            path.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            expected = pinned.get(row["file_name"])
            manifest[row["file_name"]] = {"status": "changed" if expected not in (None, digest) else "ok",
                                          "route": route, "sha256": digest, "pages": pages}
        print(row["file_name"][:50], manifest[row["file_name"]]["status"], route, flush=True)
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def load_pages(root: Path = DEFAULT_ROOT) -> list[Page]:
    """받은 PDF의 글자층을 페이지별로 읽는다. 글자층이 없는 페이지도 빈 text로 남겨 숨기지 않는다."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    pages = []
    for file, entry in manifest.items():
        if entry["status"] == "missing":
            continue
        with pymupdf.open(_pdf_path(root, file)) as pdf:
            pages += [Page(file, number, page.get_text().strip()) for number, page in enumerate(pdf, 1)]
    return pages


def load_cases(root: Path = DEFAULT_ROOT) -> tuple[list[Case], list[dict]]:
    """(쓸 수 있는 문항, 제외 문항과 이유). 분할은 전체 문항을 분야별 해시 순서로 번갈아 나눠 실행마다 같다."""
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    usable, excluded, turn = [], [], Counter()
    rows = sorted(_rows(root / "qa.csv"), key=lambda r: hashlib.sha256(r["question"].encode()).hexdigest())
    for row in rows:
        case_id = hashlib.sha256(row["question"].encode()).hexdigest()[:12]
        file, page = row["target_file_name"], row["target_page_no"].strip()
        entry = manifest.get(file)
        split = "tune" if turn[row["domain"]] % 2 == 0 else "hold"  # 제외 판정 전에 정해 파일을 더 받아도 분할이 밀리지 않는다.
        turn[row["domain"]] += 1
        reason = ("file_not_in_documents" if entry is None else "file_missing" if entry["status"] == "missing"
                  else "no_target_page" if not page.isdigit()
                  else "page_out_of_range" if not 1 <= int(page) <= entry["pages"] else None)
        if reason:
            excluded.append({"case_id": case_id, "domain": row["domain"], "file": file, "reason": reason})
            continue
        usable.append(Case(case_id, row["domain"], row["question"], row["target_answer"], file, int(page),
                           row["context_type"], split))
    return usable, excluded


def status(root: Path = DEFAULT_ROOT) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    usable, excluded = load_cases(root)
    pages = load_pages(root)
    textless = {(page.file, page.page_no) for page in pages if not page.text}
    return {"files": Counter(entry["status"] for entry in manifest.values()), "pages": len(pages),
            "pages_without_text": len(textless), "usable_cases": len(usable),
            "excluded": Counter(row["reason"] for row in excluded),
            "by_domain": Counter(case.domain for case in usable), "by_split": Counter(case.split for case in usable),
            "by_context": Counter(case.context_type for case in usable),
            "cases_on_textless_pages": sum((case.file, case.page_no) in textless for case in usable)}


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_ROOT
    if command == "fetch":
        fetch(target)
    elif command == "pin":  # 저자 전용: 현재 받은 PDF를 기준 판본으로 고정한다.
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        PINNED.write_text(json.dumps({k: v["sha256"] for k, v in manifest.items() if v["status"] != "missing"},
                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(status(target), ensure_ascii=False, indent=1, default=dict))
