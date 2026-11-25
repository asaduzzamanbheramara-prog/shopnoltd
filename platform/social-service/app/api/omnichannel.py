from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone
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
AUTOMATION_TOKEN = os.getenv("SHOPNOLTD_INTERNAL_AUTOMATION_TOKEN", "")
N8N_ACTION_TOKEN = os.getenv("SHOPNOLTD_N8N_ACTION_TOKEN", "")

PLATFORMS = {
    "whatsapp", "facebook", "instagram", "linkedin", "x", "telegram",
    "tiktok", "youtube", "gmail", "outlook", "3cx",
}

# This is deliberately a readiness registry, not a promise that every provider
# supports the same OAuth/discovery semantics. Provider credentials are supplied
# only through Kubernetes/runtime secrets.
PROVIDER_CONFIG = {
    "google": {"platforms": ["gmail", "youtube"], "client_id": settings.google_client_id, "client_secret": settings.google_client_secret, "auth_url": "https://accounts.google.com/o/oauth2/v2/auth", "token_url": "https://oauth2.googleapis.com/token", "scopes": ["openid", "email", "profile"], "credential_keys": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]},
    "microsoft": {"platforms": ["outlook"], "client_id": settings.microsoft_client_id, "client_secret": settings.microsoft_client_secret, "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize", "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token", "scopes": ["openid", "profile", "email", "offline_access", "https://graph.microsoft.com/User.Read"], "credential_keys": ["MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET"]},
    "linkedin": {"platforms": ["linkedin"], "client_id": settings.linkedin_client_id, "client_secret": settings.linkedin_client_secret, "auth_url": "https://www.linkedin.com/oauth/v2/authorization", "token_url": "https://www.linkedin.com/oauth/v2/accessToken", "scopes": ["openid", "profile", "email"], "credential_keys": ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"]},
    "x": {"platforms": ["x"], "client_id": settings.x_client_id, "client_secret": settings.x_client_secret, "auth_url": "https://x.com/i/oauth2/authorize", "token_url": "https://api.x.com/2/oauth2/token", "scopes": ["tweet.read", "users.read", "offline.access"], "credential_keys": ["X_CLIENT_ID", "X_CLIENT_SECRET"]},
    "facebook": {"platforms": ["facebook"], "client_id": settings.facebook_client_id, "client_secret": settings.facebook_client_secret, "auth_url": "https://www.facebook.com/v24.0/dialog/oauth", "token_url": "https://graph.facebook.com/v24.0/oauth/access_token", "scopes": [], "credential_keys": ["FACEBOOK_CLIENT_ID", "FACEBOOK_CLIENT_SECRET"]},
    "instagram": {"platforms": ["instagram"], "client_id": settings.instagram_client_id or settings.facebook_client_id, "client_secret": settings.instagram_client_secret or settings.facebook_client_secret, "auth_url": "https://www.facebook.com/v24.0/dialog/oauth", "token_url": "https://graph.facebook.com/v24.0/oauth/access_token", "scopes": [], "credential_keys": ["INSTAGRAM_CLIENT_ID", "INSTAGRAM_CLIENT_SECRET"]},
    "tiktok": {"platforms": ["tiktok"], "client_id": settings.tiktok_client_key, "client_secret": settings.tiktok_client_secret, "auth_url": "https://www.tiktok.com/v2/auth/authorize/", "token_url": "https://open.tiktokapis.com/v2/oauth/token/", "scopes": ["user.info.basic"], "credential_keys": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"]},
    "telegram": {"platforms": ["telegram"], "client_id": None, "client_secret": None, "bot_token": settings.telegram_bot_token, "credential_keys": ["TELEGRAM_BOT_TOKEN"], "auth_url": None, "token_url": None, "scopes": [], "mode": "bot"},
    "whatsapp": {"platforms": ["whatsapp"], "client_id": settings.whatsapp_client_id, "client_secret": settings.whatsapp_client_secret, "credential_keys": ["WHATSAPP_CLIENT_ID", "WHATSAPP_CLIENT_SECRET"], "auth_url": None, "token_url": None, "scopes": [], "mode": "business_cloud", "setup_status": "business_onboarding_required"},
    "3cx": {"platforms": ["3cx"], "client_id": settings.threecx_client_id, "client_secret": settings.threecx_client_secret, "base_url": settings.threecx_base_url, "credential_keys": ["THREECX_CLIENT_ID", "THREECX_CLIENT_SECRET", "THREECX_BASE_URL"], "auth_url": None, "token_url": None, "scopes": [], "mode": "provider_api"},
}

async def db():
    async with SessionLocal() as s:
        yield s

async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc


async def registration_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    """Allow the internal automation token only for connection registration."""
    if AUTOMATION_TOKEN and hmac.compare_digest(creds.credentials, AUTOMATION_TOKEN):
        return {"sub": "n8n-automation", "tenant_id": "default", "automation": True}
    return await current_user(creds)


async def action_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    """Allow the dedicated n8n action token to enqueue in the default tenant only."""
    if N8N_ACTION_TOKEN and hmac.compare_digest(creds.credentials, N8N_ACTION_TOKEN):
        return {"sub": "n8n-action-queue", "tenant_id": "default", "automation": True}
    return await current_user(creds)

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
    approved: bool = False


@router.get("/providers")
async def provider_status(user=Depends(current_user)):
    """Return safe provider readiness metadata; never return client secrets."""
    result = []
    for provider, cfg in PROVIDER_CONFIG.items():
        mode = cfg.get("mode", "oauth2")
        if mode == "bot":
            configured = bool(cfg.get("bot_token"))
            setup_status = "bot_configured" if configured else "needs_bot_token"
        elif mode == "business_cloud":
            configured = bool(cfg.get("client_id") and cfg.get("client_secret"))
            setup_status = cfg.get("setup_status", "business_onboarding_required") if configured else "needs_app_credentials"
        elif mode == "provider_api":
            configured = bool(cfg.get("client_id") and cfg.get("client_secret") and cfg.get("base_url"))
            setup_status = "api_config_present_adapter_unverified" if configured else "needs_api_credentials_and_base_url"
        else:
            configured = bool(cfg.get("client_id") and cfg.get("client_secret"))
            setup_status = "ready_to_authorize" if configured else "needs_app_credentials"
        result.append({
            "provider": provider,
            "platforms": cfg["platforms"],
            "configured": configured,
            "executor_enabled": settings.omnichannel_executor_enabled,
            "mode": mode,
            "setup_status": setup_status,
            "required_credentials": cfg.get("credential_keys", []),
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
        "FROM social_connections WHERE tenant_id=:tenant AND owner_user_id=:user "
        "ORDER BY platform, display_name"
    ), {"tenant": tenant_id, "user": str(user.get("sub") or user.get("user_id") or "")})).mappings().all()
    return [dict(r) for r in rows]

