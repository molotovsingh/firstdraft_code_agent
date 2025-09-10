import os
import uuid
from datetime import datetime
import time
from celery import Celery
from structlog import get_logger
from prometheus_client import Counter, Histogram, start_http_server

from shared.db.session import SessionLocal
from shared.db import models
from shared.db.models import ProcessingStatus
from shared.quality.metrics import compute_metrics_and_warnings
from shared.storage.s3 import Storage
from PIL import Image
import io
import pytesseract
import tempfile
import subprocess
from pytesseract import Output
from shared.quality.normalize import deskew_image_bytes

log = get_logger()

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery("block0")
celery_app.conf.broker_url = CELERY_BROKER_URL
celery_app.conf.result_backend = CELERY_RESULT_BACKEND

# Optional Prometheus metrics server (disabled unless METRICS_PORT is set)
try:
    _metrics_port = os.getenv("METRICS_PORT")
    if _metrics_port:
        start_http_server(int(_metrics_port))
        log.info("worker_metrics_server_started", port=_metrics_port)
except Exception:
    log.exception("worker_metrics_server_failed")

# Worker metrics
OCR_DURATION_SECONDS = Histogram(
    "worker_ocr_duration_seconds",
    "Time spent performing OCR per document",
    labelnames=["mime"],
)
JOBS_PROCESSED_TOTAL = Counter(
    "worker_jobs_processed_total",
    "Jobs processed by worker",
    labelnames=["status"],
)
PAGES_PROCESSED_TOTAL = Counter(
    "worker_pages_processed_total",
    "Pages processed (approx; images count as 1)",
    labelnames=["mime"],
)


def enqueue_process_document(job_id: str) -> None:
    process_document.delay(job_id)


