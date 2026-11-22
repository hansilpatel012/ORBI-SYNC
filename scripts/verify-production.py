#!/usr/bin/env python3
"""ORBI-SYNC Production Connectivity & System Health Verification.

Verifies end-to-end connectivity across all integrated services:
- Central FastAPI Gateway (MEMBER 4)
- Member 1 Orbital Propagation Engine & Ephemeris Datasets
- Member 2 Multi-Agent Risk & Coordination Engine
- Next.js 16 Mission Control Web Dashboard
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Any, Dict, Tuple


def check_endpoint(name: str, url: str, expected_key: str = None) -> Tuple[bool, Dict[str, Any]]:
    print(f"[*] Checking {name} ({url})...", end=" ")
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status_code = resp.getcode()
            if status_code != 200:
                print(f"[FAIL] (HTTP {status_code})")
                return False, {"status_code": status_code}
            
            raw_data = resp.read().decode("utf-8")
            try:
                data = json.loads(raw_data)
            except Exception:
                # May be HTML (like frontend)
                data = {"content_length": len(raw_data)}
            
            if expected_key and expected_key not in data:
                print(f"[WARN] (Missing expected key '{expected_key}')")
                return False, data
            
            print(f"[OK] (HTTP {status_code})")
            return True, data
    except urllib.error.URLError as exc:
        print(f"[UNREACHABLE] ({exc.reason})")
        return False, {"error": str(exc.reason)}
    except Exception as exc:
        print(f"[ERROR] ({exc})")
        return False, {"error": str(exc)}


def main():
    print("=" * 70)
    print("ORBI-SYNC Production Connectivity & Health Check")
    print("=" * 70)

    backend_base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    frontend_base = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3000"

    checks = [
        ("Backend Gateway Health", f"{backend_base}/health", "status"),
        ("Coordination Engine Health", f"{backend_base}/coordination/status", "status"),
        ("Member 1 Orbital Metadata", f"{backend_base}/orbital/metadata", "status"),
        ("Member 1 Satellite Catalogue", f"{backend_base}/orbital/satellites?limit=5", "items"),
        ("Member 1 Conjunction Screening", f"{backend_base}/orbital/conjunctions", "conjunctions"),
        ("Member 2 Enriched Conjunctions", f"{backend_base}/orbital/enriched-conjunctions?limit=5", None),
        ("Next.js Mission Control UI", f"{frontend_base}/", None),
    ]

    results = []
    for name, url, expected_key in checks:
        ok, data = check_endpoint(name, url, expected_key)
        results.append((name, ok, data))

    print("\n" + "=" * 70)
    print("Summary of System Connectivity")
    print("=" * 70)
    all_passed = True
    for name, ok, data in results:
        status_label = "PASS" if ok else "FAIL"
        print(f" - {name:<35}: {status_label}")
        if not ok:
            all_passed = False

    if all_passed:
        print("\nAll integrated ORBI-SYNC services are healthy and connected.")
        sys.exit(0)
    else:
        print("\nOne or more services reported failures or are unreachable.")
        sys.exit(1)


if __name__ == "__main__":
    main()
