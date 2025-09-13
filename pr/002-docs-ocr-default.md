# PR: Docs consistency — OCR default is tesseract

- Order: 002
- Scope: Correct documentation to reflect default OCR provider

Changes
- README.md: Notes → "Default OCR provider is tesseract…"
- CLAUDE.md: `OCR_PROVIDER` default updated to `tesseract`

Validation
- `grep -R "OCR is stubbed by default|default: stub" -n .` → no matches (except in order text)

Risk
- Low; docs-only
