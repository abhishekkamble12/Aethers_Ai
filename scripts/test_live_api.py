"""
Smoke-test the deployed Saans API.

The admin key is never stored in this file. It is read, in order, from:
  1. the SAANS_ADMIN_KEY environment variable
  2. the ADMIN_API_KEY environment variable
  3. infra/deploy.secrets (git-ignored, written by the deploy step)

The base URL comes from SAANS_API_URL, falling back to the demo deployment.

Usage:
    python scripts/test_live_api.py
Exit code is 0 only if every check returned the expected status.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS_FILE = ROOT / "infra" / "deploy.secrets"
BASE_URL = os.environ.get(
    "SAANS_API_URL", "https://367bcz1ry5.execute-api.us-east-1.amazonaws.com/Prod"
).rstrip("/")


def load_admin_key() -> str:
    for var in ("SAANS_ADMIN_KEY", "ADMIN_API_KEY"):
        if os.environ.get(var):
            return os.environ[var].strip()
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "ADMIN_API_KEY" and value.strip():
                return value.strip()
    return ""


def call(name, url, headers=None, expected_status=200):
    print(f"--- {name}: {url}")
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception as e:  # network error, timeout
        print(f"    FAIL  {e}")
        return False, {}
    try:
        body = json.loads(raw.decode("utf-8") or "{}")
    except ValueError:
        body = {}
    ok = status == expected_status
    print(f"    {'PASS' if ok else 'FAIL'}  status {status} (expected {expected_status})")
    return ok, body


def main() -> int:
    results = []

    ok, b = call("Health", f"{BASE_URL}/health")
    results.append(ok)
    print("    status:", b.get("status"), "| checks:", list(b.get("checks", {}).keys()))

    ok, b = call("Live forecast (48h)", f"{BASE_URL}/forecast?hours=48")
    results.append(ok)
    print("    source:", b.get("source"), "| hours:", len(b.get("hours", [])), "| cache:", b.get("cache"))

    ok, b = call("Live forecast (48h, cached)", f"{BASE_URL}/forecast?hours=48")
    results.append(ok)
    print("    cache:", b.get("cache"))

    ok, b = call("Replay forecast", f"{BASE_URL}/forecast?source=replay")
    results.append(ok)
    print("    source:", b.get("source"), "| hours:", len(b.get("hours", [])), "| label:", b.get("label"))

    ok, b = call("Watch without key", f"{BASE_URL}/watch", expected_status=401)
    results.append(ok)

    key = load_admin_key()
    if not key:
        print("--- Watch with key: SKIPPED (set SAANS_ADMIN_KEY or create infra/deploy.secrets)")
    else:
        ok, b = call("Watch with key", f"{BASE_URL}/watch", headers={"x-saans-admin-key": key})
        results.append(ok)
        for w in b.get("watches", []):
            print(f"    {w.get('date')}: risk={w.get('risk')} plan={w.get('plan_summary')}")
        print("    promote hint:", b.get("promote_hint"))

    passed = sum(results)
    print(f"\n{passed}/{len(results)} live checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
