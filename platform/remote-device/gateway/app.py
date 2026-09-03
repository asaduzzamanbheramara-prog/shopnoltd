import json
import os
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse, Response
from jose import JWTError, jwt


app = FastAPI(
    title="Shopnoltd Remote Device Gateway",
    version="3.2.0",
)


MESH_URL = os.getenv(
    "MESH_URL",
    "https://remote-engine.shopnoltd.dpdns.org",
).rstrip("/")


REGISTRY_URL = os.getenv(
    "REGISTRY_URL",
    "http://remote-device-registry.shopno-tools.svc.cluster.local:8080",
).rstrip("/")


KEYCLOAK_ISSUER = os.getenv(
    "KEYCLOAK_ISSUER",
    "https://auth.shopnoltd.dpdns.org/realms/shopnoltd",
).rstrip("/")


KEYCLOAK_AUDIENCE = os.getenv(
    "KEYCLOAK_AUDIENCE",
    "account",
)


REGISTRY_CONTROL_TOKEN = os.getenv(
    "REGISTRY_CONTROL_TOKEN",
)


_jwks_cache = None


async def _jwks():
    global _jwks_cache

    if _jwks_cache:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
        )
        response.raise_for_status()
        _jwks_cache = response.json()

    return _jwks_cache


async def verify_user(request: Request) -> dict:
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        header = jwt.get_unverified_header(token)
        keys = await _jwks()

        key = next(
            k for k in keys["keys"]
            if k["kid"] == header["kid"]
        )

        claims = jwt.decode(
            token,
            key,
            algorithms=[key["alg"]],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
            options={
                "verify_aud": True,
                "verify_iss": True,
            },
        )

        if claims.get("azp") != "shopnoltd-web":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="invalid token client",
            )

    except (
        JWTError,
        StopIteration,
        KeyError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    roles = claims.get("roles", [])

    if not isinstance(roles, list):
        roles = []

    realm_access = claims.get("realm_access", {})

    if not isinstance(realm_access, dict):
        realm_access = {}

    realm_roles = realm_access.get("roles", [])

    if not isinstance(realm_roles, list):
        realm_roles = []

    all_roles = set(roles) | set(realm_roles)

    subject = claims.get("sub")

    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="token subject unavailable",
        )

    return {
        "claims": claims,
        "subject": subject,
        "roles": all_roles,
        "is_platform_admin": "platform_admin" in all_roles,
    }


async def verify_admin(request: Request) -> dict:
    identity = await verify_user(request)

    if not identity["is_platform_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="platform_admin role required",
        )

    return identity


async def registry_request(
    method: str,
    path: str,
    request: Request,
):
    body = await request.body()

    headers = {}

    for name in (
        "X-Shopnoltd-Device",
        "X-Shopnoltd-Agent",
        "X-Shopnoltd-Timestamp",
        "X-Shopnoltd-Nonce",
        "X-Shopnoltd-Signature",
        "Content-Type",
    ):
        value = request.headers.get(name)

        if value:
            headers[name] = value

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.request(
                method,
                f"{REGISTRY_URL}{path}",
                content=body,
                headers=headers,
            )

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"registry unavailable: {exc}",
        ) from exc

    content_type = response.headers.get(
        "content-type",
        "application/json",
    )

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=(
            "application/json"
            if "application/json" in content_type
            else content_type.split(";", 1)[0]
        ),
    )


async def registry_control_request(
    method: str,
    path: str,
    body: bytes = b"",
):
    if not REGISTRY_CONTROL_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="registry control authentication is not configured",
        )

    headers = {
        "Content-Type": "application/json",
        "X-Shopnoltd-Control-Token": REGISTRY_CONTROL_TOKEN,
    }

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.request(
                method,
                f"{REGISTRY_URL}{path}",
                content=body,
                headers=headers,
            )

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"registry unavailable: {exc}",
        ) from exc

    content_type = response.headers.get(
        "content-type",
        "application/json",
    )

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=(
            "application/json"
            if "application/json" in content_type
            else content_type.split(";", 1)[0]
        ),
    )


@app.get("/")
def root():
    return RedirectResponse(
        url=f"{MESH_URL}/",
        status_code=307,
    )


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": "remote-device-gateway",
        "engine": "meshcentral",
        "executor": "enabled",
        "version": "3.2.0",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "remote-device-gateway",
        "engine": "meshcentral",
        "executor": "enabled",
        "version": "3.2.0",
    }


@app.get("/api/healthz")
def api_healthz():
    return {
        "status": "ok",
        "service": "remote-device-gateway",
        "engine": "meshcentral",
        "executor": "enabled",
        "version": "3.2.0",
    }


