"""2026-10 공식 원문 스냅샷 생성. 학습 Agent 실행과 독립된 강사용 수집 도구.

고정 commit 원문과 태그 릴리스 본문을 보존하고 연속 행만 발췌한다.
기존 snapshot 폴더가 있으면 덮어쓰지 않는다. 갱신은 새 CORPUS 이름으로 만든다.
평가 정답/검수 상태는 생성하지 않는다. cases/gold는 별도 수업 설계 산출물이다.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = "official-2026-10"
AS_OF = "2026-10-02"
DEEPAGENTS_COMMIT = "4394bcd00b8eb46e7c423939643a0dfcfb5d8773"
OPENVIKING_COMMIT = "e8716760934d95ef73414484a45bfe475b9296e2"


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "SDS-AX-course-snapshot"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    destination = ROOT / "data" / CORPUS
    if destination.exists():
        raise FileExistsError("기존 스냅샷은 보존합니다. 새 CORPUS 이름을 지정하세요.")
    retrieved = datetime.now(timezone.utc).isoformat()
    da_url = f"https://raw.githubusercontent.com/langchain-ai/deepagents/{DEEPAGENTS_COMMIT}/libs/deepagents/CHANGELOG.md"
    da = download(da_url)
    release_url = "https://api.github.com/repos/volcengine/OpenViking/releases/tags/v0.4.22"
    release_bytes = download(release_url)
    release = json.loads(release_bytes)
    if release["tag_name"] != "v0.4.22" or release["published_at"][:10] > AS_OF:
        raise ValueError("릴리스 태그 또는 기준일이 다릅니다.")
    ov = release["body"].encode("utf-8")
    licenses = {
        "deepagents-LICENSE": download(f"https://raw.githubusercontent.com/langchain-ai/deepagents/{DEEPAGENTS_COMMIT}/LICENSE"),
        "openviking-LICENSE": download(f"https://raw.githubusercontent.com/volcengine/OpenViking/{OPENVIKING_COMMIT}/LICENSE"),
    }
    source_specs = [
        {"id": "deepagents", "path": "sources/deepagents-changelog.md", "url": da_url,
         "version": "0.7.21", "commit": DEEPAGENTS_COMMIT, "published_at": "2026-09-30",
         "retrieved_at": retrieved, "sha256": digest(da), "license": "MIT"},
        {"id": "openviking", "path": "sources/openviking-0.4.22.md", "url": release["html_url"],
         "api_url": release_url, "release_id": release["id"], "version": "0.4.22",
         "commit": OPENVIKING_COMMIT, "published_at": release["published_at"],
         "upstream_updated_at": release["updated_at"], "retrieved_at": retrieved,
         "sha256": digest(ov), "license": "Apache-2.0"},
    ]
    destination.mkdir(parents=True)
    for folder in ("sources", "documents", "licenses"):
        (destination / folder).mkdir()
    for spec, raw in zip(source_specs, (da, ov)):
        (destination / spec["path"]).write_bytes(raw)
    (destination / "sources/openviking-release.json").write_bytes(release_bytes)
    for name, raw in licenses.items():
        (destination / "licenses" / name).write_bytes(raw)
    docs, catalog = [], []

    def excerpt(source_id, doc_id, start, stop, title, version, published):
        source = next(s for s in source_specs if s["id"] == source_id)
        raw = (destination / source["path"]).read_bytes().splitlines(keepends=True)
        content = b"".join(raw[start:stop])
        path = destination / "documents" / f"{doc_id}.md"
        path.write_bytes(content)
        docs.append({"doc_id": doc_id, "source_id": source_id, "path": f"documents/{path.name}",
                     "sha256": digest(content), "start_line": start + 1, "end_line": stop,
                     "published_at": published})
        catalog.append({"path": path.relative_to(ROOT).as_posix(), "metadata": {
            "doc_id": doc_id, "title": title, "source": source["url"], "domain": "기술",
            "entity": "공통", "version": version, "valid_from": published[:10], "valid_until": None,
            "status": "approved", "extraction_method": "verbatim-release-excerpt",
            "source_sha256": source["sha256"], "source_start_line": start + 1,
            "source_end_line": stop, "topics": [source_id, version],
        }})

    da_lines = da.decode().splitlines()
    headers = [(i, re.match(r"## \[([^]]+)\].*\((\d{4}-\d{2}-\d{2})\)$", line))
               for i, line in enumerate(da_lines) if line.startswith("## [")]
    for pos, (start, match) in enumerate(headers):
        if not match or match[1] not in {"0.7.13", "0.7.14", "0.7.15", "0.7.18", "0.7.21"}:
            continue
        stop = headers[pos + 1][0] if pos + 1 < len(headers) else len(da_lines)
        excerpt("deepagents", "deepagents-" + match[1], start, stop,
                "DeepAgents " + match[1] + " release notes", match[1], match[2])

    ov_lines = ov.decode().splitlines()
    english = ov_lines.index("## English")
    sections = [(i, re.match(r"(\d+)\. \*\*(.+?)\*\*", line))
                for i, line in enumerate(ov_lines) if i > english and re.match(r"\d+\. \*\*", line)]
    selected = {1: "session-api", 2: "commit-failure", 5: "acl", 6: "cosine"}
    for pos, (start, match) in enumerate(sections):
        if int(match[1]) not in selected:
            continue
        stop = sections[pos + 1][0] if pos + 1 < len(sections) else len(ov_lines)
        excerpt("openviking", "openviking-" + selected[int(match[1])], start, stop,
                "OpenViking 0.4.22 " + match[2], "0.4.22", release["published_at"])
    catalog_path = destination / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {"schema_version": 1, "corpus": CORPUS, "as_of": AS_OF,
                "catalog_sha256": digest(catalog_path.read_bytes()), "sources": source_specs,
                "documents": docs, "review": "Source bytes and excerpt coordinates verified; no human review claimed."}
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"공식 원문 {len(source_specs)}개, 발췌 {len(docs)}개: {destination}")


if __name__ == "__main__":
    main()
