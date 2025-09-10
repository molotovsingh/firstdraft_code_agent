import argparse
import os
import pathlib
import requests


def upload_file(api_base: str, tenant_id: str, user_id: int, path: pathlib.Path):
    url = f"{api_base.rstrip('/')}/v0/documents/upload"
    with open(path, "rb") as f:
        files = {"files": (path.name, f)}
        data = {"tenant_id": tenant_id, "user_id": str(user_id)}
        resp = requests.post(url, files=files, data=data, timeout=120)
        resp.raise_for_status()
        return resp.json()["documents"][0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="test_documents", help="Folder to scan for PDFs/images")
    parser.add_argument("--api", default=os.getenv("API_BASE", "http://localhost:8000"))
    parser.add_argument("--tenant", default="11111111-1111-1111-1111-111111111111")
    parser.add_argument("--user", type=int, default=1)
    args = parser.parse_args()

    root = pathlib.Path(args.root)
    exts = {".pdf", ".PDF", ".png", ".PNG", ".jpg", ".jpeg", ".JPG", ".JPEG"}
    paths = [p for p in root.rglob("*") if p.suffix in exts]
    if not paths:
        print("No documents found.")
        return
    print(f"Uploading {len(paths)} documents to {args.api}...")
    for p in paths:
        try:
            res = upload_file(args.api, args.tenant, args.user, p)
            print(f"OK {p} → doc={res['document_id']} job={res['job_id']} est={res['credit_estimate']}")
        except Exception as e:
            print(f"FAIL {p}: {e}")


if __name__ == "__main__":
    main()

