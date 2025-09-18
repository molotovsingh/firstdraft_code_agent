import io

import pytest
from PIL import Image, ImageDraw

import pytesseract

from shared.ocr.adapters.tesseract import TesseractAdapter


def _require_tesseract():
    try:
        pytesseract.get_tesseract_version()
    except (pytesseract.TesseractNotFoundError, OSError, RuntimeError) as exc:
        pytest.skip(f"Tesseract binary not available: {exc}")


def _make_text_image(text: str) -> bytes:
    img = Image.new("RGB", (220, 80), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 25), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_tesseract_adapter_extracts_text():
    _require_tesseract()
    content = _make_text_image("Hello OCR")
    adapter = TesseractAdapter()

    result = adapter.process(content, "image/png", languages=["eng"])

    assert result.combined_text.strip() != ""
    assert result.pages[0].text.strip() != ""


def test_tesseract_adapter_handles_non_images():
    adapter = TesseractAdapter()
    result = adapter.process(b"not an image", "application/pdf")

    assert result.combined_text == ""
    assert result.pages[0].confidence == 0.0