@celery_app.task(name="process_document")
def process_document(job_id: str):
    db = SessionLocal()
    try:
        job = db.get(models.ProcessingJob, uuid.UUID(job_id))
        if job is None:
            log.error("job_not_found", job_id=job_id)
            return
        job.status = ProcessingStatus.running
        job.started_at = datetime.utcnow()
        job.steps = ["normalize", "ocr", "quality", "finalize"]
        db.commit()

        # Load document/version
        ver = (
            db.query(models.DocumentVersion)
            .filter(models.DocumentVersion.document_id == job.document_id)
            .order_by(models.DocumentVersion.version.desc())
            .first()
        )
        if not ver:
            raise RuntimeError("document_version_missing")

        # Minimal OCR implementation: images only (ENG). PDFs get a placeholder warning.
        doc = db.get(models.Document, job.document_id)
        storage = Storage()
        ocr_text = ""
        metrics = {}
        warnings = []

        try:
            original_bytes = storage.get_object_bytes(ver.storage_uri)
            t0 = time.perf_counter()
            if doc.mime and doc.mime.lower().startswith("image/"):
                # Optional auto-deskew if needed
                lang = os.getenv("OCR_LANG", "eng")
                used_bytes = original_bytes
                # Try deskew; if applied, re-run OCR on rotated image
                rotated_bytes, applied_deg = deskew_image_bytes(original_bytes)
                if abs(applied_deg) > 0.0:
                    warnings = (warnings or []) + [f"Auto-deskew applied (~{applied_deg:.1f}°)"]
                    used_bytes = rotated_bytes
                pil_img = Image.open(io.BytesIO(used_bytes))
                # Text
                text = pytesseract.image_to_string(pil_img, lang=lang)
                ocr_text = text or ""
                # Confidence (average over valid words)
                try:
                    data = pytesseract.image_to_data(pil_img, lang=lang, output_type=Output.DICT)
                    confs = [int(c) for c in data.get('conf', []) if c not in ("-1", "-")]
                    conf_vals = [c for c in confs if c >= 0]
                    if conf_vals:
                        avg_conf = sum(conf_vals) / len(conf_vals)
                        # put into metrics after computation below
                        metrics = metrics or {}
                        metrics["ocr_confidence_avg"] = round(float(avg_conf) / 100.0, 3)
                except Exception:
                    # ignore confidence errors but continue
                    pass
                # update original_bytes for metrics calculation later
                original_bytes = used_bytes
            elif doc.mime == "application/pdf":
                # Minimal PDF OCR via ocrmypdf sidecar text
                lang = os.getenv("OCR_LANG", "eng")
                with tempfile.TemporaryDirectory() as td:
                    in_pdf = f"{td}/in.pdf"
                    out_pdf = f"{td}/out.pdf"
                    sidecar = f"{td}/out.txt"
                    with open(in_pdf, "wb") as f:
                        f.write(original_bytes)
                    cmd = [
                        "ocrmypdf",
                        "--language", lang,
                        "--sidecar", sidecar,
                        "--skip-text",
                        in_pdf,
                        out_pdf,
                    ]
                    try:
                        subprocess.run(cmd, check=True, capture_output=True)
                        try:
                            with open(sidecar, "r", encoding="utf-8", errors="ignore") as sf:
                                ocr_text = sf.read()
                        except FileNotFoundError:
                            warnings = (warnings or []) + ["PDF OCR produced no sidecar text"]
                            ocr_text = ""
                    except subprocess.CalledProcessError as e:
                        warnings = (warnings or []) + ["PDF OCR failed; see logs"]
                        log.error("ocrmypdf_failed", returncode=e.returncode, stderr=e.stderr.decode(errors="ignore"))
                        ocr_text = ""
            # Observe duration
            OCR_DURATION_SECONDS.labels(mime=(doc.mime or "unknown").lower()).observe(time.perf_counter() - t0)
        else:
            warnings = (warnings or []) + [f"Unsupported MIME for OCR at this stage: {doc.mime}"]
            ocr_text = ""
        except Exception as e:
            warnings = (warnings or []) + [f"OCR error: {e}"]
            log.exception("ocr_failed", job_id=job_id)

        # Store OCR text as object for consistency
        tenant_id = str(doc.tenant_id)
        sha = doc.bytes_sha256
        ocr_key = f"{tenant_id}/{sha[:2]}/{sha}/v{ver.version}/ocr/combined.txt"
        storage.put_object(ocr_key, ocr_text.encode("utf-8"), content_type="text/plain; charset=utf-8")

        # Update version
        # For images, set page_count=1 if not present
        if doc.mime and doc.mime.lower().startswith("image/"):
            metrics = metrics or {}
            metrics.setdefault("page_count", 1)
        # Compute metrics & warnings (image blur/skew, language, density)
        m2, w2 = compute_metrics_and_warnings(doc.mime, original_bytes, ocr_text)
        metrics.update(m2 or {})
        warnings = (warnings or []) + (w2 or [])
        ver.metrics = metrics
        ver.warnings = warnings
        ver.ocr_text_uri = ocr_key
        db.commit()

        # Finalize credits (replace estimate with actual if needed)
        estimate_credit = (
            db.query(models.Credit)
            .filter(models.Credit.job_id == job.id, models.Credit.is_estimate == True)
            .first()
        )
        if estimate_credit:
            # In stub, actual == estimate
            estimate_credit.is_estimate = False
            db.commit()

        job.status = ProcessingStatus.succeeded
        job.finished_at = datetime.utcnow()
        db.commit()
        # Metrics: jobs + pages
        JOBS_PROCESSED_TOTAL.labels(status="succeeded").inc()
        page_count = metrics.get("page_count") if isinstance(metrics, dict) else None
        if isinstance(page_count, int) and page_count > 0:
            PAGES_PROCESSED_TOTAL.labels(mime=(doc.mime or "unknown").lower()).inc(page_count)
        log.info("job_succeeded", job_id=job_id)
    except Exception as e:
        log.exception("job_failed", job_id=job_id)
        job = db.get(models.ProcessingJob, uuid.UUID(job_id)) if 'job' in locals() else None
        if job:
            job.status = ProcessingStatus.failed
            job.error = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
        JOBS_PROCESSED_TOTAL.labels(status="failed").inc()
    finally:
        db.close()
