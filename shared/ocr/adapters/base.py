from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PageText:
    index: int
    text: str
    confidence: float
    language: Optional[str] = None


@dataclass
class OCRResult:
    pages: List[PageText]
    combined_text: str


class OCRAdapter(ABC):
    @abstractmethod
    def process(self, content: bytes, mime: str, languages: Optional[List[str]] = None) -> OCRResult:
        """Return OCRResult for given document bytes and mime."""
        raise NotImplementedError

