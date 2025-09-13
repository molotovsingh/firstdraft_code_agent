# PR: OCRmyPDF adapter — transient retry/backoff

- Order: 004 (partial)
- Scope: Add light retry/backoff around `ocrmypdf` subprocess call

Changes
- `shared/ocr/adapters/ocrmypdf.py`: 3 attempts on `CalledProcessError` or `TimeoutExpired` with 0.5s, 1.0s backoff; preserve empty-result behavior on final failure

Validation
- `pytest -q tests/test_ocrmypdf_adapter_extras.py` → pass
- Normal flow unaffected; adapter interface unchanged

Risk
- Low; contained to adapter; preserves previous behavior on failure
