import cv2
import numpy as np

from shared.quality.metrics import compute_metrics_and_warnings


def _png_bytes_from_image(img: np.ndarray) -> bytes:
    success, buf = cv2.imencode(".png", img)
    if not success:
        raise RuntimeError("Failed to encode png for test")
    return buf.tobytes()


def test_quality_metrics_good_image_has_minimal_warnings():
    # Create a sharp synthetic document with clear text.
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    cv2.putText(img, "HELLO OCR WORLD", (5, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    png_bytes = _png_bytes_from_image(img)

    ocr_text = "This is a synthetic document that should have sufficient text length for metrics."
    metrics, warnings = compute_metrics_and_warnings("image/png", png_bytes, ocr_text)

    assert metrics["page_count"] == 1
    assert metrics["ocr_text_length"] == len(ocr_text)
    assert metrics["ocr_ok"] is True
    assert all("blurry" not in w for w in warnings)
    assert "Very little text extracted" not in " ".join(warnings)


def test_quality_metrics_low_quality_image_triggers_warnings():
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    cv2.putText(img, "BLUR", (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0), 5)
    blurred = cv2.GaussianBlur(img, (29, 29), 0)
    png_bytes = _png_bytes_from_image(blurred)

    ocr_text = "short text"  # purposely small to trigger density/length warnings
    metrics, warnings = compute_metrics_and_warnings("image/png", png_bytes, ocr_text)

    assert metrics["page_count"] == 1
    assert metrics["ocr_ok"] is False
    joined = " ".join(warnings).lower()
    assert "blurry" in joined
    assert "very little text" in joined
    assert "low text density" in joined