@app.get("/api/connect/{device_id}")
async def connect(device_id: str, request: Request):
    identity = await verify_user(request)

    response = await registry_control_request(
        "GET",
        "/api/devices",
    )

    devices = response.json()

    device = next(
        (
            item
            for item in devices
            if isinstance(item, dict)
            and item.get("id") == device_id
        ),
        None,
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="device not found",
        )

    if (
        not identity["is_platform_admin"]
        and device.get("owner_id") != identity["subject"]
    ):
        raise HTTPException(
            status_code=404,
            detail="device not found",
        )

    node_id = device.get("meshcentral_node_id")

    if not node_id:
        raise HTTPException(
            status_code=409,
            detail="MeshCentral device is not linked",
        )

    connect_url = (
        f"{MESH_URL}/?"
        + urlencode({
            "node": node_id,
            "viewmode": "11",
            "hide": "15",
        })
    )

    return {
        "device_id": device_id,
        "engine": "meshcentral",
        "connect_url": connect_url,
    }


@app.get("/connect/{device_id}")
async def browser_connect(device_id: str, request: Request):
    identity = await verify_user(request)

    response = await registry_control_request(
        "GET",
        "/api/devices",
    )

    devices = response.json()

    device = next(
        (
            item
            for item in devices
            if isinstance(item, dict)
            and item.get("id") == device_id
        ),
        None,
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="device not found",
        )

    if (
        not identity["is_platform_admin"]
        and device.get("owner_id") != identity["subject"]
    ):
        raise HTTPException(
            status_code=404,
            detail="device not found",
        )

    node_id = device.get("meshcentral_node_id")

    if not node_id:
        raise HTTPException(
            status_code=409,
            detail="MeshCentral device is not linked",
        )

    connect_url = (
        f"{MESH_URL}/?"
        + urlencode({
            "node": node_id,
            "viewmode": "11",
            "hide": "15",
        })
    )

    return RedirectResponse(
        url=connect_url,
        status_code=307,
    )


# ------------------------------------------------------------
# Device management
# ------------------------------------------------------------

@app.get("/api/devices")
async def list_devices(request: Request):
    identity = await verify_user(request)

    response = await registry_control_request(
        "GET",
        "/api/devices",
    )

    devices = response.json()

    if identity["is_platform_admin"]:
        return devices

    return [
        device
        for device in devices
        if isinstance(device, dict)
        and device.get("owner_id") == identity["subject"]
    ]


@app.post("/api/devices")
async def create_device(
    request: Request,
):
    identity = await verify_user(request)

    body = await request.body()

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="invalid JSON body",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="JSON object required",
        )

    # NEVER trust owner_id supplied by the browser.
    # Ownership is always the verified Keycloak subject.
    payload["owner_id"] = identity["subject"]

    body = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()

    return await registry_control_request(
        "POST",
        "/api/devices",
        body,
    )


@app.delete("/api/devices/{device_id}")
async def delete_device(
    device_id: str,
    request: Request,
):
    identity = await verify_user(request)

    response = await registry_control_request(
        "GET",
        "/api/devices",
    )

    devices = response.json()

    device = next(
        (
            item
            for item in devices
            if isinstance(item, dict)
            and item.get("id") == device_id
        ),
        None,
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="device not found",
        )

    if (
        not identity["is_platform_admin"]
        and device.get("owner_id") != identity["subject"]
    ):
        raise HTTPException(
            status_code=404,
            detail="device not found",
        )

    return await registry_control_request(
        "DELETE",
        f"/api/devices/{device_id}",
    )


# ------------------------------------------------------------
# Executor API
# ------------------------------------------------------------

@app.post("/api/executor/enroll/{device_id}")
async def executor_enroll(
    device_id: str,
    request: Request,
):
    response = await registry_request(
        "POST",
        f"/api/devices/{device_id}/executor-enroll",
        request,
    )

    return response


@app.post("/api/executor/heartbeat/{device_id}")
async def executor_heartbeat(
    device_id: str,
    request: Request,
):
    response = await registry_request(
        "POST",
        f"/api/executor/heartbeat/{device_id}",
        request,
    )

    return response


@app.get("/api/executor/jobs/{device_id}")
async def executor_jobs(
    device_id: str,
    request: Request,
):
    response = await registry_request(
        "GET",
        f"/api/executor/jobs/{device_id}",
        request,
    )

    return response


@app.post("/api/executor/jobs/{job_id}/result")
async def executor_job_result(
    job_id: str,
    request: Request,
):
    response = await registry_request(
        "POST",
        f"/api/executor/jobs/{job_id}/result",
        request,
    )

    return response


# ------------------------------------------------------------
# Admin control plane
# ------------------------------------------------------------

@app.post("/api/control/jobs")
async def create_control_job(
    request: Request,
):
    claims = await verify_admin(request)

    body = await request.body()

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="invalid JSON body",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="JSON object required",
        )

    # Do not trust client-supplied identity.
    payload["created_by"] = (
        claims.get("preferred_username")
        or claims.get("email")
        or claims.get("sub")
        or "unknown-admin"
    )

    body = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()

    response = await registry_control_request(
        "POST",
        "/api/control/jobs",
        body,
    )

    return response


@app.get("/api/control/jobs/{job_id}")
async def get_control_job(
    job_id: str,
    request: Request,
):
    await verify_admin(request)

    response = await registry_control_request(
        "GET",
        f"/api/control/jobs/{job_id}",
    )

    return response
