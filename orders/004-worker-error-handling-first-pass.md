# Order 004 — Worker OCR error handling (first pass)

Owner: Claude
Scope: Improve robustness of OCR steps without changing architecture.

Acceptance Criteria
- `ocrmypdf` invocation wrapped with light retry/backoff (max 2 tries) for transient failures; timeout kept (budget vs recommended respected).
- When OCR fails (images or PDFs), job completes with structured warning, and credits path follows current policy:
  - On full job failure: estimate row closed + `refund_failure` created.
  - On partial OCR issues but pipeline continues: warnings recorded; credits finalized as usual.
- Add a targeted test or script demonstrating the refund path on an induced failure (e.g., malformed PDF), referenced in PR notes.

Validation
- Run `./scripts/ci_smoke.sh` — still passes.
- Manually trigger a failure case and verify credits ledger shows expected rows.

Out of Scope
- Introducing a DLQ or changing queueing infrastructure.
- Broad refactors or new metrics surfaces.

Change Log (to include in PR)
- Add transient retry on `ocrmypdf`; improve warning/credit paths; add demonstration test/script for refund scenario.
