#!/usr/bin/env python3
"""
End-to-end smoke test for presigned upload -> finalize -> processing.
"""
import json
import time
import requests
import sys
import os

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TENANT_ID = os.getenv("TENANT_ID", "11111111-1111-1111-1111-111111111111")
USER_ID = int(os.getenv("USER_ID", "1"))


def wait_for_api(base: str, timeout: int = 120):
    print("[smoke] Waiting for API health...")
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{base}/healthz", timeout=5)
            if r.status_code == 200:
                print("[smoke] API is healthy")
                return
        except Exception as e:
            last_err = e
        time.sleep(5)
    print(f"[smoke] API did not become healthy in {timeout}s: {last_err}")
    sys.exit(2)


def _retry(func, tries=5, backoff=1.5, initial=1.0):
    delay = initial
    for i in range(tries):
        try:
            return func()
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"[smoke] retrying after error: {e} (sleep {delay:.1f}s)")
            time.sleep(delay)
            delay *= backoff


def main():
    test_content = b"This is a test document for the finalize flow.\nLine 2.\nLine 3.\n"
    filename = os.getenv("SMOKE_FILENAME", "test_finalize.txt")
    mime = os.getenv("SMOKE_MIME", "text/plain")

    print("=== Presigned Upload + Finalize Flow Test ===\n")

    # Step 0: Wait for API
    wait_for_api(API_BASE, timeout=120)

    # Step 1: Get presigned URL
    print("1. Getting presigned upload URL...")
    presign_resp = _retry(lambda: requests.post(
        f"{API_BASE}/v0/uploads/presign",
        json={
            "tenant_id": TENANT_ID,
            "user_id": USER_ID,
            "filename": filename,
            "mime": mime,
        },
        timeout=30,
    ))
    presign_resp.raise_for_status()
    presign_data = presign_resp.json()
    upload_url = presign_data["url"]
    object_key = presign_data["object_key"]
    print(f"   Got presigned URL for key: {object_key}")

    # Step 2: Upload directly to S3/MinIO
    print("\n2. Uploading content directly to S3...")
    upload_resp = requests.put(upload_url, data=test_content, headers={"Content-Type": mime}, timeout=60)
    if upload_resp.status_code not in (200, 201, 204):
        print(f"Error uploading to S3: {upload_resp.status_code}")
        print(upload_resp.text)
        sys.exit(1)
    print("   Upload successful")

    # Step 3: Finalize the upload
    print("\n3. Finalizing upload...")
    finalize_resp = _retry(lambda: requests.post(
        f"{API_BASE}/v0/uploads/finalize",
        json={
            "tenant_id": TENANT_ID,
            "user_id": USER_ID,
            "key": object_key,
            "filename": filename,
            "mime": mime,
        },
        timeout=60,
    ))
    finalize_resp.raise_for_status()
    finalize_data = finalize_resp.json()
    document_id = finalize_data["document_id"]
    job_id = finalize_data["job_id"]
    print(f"   Document ID: {document_id}\n   Job ID: {job_id}")

    # Step 4: Poll job status
    print("\n4. Polling job status...")
    for _ in range(60):  # up to ~60 seconds
        job_resp = requests.get(f"{API_BASE}/v0/jobs/{job_id}", timeout=15)
        job_resp.raise_for_status()
        job_data = job_resp.json()
        status = job_data["status"]
        print(f"   Status: {status}")
        if status in ("succeeded", "failed"):
            break
        time.sleep(1)

    # Step 5: Fetch processed document
    print("\n5. Fetching processed document...")
    processed_resp = requests.get(f"{API_BASE}/v0/documents/{document_id}/processed.json", timeout=30)
    processed_resp.raise_for_status()
    processed_data = processed_resp.json()
    print(f"   Version: {processed_data['version']}")
    print(f"   Metrics: {json.dumps(processed_data['metrics'], indent=2)}")
    print(f"   Warnings: {processed_data['warnings']}")
    print("\n✅ Smoke finalize flow OK")


if __name__ == "__main__":
    main()
