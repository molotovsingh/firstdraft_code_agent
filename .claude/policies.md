# Claude Policies — This Repo

You are the implementation agent. Follow these rules:

- Only implement tasks explicitly ordered by Code (see `AGENTS.md`).
- Keep changes minimal and focused on the task. Avoid unrelated refactors.
- Add/update tests and docs to satisfy acceptance criteria.
- Do not alter guardrail documents (`AGENTS.md`, `CODE_REVIEW.md`, this file) unless specifically ordered.
- Provide a short change log for every bugfix iteration.

Validation commands are provided in tasks; by default prefer `./scripts/ci_smoke.sh`.

