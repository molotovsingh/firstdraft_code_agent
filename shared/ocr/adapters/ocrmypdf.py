from typing import List, Optional
import io
import subprocess
import tempfile
import time

from pypdf import PdfReader

from .base import OCRAdapter, OCRResult, PageText


class OCRmyPDFAdapter(OCRAdapter):
    def __init__(self, timeout_seconds: int = 180, fast_mode: bool = False, tesseract_timeout: int | None = None, extra_args: list[str] | None = None):
        self.timeout_seconds = timeout_seconds
        self.fast_mode = fast_mode
        self.tesseract_timeout = tesseract_timeout
        self.extra_args = extra_args or []

    def process(self, content: bytes, mime: str, languages: Optional[List[str]] = None) -> OCRResult:
        """OCR for PDFs using ocrmypdf with a sidecar text file.
        For non-PDF MIME types, returns an empty result.
        """
        if (mime or "").lower() != "application/pdf":
            return OCRResult(pages=[PageText(index=0, text="", confidence=0.0)], combined_text="")

        lang = None
        if languages:
            # ocrmypdf language list format uses plus as well
            lang = "+".join([l.strip() for l in languages if l.strip()])

        with tempfile.TemporaryDirectory() as td:
            in_pdf = f"{td}/in.pdf"
            out_pdf = f"{td}/out.pdf"
            sidecar = f"{td}/out.txt"
            with open(in_pdf, "wb") as f:
                f.write(content)
            cmd = [
                "ocrmypdf",
                "--language", (lang or "eng"),
                "--sidecar", sidecar,
                "--skip-text",
            ]
            if self.fast_mode:
                cmd += ["--optimize", "0", "--clean", "0"]
            if isinstance(self.tesseract_timeout, int) and self.tesseract_timeout > 0:
                cmd += ["--tesseract-timeout", str(self.tesseract_timeout)]
            if self.extra_args:
                cmd += list(self.extra_args)
            cmd += [in_pdf, out_pdf]
            # Retry logic with exponential backoff (2 attempts total)
            delay = 0.5
            for attempt in range(2):
                try:
                    subprocess.run(cmd, check=True, capture_output=True, timeout=self.timeout_seconds)
                    break  # Success
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    if attempt == 1:
                        raise RuntimeError("ocrmypdf failed after retries")
                    time.sleep(delay)
                    delay *= 2

            text = ""
            try:
                with open(sidecar, "r", encoding="utf-8", errors="ignore") as sf:
                    text = sf.read()
            except FileNotFoundError:
                text = ""

            # Build minimal pages info (one combined page). If we can count pages, include that many empty pages.
            pages = []
            try:
                reader = PdfReader(io.BytesIO(content))
                for i in range(len(reader.pages)):
                    pages.append(PageText(index=i, text="", confidence=0.0, language=lang))
            except Exception:
                pages = [PageText(index=0, text="", confidence=0.0, language=lang)]

            return OCRResult(pages=pages, combined_text=text)
