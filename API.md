# Block 0a API (v0)

Base URL: `http://localhost:8000`

## POST /v0/uploads/presign
- JSON body:
  - `tenant_id` (UUID string, required)
  - `user_id` (int, required)
  - `filename` (string, required)
  - `mime` (string, optional; default `application/octet-stream`)

Returns a presigned PUT URL to upload directly to S3/MinIO. No DB writes.

Notes:
- Upload denylist: executables/installers/disk images and similar non-document artefacts (e.g., `.exe`, `.msi`, `.dmg`, `.iso`, `.apk`, VM images like `.vmdk`) are rejected during upload/finalize.
- Configure overrides via environment variables `UPLOAD_DENYLIST_EXTS` and `UPLOAD_DENYLIST_MIMES` (comma-separated).

Response 200:
```json
{
  "object_key": "tenant/ab/abcdef.../v1/orig/file.pdf.1a2b3c4d",
  "url": "http://minio.local/...",
  "expiry": 3600,
  "mime": "application/pdf"
}
```

## GET /v0/uploads/presign_download
Query parameters:
- `key` (string, required): `object_key` returned by presign.
- `expiry` (int, optional; seconds, default 600)

Returns a short-lived presigned GET URL to download the object (for QA).

Response 200:
```json
{
  "url": "http://minio.local/...",
  "expiry": 600
}
```

## POST /v0/uploads/finalize
Finalize a presigned upload by moving it to permanent storage and creating database records.

- JSON body:
  - `tenant_id` (UUID string, required)
  - `user_id` (int, required)
  - `key` (string, required): The `object_key` from presign where file was uploaded
  - `filename` (string, optional): Override filename; otherwise extracted from key
  - `mime` (string, optional): Default `application/octet-stream`

Process:
1. Fetch object from staging
2. Compute SHA256
3. Copy to final storage location
4. Insert Document + Version (v1)
5. Create ProcessingJob and enqueue
6. Insert credit estimate

Response 200:
```json
{
  "document_id": "uuid",
  "job_id": "uuid",
  "version": 1,
  "storage_uri": "tenant/ab/abcdef.../v1/orig/file.pdf",
  "credit_estimate": 42,
  "tenant_balance": -42
}
```

## POST /v0/documents/upload
- Multipart form-data parameters:
  - `tenant_id` (UUID, required)
  - `user_id` (int, required)
  - `case_ref` (string, optional)
  - `quality_mode` (enum: `recommended|budget`, optional)
  - `files` (one or more files)

Response 200:
```json
{
  "documents": [
    {
      "document_id": "<uuid>",
      "job_id": "<uuid>",
      "credit_estimate": 42,
      "tenant_balance": -42
    }
  ]
}
```

## GET /v0/jobs/{id}
Returns processing status and steps.

## GET /v0/documents/{id}/report.json
Returns JSON metadata including warnings and metrics.

## GET /v0/documents/{id}/report.md
Returns Markdown summary.

## GET /v0/documents/{id}/processed.json
Returns a stable machine-readable summary for Block 1 handoff.
```json
{
  "schema_version": 1,
  "document_id": "uuid",
  "version": 1,
  "filename": "foo.pdf",
  "mime": "application/pdf",
  "artifacts": {
    "original_uri": "<s3-key>",
    "ocr_text_uri": "<s3-key>"
  },
  "metrics": {"ocr_confidence": 0.62},
  "warnings": ["Low DPI may reduce OCR accuracy"]
}
```

## GET /metrics
Prometheus exposition endpoint for API process metrics only.
Includes:
- `upload_files_total{tenant_id,mime}`
- `jobs_queued_total{tenant_id}`
- `upload_bytes_total{tenant_id}`
- `upload_handle_seconds` (histogram)

## Credits

### GET /v0/credits/balance
Query:
- `tenant_id` (UUID string, required)
- `user_id` (int, optional)

Response 200:
```json
{ "tenant_id": "uuid", "user_id": 1, "balance": -42, "count": 3 }
```
Notes:
- Positive `balance` means net credits added or refunded; negative means net spend.

### GET /v0/credits/ledger
Query:
- `tenant_id` (UUID string, required)
- `limit` (int, optional; default 50)

Response 200:
```json
{
  "tenant_id": "uuid",
  "items": [
    { "id": 10, "user_id": 1, "delta": 42,  "reason": "estimate_reversal", "job_id": "uuid", "is_estimate": false, "created_at": "2025-09-11T08:00:00Z" },
    { "id": 11, "user_id": 1, "delta": -42, "reason": "actual",             "job_id": "uuid", "is_estimate": false, "created_at": "2025-09-11T08:00:00Z" }
  ]
}
```

### Credit Behavior
- On finalize, an estimate row is inserted (`delta = -estimate`, `reason = "estimate"`, `is_estimate = true`).
- On job success, the worker inserts a compensating reversal for the estimate (`+estimate`, reason `estimate_reversal`) and a new `actual` charge (`-actual`). The original estimate row is marked `is_estimate = false`.
- On job failure, the worker refunds the estimate (`+estimate`, reason `refund_failure`) and marks the estimate row `is_estimate = false`.

### GET /v0/credits/summary
Query:
- `tenant_id` (UUID string, required)

Response 200:
```json
{
  "tenant_id": "uuid",
  "total": -84,
  "by_reason": {"estimate": -42, "estimate_reversal": +42, "actual": -84},
  "pending_estimates": {"count": 0, "sum": 0}
}
```
