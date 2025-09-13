from shared.quality.metrics import compute_metrics_and_warnings
from PIL import Image, ImageDraw
import io


def _make_image_bytes(text="Hello World") -> bytes:
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 80), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_compute_metrics_image():
    b = _make_image_bytes()
    metrics, warnings = compute_metrics_and_warnings("image/png", b, "Hello World")
    assert "text_density_per_page" in metrics
    assert metrics.get("ocr_ok") in (True, False)
    # blur/skew keys may or may not be present depending on detection; ensure no crash
    assert isinstance(warnings, list)


def test_compute_metrics_pdf_empty_text():
    # No PDF bytes (None) with empty text still returns density and warnings list
    metrics, warnings = compute_metrics_and_warnings("application/pdf", None, "")
    assert "text_density_per_page" in metrics
    assert isinstance(warnings, list)
