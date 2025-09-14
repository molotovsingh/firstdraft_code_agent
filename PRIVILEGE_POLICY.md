# Privilege Escalation Policy

This repository follows a strict operator-only policy for any command that requires elevated privileges.

- Sudo/root actions are performed by the operator only (you), never by repository scripts or agents.
- Project scripts and automation MUST NOT call `sudo` or assume root.
- Documentation will list any required privileged commands as explicit, manual steps for the operator to run.
- Third‑party installers (e.g., Docker’s install script) are not modified; use them manually as needed.

## Operator Checklist (manual)
- System package installs (apt, yum, dnf, brew cask, snap) when they require `sudo`.
- Docker installation and host configuration (adding user to `docker` group, daemon restarts).
- Any command that writes to privileged system paths (e.g., `/usr/local/bin`, `/etc/*`).

## Non‑root Development Workflow
- All day‑to‑day dev commands run as an unprivileged user.
- Use `docker compose` (v2) without sudo by ensuring your user is in the `docker` group.
- If a step appears to require `sudo`, pause and perform it manually as the operator; do not bake it into scripts.

If anything violates this policy, file a bug and remove the `sudo` usage.

