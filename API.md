# Block 0a API (v0)

Base URL: `http://localhost:8000`

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
      "credit_estimate": 42
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
