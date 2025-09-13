#!/usr/bin/env python3
"""
Offline Block 0a processor (no DB/S3/Redis). Useful when Docker Compose isn't ready.

For each supported file under an input directory, computes basic metrics and warnings
using shared.quality.metrics and writes a processed.json artifact to the output dir.

Supported:
- Images: jpg/jpeg/png (metrics include blur/skew; OCR text length will be 0 here)
- PDFs: page count; no OCR unless ocrmypdf is present (not invoked by default)

Usage:
  python scripts/offline_process_dir.py --in test_documents/Famas_test_case_files --out /tmp/block0_offline/famas
"""
import argparse
import hashlib
import io
import json
import mimetypes
import os
from pathlib import Path

from shared.quality.metrics import compute_metrics_and_warnings
from pypdf import PdfReader


def sha256_hex(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def detect_mime(path: Path) -> str:
    mt, _ = mimetypes.guess_type(str(path))
    return mt or "application/octet-stream"


def process_file(path: Path) -> dict:
    mime = detect_mime(path)
    content = path.read_bytes()
    sha = sha256_hex(content)
    ocr_text = ""  # offline mode: skip OCR; quality metrics still useful
    # Best-effort PDF page count to enrich metrics
    if mime == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            # Let compute_metrics_and_warnings also handle page_count; this enriches inputs
        except Exception:
            pass
    metrics, warnings = compute_metrics_and_warnings(mime, content, ocr_text)
    return {
        "schema_version": 1,
        "filename": path.name,
        "mime": mime,
        "bytes_sha256": sha,
        "artifacts": {
            "original_path": str(path.resolve()),
            "ocr_text": None,
        },
        "metrics": metrics,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="input directory")
    ap.add_argument("--out", dest="out", required=True, help="output directory")
    args = ap.parse_args()

    inp = Path(args.inp)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    supported_ext = {".pdf", ".png", ".jpg", ".jpeg"}
    count = 0
    skipped = 0
    for p in sorted(inp.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in supported_ext:
            skipped += 1
            continue
        try:
            result = process_file(p)
            out_path = out / f"{p.stem}.processed.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            count += 1
            print(f"[ok] {p} -> {out_path}")
        except Exception as e:
            print(f"[err] {p}: {e}")

    print(f"Done. processed={count} skipped={skipped} out={out}")


if __name__ == "__main__":
    main()

