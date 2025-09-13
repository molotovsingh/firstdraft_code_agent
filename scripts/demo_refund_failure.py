#!/usr/bin/env python3
"""
Demo: trigger a worker failure → credits refund.

How it works:
- Creates a Document + Version pointing to a non-existent storage key.
- Adds a queued ProcessingJob and an estimate credit row.
- Enqueues the job; the worker fails when fetching bytes, triggering refund.

Run inside the API container:
  docker compose -f infra/docker-compose.yml exec api python scripts/demo_refund_failure.py
"""
import os
import sys
import time
import uuid
from dataclasses import dataclass

from shared.db.session import SessionLocal
from shared.db import models
from shared.db.models import ProcessingStatus
from shared.quality.metrics import estimate_credits
from apps.block0_worker.worker import enqueue_process_document


def env_or(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v else default


def main():
    tenant_id = env_or("UI_TENANT_ID", "11111111-1111-1111-1111-111111111111")
    user_id = int(env_or("UI_USER_ID", "1"))
    fake_key = f"{tenant_id}/zz/does-not-exist/v1/orig/broken.pdf"
    mime = "application/pdf"
    est = estimate_credits(mime, 1024)

    db = SessionLocal()
    try:
        tenant = db.get(models.Tenant, uuid.UUID(tenant_id))
        if not tenant:
            print("[refund-demo] No tenant found. Did you run bootstrap_dev.py?", file=sys.stderr)
            sys.exit(2)
        user = db.get(models.User, user_id)
        if not user or str(user.tenant_id) != tenant_id:
            print("[refund-demo] Invalid UI_USER_ID for tenant.", file=sys.stderr)
            sys.exit(2)

        doc = models.Document(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            case_ref=None,
            orig_filename="broken.pdf",
            mime=mime,
            bytes_sha256=uuid.uuid4().hex,
        )
        db.add(doc)
        db.flush()

        ver = models.DocumentVersion(
            document_id=doc.id,
            version=1,
            storage_uri=fake_key,  # non-existent key
        )
        db.add(ver)
        db.flush()

        job = models.ProcessingJob(
            id=uuid.uuid4(),
            document_id=doc.id,
            status=ProcessingStatus.queued,
        )
        db.add(job)
        db.flush()

        credit = models.Credit(
            tenant_id=tenant.id,
            user_id=user.id,
            delta=-abs(int(est)),
            reason="estimate",
            job_id=job.id,
            is_estimate=True,
        )
        db.add(credit)
        db.commit()

        print(f"[refund-demo] Enqueued job {job.id} for fake key → expect failure + refund")
        enqueue_process_document(str(job.id))

        # Poll for failure
        deadline = time.time() + 60
        while time.time() < deadline:
            j = db.get(models.ProcessingJob, job.id)
            if j and j.status in (ProcessingStatus.failed, ProcessingStatus.succeeded):
                job = j
                break
            time.sleep(1)
            db.expire_all()

        if job.status != ProcessingStatus.failed:
            print(f"[refund-demo] Unexpected status: {job.status}. Check worker logs.")
        else:
            print("[refund-demo] Job failed as expected. Fetching recent credits…")
            rows = (
                db.query(models.Credit)
                .filter(models.Credit.tenant_id == tenant.id)
                .order_by(models.Credit.created_at.desc())
                .limit(5)
                .all()
            )
            for r in rows:
                print(
                    f"  credit id={r.id} user={r.user_id} delta={r.delta} reason={r.reason} "
                    f"estimate={bool(r.is_estimate)} job={str(r.job_id) if r.job_id else '-'}"
                )
            print("[refund-demo] Look for reason=refund_failure and original estimate closed (is_estimate=False).")
    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()

