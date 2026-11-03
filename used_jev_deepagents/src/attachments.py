"""채팅에 붙은 파일을 텍스트로 풀어 /retrieved/attachment 에 넣는다.

검색 도구는 corpus/와 Exa만 본다. 첨부를 그 파이프에 넣지 않으면
채팅 모델이 학습 지식으로 답한다.
"""

from __future__ import annotations

import base64
import io
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from src.schemas import GatedPassage, Passage

_TEXT_EXTS = {".txt", ".md", ".markdown", ".csv", ".json"}
_EXCERPT_CHARS = 12_000


@dataclass
class AttachedFile:
    """메시지에서 꺼낸 첨부 하나."""

    filename: str
    mime_type: str
    data: bytes
    text: str = ""
    pages: int = 0
    error: str = ""
    passages: list[Passage] = field(default_factory=list)


def latest_human_content(state: dict[str, Any]) -> object:
    """가장 최근 HumanMessage.content."""
    from langchain_core.messages import HumanMessage

    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return message.content
    return None


def extract_attached_files(content: object) -> list[AttachedFile]:
    """file 파트만 디코드하고 텍스트를 뽑는다. 질문은 건드리지 않는다."""
    files: list[AttachedFile] = []
    if not isinstance(content, list):
        return files
    for item in content:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").lower() not in {"file", "document"}:
            continue
        attached = _from_part(item)
        _fill_text(attached)
        files.append(attached)
    return files


def inventory_markdown(files: list[AttachedFile]) -> str:
    """Jev에 넣을 짧은 첨부 목록. 바이너리는 넣지 않는다."""
    if not files:
        return ""
    lines = [
        "[User attached documents — text already extracted "
        "to /retrieved/attachment]",
    ]
    for item in files:
        if item.error:
            lines.append(f"- {item.filename}: {item.error}")
            continue
        extra = f"{item.pages} pages, " if item.pages else ""
        lines.append(
            f"- {item.filename} ({extra}{len(item.text)} chars extracted)"
        )
    return "\n".join(lines)


def attachment_note(files: list[AttachedFile], gated: list[GatedPassage]) -> str:
    """파일 파트를 뺀 HumanMessage에 남기는 한 줄."""
    if not files:
        return ""
    names = ", ".join(item.filename for item in files)
    folder = _folder(gated)
    if any(item.text.strip() for item in files):
        return f"(첨부 {len(files)}개 추출됨: {names} → {folder})"
    return f"(첨부 {len(files)}개: {names}. 추출된 텍스트 없음)"


def attachment_system_block(
    files: list[AttachedFile],
    gated: list[GatedPassage],
) -> str:
    """이미 검색된 첨부 근거. 모델이 도구를 안 불러도 본문을 보게 한다."""
    if not files:
        return ""
    lines = [
        "",
        "## User attachments (already retrieved — use these)",
        "",
        "Primary evidence is the attached files. Do not answer from "
        "parametric knowledge while they exist. Search corpus/web only "
        "if this text is silent on the question. Cite the attachment paths.",
        "",
    ]
    if gated:
        for item in gated:
            path = item.path or ""
            lines.append(f"- include `{path}`  {item.passage.source}")
        lines.append("")
    failed = [item for item in files if item.error or not item.text.strip()]
    for item in failed:
        reason = item.error or "no extractable text"
        lines.append(
            f"- {item.filename}: {reason}. Do not invent the document contents."
        )
    excerpt = _excerpt(gated)
    if excerpt:
        lines.extend(["", "### Extracted attachment text", "", excerpt])
    return "\n".join(lines)


def store_attachment_passages(
    backend: Any,
    files: list[AttachedFile],
) -> list[GatedPassage]:
    """통과한 첨부 청크를 /retrieved/attachment 에 쓴다."""
    passages = [passage for item in files for passage in item.passages]
    gated = _as_included(passages)
    uploads: list[tuple[str, bytes]] = []
    for item in gated:
        path = item.path
        if not path:
            continue
        uploads.append((path, _chunk_markdown(item).encode("utf-8")))
    if uploads and backend is not None:
        try:
            backend.upload_files(uploads)
        except RuntimeError:
            # StateBackend는 CONFIG_KEY_SEND가 있을 때만 쓴다.
            # before_agent는 files 채널 업데이트로 같은 경로를 남긴다.
            pass
    return gated


def attachment_state_files(gated: list[GatedPassage]) -> dict[str, dict[str, str]]:
    """LangGraph ``files`` 채널에 넣을 FileData. read_file이 여기를 본다.

    StateBackend.upload_files는 before_agent에서 실패할 수 있다. 청크 경로만
    시스템 프롬프트에 남기면 12_000자 이후 본문(chunk_18 등)을 읽지 못한다.
    """
    now = datetime.now(UTC).isoformat()
    stored: dict[str, dict[str, str]] = {}
    for item in gated:
        path = item.path
        if not path:
            continue
        stored[path] = {
            "content": _chunk_markdown(item),
            "encoding": "utf-8",
            "created_at": now,
            "modified_at": now,
        }
    return stored


