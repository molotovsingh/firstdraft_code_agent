#!/usr/bin/env python3
"""
Test Block 0a with real-world client documents from test_documents/ folder.

This script tests the "Never Reject, Always Warn" philosophy with actual legal documents
from two client cases: Famas (arbitration) and Igyan (defamation).
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add shared modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TENANT_ID = os.getenv("TEST_TENANT_ID", "11111111-1111-1111-1111-111111111111")
USER_ID = int(os.getenv("TEST_USER_ID", "1"))

# Test document directories
TEST_DOCS_DIR = Path(__file__).parent.parent / "test_documents"
FAMAS_DIR = TEST_DOCS_DIR / "Famas_test_case_files"
IGYAN_DIR = TEST_DOCS_DIR / "igyan_test_case_files" / "IGYAN_Defemation"

class Block0TestRunner:
    def __init__(self):
        self.results = {
            "test_summary": {},
            "document_results": {},
            "quality_analysis": {},
            "performance_metrics": {},
            "errors": []
        }

    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get file metadata and determine expected processing behavior."""
        stat = file_path.stat()
        size_mb = round(stat.st_size / (1024 * 1024), 2)

        # Classify file type for expected behavior
        suffix = file_path.suffix.lower()
        if suffix in ['.pdf']:
            category = "pdf_document"
            ocr_expected = True
        elif suffix in ['.jpeg', '.jpg', '.png', '.tiff', '.tif']:
            category = "image_document"
            ocr_expected = True
        elif suffix in ['.eml']:
            category = "email_document"
            ocr_expected = False  # Not currently supported
        elif suffix in ['.docx', '.doc']:
            category = "word_document"
            ocr_expected = False  # Not currently supported
        else:
            category = "unknown"
            ocr_expected = False

        return {
            "size_bytes": stat.st_size,
            "size_mb": size_mb,
            "category": category,
            "ocr_expected": ocr_expected,
            "mime_type": self.guess_mime_type(suffix)
        }

    def guess_mime_type(self, suffix: str) -> str:
        """Guess MIME type from file extension."""
        mime_map = {
            '.pdf': 'application/pdf',
            '.jpeg': 'image/jpeg',
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.eml': 'message/rfc822',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword'
        }
        return mime_map.get(suffix.lower(), 'application/octet-stream')

    def upload_document(self, file_path: Path, case_ref: str) -> Dict[str, Any]:
        """Upload document using presign flow and track processing."""
        file_info = self.get_file_info(file_path)

        try:
            start_time = time.time()

            # Step 1: Get presigned URL
            presign_response = requests.post(f"{API_BASE}/v0/uploads/presign",
                json={
                    "tenant_id": TENANT_ID,
                    "user_id": USER_ID,
                    "filename": file_path.name,
                    "mime": file_info["mime_type"]
                }
            )
            presign_response.raise_for_status()
            presign_data = presign_response.json()

            # Step 2: Upload file to S3/MinIO
            with open(file_path, 'rb') as f:
                upload_response = requests.put(presign_data["url"], data=f)
                upload_response.raise_for_status()

            # Step 3: Finalize upload
            finalize_response = requests.post(f"{API_BASE}/v0/uploads/finalize",
                json={
                    "tenant_id": TENANT_ID,
                    "user_id": USER_ID,
                    "key": presign_data["object_key"],
                    "filename": file_path.name,
                    "mime": file_info["mime_type"]
                }
            )
            finalize_response.raise_for_status()
            finalize_data = finalize_response.json()

            upload_time = time.time() - start_time

            # Step 4: Wait for processing and get results
            processing_start = time.time()
            job_id = finalize_data["job_id"]
            document_id = finalize_data["document_id"]

            # Poll job status
            job_status = self.wait_for_job_completion(job_id, timeout=300)
            processing_time = time.time() - processing_start

            # Get document reports
            report_json = self.get_document_report(document_id)
            processed_json = self.get_processed_document(document_id)

            return {
                "success": True,
                "file_path": str(file_path),
                "file_info": file_info,
                "case_ref": case_ref,
                "document_id": document_id,
                "job_id": job_id,
                "upload_time": upload_time,
                "processing_time": processing_time,
                "credit_estimate": finalize_data.get("credit_estimate"),
                "job_status": job_status,
                "report": report_json,
                "processed": processed_json,
                "warnings": report_json.get("warnings", []),
                "metrics": report_json.get("metrics", {})
            }

        except Exception as e:
            return {
                "success": False,
                "file_path": str(file_path),
                "file_info": file_info,
                "case_ref": case_ref,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def wait_for_job_completion(self, job_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for processing job to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{API_BASE}/v0/jobs/{job_id}")
                response.raise_for_status()
                job_data = response.json()

                status = job_data.get("status")
                if status in ["succeeded", "failed"]:
                    return job_data

                time.sleep(2)  # Poll every 2 seconds

            except Exception as e:
                print(f"Error polling job {job_id}: {e}")
                time.sleep(5)

        return {"status": "timeout", "error": "Job processing timed out"}

    def get_document_report(self, document_id: str) -> Dict[str, Any]:
        """Get document processing report."""
        try:
            response = requests.get(f"{API_BASE}/v0/documents/{document_id}/report.json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_processed_document(self, document_id: str) -> Dict[str, Any]:
        """Get processed document data."""
        try:
            response = requests.get(f"{API_BASE}/v0/documents/{document_id}/processed.json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def run_comprehensive_test(self):
        """Run comprehensive test on all real-world documents."""
        print("🚀 Starting Block 0a Real-World Document Testing")
        print(f"📁 Test documents directory: {TEST_DOCS_DIR}")
        print(f"🏢 Tenant ID: {TENANT_ID}")
        print(f"👤 User ID: {USER_ID}")
        print()

        # Collect all test files
        test_files = []

        # Famas case files
        if FAMAS_DIR.exists():
            for file_path in FAMAS_DIR.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    test_files.append((file_path, "Famas_Arbitration"))

        # Igyan case files
        if IGYAN_DIR.exists():
            for file_path in IGYAN_DIR.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.') and not file_path.name.endswith('.dmg'):
                    test_files.append((file_path, "Igyan_Defamation"))

        print(f"📄 Found {len(test_files)} test documents")
        print()

        # Process documents with threading for efficiency
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_file = {
                executor.submit(self.upload_document, file_path, case_ref): (file_path, case_ref)
                for file_path, case_ref in test_files
            }

            for future in as_completed(future_to_file):
                file_path, case_ref = future_to_file[future]
                try:
                    result = future.result()
                    self.results["document_results"][str(file_path)] = result

                    if result["success"]:
                        print(f"✅ {file_path.name} - {case_ref}")
                        print(f"   📊 Size: {result['file_info']['size_mb']}MB")
                        print(f"   ⏱️  Upload: {result['upload_time']:.1f}s, Processing: {result['processing_time']:.1f}s")
                        print(f"   💰 Credits: {result['credit_estimate']}")
                        print(f"   ⚠️  Warnings: {len(result['warnings'])}")
                        if result['warnings']:
                            for warning in result['warnings']:
                                print(f"      • {warning}")
                    else:
                        print(f"❌ {file_path.name} - FAILED: {result['error']}")
                        self.results["errors"].append(result)
                    print()

                except Exception as e:
                    print(f"❌ {file_path.name} - EXCEPTION: {str(e)}")
                    self.results["errors"].append({
                        "file": str(file_path),
                        "error": str(e),
                        "error_type": type(e).__name__
                    })

        # Generate summary analysis
        self.analyze_results()
        self.print_summary()

        # Save detailed results to file
        results_file = Path(__file__).parent.parent / "block0a_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"📄 Detailed results saved to: {results_file}")

    def analyze_results(self):
        """Analyze test results and generate insights."""
        successful = []
        failed = []

        for file_path, result in self.results["document_results"].items():
            if result["success"]:
                successful.append(result)
            else:
                failed.append(result)

        # Basic statistics
        self.results["test_summary"] = {
            "total_files": len(self.results["document_results"]),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.results["document_results"]) * 100 if self.results["document_results"] else 0
        }

        # Quality analysis
        warnings_by_type = {}
        metrics_summary = {}
        file_type_performance = {}

        for result in successful:
            # Warning analysis
            for warning in result.get("warnings", []):
                warning_key = warning.split(':')[0].strip() if ':' in warning else warning.split('(')[0].strip()
                warnings_by_type[warning_key] = warnings_by_type.get(warning_key, 0) + 1

            # Metrics analysis
            metrics = result.get("metrics", {})
            for key, value in metrics.items():
                if key not in metrics_summary:
                    metrics_summary[key] = []
                metrics_summary[key].append(value)

            # Performance by file type
            category = result["file_info"]["category"]
            if category not in file_type_performance:
                file_type_performance[category] = {"count": 0, "total_time": 0, "total_size": 0}

            file_type_performance[category]["count"] += 1
            file_type_performance[category]["total_time"] += result.get("processing_time", 0)
            file_type_performance[category]["total_size"] += result["file_info"]["size_mb"]

        self.results["quality_analysis"] = {
            "warnings_by_type": warnings_by_type,
            "metrics_summary": metrics_summary,
            "file_type_performance": file_type_performance
        }

    def print_summary(self):
        """Print comprehensive test summary."""
        summary = self.results["test_summary"]
        quality = self.results["quality_analysis"]

        print("=" * 60)
        print("📊 BLOCK 0A REAL-WORLD TESTING SUMMARY")
        print("=" * 60)

        print(f"📈 Overall Results:")
        print(f"   Total Files: {summary['total_files']}")
        print(f"   Successful: {summary['successful']}")
        print(f"   Failed: {summary['failed']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print()

        if quality.get("warnings_by_type"):
            print("⚠️  Most Common Warnings:")
            sorted_warnings = sorted(quality["warnings_by_type"].items(), key=lambda x: x[1], reverse=True)
            for warning, count in sorted_warnings[:5]:
                print(f"   • {warning}: {count} files")
            print()

        if quality.get("file_type_performance"):
            print("📁 Performance by File Type:")
            for file_type, perf in quality["file_type_performance"].items():
                avg_time = perf["total_time"] / perf["count"] if perf["count"] > 0 else 0
                avg_size = perf["total_size"] / perf["count"] if perf["count"] > 0 else 0
                print(f"   • {file_type}: {perf['count']} files, avg {avg_time:.1f}s, avg {avg_size:.1f}MB")
            print()

        if self.results["errors"]:
            print("❌ Errors Encountered:")
            for error in self.results["errors"][:5]:  # Show first 5 errors
                print(f"   • {Path(error.get('file_path', error.get('file', 'unknown'))).name}: {error['error']}")
            print()

        print("🎯 Block 0a Assessment:")
        if summary['success_rate'] >= 80:
            print("   ✅ EXCELLENT - Block 0a handles real-world documents well")
        elif summary['success_rate'] >= 60:
            print("   ⚠️  GOOD - Block 0a works but has some gaps")
        else:
            print("   ❌ NEEDS WORK - Block 0a struggling with real documents")

        print("=" * 60)


def main():
    """Main test execution."""
    if not TEST_DOCS_DIR.exists():
        print(f"❌ Test documents directory not found: {TEST_DOCS_DIR}")
        sys.exit(1)

    # Health check
    try:
        health_response = requests.get(f"{API_BASE}/healthz", timeout=10)
        health_response.raise_for_status()
        health_data = health_response.json()
        if health_data.get("status") != "ok":
            print("⚠️  API health check shows degraded status")
            print(f"   Components: {health_data.get('components', {})}")
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        print("Make sure Docker services are running: docker compose -f infra/docker-compose.yml up -d")
        sys.exit(1)

    # Run the comprehensive test
    runner = Block0TestRunner()
    runner.run_comprehensive_test()


if __name__ == "__main__":
    main()