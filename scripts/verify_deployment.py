#!/usr/bin/env python3
"""
Proof-of-deployment checker: hits every public hostname this platform is
supposed to expose, and reports pass/fail with *why* for each. Run this from
a machine that can actually reach the internet/your cluster -- I can't reach
your private domains from the sandbox I built this in.

Usage:
    pip install requests --break-system-packages
    python3 scripts/verify_deployment.py
    python3 scripts/verify_deployment.py --json report.json   # machine-readable
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Run: pip install requests --break-system-packages")

ROOT = Path(__file__).resolve().parent.parent

# Hosts pulled from k8s/services/*/ingress.yaml at run time (see below), plus
# a few specific per-page checks worth calling out by name.
SPECIFIC_CHECKS = {
    "web-portal": [
        ("/", ["logo.svg", 'href="/login"', 'href="/register"', 'href="/blog"', 'href="/plugins"', 'href="/pricing"']),
    ],
    "api-service": [("/health", None)],
    "billing-engine": [("/health", None)],
    "oauth-service": [("/health", None)],
    "keycloak": [("/realms/shopnoltd/.well-known/openid-configuration", ["authorization_endpoint", "token_endpoint"])],
}


def find_hosts():
    """(service_name, hostname) pairs from every ingress.yaml in the repo."""
    hosts = []
    for ing in (ROOT / "k8s" / "services").glob("*/ingress.yaml"):
        service = ing.parent.name
        text = ing.read_text()
        for m in re.finditer(r"host:\s*([^\s]+)", text):
            hosts.append((service, m.group(1)))
    return hosts


def check(service, host, path, must_contain, timeout=10):
    url = f"https://{host}{path}"
    t0 = time.time()
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        elapsed = round((time.time() - t0) * 1000)
        ok = r.status_code < 400
        missing = []
        if must_contain:
            for needle in must_contain:
                if needle not in r.text:
                    missing.append(needle)
                    ok = False
        return {
            "service": service, "host": host, "path": path, "url": url,
            "status": r.status_code, "ms": elapsed, "ok": ok,
            "missing": missing,
            "redirected_to": r.url if r.url != url else None,
        }
    except requests.exceptions.SSLError as e:
        return {"service": service, "host": host, "path": path, "url": url, "ok": False, "error": f"TLS error: {e}"}
    except requests.exceptions.ConnectionError as e:
        return {"service": service, "host": host, "path": path, "url": url, "ok": False, "error": f"Unreachable: {e}"}
    except requests.exceptions.Timeout:
        return {"service": service, "host": host, "path": path, "url": url, "ok": False, "error": f"Timed out after {timeout}s"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="also write a machine-readable report to this path")
    ap.add_argument("--service", help="only check this one service")
    args = ap.parse_args()

    hosts = find_hosts()
    if args.service:
        hosts = [(s, h) for s, h in hosts if s == args.service]
    if not hosts:
        sys.exit("No ingress hosts found (or --service didn't match anything).")

    results = []
    for service, host in hosts:
        checks = SPECIFIC_CHECKS.get(service, [("/", None)])
        for path, must_contain in checks:
            results.append(check(service, host, path, must_contain))

    passed = [r for r in results if r.get("ok")]
    failed = [r for r in results if not r.get("ok")]

    print(f"Checked {len(results)} endpoints across {len(hosts)} services\n")
    for r in results:
        mark = "OK  " if r.get("ok") else "FAIL"
        detail = r.get("error") or (f"missing: {r['missing']}" if r.get("missing") else f"{r.get('status')} in {r.get('ms')}ms")
        print(f"[{mark}] {r['service']:20s} {r['url']:55s} {detail}")

    print(f"\n{len(passed)} passed, {len(failed)} failed")

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))
        print(f"Wrote {args.json}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
