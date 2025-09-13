# Gemini — Repo Reading Playbook

Gemini acts as the repository analyst. Do not modify code. Produce concise, actionable analysis.

## Deliverable

Create a report (preferred: `reports/<date>-gemini-read.md`) covering:

- Ownership map: main services, modules, and their responsibilities
- Entrypoints: binaries, scripts, Docker compose targets, CI entrypoints
- Data model: DB schemas, key relations, migrations hotspots
- Interfaces: public APIs, CLI commands, message queues, storage contracts
- Risks: migrations, security/authz, tenancy, idempotency, performance, cost
- Test surface: current tests to extend; must‑add test ideas for the change
- Suggested plan: 3–6 steps to implement the asked change safely
- Impacted files: list with rationale and potential conflicts

## Constraints

- Read‑only. No code edits or auto‑formatting.
- Prefer links to files and line ranges; avoid long quotes.
- Keep the report under 500 lines; prioritize signal.

## Invocation Snippet

See `AGENTS.md` → Invocation Patterns → “Ask Gemini for a Repo Read”.

