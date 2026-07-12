"""Upstream service health checker."""
import httpx, asyncio
SERVICES = {
    "auth":        "http://oauth-service.shopno-identity.svc.cluster.local:8080",
    "payment":     "http://payment-service.shopno-payments.svc.cluster.local:8080",
    "billing":     "http://billing-engine.shopno-payments.svc.cluster.local:8080",
    "exchange":    "http://exchange-service.shopno-payments.svc.cluster.local:8080",
    "social":      "http://social-service.shopno-platform.svc.cluster.local:8080",
    "messaging":   "http://messaging-service.shopno-platform.svc.cluster.local:8080",
    "notification":"http://notification-service.shopno-platform.svc.cluster.local:8080",
    "storage":     "http://storage-service.shopno-platform.svc.cluster.local:8080",
    "ai":          "http://ai-platform.shopno-platform.svc.cluster.local:8000",
    "analytics":   "http://analytics-service.shopno-platform.svc.cluster.local:8080",
}
async def health() -> dict:
    async def check(name, url):
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{url}/healthz")
            return name, "ok" if r.status_code == 200 else f"down:{r.status_code}"
        except Exception as e:
            return name, f"down:{e.__class__.__name__}"
    results = await asyncio.gather(*[check(n, u) for n, u in SERVICES.items()])
    return {n: s for n, s in results}
