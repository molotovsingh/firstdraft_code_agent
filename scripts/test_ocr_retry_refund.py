#!/usr/bin/env python3
"""
End-to-end smoke to demonstrate OCR retry behaviour and refund path.

This script inserts a document whose PDF bytes are intentionally corrupted so
`ocrmypdf` fails even after retries. The worker should mark the job as failed
and issue a `refund_failure` credit row, closing the original estimate.

Run from the API container:

  docker compose -f infra/docker-compose.yml exec api python scripts/test_ocr_retry_refund.py
"""

import os
import sys
import time
import uuid
import random
from dataclasses import dataclass

from shared.db.session import SessionLocal
from shared.db import models
from shared.db.models import ProcessingStatus
from shared.quality.metrics import estimate_credits
from shared.storage.s3 import Storage
from apps.block0_worker.worker import enqueue_process_document


def env_or(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def _store_corrupted_pdf(storage: Storage, tenant_id: str) -> str:
    key = f"{tenant_id}/ff/{uuid.uuid4().hex}/v1/orig/corrupted.pdf"
    garbage = os.urandom(2048)  # invalid PDF bytes
    storage.put_object(key, garbage, content_type="application/pdf")
    return key


def _print_latest_credits(db: SessionLocal, tenant_id: uuid.UUID, limit: int = 5) -> None:
    rows = (
        db.query(models.Credit)
        .filter(models.Credit.tenant_id == tenant_id)
        .order_by(models.Credit.created_at.desc())
        .limit(limit)
        .all()
    )
    for row in rows:
        print(
            f"  credit id={row.id} user={row.user_id} delta={row.delta} reason={row.reason} "
            f"estimate={bool(row.is_estimate)} job={str(row.job_id) if row.job_id else '-'}"
        )


def main() -> None:
    tenant_id_str = env_or("UI_TENANT_ID", "11111111-1111-1111-1111-111111111111")
    user_id = int(env_or("UI_USER_ID", "1"))
    tenant_uuid = uuid.UUID(tenant_id_str)

    db = SessionLocal()
    storage = Storage()
    try:
        tenant = db.get(models.Tenant, tenant_uuid)
        if not tenant:
            print("[ocr-refund] Tenant not found. Run bootstrap_dev.py first?", file=sys.stderr)
            sys.exit(2)
        user = db.get(models.User, user_id)
        if not user or str(user.tenant_id) != tenant_id_str:
            print("[ocr-refund] UI_USER_ID does not belong to tenant.", file=sys.stderr)
            sys.exit(2)

        storage_key = _store_corrupted_pdf(storage, tenant_id_str)
        est = estimate_credits("application/pdf", 2_048)

        doc = models.Document(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            user_id=user.id,
            orig_filename="corrupted.pdf",
            mime="application/pdf",
            bytes_sha256=uuid.uuid4().hex,
        )
        db.add(doc)
        db.flush()

        ver = models.DocumentVersion(
            document_id=doc.id,
            version=1,
            storage_uri=storage_key,
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

        estimate_row = models.Credit(
            tenant_id=tenant.id,
            user_id=user.id,
            delta=-abs(int(est)),
            reason="estimate",
            job_id=job.id,
            is_estimate=True,
        )
        db.add(estimate_row)
        db.commit()

        print(f"[ocr-refund] Enqueued job {job.id} with corrupted PDF to force OCR retry failure")
        enqueue_process_document(str(job.id))

        deadline = time.time() + 90
        while time.time() < deadline:
            latest = db.get(models.ProcessingJob, job.id)
            if latest and latest.status in (ProcessingStatus.failed, ProcessingStatus.succeeded):
                job = latest
                break
            time.sleep(1)
            db.expire_all()

        print(f"[ocr-refund] Final job status: {job.status}")
        if job.status != ProcessingStatus.failed:
            print("[ocr-refund] Expected failure to demonstrate refund. Inspect worker logs.")
        else:
            print("[ocr-refund] Failure confirmed. Recent ledger entries:")
            _print_latest_credits(db, tenant.id)
            print("[ocr-refund] Look for reason=refund_failure and estimate closed (is_estimate=False).")
    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
