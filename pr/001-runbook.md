# PR: RUNBOOK formatting fixes

- Order: 001
- Scope: Remove stray artifacts and align bullets in `RUNBOOK.md` only

Changes
- Fixed literal header artifacts and ensured H3 headings render
- Aligned service bullet for `migrator` and two mis-indented list items

Validation
- `grep -n "\\n+###" RUNBOOK.md` → no matches
- Visual check renders "OCR Tuning (Advanced)" and "API Auth (Optional)" as H3

Risk
- Low; text-only formatting edits
