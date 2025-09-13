from typing import List, Optional
from .base import OCRAdapter, OCRResult, PageText
from PIL import Image
import io
import pytesseract
from pytesseract import Output


class TesseractAdapter(OCRAdapter):
    def __init__(self, oem: int | None = None, psm: int | None = None, extra_config: str | None = None):
        self.oem = oem
        self.psm = psm
        self.extra_config = extra_config

    def process(self, content: bytes, mime: str, languages: Optional[List[str]] = None) -> OCRResult:
        """OCR for image/* using pytesseract. Returns combined text and a single PageText.
        For non-image MIME types, returns an empty result.
        """
        if not (mime or "").lower().startswith("image/"):
            return OCRResult(pages=[PageText(index=0, text="", confidence=0.0)], combined_text="")

        pil_img = Image.open(io.BytesIO(content))
        lang = None
        if languages:
            # Tesseract language list format: "eng+hin"
            lang = "+".join([l.strip() for l in languages if l.strip()])
        cfg_parts: list[str] = []
        if self.oem is not None:
            cfg_parts.append(f"--oem {int(self.oem)}")
        if self.psm is not None:
            cfg_parts.append(f"--psm {int(self.psm)}")
        if self.extra_config:
            cfg_parts.append(self.extra_config)
        config = " ".join(cfg_parts) if cfg_parts else None
        if config:
            text = pytesseract.image_to_string(pil_img, lang=lang, config=config) or ""
        else:
            text = pytesseract.image_to_string(pil_img, lang=lang) or ""

        confidence = 0.0
        try:
            data = pytesseract.image_to_data(pil_img, lang=lang, output_type=Output.DICT, config=config or None)
            confs = [int(c) for c in data.get("conf", []) if c not in ("-1", "-")]
            vals = [c for c in confs if c >= 0]
            if vals:
                confidence = round(float(sum(vals)) / max(1, len(vals)) / 100.0, 3)
        except Exception:
            pass

        page = PageText(index=0, text=text, confidence=confidence, language=(lang or None))
        return OCRResult(pages=[page], combined_text=text)