def _from_part(part: dict[str, Any]) -> AttachedFile:
    filename = _filename(part)
    mime = str(part.get("mimeType") or part.get("mime_type") or "").lower()
    data = _decode_bytes(part)
    return AttachedFile(filename=filename, mime_type=mime, data=data)


def _filename(part: dict[str, Any]) -> str:
    meta = part.get("metadata")
    if isinstance(meta, dict) and meta.get("filename"):
        return str(meta["filename"])
    for key in ("filename", "name", "file_name"):
        if part.get(key):
            return str(part[key])
    source = part.get("source")
    if isinstance(source, dict):
        return _filename(source)
    return "attachment"


def _decode_bytes(part: dict[str, Any]) -> bytes:
    data = part.get("data")
    if isinstance(data, bytes):
        return data
    if isinstance(data, str) and data.strip():
        return _decode_text_payload(data)
    source = part.get("source")
    if isinstance(source, dict):
        return _decode_bytes(source)
    return b""


def _decode_text_payload(data: str) -> bytes:
    payload = data
    if payload.startswith("data:") and "," in payload:
        payload = payload.split(",", 1)[1]
    try:
        return base64.b64decode(payload, validate=False)
    except Exception:
        return payload.encode("utf-8", errors="replace")


def _fill_text(attached: AttachedFile) -> None:
    if not attached.data:
        attached.error = "empty file part"
        return
    name = attached.filename.lower()
    mime = attached.mime_type
    is_pdf = (
        mime == "application/pdf"
        or name.endswith(".pdf")
        or attached.data.startswith(b"%PDF")
    )
    if is_pdf:
        _fill_pdf(attached)
        return
    ext = ""
    if "." in name:
        ext = "." + name.rsplit(".", 1)[-1]
    is_text = mime.startswith("text/") or ext in _TEXT_EXTS
    if is_text:
        attached.text = _clean(attached.data.decode("utf-8", errors="replace"))
        attached.passages = _split_passages(attached.filename, attached.text)
        if not attached.text.strip():
            attached.error = "no extractable text"
        return
    attached.error = f"unsupported attachment type ({mime or ext or 'unknown'})"


def _fill_pdf(attached: AttachedFile) -> None:
    try:
        reader = PdfReader(io.BytesIO(attached.data))
    except Exception as exc:  # noqa: BLE001 - 첨부 파싱 실패는 턴을 죽이지 않는다
        attached.error = f"pdf parse failed: {exc}"
        return
    pages: list[str] = []
    for page in reader.pages:
        pages.append(_clean(page.extract_text() or ""))
    attached.pages = len(pages)
    attached.text = "\n\n".join(part for part in pages if part.strip())
    if not attached.text.strip():
        attached.error = "no extractable text (image-only or encoded fonts)"
        return
    attached.passages = _split_passages(attached.filename, attached.text)


def _split_passages(filename: str, text: str) -> list[Passage]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=150,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    stem = _safe(filename.rsplit(".", 1)[0] or filename)
    passages: list[Passage] = []
    for index, chunk in enumerate(splitter.split_text(text), start=1):
        body = chunk.strip()
        if not body:
            continue
        passages.append(
            Passage(
                doc_id=f"{stem}-{index:02d}",
                title=filename,
                source=f"attachment/{filename}",
                source_type="user_attachment",
                text=body,
            )
        )
    return passages


def _as_included(passages: list[Passage]) -> list[GatedPassage]:
    batch_id = uuid.uuid4().hex[:8]
    gated: list[GatedPassage] = []
    for index, passage in enumerate(passages, start=1):
        path = (
            f"/retrieved/attachment/{batch_id}/"
            f"chunk_{index:02d}_{passage.doc_id}.md"
        )
        gated.append(
            GatedPassage(
                passage=passage,
                is_relevant=1.0,
                contains_answer_evidence=1.0,
                contradicts_query_premise=0.0,
                contains_prompt_injection=0.0,
                route="include",
                path=path,
            )
        )
    return gated


def _chunk_markdown(item: GatedPassage) -> str:
    passage = item.passage
    return (
        f"# Source: {passage.source}\n"
        f"Title: {passage.title}\n"
        f"Route: {item.route}\n"
        f"Source type: {passage.source_type}\n\n"
        f"{passage.text}\n"
    )


def _excerpt(gated: list[GatedPassage]) -> str:
    parts: list[str] = []
    used = 0
    for item in gated:
        text = item.passage.text.strip()
        if not text:
            continue
        header = f"[{item.path}]\n"
        room = _EXCERPT_CHARS - used
        if room <= 80:
            parts.append(
                f"... remaining attachment text is in "
                f"{item.path} and later files. Use read_file."
            )
            break
        if len(header) + len(text) <= room:
            body = text
        else:
            body = text[: max(0, room - len(header) - 20)] + "..."
        block = header + body
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts)


def _folder(gated: list[GatedPassage]) -> str:
    for item in gated:
        if item.path:
            return item.path.rsplit("/", 1)[0] + "/"
    return "/retrieved/attachment/"


def _clean(text: str) -> str:
    """PDF 추출이 남기는 서로게이트를 버린다."""
    return "".join(
        ch if not (0xD800 <= ord(ch) <= 0xDFFF) else " " for ch in text
    ).strip()


def _safe(title: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in title)
