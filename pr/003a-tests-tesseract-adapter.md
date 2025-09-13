# PR: Minimal unit test for TesseractAdapter

- Order: 003a
- Scope: Add a fast, isolated unit test that exercises `shared/ocr/adapters/tesseract.py`

Changes
- Added `tests/test_ocr_tesseract_adapter.py` (creates tiny text image; skips if tesseract missing)

Validation
- `pytest -q tests/test_ocr_tesseract_adapter.py` → pass (or skipped with clear message)

Risk
- Low; test-only
