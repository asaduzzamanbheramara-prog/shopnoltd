from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.core.config import settings

router = APIRouter()
bearer = HTTPBearer()

PLATFORMS = {
    "whatsapp", "facebook", "instagram", "linkedin", "x", "telegram",
    "tiktok", "youtube", "gmail", "outlook", "3cx",
}

# This is deliberately a readiness registry, not a promise that every provider
# supports the same OAuth/discovery semantics. Provider credentials are supplied
# only through Kubernetes/runtime secrets.
PROVIDER_CONFIG = {
    "google": {"platforms": ["gmail", "youtube"], "client_id": settings.google_client_id, "client_secret": settings.google_client_secret, "auth_url": "https://accounts.google.com/o/oauth2/v2/auth", "token_url": "https://oauth2.googleapis.com/token", "scopes": ["openid", "email", "profile"]},
    "microsoft": {"platforms": ["outlook"], "client_id": settings.microsoft_client_id, "client_secret": settings.microsoft_client_secret, "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize", "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token", "scopes": ["openid", "profile", "email", "offline_access", "https://graph.microsoft.com/User.Read"]},
    "linkedin": {"platforms": ["linkedin"], "client_id": settings.linkedin_client_id, "client_secret": settings.linkedin_client_secret, "auth_url": "https://www.linkedin.com/oauth/v2/authorization", "token_url": "https://www.linkedin.com/oauth/v2/accessToken", "scopes": ["openid", "profile", "email"]},
    "x": {"platforms": ["x"], "client_id": settings.x_client_id, "client_secret": settings.x_client_secret, "auth_url": "https://twitter.com/i/oauth2/authorize", "token_url": "https://api.x.com/2/oauth2/token", "scopes": ["tweet.read", "users.read", "offline.access"]},
    "facebook": {"platforms": ["facebook", "instagram"], "client_id": settings.facebook_client_id, "client_secret": settings.facebook_client_secret, "auth_url": "https://www.facebook.com/v24.0/dialog/oauth", "token_url": "https://graph.facebook.com/v24.0/oauth/access_token", "scopes": []},
    "instagram": {"platforms": ["instagram"], "client_id": settings.instagram_client_id, "client_secret": settings.instagram_client_secret, "auth_url": "https://www.facebook.com/v24.0/dialog/oauth", "token_url": "https://graph.facebook.com/v24.0/oauth/access_token", "scopes": []},
    "tiktok": {"platforms": ["tiktok"], "client_id": settings.tiktok_client_key, "client_secret": settings.tiktok_client_secret, "auth_url": "https://www.tiktok.com/v2/auth/authorize/", "token_url": "https://open.tiktokapis.com/v2/oauth/token/", "scopes": ["user.info.basic"]},
    "telegram": {"platforms": ["telegram"], "client_id": None, "client_secret": None, "auth_url": None, "token_url": None, "scopes": [], "mode": "bot"},
    "whatsapp": {"platforms": ["whatsapp"], "client_id": settings.whatsapp_client_id, "client_secret": settings.whatsapp_client_secret, "auth_url": None, "token_url": None, "scopes": [], "mode": "business_cloud"},
    "3cx": {"platforms": ["3cx"], "client_id": settings.threecx_client_id, "client_secret": settings.threecx_client_secret, "auth_url": None, "token_url": None, "scopes": [], "mode": "provider_api"},
}

async def db():
    async with SessionLocal() as s:
        yield s

async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)

class ConnectionIn(BaseModel):
    platform: str
    account_type: str = "user"
    platform_account_id: str = Field(min_length=1, max_length=255)
    username: str | None = None
    display_name: str | None = None
    status: str = "connected"
    scopes: list[str] = Field(default_factory=list)
    access_token_ref: str | None = None
    refresh_token_ref: str | None = None
    token_expires_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class ConnectionPatch(BaseModel):
    account_type: str | None = None
    username: str | None = None
    display_name: str | None = None
    status: str | None = None
    scopes: list[str] | None = None
    access_token_ref: str | None = None
    refresh_token_ref: str | None = None
    token_expires_at: str | None = None
    metadata: dict[str, Any] | None = None


class ActionIn(BaseModel):
    platform: str
    action: str
    connection_id: str | None = None
    client_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    idempotency_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@router.get("/providers")
