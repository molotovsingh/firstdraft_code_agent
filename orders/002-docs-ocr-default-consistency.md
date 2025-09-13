# Order 002 — Docs consistency: OCR default is tesseract

Owner: Claude
Scope: Align documentation statements about the OCR default across repo.

Current State
- Code default: `tesseract` (see `apps/block0_worker/worker.py` provider env fallback).
- `.env.example`: comments indicate tesseract by default.
- README.md note says “OCR is stubbed by default” — incorrect.
- CLAUDE.md lists `OCR_PROVIDER` default as `stub` — incorrect.

Acceptance Criteria
- README.md “Notes” section updated to: default is `tesseract`; include how to switch to `stub` and `ocrmypdf`.
- CLAUDE.md Configuration → Environment Variables updated to reflect default `tesseract`.
- `grep -R "OCR is stubbed by default|default: stub" -n .` returns no hits (except in git history).

Validation
- Run the grep check above.
- Sanity: Upload an image via smokes and confirm OCR runs (no code change expected).

Out of Scope
- Changing runtime defaults in code.

Change Log (to include in PR)
- Correct OCR default in README and CLAUDE docs; add quick switch instructions.
