# Multi‑Agent Workflow

This repository is operated with a strict multi‑agent process:

- Role: Code (you are here)
  - Orchestrates work, defines tasks, reviews deliverables, and files bugfix orders.
  - Writes plans and checklists only; does not write application code.

- Role: Claude (implementation)
  - Writes and modifies code, docs, tests, infra, and fixes bugs identified in review.
  - Must follow tasks/specs issued by Code and pass the review checklist.

- Role: Gemini (repo analysis)
  - Reads the repo, maps architecture, identifies impacts, risks, and suggests approaches.
  - Produces concise reports and design nudges; makes no code changes.

## Operating Loop

1) Task Order (Code)
   - Define scope, acceptance criteria, constraints, and interfaces.
   - Request a Gemini Read‑Through Report (see template below) when context is needed.

2) Repo Read (Gemini)
   - Deliver the report only; no edits. Include file references and risks.

3) Implementation (Claude)
   - Implement exactly what is ordered. Update/extend tests and docs as required.
   - Keep changes scoped and cohesive. Avoid unrelated refactors.

4) Review (Code)
   - Use `CODE_REVIEW.md` checklist. File bugs or change requests as separate tasks.

5) Bugfix / Iteration (Claude)
   - Address all blocking items. Provide a short change log per fix cycle.

6) Done (Code)
   - Verify DoD met and merge readiness.

## Definition of Done (DoD)

- All acceptance criteria satisfied and documented.
- CI/Smoke scripts pass (`./scripts/ci_smoke.sh`) or equivalent validation noted.
- New/changed behavior covered by tests (unit or smoke, as appropriate).
- Public interfaces and runbooks updated when affected.
- No critical/severe review findings outstanding.

## Invocation Patterns (Codex CLI)

Use agents with the CLI’s agent runner. Examples below assume the CLI has access to the repo root.

### Ask Gemini for a Repo Read

Task: “Provide a repo read‑through: ownership map, entrypoints, risks, test surface, and suggested approach for <feature>. No code changes.”

Suggested launch (operator):

```
agent_run {
  "task": "Repo read-through and suggestions for <feature>",
  "context": "Root: project repo. No edits.",
  "files": ["."],
  "model": "gemini",
  "output": "Read-through report with risks + plan",
  "read_only": true
}
```

Deliverable: `reports/<timestamp>-gemini-read.md` or message output.

### Order Claude to Implement

Task: “Implement <feature> per AGENTS.md and acceptance criteria. Include tests and docs. Keep changes minimal and focused.”

Suggested launch (operator):

```
agent_run {
  "task": "Implement <feature> with tests + docs",
  "context": "Service: <path>. Env via .env. CI: ./scripts/ci_smoke.sh",
  "files": ["apps", "shared", "infra", "tests"],
  "model": "claude",
  "output": "PR-ready changes + passing validation",
  "read_only": false
}
```

### Order Claude to Fix Bugs

Task: “Fix issues from Code review (IDs listed) without scope creep. Provide a concise change log.”

```
agent_run {
  "task": "Bugfix cycle <n> for <PR/feature>",
  "context": "Apply CODE_REVIEW findings only.",
  "files": ["."],
  "model": "claude",
  "output": "All blocking items resolved",
  "read_only": false
}
```

## Templates

### Gemini Read‑Through Prompt

- Objective: <what we plan to build/modify>
- Top‑level map: components, entrypoints, key configs
- Risk register: migrations, API breaks, non‑idempotence, security, perf
- Test surface: existing tests to extend, gaps to add
- Suggested plan: 3–6 steps, with smallest viable increments
- Impacted files: list with rationale

### Claude Implementation Prompt

- Task: <clear, bounded description>
- Acceptance criteria: bullet list (testable)
- Constraints: style, interfaces, perf, security, tenancy, backwards compat
- Validation: exact commands (tests, smoke)
- Out‑of‑scope: explicitly list to avoid scope creep

## Guardrails

- Only Code may approve merges and move tasks to Done.
- Claude does not bypass review gates or modify guardrail docs without order.
- Gemini never writes/commits code.
- No `sudo`/root commands by any agent. If a privileged step is required, request an operator-run step and document it in `PRIVILEGE_POLICY.md`.
