import os
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from shopno_core.security.jwt import JWTError, jwt

APP_NAME = "shopnoltd-admin-infrastructure"
KUBE_HOST = os.getenv("KUBE_HOST", "https://kubernetes.default.svc")
KUBE_TOKEN_FILE = Path(os.getenv("KUBE_TOKEN_FILE", "/var/run/secrets/kubernetes.io/serviceaccount/token"))
KUBE_CA_FILE = Path(os.getenv("KUBE_CA_FILE", "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"))
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "https://auth.shopnoltd.dpdns.org/realms/shopnoltd").rstrip("/")
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "shopnoltd-web")
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "https://shopnoltd.dpdns.org,https://admin-portal.shopnoltd.dpdns.org").split(",") if x.strip()]

app = FastAPI(title=APP_NAME, version="1.0.0")
bearer = HTTPBearer(auto_error=True)
_jwks_cache: Optional[dict[str, Any]] = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Authorization", "Accept", "Content-Type"],
)


def _kube_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {KUBE_TOKEN_FILE.read_text().strip()}", "Accept": "application/json"}


async def _jwks() -> dict[str, Any]:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs")
        response.raise_for_status()
        _jwks_cache = response.json()
    return _jwks_cache


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict[str, Any]:
    token = credentials.credentials
    try:
        unverified = jwt.get_unverified_header(token)
        keys = await _jwks()
        key = next(item for item in keys["keys"] if item["kid"] == unverified["kid"])
        claims = jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
            options={"verify_aud": True, "verify_iss": True},
        )
    except (JWTError, StopIteration, KeyError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=401, detail="invalid authentication token") from exc

    roles = claims.get("roles", []) or claims.get("realm_access", {}).get("roles", [])
    if "platform_admin" not in roles and "admin" not in roles:
        raise HTTPException(status_code=403, detail="admin only")
    return claims