@router.get("/connections/{connection_id}")
async def get_connection(connection_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    row = (await s.execute(text(
        """SELECT id, platform, account_type, platform_account_id, username, display_name,
                  status, scopes, token_expires_at, metadata, connected_at, last_sync_at,
                  created_at, updated_at
           FROM social_connections
           WHERE tenant_id=:tenant AND owner_user_id=:user AND id=:id"""
    ), {"tenant": tenant_id, "user": str(user.get("sub") or user.get("user_id") or ""), "id": connection_id})).mappings().one_or_none()
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
    params = {"tenant": tenant_id, "user": str(user.get("sub") or user.get("user_id") or ""), "id": connection_id}
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
            WHERE tenant_id=:tenant AND owner_user_id=:user AND id=:id
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
    user_id = str(user.get("sub") or user.get("user_id") or "")
    row = (await s.execute(text(
        """SELECT c.platform, c.platform_account_id, t.user_id
           FROM social_connections c
           LEFT JOIN omnichannel_oauth_tokens t
             ON t.tenant_id=c.tenant_id
            AND t.platform=c.platform
            AND t.provider_account_id=c.platform_account_id
            AND t.provider=COALESCE(c.metadata->>'provider', t.provider)
           WHERE c.tenant_id=:tenant AND c.owner_user_id=:user AND c.id=:id"""
    ), {"tenant": tenant_id, "user": user_id, "id": connection_id})).mappings().one_or_none()
    if row is None or (row["user_id"] and row["user_id"] != user_id):
        raise HTTPException(404, "connection not found")
    # Remove the encrypted credentials as part of disconnect; do not leave an
    # orphaned OAuth profile/token that can still be selected by the executor.
    await s.execute(text(
        """DELETE FROM omnichannel_oauth_tokens
           WHERE tenant_id=:tenant AND platform=:platform AND provider_account_id=:account_id
             AND provider=COALESCE((SELECT metadata->>'provider' FROM social_connections
                                    WHERE tenant_id=:tenant AND id=:id), provider)
             AND user_id=:user"""
    ), {
        "tenant": tenant_id, "platform": row["platform"],
        "account_id": row["platform_account_id"], "user": user_id,
    })
    await s.execute(text(
        "DELETE FROM social_connections WHERE tenant_id=:tenant AND id=:id"
    ), {"tenant": tenant_id, "id": connection_id})
    await s.commit()
    return None


@router.post("/connections", status_code=201)
async def add_connection(body: ConnectionIn, user=Depends(registration_user), s: AsyncSession = Depends(db)):
    platform = body.platform.lower().strip()
    if platform not in PLATFORMS:
        raise HTTPException(400, f"unsupported platform: {platform}")
    tenant_id = user.get("tenant_id", "default")
    connection_id = str(uuid4())
    row = (await s.execute(text(
        """INSERT INTO social_connections
        (id, tenant_id, owner_user_id, platform, account_type, platform_account_id, username, display_name,
         status, scopes, access_token_ref, refresh_token_ref, token_expires_at, metadata, connected_at)
        VALUES (:id, :tenant, :user, :platform, :account_type, :account_id, :username, :display_name,
                :status, :scopes::jsonb, :access_ref, :refresh_ref,
                NULLIF(:expires, '')::timestamptz, :metadata::jsonb, NOW())
        ON CONFLICT (tenant_id, platform, platform_account_id)
        DO UPDATE SET username=EXCLUDED.username, display_name=EXCLUDED.display_name,
                      status=EXCLUDED.status, scopes=EXCLUDED.scopes,
                      access_token_ref=EXCLUDED.access_token_ref,
                      refresh_token_ref=EXCLUDED.refresh_token_ref,
                      token_expires_at=EXCLUDED.token_expires_at,
                      metadata=EXCLUDED.metadata, updated_at=NOW()
        WHERE social_connections.owner_user_id=EXCLUDED.owner_user_id
        RETURNING id, platform, account_type, platform_account_id, username, display_name,
                  status, scopes, token_expires_at, metadata, connected_at, last_sync_at"""
    ), {
        "id": connection_id, "tenant": tenant_id,
        "user": str(user.get("sub") or user.get("user_id") or ""),
        "platform": platform, "account_type": body.account_type, "account_id": body.platform_account_id,
        "username": body.username, "display_name": body.display_name, "status": body.status,
        "scopes": __import__("json").dumps(body.scopes),
        "access_ref": body.access_token_ref, "refresh_ref": body.refresh_token_ref,
        "expires": body.token_expires_at or "",
        "metadata": __import__("json").dumps(body.metadata),
    })).mappings().one_or_none()
    if row is None:
        raise HTTPException(409, "this platform account is already registered by another owner")
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
async def queue_action(body: ActionIn, user=Depends(action_user), s: AsyncSession = Depends(db)):
    platform = body.platform.lower().strip()
    action = body.action.lower().strip()
    if platform not in PLATFORMS:
        raise HTTPException(400, f"unsupported platform: {platform}")
    # Do not acknowledge work that has no active consumer. The executor is
    # intentionally disabled until provider credentials and sandbox E2E tests
    # pass; returning 202 here would leave approved messages/posts queued forever.
    if not settings.omnichannel_executor_enabled:
        raise HTTPException(
            status_code=503,
            detail="omnichannel action executor is disabled; no action was queued",
        )
    tenant_id = user.get("tenant_id", "default")
    capability = (await s.execute(text(
        "SELECT availability FROM platform_capabilities WHERE platform=:platform AND action=:action"
    ), {"platform": platform, "action": action})).scalar_one_or_none()
    if capability is None:
        raise HTTPException(400, f"unsupported action for platform: {platform}/{action}")

    supported_provider_actions = {
        ("gmail", "send_message"), ("outlook", "send_message"),
        ("x", "create_post"), ("linkedin", "create_post"),
    }
    if (platform, action) in supported_provider_actions and not body.connection_id:
        raise HTTPException(422, "connection_id is required for this provider action")
    if (platform, action) in supported_provider_actions and not (body.idempotency_key or "").strip():
        raise HTTPException(422, "idempotency_key is required for this provider action")

    if body.connection_id:
        connection = (await s.execute(text(
            "SELECT platform, status FROM social_connections WHERE tenant_id=:tenant AND id=:id"
        ), {"tenant": tenant_id, "id": body.connection_id})).mappings().one_or_none()
        if connection is None:
            raise HTTPException(404, "connection not found")
        if connection["platform"] != platform:
            raise HTTPException(409, "connection platform does not match action platform")
        if (platform, action) in supported_provider_actions and connection["status"] != "connected":
            raise HTTPException(409, "provider connection is not connected")
        if (platform, action) in supported_provider_actions:
            owned = (await s.execute(text("""
                SELECT 1
                FROM social_connections c
                JOIN omnichannel_oauth_tokens t
                  ON t.tenant_id=c.tenant_id
                 AND t.platform=c.platform
                 AND t.provider_account_id=c.platform_account_id
                WHERE c.tenant_id=:tenant AND c.id=:id
                  AND c.platform=:platform
                  AND t.user_id=:user AND t.status='connected'
            """), {
                "tenant": tenant_id, "id": body.connection_id,
                "platform": platform, "user": str(user.get("sub") or user.get("user_id") or ""),
            })).scalar_one_or_none()
            if not owned:
                raise HTTPException(404, "connected account not found for this user")

    # Any action with external side effects requires an explicit approval from an
    # authenticated human. The n8n/service tokens are intentionally not approvers.
    side_effect_actions = {
        "send_message", "send_email", "create_post", "schedule_post", "comment",
        "reply", "like", "reaction", "share", "follow", "unfollow",
        "friend_request", "live", "call",
    }
    payload = dict(body.payload)
    if action in side_effect_actions:
        if not body.approved:
            raise HTTPException(403, "explicit human approval is required for provider actions")
        if user.get("automation") or str(user.get("sub") or "").startswith(("n8n-", "automation-")):
            raise HTTPException(403, "automation identities cannot approve provider actions")
        payload["_requested_by"] = str(user.get("sub") or user.get("user_id") or "")
        payload["approval"] = {
            "approved": True,
            "approved_by": str(user.get("sub") or user.get("user_id") or ""),
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }

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
        "client": body.client_id, "platform": platform, "action": action,
        "target_type": body.target_type, "target_id": body.target_id,
        "idem": body.idempotency_key or action_id,
        "payload": __import__("json").dumps(payload),
    })).mappings().one()
    await s.commit()
    return {**dict(row), "capability": capability}
