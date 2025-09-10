import argparse
import requests
from typing import List


def list_documents(api: str, tenant: str, limit: int) -> List[str]:
    url = f"{api.rstrip('/')}/v0/documents"
    r = requests.get(url, params={"tenant_id": tenant, "limit": limit}, timeout=60)
    r.raise_for_status()
    data = r.json()
    return [d["id"] for d in data.get("documents", [])]


def fetch_processed(api: str, doc_id: str) -> dict:
    url = f"{api.rstrip('/')}/v0/documents/{doc_id}/processed.json"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    p = argparse.ArgumentParser(description="Print a one-line quality summary for documents")
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--tenant", default="11111111-1111-1111-1111-111111111111")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--ids", default="", help="Comma-separated document IDs; overrides --limit list")
    args = p.parse_args()

    if args.ids:
        ids = [s.strip() for s in args.ids.split(",") if s.strip()]
    else:
        ids = list_documents(args.api, args.tenant, args.limit)

    headers = ["doc_id", "ver", "pages", "density", "conf_avg", "ocr_ok", "warnings", "filename"]
    print("\t".join(headers))
    for doc_id in ids:
        try:
            pj = fetch_processed(args.api, doc_id)
            m = pj.get("metrics", {}) or {}
            w = pj.get("warnings", []) or []
            row = [
                pj.get("document_id", ""),
                str(pj.get("version", "")),
                str(m.get("page_count", "")),
                str(m.get("text_density_per_page", "")),
                str(m.get("ocr_confidence_avg", "")),
                str(m.get("ocr_ok", "")),
                str(len(w)),
                pj.get("filename", ""),
            ]
            print("\t".join(row))
        except Exception as e:
            print(f"{doc_id}\tERROR\t{e}")


if __name__ == "__main__":
    main()
