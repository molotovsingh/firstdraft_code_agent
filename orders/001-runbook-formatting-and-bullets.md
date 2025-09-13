# Order 001 — RUNBOOK formatting and bullet alignment

Owner: Claude
Scope: Fix markdown formatting artifacts and inconsistent bullet indentation in `RUNBOOK.md` only.

Acceptance Criteria
- Stray sequences like `\n\n+###` are removed; headings render correctly in common viewers.
- Services list uses uniform bullets; `migrator` aligns with peers and spacing is consistent.
- No content changes beyond formatting/indentation.

Validation
- Open `RUNBOOK.md` in a markdown preview; verify sections “OCR Tuning (Advanced)” and “API Auth (Optional)” render as proper H3s.
- `grep -n "\\n\\n+###" RUNBOOK.md` returns no matches.

Out of Scope
- Adding/removing sections or editing other files.

Change Log (to include in PR)
- Normalize markdown headers and bullet alignment in RUNBOOK.
