#!/usr/bin/env bash
set -euo pipefail

# Enforce repository policy: no sudo in repo scripts.
# Scans shell scripts under scripts/ for un-commented 'sudo' usage.

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)

violations=0
while IFS= read -r -d '' file; do
  if grep -nE '\\bsudo\\b' "$file" | awk -F: '$0 !~ /^[^:]+:[0-9]+:\\s*#/' >/tmp/sudo_hits.$$ 2>/dev/null; then
    if [[ -s /tmp/sudo_hits.$$ ]]; then
      echo "[policy] Forbidden sudo found in: $file" >&2
      cat /tmp/sudo_hits.$$ >&2
      violations=1
    fi
  fi
  rm -f /tmp/sudo_hits.$$ || true
done < <(find "$ROOT_DIR/scripts" -type f \( -name "*.sh" -o -perm -u+x -o -perm -g+x -o -perm -o+x \) -print0)

if [[ "$violations" -ne 0 ]]; then
  echo "[policy] ERROR: Remove sudo from scripts. See PRIVILEGE_POLICY.md." >&2
  exit 1
fi

echo "[policy] OK: no sudo usage detected in scripts/."

