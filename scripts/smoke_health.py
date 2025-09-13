#!/usr/bin/env python3
import os
import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def main():
    h = requests.get(f"{API_BASE}/healthz", timeout=10)
    print("/healthz:", h.status_code, h.text[:200])

    m = requests.get(f"{API_BASE}/metrics", timeout=10)
    print("/metrics:", m.status_code)
    # Print a few lines
    for line in m.text.splitlines()[:10]:
        print(line)


if __name__ == "__main__":
    main()

