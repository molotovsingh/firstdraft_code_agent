# Code Review Checklist (used by Code)

Severity levels: Blocker (must fix), Major (should fix before merge), Minor (nice to have).

## Functional

- Acceptance criteria fully met with reproducible evidence. [Severity: Blocker]
- Happy‑path and error handling covered; idempotent operations remain idempotent. [Blocker]
- Backwards compatibility preserved for public APIs and DB schemas. [Blocker]

## Correctness & Tests

- CI/smoke passes (`./scripts/ci_smoke.sh`) or explicit equivalent proof. [Blocker]
- Unit/functional tests added or updated for changed behavior. [Blocker]
- Edge cases addressed (timeouts, retries, partial failures). [Major]

## Security & Tenancy

- AuthN/AuthZ rules enforced; secrets from env; least privilege. [Blocker]
- Multi‑tenant access correctly scoped and filtered. [Blocker]
- Inputs validated; no injection or unsafe deserialization. [Blocker]

## Performance & Reliability

- No pathological N+1 or unbounded loops; reasonable timeouts. [Major]
- External calls wrapped with retries/circuit breakers where applicable. [Major]
- Resource cleanup and error propagation are sound. [Major]

## Docs & Scope

- README/CLAUDE/RUNBOOK updated if behavior or ops changed. [Major]
- Changes are minimal and focused; no unrelated refactors. [Major]
- Clear change log for each bugfix cycle. [Minor]

## Review Output Format

Use this structure when filing findings:

```
Finding <ID>: <short title>
Severity: Blocker|Major|Minor
Details: <what/where/why>
Repro/Proof: <steps or failing test/ref>
Fix Suggestion: <concise guidance>
```

