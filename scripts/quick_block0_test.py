#!/usr/bin/env python3
"""
Quick Block 0a test with a few real-world documents to validate functionality.
"""
import os
import sys
import json
import time
from pathlib import Path
import requests

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TENANT_ID = os.getenv("TEST_TENANT_ID", "11111111-1111-1111-1111-111111111111")
USER_ID = int(os.getenv("TEST_USER_ID", "1"))

# Use localhost MinIO endpoint for external access
os.environ.setdefault("S3_PUBLIC_ENDPOINT_URL", "http://localhost:9000")

def test_single_document(file_path: Path):
    """Test processing of a single document."""
    print(f"🔍 Testing: {file_path.name}")
    print(f"   Size: {file_path.stat().st_size / (1024*1024):.1f}MB")

    # Determine MIME type
    suffix = file_path.suffix.lower()
    mime_map = {
        '.pdf': 'application/pdf',
        '.jpeg': 'image/jpeg', '.jpg': 'image/jpeg',
        '.png': 'image/png', '.tiff': 'image/tiff'
    }
    mime_type = mime_map.get(suffix, 'application/octet-stream')

    try:
        start_time = time.time()

        # 1. Presign
        print("   📤 Requesting presigned URL...")
        presign_resp = requests.post(f"{API_BASE}/v0/uploads/presign", json={
            "tenant_id": TENANT_ID,
            "user_id": USER_ID,
            "filename": file_path.name,
            "mime": mime_type
        })
        presign_resp.raise_for_status()
        presign_data = presign_resp.json()

        # 2. Upload
        print("   ⬆️  Uploading to S3...")
        with open(file_path, 'rb') as f:
            upload_resp = requests.put(presign_data["url"], data=f)
            upload_resp.raise_for_status()

        # 3. Finalize
        print("   🔐 Finalizing upload...")
        finalize_resp = requests.post(f"{API_BASE}/v0/uploads/finalize", json={
            "tenant_id": TENANT_ID,
            "user_id": USER_ID,
            "key": presign_data["object_key"],
            "filename": file_path.name,
            "mime": mime_type
        })
        finalize_resp.raise_for_status()
        finalize_data = finalize_resp.json()

        job_id = finalize_data["job_id"]
        document_id = finalize_data["document_id"]

        print(f"   🆔 Document ID: {document_id}")
        print(f"   🆔 Job ID: {job_id}")
        print(f"   💰 Credit estimate: {finalize_data.get('credit_estimate')}")

        # 4. Wait for processing
        print("   ⏳ Waiting for processing...")
        max_wait = 120  # 2 minutes
        start_wait = time.time()

        while time.time() - start_wait < max_wait:
            job_resp = requests.get(f"{API_BASE}/v0/jobs/{job_id}")
            job_resp.raise_for_status()
            job_data = job_resp.json()

            status = job_data.get("status")
            print(f"   📊 Status: {status}")

            if status == "succeeded":
                break
            elif status == "failed":
                print(f"   ❌ Job failed: {job_data.get('error')}")
                return False

            time.sleep(3)
        else:
            print("   ⏰ Timeout waiting for job completion")
            return False

        total_time = time.time() - start_time
        print(f"   ⏱️  Total time: {total_time:.1f}s")

        # 5. Get results
        print("   📄 Fetching results...")
        report_resp = requests.get(f"{API_BASE}/v0/documents/{document_id}/report.json")
        report_resp.raise_for_status()
        report = report_resp.json()

        processed_resp = requests.get(f"{API_BASE}/v0/documents/{document_id}/processed.json")
        processed_resp.raise_for_status()
        processed = processed_resp.json()

        # Display results
        print("   📊 Results:")
        warnings = report.get("warnings", [])
        metrics = report.get("metrics", {})

        print(f"      Warnings: {len(warnings)}")
        for warning in warnings[:3]:  # Show first 3
            print(f"        • {warning}")

        print(f"      Metrics: {len(metrics)}")
        for key, value in list(metrics.items())[:3]:  # Show first 3
            print(f"        • {key}: {value}")

        artifacts = processed.get("artifacts", {})
        print(f"      Artifacts: {list(artifacts.keys())}")

        print("   ✅ SUCCESS")
        return True

    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        return False


def main():
    """Run quick test on selected real-world documents."""
    print("🚀 Quick Block 0a Real-World Test")
    print("=" * 50)

    # Check health
    try:
        health_resp = requests.get(f"{API_BASE}/healthz", timeout=5)
        health_data = health_resp.json()
        print(f"🏥 Health: {health_data.get('status')}")
        if health_data.get('status') != 'ok':
            print(f"   Components: {health_data.get('components')}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return

    # Test documents directory
    test_dir = Path(__file__).parent.parent / "test_documents"
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return

    # Select a few test files for quick validation
    test_files = []

    # From Famas case - try a PDF
    famas_dir = test_dir / "Famas_test_case_files"
    if famas_dir.exists():
        pdf_files = list(famas_dir.glob("*.pdf"))
        if pdf_files:
            test_files.append(pdf_files[0])  # First PDF

    # From Igyan case - try a PDF and an image
    igyan_dir = test_dir / "igyan_test_case_files" / "IGYAN_Defemation"
    if igyan_dir.exists():
        pdf_files = list(igyan_dir.glob("*.pdf"))
        img_files = list(igyan_dir.glob("*.jpeg"))

        if pdf_files:
            test_files.append(pdf_files[0])  # First PDF
        if img_files:
            test_files.append(img_files[0])  # First image

    if not test_files:
        print("❌ No test files found")
        return

    print(f"📄 Testing {len(test_files)} documents:")
    for f in test_files:
        print(f"   • {f.name}")
    print()

    # Run tests
    results = []
    for test_file in test_files:
        success = test_single_document(test_file)
        results.append((test_file.name, success))
        print()

    # Summary
    print("=" * 50)
    print("📊 SUMMARY")
    successful = sum(1 for _, success in results if success)
    total = len(results)

    print(f"   Total: {total}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {total - successful}")
    print(f"   Success rate: {successful/total*100:.1f}%")

    for name, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {name}")

    if successful == total:
        print("\n🎉 All tests passed! Block 0a is working well with real documents.")
    elif successful > total // 2:
        print(f"\n⚠️  Most tests passed ({successful}/{total}). Some improvements needed.")
    else:
        print(f"\n❌ Many tests failed ({total-successful}/{total}). Block 0a needs attention.")


if __name__ == "__main__":
    main()