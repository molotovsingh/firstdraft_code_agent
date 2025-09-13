import os
import sys
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TENANT_ID = os.getenv("TENANT_ID", "11111111-1111-1111-1111-111111111111")
USER_ID = int(os.getenv("USER_ID", "1"))


def main():
    filename = "hello.txt"
    mime = "text/plain"
    body = {
        "tenant_id": TENANT_ID,
        "user_id": USER_ID,
        "filename": filename,
        "mime": mime,
    }

    # Presign PUT
    r = requests.post(f"{BASE_URL}/v0/uploads/presign", json=body, timeout=10)
    r.raise_for_status()
    presign = r.json()
    put_url = presign["url"]
    key = presign["object_key"]
    print(f"Presigned PUT URL received. key={key}")

    # Upload small payload (optionally from file path argv[1])
    data = b"hello world\n"
    if len(sys.argv) > 1:
        with open(sys.argv[1], "rb") as fh:
            data = fh.read()
    put_headers = {"Content-Type": mime}
    r = requests.put(put_url, data=data, headers=put_headers, timeout=30)
    if r.status_code not in (200, 201):
        print(f"PUT failed: {r.status_code} {r.text}")
        sys.exit(2)
    print("Upload via presigned URL succeeded.")

    # Presign GET
    r = requests.get(f"{BASE_URL}/v0/uploads/presign_download", params={"key": key}, timeout=10)
    r.raise_for_status()
    get_url = r.json()["url"]

    # GET content back
    r = requests.get(get_url, timeout=30)
    if r.status_code != 200:
        print(f"GET failed: {r.status_code} {r.text}")
        sys.exit(3)
    print(f"Downloaded {len(r.content)} bytes via presigned GET. OK")


if __name__ == "__main__":
    main()

