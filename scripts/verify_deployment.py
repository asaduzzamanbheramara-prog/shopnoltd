#!/usr/bin/env python3
"""
Shopnoltd public-link/service proof checker.

This checker has two layers:
  1. Static contract checks: React routes and public URLs referenced by the
     web portal must have an explicit target and must use the approved
     Shopnoltd domains (or an explicitly external URL).
  2. Runtime checks: every Kubernetes ingress hostname plus important public
     health/login/page endpoints is requested from a machine that can reach
     the production network.

Run from shopnoltd-pc-1 / a networked CI runner:
    python3 scripts/verify_deployment.py
    python3 scripts/verify_deployment.py --json report.json
    python3 scripts/verify_deployment.py --static-only

Exit codes:
    0 = all requested checks passed
    1 = one or more checks failed
    2 = runtime checks were skipped because this is a static-only run
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    sys.exit("Run: pip install requests --break-system-packages")

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "platform" / "web-portal" / "src"
MAIN_JSX = WEB / "main.jsx"

ALLOWED_PUBLIC_SUFFIXES = (".shopnoltd.dpdns.org",)
EXTERNAL_SCHEMES = ("mailto:", "tel:", "javascript:")

# Important runtime contracts. Other ingress hosts are discovered directly
# from k8s/services/*/ingress.yaml so new services are automatically covered.
SPECIFIC_CHECKS = {
    "web-portal": [
        ("/", ["/login", "/register", "/blog", "/plugins", "/pricing"]),
        ("/pricing", None),
        ("/blog", None),
        ("/plugins", None),
        ("/services", None),
        ("/login", None),
        ("/register", None),
        ("/domain-registration", None),
    ],
    "api-service": [("/health", None)],
    "billing-engine": [("/health", None)],
    "oauth-service": [("/health", None)],
    "keycloak": [
        ("/realms/shopnoltd/.well-known/openid-configuration", ["authorization_endpoint", "token_endpoint"])
    ],
}


def find_hosts():
    """Return (service_name, hostname) pairs from every ingress manifest."""
    hosts = []
    for ing in (ROOT / "k8s" / "services").glob("*/ingress.yaml"):
        service = ing.parent.name
        text = ing.read_text(encoding="utf-8")
        for m in re.finditer(r"^\s*host:\s*([^\s#]+)", text, re.MULTILINE):
            host = m.group(1).strip().strip("\"'")
            if host not in {h for _, h in hosts}:
                hosts.append((service, host))
    return hosts


def find_frontend_contract():
    """Extract route declarations and public URLs from the web portal source."""
    if not MAIN_JSX.exists():
        return {"error": f"missing {MAIN_JSX}"}

    text = MAIN_JSX.read_text(encoding="utf-8")
    routes = sorted(set(re.findall(r'path=["\']([^"\']+)["\']', text)))

    urls = set(re.findall(r'https?://[^\s"\'`<>)}]+', text))
    public_urls = []
    bad_urls = []
    for raw in sorted(urls):
        url = raw.rstrip(",.;")
        host = urlparse(url).hostname or ""
        if url.lower().startswith(EXTERNAL_SCHEMES):
            public_urls.append(url)
        elif host.endswith(ALLOWED_PUBLIC_SUFFIXES) or host == "shopnoltd.dpdns.org":
            public_urls.append(url)
        else:
            bad_urls.append(url)

    # Catch common JSX navigation forms. The route list is deliberately
    # independent from href extraction so React-router paths cannot silently
    # disappear from the declared route table.
    hrefs = sorted(set(re.findall(r'(?:href|to)=["\'](/[^"\']*)["\']', text)))
    missing_internal_routes = []
    route_set = set(routes)
    for href in hrefs:
        path = href.split("?", 1)[0].split("#", 1)[0]
        if not path or path.startswith("//"):
            continue
        if path not in route_set and not any(
            path.startswith(r.rstrip("/:")) and ":" in r for r in route_set
        ):
            missing_internal_routes.append(path)

    return {
        "routes": routes,
        "hrefs": hrefs,
        "public_urls": public_urls,
        "bad_urls": bad_urls,
        "missing_internal_routes": sorted(set(missing_internal_routes)),
    }


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
            "kind": "runtime",
            "service": service,
            "host": host,
            "path": path,
            "url": url,
            "status": r.status_code,
            "ms": elapsed,
            "ok": ok,
            "missing": missing,
            "redirected_to": r.url if r.url != url else None,
        }
    except requests.exceptions.SSLError as e:
        return {"kind": "runtime", "service": service, "host": host, "path": path, "url": url, "ok": False, "error": f"TLS error: {e}"}
    except requests.exceptions.ConnectionError as e:
        return {"kind": "runtime", "service": service, "host": host, "path": path, "url": url, "ok": False, "error": f"Unreachable: {e}"}
    except requests.exceptions.Timeout:
        return {"kind": "runtime", "service": service, "host": host, "path": path, "url": url, "ok": False, "error": f"Timed out after {timeout}s"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="also write a machine-readable report")
    ap.add_argument("--service", help="only check one ingress service")
    ap.add_argument("--static-only", action="store_true", help="do not make network requests")
    args = ap.parse_args()

    results = []
    contract = find_frontend_contract()
    if "error" in contract:
        results.append({"kind": "static", "check": "web-portal-source", "ok": False, "error": contract["error"]})
    else:
        results.append({"kind": "static", "check": "frontend-routes-present", "ok": bool(contract["routes"]), "count": len(contract["routes"])})
        results.append({"kind": "static", "check": "frontend-links-resolve-to-routes", "ok": not contract["missing_internal_routes"], "missing": contract["missing_internal_routes"]})
        results.append({"kind": "static", "check": "frontend-public-url-policy", "ok": not contract["bad_urls"], "bad_urls": contract["bad_urls"]})

    hosts = find_hosts()
    if args.service:
        hosts = [(s, h) for s, h in hosts if s == args.service]

    if not args.static_only:
        if not hosts:
            results.append({"kind": "runtime", "check": "ingress-discovery", "ok": False, "error": "No ingress hosts found"})
        else:
            for service, host in hosts:
                checks = SPECIFIC_CHECKS.get(service, [("/", None)])
                for path, must_contain in checks:
                    results.append(check(service, host, path, must_contain))

    failed = [r for r in results if not r.get("ok")]
    passed = [r for r in results if r.get("ok")]

    print("================ SHOPNOLTD LINK + SERVICE AUDIT ================")
    if not contract.get("error"):
        print(f"Frontend routes discovered : {len(contract['routes'])}")
        print(f"Internal href/to targets    : {len(contract['hrefs'])}")
        print(f"Public URLs discovered      : {len(contract['public_urls'])}")
    print(f"Ingress hosts discovered    : {len(hosts)}")
    print()

    for r in results:
        mark = "PASS" if r.get("ok") else "FAIL"
        if r.get("kind") == "static":
            detail = r.get("error") or r.get("missing") or r.get("bad_urls") or r.get("count", "ok")
            print(f"[{mark}] STATIC  {r.get('check')}: {detail}")
        else:
            detail = r.get("error") or (f"missing={r['missing']}" if r.get("missing") else f"HTTP {r.get('status')} in {r.get('ms')}ms")
            print(f"[{mark}] RUNTIME {r.get('service'):20s} {r.get('url'):65s} {detail}")

    print(f"\nSUMMARY: {len(passed)} PASS / {len(failed)} FAIL")
    if args.static_only:
        print("RUNTIME: SKIPPED (--static-only). Run this on shopnoltd-pc-1 for live DNS/TLS/HTTP verification.")

    if args.json:
        Path(args.json).write_text(json.dumps({"results": results, "frontend": contract, "ingress_hosts": hosts}, indent=2), encoding="utf-8")
        print(f"REPORT: {args.json}")

    if failed:
        sys.exit(1)
    if args.static_only:
        sys.exit(2)


if __name__ == "__main__":
    main()
