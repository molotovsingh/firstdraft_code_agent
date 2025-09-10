from typing import Tuple
import io
import numpy as np
import cv2


def deskew_image_bytes(image_bytes: bytes, skew_threshold: float = 1.5) -> Tuple[bytes, float]:
    """Return (possibly rotated_image_bytes, applied_degrees).
    Positive degrees indicate clockwise rotation applied to correct skew.
    If |skew| <= threshold or detection fails, returns original and 0.0.
    """
    try:
        data = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes, 0.0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi / 180.0, 200)
        if lines is None or len(lines) == 0:
            return image_bytes, 0.0
        angles = []
        for rho_theta in lines[:50]:
            rho, theta = rho_theta[0]
            angle = (theta * 180.0 / np.pi) - 90.0
            while angle > 45:
                angle -= 90
            while angle < -45:
                angle += 90
            angles.append(angle)
        if not angles:
            return image_bytes, 0.0
        median_angle = float(np.median(angles))
        if abs(median_angle) <= skew_threshold:
            return image_bytes, 0.0
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        ok, buf = cv2.imencode('.png', rotated)
        if not ok:
            return image_bytes, 0.0
        return buf.tobytes(), median_angle
    except Exception:
        return image_bytes, 0.0


def normalize_image(image_bytes: bytes) -> Tuple[bytes, float]:
    """Backwards-compatible alias: currently only deskews.
    Returns: (normalized_image_bytes, applied_skew_degrees)
    """
    return deskew_image_bytes(image_bytes)
