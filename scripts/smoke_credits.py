import os
import sys
import requests


def main():
    base = os.getenv("API_BASE", "http://localhost:8000")
    if len(sys.argv) < 2:
        print("Usage: python scripts/smoke_credits.py <tenant_id> [limit]")
        sys.exit(2)
    tenant_id = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    b = requests.get(f"{base}/v0/credits/balance", params={"tenant_id": tenant_id}, timeout=10)
    print("BALANCE", b.status_code, b.json())

    l = requests.get(
        f"{base}/v0/credits/ledger", params={"tenant_id": tenant_id, "limit": limit}, timeout=10
    )
    print("LEDGER", l.status_code)
    for item in l.json().get("items", []):
        print(
            f"  id={item['id']} user={item['user_id']} delta={item['delta']} reason={item['reason']} job={item['job_id']} at={item['created_at']}"
        )


if __name__ == "__main__":
    main()

