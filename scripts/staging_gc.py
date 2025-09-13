"""
Sweep orphaned staging uploads created by presign that were never finalized.

Heuristic: staging keys contain "/orig/" in the path (e.g., .../v1/orig/<filename>.<suffix>).
We delete such objects older than TTL hours.

Usage:
  API_BASE=http://localhost:8000 python scripts/staging_gc.py [--prefix <tenant_id>/] [--ttl-hours 48] [--dry-run]
"""

import argparse
from datetime import datetime, timedelta, timezone
from shared.storage.s3 import Storage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="", help="Optional S3 prefix to limit scanning, e.g., <tenant_id>/")
    ap.add_argument("--ttl-hours", type=int, default=48, help="Delete objects older than this many hours")
    ap.add_argument("--dry-run", action="store_true", help="List deletions without performing them")
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.ttl_hours)
    s = Storage()
    to_delete = []
    scanned = 0
    for obj in s.list_objects(prefix=args.prefix, recursive=True):
        scanned += 1
        try:
            name = obj.object_name
            if "/orig/" not in name:
                continue
            lm = obj.last_modified
            if lm and lm < cutoff:
                to_delete.append(name)
        except Exception:
            continue

    print(f"Scanned={scanned} candidates={len(to_delete)} ttl_hours={args.ttl_hours}")
    if args.dry_run:
        for k in to_delete[:200]:
            print("would delete:", k)
        if len(to_delete) > 200:
            print("... and", len(to_delete) - 200, "more")
        return

    # Delete in batches
    BATCH = 1000
    for i in range(0, len(to_delete), BATCH):
        s.remove_objects(to_delete[i : i + BATCH])
    print("Deleted", len(to_delete), "objects")


if __name__ == "__main__":
    main()

