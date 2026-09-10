"""Static contract checks for the Shopnoltd browser/API boundary.

This is intentionally conservative: it verifies required routes/facades and
prevents newly-unified business screens from depending on internal service
origins. It does not claim that external provider credentials are live.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    p = ROOT / path
    if not p.is_file() or not p.read_text(encoding="utf-8").strip():
        raise SystemExit(f"Missing/empty required file: {path}")
    return p.read_text(encoding="utf-8")


main = read("platform/web-portal/src/main.jsx")
required_routes = [
    "/discover", "/feed", "/post/:id", "/work", "/work/:id", "/create-work",
    "/my-created-work", "/my-active-work", "/my-submission", "/work-review",
    "/account", "/notifications", "/blog", "/blog/:slug", "/my-blog",
    "/domain-registration", "/domain-management", "/ai", "/billing", "/payments",
    "/transactions", "/wallet", "/wallet/ledger", "/exchange", "/reports",
    "/admin", "/admin/database", "/admin/blog", "/admin/infrastructure",
]
missing = [r for r in required_routes if f'path="{r}"' not in main]
if missing:
    raise SystemExit("Missing frontend routes: " + ", ".join(missing))

for path in [
    "platform/api-service/app/api/ai_proxy.py",
    "platform/api-service/app/api/domain_proxy.py",
    "platform/api-service/app/api/freedomain_proxy.py",
    "platform/api-service/app/api/storage_proxy.py",
    "platform/api-service/app/api/admin_proxy.py",
    "platform/api-service/app/api/v3_work.py",
    "platform/web-portal/src/lib/platformApi.js",
    "platform/web-portal/src/lib/financialApi.js",
    "platform/web-portal/src/pages/DatabaseControlPlaneEnhanced.jsx",
    "platform/web-portal/src/pages/CheckoutCurrencySafe.jsx",
    "platform/web-portal/src/pages/WorkHub.jsx",
]:
    read(path)

# These screens must use the unified API facade rather than browser-calling
# internal/public service origins for business operations.
for path in [
    "platform/web-portal/src/pages/AIWorkspace.jsx",
    "platform/web-portal/src/pages/DomainRegistration.jsx",
    "platform/web-portal/src/pages/DomainManagement.jsx",
]:
    text = read(path)
    forbidden = [
        "https://ai-platform.shopnoltd.dpdns.org",
        "https://domain.shopnoltd.dpdns.org",
        "https://freedomain.shopnoltd.dpdns.org",
    ]
    found = [x for x in forbidden if x in text]
    if found:
        raise SystemExit(f"Direct service origin remains in {path}: {found}")

# Storage mutations must use the API facade; public published assets may still
# use the public storage URL for cacheable image delivery.
platform_api = read("platform/web-portal/src/lib/platformApi.js")
if "/api/v1/storage" not in platform_api:
    raise SystemExit("platformApi storage mutations are not routed through /api/v1/storage")

print(f"Validated {len(required_routes)} required frontend routes and unified API facades.")
