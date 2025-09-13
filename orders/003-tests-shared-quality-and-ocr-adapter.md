# Order 003 — Minimal tests for shared quality + OCR adapter

Owner: Claude
Scope: Add first-slice unit tests covering `shared/quality/metrics.py::compute_metrics_and_warnings` and `shared/ocr/adapters/tesseract.py`.

Acceptance Criteria
- New tests under `tests/`:
  - `test_quality_metrics_basic.py`: happy-path on a simple small image; one low-quality/synthetic case exercising warning path.
  - `test_ocr_tesseract_adapter.py`: generate a tiny image with text; call adapter; assert non-empty text when Tesseract is available.
- `test_ocr_tesseract_adapter.py` is skipped with a clear message if Tesseract binary is missing (do not fail CI).
- Tests run fast (<5s locally) and do not require Docker services.

Validation
- `pytest -q` runs and passes locally.
- `./scripts/ci_smoke.sh` still passes.

Out of Scope
- PDF OCR tests and performance benchmarking.
- Broad refactors in shared libs.

Change Log (to include in PR)
- Add minimal unit tests for quality metrics and Tesseract adapter with graceful skip.
