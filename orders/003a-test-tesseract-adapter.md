# Order 003a — Unit test for `TesseractAdapter`

Owner: Claude
Scope: Add a single, fast unit test for `shared/ocr/adapters/tesseract.py`.

Rationale
- We already have tests for quality metrics and OCRmyPDF extras; missing coverage is the Tesseract adapter happy path.

Acceptance Criteria
- New file: `tests/test_ocr_tesseract_adapter.py` with:
  - Creates a tiny in-memory image with text using PIL.
  - Invokes `TesseractAdapter.process(...)` with languages like `["eng"]`.
  - Asserts non-empty `combined_text` when Tesseract binary is available.
  - Skips with a clear message if Tesseract binary is missing (e.g., check `shutil.which("tesseract")`).
- Test runtime < 1s locally; no Docker dependencies.

Validation
- `pytest -q tests/test_ocr_tesseract_adapter.py` passes (or is skipped with message if binary missing).

Out of Scope
- PDF OCR tests, performance tests, or code refactors.

Change Log (for PR)
- Add unit test for Tesseract adapter with graceful skip if Tesseract is not installed.
