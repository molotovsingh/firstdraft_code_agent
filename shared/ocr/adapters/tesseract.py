from typing import List, Optional
from .base import OCRAdapter, OCRResult, PageText


class TesseractAdapter(OCRAdapter):
    def __init__(self):
        pass

    def process(self, content: bytes, mime: str, languages: Optional[List[str]] = None) -> OCRResult:
        # Placeholder implementation — real wiring to pytesseract/ocrmypdf will follow.
        pages = [PageText(index=0, text="[tesseract-stub]", confidence=0.6, language=(",".join(languages) if languages else None))]
        return OCRResult(pages=pages, combined_text="[tesseract-stub]\n")

