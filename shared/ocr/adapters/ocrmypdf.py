from typing import List, Optional
from .base import OCRAdapter, OCRResult, PageText


class OCRmyPDFAdapter(OCRAdapter):
    def __init__(self):
        pass

    def process(self, content: bytes, mime: str, languages: Optional[List[str]] = None) -> OCRResult:
        # Placeholder implementation for planning; real implementation will call ocrmypdf.
        pages = [PageText(index=0, text="[ocrmypdf-stub]", confidence=0.7, language=(",".join(languages) if languages else None))]
        return OCRResult(pages=pages, combined_text="[ocrmypdf-stub]\n")

