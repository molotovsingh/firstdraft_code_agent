# PR: Adopt `uv` for installs (Docker) + local docs

- Order: 005
- Scope: Switch Dockerfiles to `uv pip install --system -r requirements.txt` and add short uv usage notes

Changes
- Dockerfiles: `infra/dockerfiles/Dockerfile.api`, `infra/dockerfiles/Dockerfile.worker`
  - Install uv via official script; set PATH to `/root/.local/bin`
  - Use `uv pip install --system -r requirements.txt`
- Docs: README.md and RUNBOOK.md add quick "Using uv" blocks

Validation
- `docker compose -f infra/docker-compose.yml build` → succeeded for api/worker

Risk
- Low; build-time/tooling changes only