async def kube_get(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    verify: Any = str(KUBE_CA_FILE) if KUBE_CA_FILE.exists() else True
    try:
        async with httpx.AsyncClient(base_url=KUBE_HOST, verify=verify, timeout=15) as client:
            response = await client.get(path, headers=_kube_headers(), params=params)
    except (httpx.HTTPError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"kubernetes api unavailable: {exc}") from exc
    if response.status_code == 403:
        raise HTTPException(status_code=503, detail="kubernetes api denied this read-only operation")
    if not response.is_success:
        raise HTTPException(status_code=502, detail=f"kubernetes api returned {response.status_code}")
    return response.json()


def normalize_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload.get("items", []) if isinstance(payload, dict) else []


def compact(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata", {})
    status = item.get("status", {})
    spec = item.get("spec", {})
    return {
        "name": metadata.get("name"),
        "namespace": metadata.get("namespace"),
        "uid": metadata.get("uid"),
        "created_at": metadata.get("creationTimestamp"),
        "labels": metadata.get("labels", {}),
        "status": status,
        "spec": spec,
    }


def namespace_path(namespace: Optional[str], resource: str) -> str:
    if namespace:
        return f"/apis/{resource}/namespaces/{namespace}"
    return f"/apis/{resource}"


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": APP_NAME}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    if not KUBE_TOKEN_FILE.exists():
        raise HTTPException(status_code=503, detail="kubernetes service-account token is missing")
    await kube_get("/version")
    return {"status": "ready"}


@app.get("/api/v1/admin/infrastructure/cluster")
async def cluster(_: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return await kube_get("/version")


@app.get("/api/v1/admin/infrastructure/nodes")
async def nodes(_: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    return [compact(x) for x in normalize_items(await kube_get("/api/v1/nodes"))]


@app.get("/api/v1/admin/infrastructure/namespaces")
async def namespaces(_: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    return [compact(x) for x in normalize_items(await kube_get("/api/v1/namespaces"))]


@app.get("/api/v1/admin/infrastructure/pods")
async def pods(namespace: Optional[str] = Query(default=None), _: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = f"/api/v1/namespaces/{namespace}/pods" if namespace else "/api/v1/pods"
    result = []
    for item in normalize_items(await kube_get(path)):
        metadata = item.get("metadata", {})
        status = item.get("status", {})
        containers = status.get("containerStatuses", []) or []
        result.append({
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "created_at": metadata.get("creationTimestamp"),
            "phase": status.get("phase"),
            "ready": all(c.get("ready", False) for c in containers) if containers else False,
            "restarts": sum(int(c.get("restartCount", 0) or 0) for c in containers),
            "containers": [{"name": c.get("name"), "ready": c.get("ready"), "restarts": c.get("restartCount", 0)} for c in containers],
        })
    return result


@app.get("/api/v1/admin/infrastructure/deployments")
async def deployments(namespace: Optional[str] = Query(default=None), _: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = namespace_path(namespace, "apps/v1") + "/deployments"
    return [compact(x) for x in normalize_items(await kube_get(path))]


@app.get("/api/v1/admin/infrastructure/statefulsets")
async def statefulsets(namespace: Optional[str] = Query(default=None), _: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = namespace_path(namespace, "apps/v1") + "/statefulsets"
    return [compact(x) for x in normalize_items(await kube_get(path))]


@app.get("/api/v1/admin/infrastructure/services")
async def services(namespace: Optional[str] = Query(default=None), _: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = f"/api/v1/namespaces/{namespace}/services" if namespace else "/api/v1/services"
    return [compact(x) for x in normalize_items(await kube_get(path))]


@app.get("/api/v1/admin/infrastructure/ingresses")
async def ingresses(namespace: Optional[str] = Query(default=None), _: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = namespace_path(namespace, "networking.k8s.io/v1") + "/ingresses"
    return [compact(x) for x in normalize_items(await kube_get(path))]


@app.get("/api/v1/admin/infrastructure/pvc")
async def pvc(namespace: Optional[str] = Query(default=None), _: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = f"/api/v1/namespaces/{namespace}/persistentvolumeclaims" if namespace else "/api/v1/persistentvolumeclaims"
    return [compact(x) for x in normalize_items(await kube_get(path))]


@app.get("/api/v1/admin/infrastructure/events")
async def events(namespace: Optional[str] = Query(default=None), _: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = f"/apis/events.k8s.io/v1/namespaces/{namespace}/events" if namespace else "/apis/events.k8s.io/v1/events"
    return [compact(x) for x in normalize_items(await kube_get(path))]


@app.get("/api/v1/admin/infrastructure/hpa")
async def hpa(namespace: Optional[str] = Query(default=None), _: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = namespace_path(namespace, "autoscaling/v2") + "/horizontalpodautoscalers"
    return [compact(x) for x in normalize_items(await kube_get(path))]


@app.get("/api/v1/admin/argocd/applications")
async def argocd_applications(_: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    path = "/apis/argoproj.io/v1alpha1/namespaces/argocd/applications"
    result = []
    for item in normalize_items(await kube_get(path)):
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        status = item.get("status", {})
        result.append({
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "project": spec.get("project"),
            "repo": (spec.get("source") or {}).get("repoURL"),
            "revision": ((status.get("sync") or {}).get("revision") or (status.get("operationState") or {}).get("syncResult", {}).get("revision")),
            "sync": (status.get("sync") or {}).get("status"),
            "health": (status.get("health") or {}).get("status"),
            "message": (status.get("health") or {}).get("message"),
            "resources": status.get("resources", []),
            "conditions": status.get("conditions", []),
        })
    return result


@app.get("/api/v1/admin/argocd/applications/{name}")
async def argocd_application(name: str, _: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return await kube_get(f"/apis/argoproj.io/v1alpha1/namespaces/argocd/applications/{name}")


@app.get("/api/v1/admin/argocd/applications/{name}/resources")
async def argocd_resources(name: str, _: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    app_obj = await kube_get(f"/apis/argoproj.io/v1alpha1/namespaces/argocd/applications/{name}")
    status = app_obj.get("status", {})
    return {
        "application": name,
        "resources": status.get("resources", []),
        "summary": status.get("summary", {}),
        "sync": status.get("sync", {}),
        "health": status.get("health", {}),
    }
