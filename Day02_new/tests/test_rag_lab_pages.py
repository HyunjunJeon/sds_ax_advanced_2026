import pymupdf
import pytest
from fakes import ScriptedChatModel
from langchain_core.messages import AIMessage
from rag_lab.pages import needs_reading, read_page
from rag_lab.settings import ROOT

SAMPLE = ROOT / "data" / "pdf" / "credit-trend-chart.pdf"
LONG_TEXT = "분기별 서비스 크레딧 신청 절차를 안내합니다. " * 10


def test_sample_chart_page_has_no_text_layer():
    with pymupdf.open(SAMPLE) as document:
        assert document.page_count == 1
        assert document[0].get_text() == ""


def test_needs_reading_true_on_image_only_sample():
    with pymupdf.open(SAMPLE) as document:
        assert needs_reading(document[0]) is True


def test_needs_reading_false_on_text_only_page():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_textbox(pymupdf.Rect(40, 40, 555, 400), LONG_TEXT)
        assert len(page.get_text().strip()) >= 100
        assert needs_reading(page) is False


def test_needs_reading_true_on_short_text_page():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), "short")
        assert needs_reading(page) is True


def test_read_page_sends_jpeg_image_block_and_returns_model_text():
    model = ScriptedChatModel(steps=[AIMessage(content="  Q1 12건, Q2 18건  ")])
    assert read_page(model, SAMPLE, 1) == "Q1 12건, Q2 18건"
    blocks = model.calls[0][0].content
    image = next(block for block in blocks if block["type"] == "image")
    assert image["source"]["media_type"] == "image/jpeg"
    assert image["source"]["data"].startswith("/9j/")  # JPEG 시작 바이트의 base64
    assert "지어내지 말고" in next(block["text"] for block in blocks if block["type"] == "text")


@pytest.mark.parametrize("page_no", [0, 2, -1])
def test_read_page_rejects_out_of_range_without_calling_model(page_no):
    model = ScriptedChatModel(steps=[])
    with pytest.raises(ValueError):
        read_page(model, SAMPLE, page_no)
    assert model.calls == []
