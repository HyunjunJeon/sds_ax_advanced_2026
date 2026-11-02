"""올거나이즈 벤치마크 도구. 네트워크 없이 경계(HTTP)만 흉내 내어 판본 대조와 제외 집계를 확인한다."""
import csv
import json
from pathlib import Path

import httpx
import pymupdf
import pytest

from benchmarks.allganize import fetch, load_cases, load_pages, resolve_pdf, status


def make_pdf(texts: list[str]) -> bytes:
    pdf = pymupdf.open()
    for text in texts:
        page = pdf.new_page()
        if text:
            page.insert_text((72, 72), text)
    return pdf.tobytes()


def client_for(routes: dict[str, bytes]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if "web.archive.org/cdx" in str(request.url):
            return httpx.Response(200, json=[["urlkey", "timestamp", "original"]])
        body = routes.get(str(request.url).split("?")[0])
        return httpx.Response(200, content=body) if body is not None else httpx.Response(404, content=b"not found")
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


def test_resolve_rejects_other_edition_with_different_page_count():
    client = client_for({"https://a.test/x.pdf": make_pdf(["one", "two"])})
    data, reason = resolve_pdf(client, "https://a.test/x.pdf", pages=3)
    assert data is None and reason == "page_count_mismatch:2"


def test_resolve_follows_board_attachment():
    html = b'<a href="./down.do?seq=1&amp;file_seq=1">file</a>'
    client = client_for({"https://a.test/view.do": html, "https://a.test/down.do": make_pdf(["one"])})
    data, route = resolve_pdf(client, "https://a.test/view.do", pages=1)
    assert data is not None and route == "attachment"


def test_resolve_reports_html_page_as_not_found():
    client = client_for({"https://a.test/view.do": b"<html>no attachment</html>"})
    assert resolve_pdf(client, "https://a.test/view.do", pages=1) == (None, "pdf_not_found")


def test_timeout_on_origin_still_tries_web_archive():
    pdf = make_pdf(["one"])

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "a.test" in url and "web.archive.org" not in url:
            raise httpx.ConnectTimeout("origin down")
        if "/cdx/" in url:
            return httpx.Response(200, json=[["urlkey", "timestamp", "original"], ["k", "2024", "https://a.test/x.pdf"]])
        return httpx.Response(200, content=pdf)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    data, route = resolve_pdf(client, "https://a.test/x.pdf", pages=1)
    assert data == pdf and route == "wayback"


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    def write(name: str, rows: list[dict]) -> None:
        with (tmp_path / name).open("w", encoding="utf-8-sig", newline="") as out:
            writer = csv.DictWriter(out, rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    write("documents.csv", [
        {"domain": "law", "file_name": "got.pdf", "pages": "2", "url": "https://a.test/got.pdf"},
        {"domain": "law", "file_name": "lost.pdf", "pages": "1", "url": "https://a.test/lost.pdf"}])
    question = {"domain": "law", "target_answer": "a", "context_type": "paragraph", "target_file_name": "got.pdf"}
    write("qa.csv", [{**question, "question": f"q{i}", "target_page_no": "1"} for i in range(4)] + [
        {**question, "question": "lost", "target_file_name": "lost.pdf", "target_page_no": "1"},
        {**question, "question": "blank", "target_page_no": " "},
        {**question, "question": "far", "target_page_no": "9"},
        {**question, "question": "unknown", "target_file_name": "other.pdf", "target_page_no": "1"}])
    fetch(tmp_path, client_for({"https://a.test/got.pdf": make_pdf(["alpha", ""])}))
    return tmp_path


def test_every_excluded_case_keeps_its_reason(dataset: Path):
    usable, excluded = load_cases(dataset)
    assert len(usable) == 4
    assert sorted(row["reason"] for row in excluded) == [
        "file_missing", "file_not_in_documents", "no_target_page", "page_out_of_range"]


def test_split_does_not_shift_when_a_missing_file_arrives(dataset: Path):
    before = {case.case_id: case.split for case in load_cases(dataset)[0]}
    assert set(before.values()) <= {"tune", "hold"}
    assert load_cases(dataset)[0] == load_cases(dataset)[0]
    fetch(dataset, client_for({"https://a.test/lost.pdf": make_pdf(["one"])}))
    after = {case.case_id: case.split for case in load_cases(dataset)[0]}
    assert len(after) == len(before) + 1
    assert all(after[case_id] == split for case_id, split in before.items())


def test_textless_page_stays_visible(dataset: Path):
    pages = load_pages(dataset)
    assert [(p.page_no, bool(p.text)) for p in pages] == [(1, True), (2, False)]
    assert status(dataset)["pages_without_text"] == 1


def test_changed_pdf_is_flagged_against_pinned_digest(tmp_path: Path, dataset: Path, monkeypatch):
    pinned = tmp_path / "pinned.json"
    pinned.write_text(json.dumps({"got.pdf": "different"}), encoding="utf-8")
    monkeypatch.setattr("benchmarks.allganize.PINNED", pinned)
    manifest = fetch(dataset, client_for({}))
    assert manifest["got.pdf"]["status"] == "changed"
    assert manifest["lost.pdf"]["status"] == "missing"
