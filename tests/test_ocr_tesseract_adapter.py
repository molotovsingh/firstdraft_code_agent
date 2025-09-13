import io
import shutil
import pytest
from PIL import Image, ImageDraw
from shared.ocr.adapters.tesseract import TesseractAdapter


def test_tesseract_adapter_process():
    """Test TesseractAdapter with a simple text image."""
    if shutil.which("tesseract") is None:
        pytest.skip("Tesseract binary not found - skipping test")

    # Create a tiny test image with text
    img = Image.new('RGB', (200, 50), color='white')
    draw = ImageDraw.Draw(img)

    # Draw simple text
    draw.text((10, 15), "TEST", fill='black')

    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    content = img_bytes.getvalue()

    # Test the adapter
    adapter = TesseractAdapter()
    result = adapter.process(content, "image/png", languages=["eng"])

    assert result.combined_text.strip() != "", "Expected non-empty OCR text"
