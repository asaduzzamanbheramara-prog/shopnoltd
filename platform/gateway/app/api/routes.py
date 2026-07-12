"""Generates Traefik dynamic config from the live service registry."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token_admin
from app.services.services import SERVICES
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
HOSTS = {
    "auth":        "auth.shopnoltd.dpdns.org",
    "payment":     "billing.shopnoltd.dpdns.org",
    "billing":     "billing.shopnoltd.dpdns.org",
    "exchange":    "billing.shopnoltd.dpdns.org",
    "social":      "chat.shopnoltd.dpdns.org",
    "messaging":   "chat.shopnoltd.dpdns.org",
    "notification":"shopnoltd.dpdns.org",
    "storage":     "shopnoltd.dpdns.org",
    "ai":          "api.shopnoltd.dpdns.org",
    "analytics":   "grafana.shopnoltd.dpdns.org",
    "api":         "api.shopnoltd.dpdns.org",
    "search":      "api.shopnoltd.dpdns.org",
    "audit":       "api.shopnoltd.dpdns.org",
}
@router.get("/traefik.yml")
async def traefik_config():
    """Produces Traefik dynamic config that fronts every service."""
    http_routers, http_services, http_middlewares = {}, {}, {}
    for svc, url in SERVICES.items():
        host = HOSTS.get(svc, "api.shopnoltd.dpdns.org")
        rid = f"shopno-{svc}"
        http_routers[rid] = {"rule": f"Host(`{host}`) && PathPrefix(`/{svc}`)", "service": rid, "entryPoints": ["websecure"], "tls": {"certResolver": "letsencrypt"}, "middlewares": [f"{rid}-auth"]}
        http_services[rid] = {"loadBalancer": {"servers": [{"url": url}]}}
        http_middlewares[f"{rid}-auth"] = {"forwardauth": {"address": f"http://oauth-service.shopno-identity.svc.cluster.local:8080/api/v1/verify"}}
    return {"http": {"routers": http_routers, "services": http_services, "middlewares": http_middlewares}, "generated_at": datetime.utcnow().isoformat()}
@router.get("/list")
async def list_routes(user=Depends(admin)):
    return [{"service": s, "url": u, "host": HOSTS.get(s, "")} for s, u in SERVICES.items()]
