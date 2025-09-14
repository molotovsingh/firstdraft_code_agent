# Docker Installation (Operator-Only)

If you need Docker or Docker Compose v2 on your host, follow the official installation docs or use Docker’s installer script. These steps typically require `sudo` and must be run manually by the operator.

References:
- https://docs.docker.com/engine/install/
- https://docs.docker.com/compose/install/

Notes:
- Our repository does not run privileged commands. Do not bake `sudo` into scripts or CI.
- After installation, add your user to the `docker` group to use `docker` without sudo, then re‑login:

```
# Operator-only (requires sudo)
sudo usermod -aG docker "$USER"
newgrp docker # or log out/in
docker run --rm hello-world
```

The bundled `get-docker.sh` is an upstream script for convenience and is not modified by this repo. Execute it manually if you choose to use it.