async def provider_status(user=Depends(current_user)):
    """Return safe provider readiness metadata; never return client secrets."""
    result = []
    for provider, cfg in PROVIDER_CONFIG.items():
        result.append({
            "provider": provider,
            "platforms": cfg["platforms"],
            "configured": bool(cfg.get("client_id") and cfg.get("client_secret")),
            "mode": cfg.get("mode", "oauth2"),
            "authorization_supported": bool(cfg.get("auth_url") and cfg.get("token_url")),
            "scopes": cfg.get("scopes", []),
            "redirect_uri": settings.provider_oauth_redirect_uri if cfg.get("auth_url") else None,
        })
    return result

@router.get("/capabilities")
async def capabilities(user=Depends(current_user), s: AsyncSession = Depends(db)):
    rows = (await s.execute(text(
        "SELECT platform, action, availability, requires_oauth, notes "
        "FROM platform_capabilities ORDER BY platform, action"
    ))).mappings().all()
    return [dict(r) for r in rows]

@router.get("/connections")
async def list_connections(user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    rows = (await s.execute(text(
        "SELECT id, platform, account_type, platform_account_id, username, display_name, "
        "status, scopes, token_expires_at, metadata, connected_at, last_sync_at "
        "FROM social_connections WHERE tenant_id=:tenant ORDER BY platform, display_name"
    ), {"tenant": tenant_id})).mappings().all()
    return [dict(r) for r in rows]

@router.get("/connections/{connection_id}")
async def get_connection(connection_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    row = (await s.execute(text(
        """SELECT id, platform, account_type, platform_account_id, username, display_name,
                  status, scopes, token_expires_at, metadata, connected_at, last_sync_at,
                  created_at, updated_at
           FROM social_connections
           WHERE tenant_id=:tenant AND id=:id"""
    ), {"tenant": tenant_id, "id": connection_id})).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "connection not found")
    capabilities = (await s.execute(text(
        "SELECT action, availability, requires_oauth, notes "
        "FROM platform_capabilities WHERE platform=:platform ORDER BY action"
    ), {"platform": row["platform"]})).mappings().all()
    return {**dict(row), "capabilities": [dict(item) for item in capabilities]}


@router.patch("/connections/{connection_id}")
async def update_connection(connection_id: str, body: ConnectionPatch, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    values = body.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(422, "at least one field is required")

    allowed = {
        "account_type": "account_type",
        "username": "username",
        "display_name": "display_name",
        "status": "status",
        "scopes": "scopes",
        "access_token_ref": "access_token_ref",
        "refresh_token_ref": "refresh_token_ref",
        "token_expires_at": "token_expires_at",
        "metadata": "metadata",
    }
    unknown = set(values) - set(allowed)
    if unknown:
        raise HTTPException(422, "unsupported connection field")

    assignments = []
    params = {"tenant": tenant_id, "id": connection_id}
    for key, column in allowed.items():
        if key not in values:
            continue
        assignments.append(f"{column}=:{key}")
        value = values[key]
        if key == "scopes":
            params[key] = __import__("json").dumps(value or [])
            assignments[-1] = f"{column}=:{key}::jsonb"
        elif key == "metadata":
            params[key] = __import__("json").dumps(value or {})
            assignments[-1] = f"{column}=:{key}::jsonb"
        elif key == "token_expires_at":
            params[key] = value or ""
            assignments[-1] = f"{column}=NULLIF(:{key}, '')::timestamptz"
        else:
            params[key] = value

    row = (await s.execute(text(
        f"""UPDATE social_connections
            SET {", ".join(assignments)}, updated_at=NOW()
            WHERE tenant_id=:tenant AND id=:id
            RETURNING id, platform, account_type, platform_account_id, username, display_name,
                      status, scopes, token_expires_at, metadata, connected_at, last_sync_at,
                      created_at, updated_at"""
    ), params)).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "connection not found")
    await s.commit()
    return dict(row)


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(connection_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    result = await s.execute(text(
        "DELETE FROM social_connections WHERE tenant_id=:tenant AND id=:id RETURNING id"
    ), {"tenant": tenant_id, "id": connection_id})
    if result.scalar_one_or_none() is None:
        raise HTTPException(404, "connection not found")
    await s.commit()
    return None


@router.post("/connections", status_code=201)
async def add_connection(body: ConnectionIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    platform = body.platform.lower().strip()
    if platform not in PLATFORMS:
        raise HTTPException(400, f"unsupported platform: {platform}")
    tenant_id = user.get("tenant_id", "default")
    connection_id = str(uuid4())
    row = (await s.execute(text(
        """INSERT INTO social_connections
        (id, tenant_id, platform, account_type, platform_account_id, username, display_name,
         status, scopes, access_token_ref, refresh_token_ref, token_expires_at, metadata, connected_at)
        VALUES (:id, :tenant, :platform, :account_type, :account_id, :username, :display_name,
                :status, :scopes::jsonb, :access_ref, :refresh_ref,
                NULLIF(:expires, '')::timestamptz, :metadata::jsonb, NOW())
        ON CONFLICT (tenant_id, platform, platform_account_id)
        DO UPDATE SET username=EXCLUDED.username, display_name=EXCLUDED.display_name,
                      status=EXCLUDED.status, scopes=EXCLUDED.scopes,
                      access_token_ref=EXCLUDED.access_token_ref,
                      refresh_token_ref=EXCLUDED.refresh_token_ref,
                      token_expires_at=EXCLUDED.token_expires_at,
                      metadata=EXCLUDED.metadata, updated_at=NOW()
        RETURNING id, platform, account_type, platform_account_id, username, display_name,
                  status, scopes, token_expires_at, metadata, connected_at, last_sync_at"""
    ), {
        "id": connection_id, "tenant": tenant_id, "platform": platform,
        "account_type": body.account_type, "account_id": body.platform_account_id,
        "username": body.username, "display_name": body.display_name, "status": body.status,
        "scopes": __import__("json").dumps(body.scopes),
        "access_ref": body.access_token_ref, "refresh_ref": body.refresh_token_ref,
        "expires": body.token_expires_at or "",
        "metadata": __import__("json").dumps(body.metadata),
    })).mappings().one()
    await s.commit()
    return dict(row)

@router.get("/clients/{client_id}/identities")
async def client_identities(client_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    rows = (await s.execute(text(
        "SELECT id, platform, platform_user_id, username, display_name, profile_url, phone, email, "
        "connection_id, first_seen_at, last_seen_at FROM client_platform_identity "
        "WHERE tenant_id=:tenant AND client_id=:client ORDER BY platform"
    ), {"tenant": tenant_id, "client": client_id})).mappings().all()
    return [dict(r) for r in rows]

@router.get("/clients/search")
async def search_clients(q: str = Query(min_length=2, max_length=200), user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    needle = f"%{q.strip()}%"
    rows = (await s.execute(text(
        """SELECT DISTINCT ON (client_id) client_id, display_name, username, phone, email, platform
        FROM client_platform_identity
        WHERE tenant_id=:tenant AND client_id IS NOT NULL
          AND (display_name ILIKE :q OR username ILIKE :q OR phone ILIKE :q OR email ILIKE :q
               OR platform_user_id ILIKE :q)
        ORDER BY client_id, last_seen_at DESC LIMIT 50"""
    ), {"tenant": tenant_id, "q": needle})).mappings().all()
    return [dict(r) for r in rows]

@router.post("/actions", status_code=202)
async def queue_action(body: ActionIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    platform = body.platform.lower().strip()
    if platform not in PLATFORMS:
        raise HTTPException(400, f"unsupported platform: {platform}")
    tenant_id = user.get("tenant_id", "default")
    capability = (await s.execute(text(
        "SELECT availability FROM platform_capabilities WHERE platform=:platform AND action=:action"
    ), {"platform": platform, "action": body.action})).scalar_one_or_none()
    if capability is None:
        raise HTTPException(400, f"unsupported action for platform: {platform}/{body.action}")

    if body.connection_id:
        connection = (await s.execute(text(
            "SELECT platform FROM social_connections WHERE tenant_id=:tenant AND id=:id"
        ), {"tenant": tenant_id, "id": body.connection_id})).scalar_one_or_none()
        if connection is None:
            raise HTTPException(404, "connection not found")
        if connection != platform:
            raise HTTPException(409, "connection platform does not match action platform")

    action_id = str(uuid4())
    row = (await s.execute(text(
        """INSERT INTO platform_actions
        (id, tenant_id, connection_id, client_id, platform, action, target_type, target_id,
         status, idempotency_key, request_payload)
        VALUES (:id, :tenant, NULLIF(:connection_id,'')::uuid, :client, :platform, :action,
                :target_type, :target_id, 'queued', NULLIF(:idem,''), :payload::jsonb)
        ON CONFLICT (tenant_id, idempotency_key) DO UPDATE SET updated_at=NOW()
        RETURNING id, status, platform, action, created_at"""
    ), {
        "id": action_id, "tenant": tenant_id, "connection_id": body.connection_id or "",
        "client": body.client_id, "platform": platform, "action": body.action,
        "target_type": body.target_type, "target_id": body.target_id,
        "idem": body.idempotency_key or action_id,
        "payload": __import__("json").dumps(body.payload),
    })).mappings().one()
    await s.commit()
    return {**dict(row), "capability": capability}
