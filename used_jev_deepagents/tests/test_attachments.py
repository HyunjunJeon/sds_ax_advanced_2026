"""User file parts become /retrieved/attachment evidence."""

from __future__ import annotations

import base64
from dataclasses import replace
from unittest.mock import MagicMock

from langchain_core.messages import HumanMessage

from src.agent.config import load_settings
from src.attachments import (
    attachment_state_files,
    attachment_system_block,
    extract_attached_files,
    inventory_markdown,
    store_attachment_passages,
)
from src.harness import JevHarness
from src.middleware.turn_plan import (
    TurnPlanMiddleware,
    _human_text,
    _messages_for_model,
)


def _min_pdf() -> bytes:
    """xref가 있는 한 페이지 PDF. Helvetica 한 줄을 넣는다."""
    stream = b"BT /F1 12 Tf 20 60 Td (vLLM is a serving engine) Tj ET\n"
    objects = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n",
        (
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
            b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
        ),
        (
            b"4 0 obj<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>stream\n"
            + stream
            + b"endstream\nendobj\n"
        ),
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n",
    ]
    header = b"%PDF-1.4\n"
    buf = header
    offsets = [0]
    for obj in objects:
        offsets.append(len(buf))
        buf += obj
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        xref += f"{offset:010d} 00000 n \n".encode("ascii")
    trailer = (
        b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(len(buf)).encode("ascii")
        + b"\n%%EOF\n"
    )
    return buf + xref + trailer


class _MemBackend:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def upload_files(self, files):
        for path, data in files:
            self.files[path] = data
        return []


def _pdf_part() -> dict:
    return {
        "type": "file",
        "mimeType": "application/pdf",
        "data": base64.b64encode(_min_pdf()).decode("ascii"),
        "metadata": {"filename": "01_vLLM_Basic.pdf"},
    }


def test_extract_pdf_and_store_under_retrieved() -> None:
    files = extract_attached_files(
        [
            {"type": "text", "text": "vLLM 은 어떤 서비스인가요?"},
            _pdf_part(),
        ]
    )
    assert len(files) == 1
    assert files[0].filename == "01_vLLM_Basic.pdf"
    assert "vLLM is a serving engine" in files[0].text
    assert files[0].passages
    backend = _MemBackend()
    gated = store_attachment_passages(backend, files)
    assert gated
    assert gated[0].route == "include"
    assert gated[0].passage.source_type == "user_attachment"
    assert gated[0].path and gated[0].path.startswith("/retrieved/attachment/")
    stored = next(iter(backend.files.values())).decode("utf-8")
    assert "vLLM is a serving engine" in stored
    inventory = inventory_markdown(files)
    assert "01_vLLM_Basic.pdf" in inventory
    assert "JVBERi" not in inventory
    block = attachment_system_block(files, gated)
    assert "already retrieved" in block
    assert "vLLM is a serving engine" in block


def test_text_attachment_is_kept() -> None:
    files = extract_attached_files(
        [
            {
                "type": "file",
                "mimeType": "text/markdown",
                "data": base64.b64encode(b"# vLLM\n\nPagedAttention engine").decode(
                    "ascii"
                ),
                "metadata": {"filename": "notes.md"},
            }
        ]
    )
    assert files[0].text.startswith("# vLLM")
    assert files[0].passages[0].source == "attachment/notes.md"


def test_state_files_include_chunks_past_the_excerpt() -> None:
    """12_000자 이후 청크도 files 채널에 남아 read_file이 찾는다."""
    body = "\n\n".join(
        f"## 섹션 {index}\n\n" + ("Candle 데이터 레이크하우스 설계. " * 40)
        for index in range(1, 30)
    )
    files = extract_attached_files(
        [
            {
                "type": "file",
                "mimeType": "text/markdown",
                "data": base64.b64encode(body.encode("utf-8")).decode("ascii"),
                "metadata": {"filename": "Candle- 데이터 아키텍처.md"},
            }
        ]
    )
    gated = store_attachment_passages(None, files)
    stored = attachment_state_files(gated)
    late = [item for item in gated if item.path and "/chunk_18_" in item.path]
    assert late
    path = late[0].path
    assert path in stored
    assert "레이크하우스" in stored[path]["content"]
    block = attachment_system_block(files, gated)
    assert "Use read_file" in block
    assert path in block


def test_before_agent_puts_attachment_chunks_in_files_state() -> None:
    """before_agent가 files를 돌려줘야 StateBackend read_file이 산다."""
    harness = JevHarness(replace(load_settings(), jev_mode="fallback"))
    model = MagicMock()
    middleware = TurnPlanMiddleware(harness, model, model, backend=None)
    body = "\n\n".join(
        f"## 섹션 {index}\n\n" + ("Candle 데이터 레이크하우스 설계. " * 40)
        for index in range(1, 30)
    )
    human = HumanMessage(
        content=[
            {"type": "text", "text": "이 문서의 데이터 아키텍처를 요약하세요."},
            {
                "type": "file",
                "mimeType": "text/markdown",
                "data": base64.b64encode(body.encode("utf-8")).decode("ascii"),
                "metadata": {"filename": "Candle- 데이터 아키텍처.md"},
            },
        ]
    )
    update = middleware.before_agent({"messages": [human]}, None)
    assert update is not None
    files = update["files"]
    late = [path for path in files if "/chunk_18_" in path]
    assert late
    assert files[late[0]]["content"]
    assert late[0].startswith("/retrieved/attachment/")


def test_messages_drop_pdf_binary_and_keep_note() -> None:
    human = HumanMessage(
        content=[
            {"type": "text", "text": "vLLM 은 어떤 서비스인가요?"},
            _pdf_part(),
        ]
    )
    note = "(첨부 1개 추출됨: 01_vLLM_Basic.pdf → /retrieved/attachment/abcd/)"
    kept = _messages_for_model([human], attachment_note=note)
    assert len(kept) == 1
    content = kept[0].content
    assert isinstance(content, str)
    assert "vLLM 은 어떤 서비스인가요?" in content
    assert note in content
    assert "JVBERi" not in content
    assert _human_text(human.content) == "vLLM 은 어떤 서비스인가요?"
