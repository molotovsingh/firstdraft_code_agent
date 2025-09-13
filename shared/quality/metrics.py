from typing import Tuple, Dict, List, Optional
import numpy as np
import cv2
from langdetect import detect_langs
from pypdf import PdfReader
import io


def _variance_of_laplacian(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _estimate_skew_degrees(gray: np.ndarray) -> float:
    # Simple skew estimate via Hough lines around horizontal text baselines
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi / 180.0, 200)
    if lines is None:
        return 0.0
    angles = []
    for rho_theta in lines[:50]:
        rho, theta = rho_theta[0]
        angle = (theta * 180.0 / np.pi) - 90.0  # around 0 for horizontal lines
        # Normalize to [-45, 45]
        while angle > 45:
            angle -= 90
        while angle < -45:
            angle += 90
        angles.append(angle)
    if not angles:
        return 0.0
    return float(np.median(angles))


def _detect_language(ocr_text: str) -> Optional[str]:
    try:
        if not ocr_text or len(ocr_text.strip()) < 30:
            return None
        langs = detect_langs(ocr_text)
        if not langs:
            return None
        return langs[0].lang
    except Exception:
        return None


def compute_metrics_and_warnings(mime: str, original_bytes: Optional[bytes], ocr_text: str) -> Tuple[Dict, List[str]]:
    metrics: Dict = {}
    warnings: List[str] = []

    if mime and mime.lower().startswith("image/") and original_bytes:
        try:
            data = np.frombuffer(original_bytes, dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                blur_var = _variance_of_laplacian(img)
                skew_deg = _estimate_skew_degrees(img)
                metrics["blur_variance"] = round(blur_var, 2)
                metrics["skew_degrees"] = round(skew_deg, 2)
                if blur_var < 100:
                    warnings.append("Image appears blurry; sharper scan recommended")
                if abs(skew_deg) > 1.5:
                    warnings.append("Page appears rotated/skewed; auto-correction recommended")
        except Exception:
            warnings.append("Failed to compute image quality metrics")

    # For images, assume single page
    if mime and mime.lower().startswith("image/") and original_bytes:
        metrics.setdefault("page_count", 1)

    lang = _detect_language(ocr_text)
    if lang:
        metrics["language_detected"] = lang

    text_len = len(ocr_text or "")
    metrics["ocr_text_length"] = text_len
    if text_len < 20:
        warnings.append("Very little text extracted; check document quality or language setting")

    # PDF-specific basic metrics
    try:
        if mime == "application/pdf" and original_bytes:
            reader = PdfReader(io.BytesIO(original_bytes))
            page_count = len(reader.pages)
            metrics["page_count"] = page_count
    except Exception:
        # Don't fail metrics entirely if PDF parsing is problematic
        pass

    # Density and simple success flag
    page_count = metrics.get("page_count", 0)
    if page_count and page_count > 0:
        density = text_len / page_count
    else:
        density = float(text_len)
    metrics["text_density_per_page"] = round(density, 2)
    if density < 40:
        warnings.append("Low text density per page; OCR may be incomplete")
    metrics["ocr_ok"] = bool(text_len >= 20)

    return metrics, warnings


def estimate_credits(mime: str, size_bytes: int) -> int:
    """Size-based rough estimate used pre-processing."""
    mb = max(1, int((size_bytes + 1_000_000 - 1) / 1_000_000))
    base = 10 * mb
    if (mime or "").lower().startswith("image/"):
        base += 5
    return max(1, int(base))


def estimate_actual_credits(mime: str, size_bytes: int, metrics: dict | None) -> int:
    """
    Minimal actualization heuristic for Block 0:
    - Prefer page_count if present: 8 credits/page for PDFs; 10/page for images.
    - Fallback to size-based estimate_credits.
    """
    try:
        if isinstance(metrics, dict):
            pc = metrics.get("page_count")
            if isinstance(pc, int) and pc > 0:
                if (mime or "").lower() == "application/pdf":
                    return max(1, int(8 * pc))
                if (mime or "").lower().startswith("image/"):
                    return max(1, int(10 * pc))
    except Exception:
        pass
    return estimate_credits(mime or "application/octet-stream", size_bytes)
