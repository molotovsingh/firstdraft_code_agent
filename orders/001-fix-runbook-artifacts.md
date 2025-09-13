# Order 001-fix — RUNBOOK artifact cleanup (precise)

Owner: Claude
Scope: Apply the exact, minimal edits below to RUNBOOK.md.

Edits (line-based, current HEAD):
- Line 9: remove the leading space before the dash so it reads `- \`migrator\`:`.
- Line 57: replace the literal text `\\n+### OCR Tuning (Advanced)` with an actual blank line followed by `### OCR Tuning (Advanced)`.
- Line 65: replace the literal text `\\n+### API Auth (Optional)` with an actual blank line followed by `### API Auth (Optional)`.
- Line 79: remove the leading space before the dash in the `scripts/smoke_in_network.sh` bullet.
- Line 117: remove the leading space before the dash in the `API healthcheck failing:` bullet.

Notes
- Do not change any other content, ordering, or wording.

Validation
- `grep -n "\\\\n\+###" RUNBOOK.md` returns no matches.
- `sed -n '1,140p' RUNBOOK.md` shows the five lines corrected as above.

Change Log (for PR)
- Fix literal `\\n+###` artifacts; align 3 misindented bullets in RUNBOOK.
