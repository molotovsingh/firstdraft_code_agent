import argparse
import os
import pathlib
import mimetypes
import requests


def upload_file_legacy(api_base: str, tenant_id: str, user_id: int, path: pathlib.Path):
    url = f"{api_base.rstrip('/')}/v0/documents/upload"
    with open(path, "rb") as f:
        files = {"files": (path.name, f)}
        data = {"tenant_id": tenant_id, "user_id": str(user_id)}
        resp = requests.post(url, files=files, data=data, timeout=300)
        resp.raise_for_status()
        return resp.json()["documents"][0]


def upload_file_presigned(api_base: str, tenant_id: str, user_id: int, path: pathlib.Path):
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    presign = requests.post(
        f"{api_base.rstrip('/')}/v0/uploads/presign",
        json={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "filename": path.name,
            "mime": mime,
        },
        timeout=60,
    ).json()
    put_url = presign["url"]
    key = presign["object_key"]
    with open(path, "rb") as f:
        put = requests.put(put_url, data=f, headers={"Content-Type": mime}, timeout=600)
        if put.status_code not in (200, 201, 204):
            raise RuntimeError(f"PUT failed: {put.status_code} {put.text}")
    finalize = requests.post(
        f"{api_base.rstrip('/')}/v0/uploads/finalize",
        json={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "key": key,
            "filename": path.name,
            "mime": mime,
        },
        timeout=120,
    )
    finalize.raise_for_status()
    data = finalize.json()
    return {"document_id": data["document_id"], "job_id": data["job_id"], "credit_estimate": data.get("credit_estimate")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="test_documents", help="Folder to scan for PDFs/images")
    parser.add_argument("--api", default=os.getenv("API_BASE", "http://localhost:8000"))
    parser.add_argument("--tenant", default="11111111-1111-1111-1111-111111111111")
    parser.add_argument("--user", type=int, default=1)
    parser.add_argument("--legacy", action="store_true", help="Use legacy multipart upload path instead of presigned finalize")
    args = parser.parse_args()

    root = pathlib.Path(args.root)
    exts = {".pdf", ".PDF", ".png", ".PNG", ".jpg", ".jpeg", ".JPG", ".JPEG"}
    paths = [p for p in root.rglob("*") if p.suffix in exts]
    if not paths:
        print("No documents found.")
        return
    print(f"Uploading {len(paths)} documents to {args.api} using {'legacy' if args.legacy else 'presigned'} path...")
    for p in paths:
        try:
            if args.legacy:
                res = upload_file_legacy(args.api, args.tenant, args.user, p)
            else:
                res = upload_file_presigned(args.api, args.tenant, args.user, p)
            print(f"OK {p} → doc={res['document_id']} job={res['job_id']} est={res['credit_estimate']}")
        except Exception as e:
            print(f"FAIL {p}: {e}")


if __name__ == "__main__":
    main()
