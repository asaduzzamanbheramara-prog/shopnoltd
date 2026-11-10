from __future__ import annotations

import hmac
import os
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.core.social_capabilities import (
    SIDE_EFFECT_ACTIONS,
    SUPPORTED_PROVIDER_ACTIONS,
    is_supported_provider_action,
    requires_human_approval,
)

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
    "google": {"platforms": ["gmail", "youtube"], "client_id": settings.google_client_id, "client_secret": settings.google_client_secret, "auth_url": "https://accounts.google.com/o/oauth2/v2/auth", "token_url": "https://oauth2.googleapis.com/token", "scopes": ["openid", "email", "profile"]},
    "microsoft": {"platforms": ["outlook"], "client_id": settings.microsoft_client_id, "client_secret": settings.microsoft_client_secret, "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize", "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token", "scopes": ["openid", "profile", "email", "offline_access", "https://graph.microsoft.com/User.Read"]},
    "linkedin": {"platforms": ["linkedin"], "client_id": settings.linkedin_client_id, "client_secret": settings.linkedin_client_secret, "auth_url": "https://www.linkedin.com/oauth/v2/authorization", "token_url": "https://www.linkedin.com/oauth/v2/accessToken", "scopes": ["openid", "profile", "email"]},
    "x": {"platforms": ["x"], "client_id": settings.x_client_id, "client_secret": settings.x_client_secret, "auth_url": "https://twitter.com/i/oauth2/authorize", "token_url": "https://api.x.com/2/oauth2/token", "scopes": ["tweet.read", "users.read", "offline.access"]},
    "facebook": {"platforms": ["facebook", "instagram"], "client_id": settings.facebook_client_id, "client_secret": settings.facebook_client_secret, "auth_url": "https://www.facebook.com/v24.0/dialog/oauth", "token_url": "https://graph.facebook.com/v24.0/oauth/access_token", "scopes": []},
    "instagram": {"platforms": ["instagram"], "client_id": settings.facebook_client_id, "client_secret": settings.facebook_client_secret, "auth_url": "https://www.facebook.com/v24.0/dialog/oauth", "token_url": "https://graph.facebook.com/v24.0/oauth/access_token", "scopes": []},
    "tiktok": {"platforms": ["tiktok"], "client_id": settings.tiktok_client_key, "client_secret": settings.tiktok_client_secret, "auth_url": "https://www.tiktok.com/v2/auth/authorize/", "token_url": "https://open.tiktokapis.com/v2/oauth/token/", "scopes": ["user.info.basic"]},
    "telegram": {"platforms": ["telegram"], "client_id": None, "client_secret": None, "auth_url": None, "token_url": None, "scopes": [], "mode": "bot"},
    "whatsapp": {"platforms": ["whatsapp"], "client_id": settings.whatsapp_client_id, "client_secret": settings.whatsapp_client_secret, "auth_url": None, "token_url": None, "scopes": [], "mode": "business_cloud"},
    "3cx": {"platforms": ["3cx"], "client_id": settings.threecx_client_id, "client_secret": settings.threecx_client_secret, "auth_url": None, "token_url": None, "scopes": [], "mode": "provider_api"},
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
    model_config = ConfigDict(extra="forbid")
    platform: str
    account_type: str = "user"
    platform_account_id: str = Field(min_length=1, max_length=255)
    username: str | None = None
    display_name: str | None = None
    status: str = "connected"
    scopes: list[str] = Field(default_factory=list)
    access_token_ref: str | None = Field(default=None, max_length=255)
    refresh_token_ref: str | None = Field(default=None, max_length=255)
    token_expires_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("access_token_ref", "refresh_token_ref")
    @classmethod
    def validate_secret_reference(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        reference = value.strip()
        if not re.fullmatch(
            r"(?:vault|k8s-secret|secret|aws-secretsmanager|gcp-secretmanager|azure-keyvault)://[A-Za-z0-9._/:#@-]+",
            reference,
        ):
            raise ValueError("credential fields must be secret-manager reference URIs; never paste raw tokens")
        return reference

    @model_validator(mode="after")
    def reject_secret_material_in_metadata(self):
        forbidden = re.compile(r"(?:access|refresh)?_?token|secret|password|credential|authorization|cookie|api[_-]?key", re.I)

        def inspect(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    if forbidden.search(str(key)):
                        raise ValueError("metadata must not contain token, secret, password, or credential fields")
                    inspect(nested)
            elif isinstance(value, list):
                for nested in value:
                    inspect(nested)
            elif isinstance(value, str):
                candidate = value.strip()
                if candidate.lower().startswith(("bearer ", "ya29.", "eaa", "rft.", "act.")):
                    raise ValueError("metadata must not contain raw provider credentials")

        inspect(self.metadata)
        return self


class ConnectionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_type: str | None = None
    username: str | None = None
    display_name: str | None = None


class ActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    platform: str
    action: str
    connection_id: UUID | None = None
    client_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    idempotency_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False


def _normalize_action(value: str) -> str:
    action = value.lower().strip()
    if not action or len(action) > 64:
        raise HTTPException(400, "invalid action")
    return action


@router.get("/providers")
async def provider_status(user=Depends(current_user)):
    """Return safe provider readiness metadata; never return client secrets."""
    result = []
    for provider, cfg in PROVIDER_CONFIG.items():
        result.append({
            "provider": provider,
            "platforms": cfg["platforms"],
            "configured": bool(
                cfg.get("client_id") and cfg.get("client_secret")
                and settings.provider_oauth_state_secret
                and settings.provider_oauth_encryption_ready
            ),
            "security_ready": bool(
                settings.provider_oauth_state_secret
                and settings.provider_oauth_encryption_ready
            ),
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
        "status, scopes, token_expires_at, metadata, connected_at, last_sync_at, "
        "EXISTS (SELECT 1 FROM omnichannel_oauth_tokens t WHERE t.tenant_id=c.tenant_id "
        "AND t.platform=c.platform AND t.provider_account_id=c.platform_account_id "
        "AND t.user_id=:user AND t.status='connected' "
        "AND (t.token_expires_at IS NULL OR t.token_expires_at > NOW() "
        "OR (t.encrypted_refresh_token IS NOT NULL "
        "AND (t.refresh_token_expires_at IS NULL OR t.refresh_token_expires_at > NOW())))) AS oauth_authorized "
        "FROM social_connections c WHERE tenant_id=:tenant AND (owner_user_id=:user OR EXISTS ("
        "SELECT 1 FROM omnichannel_oauth_tokens t WHERE t.tenant_id=c.tenant_id "
        "AND t.platform=c.platform AND t.provider_account_id=c.platform_account_id "
        "AND t.user_id=:user AND t.status='connected') AND owner_user_id IS NULL) "
        "ORDER BY platform, display_name"
    ), {"tenant": tenant_id, "user": str(user.get("sub") or user.get("user_id") or "")})).mappings().all()
    return [dict(r) for r in rows]

@router.get("/connections/{connection_id}")
async def get_connection(connection_id: UUID, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    row = (await s.execute(text(
        """SELECT id, platform, account_type, platform_account_id, username, display_name,
                  status, scopes, token_expires_at, metadata, connected_at, last_sync_at,
                  created_at, updated_at
           FROM social_connections
           WHERE tenant_id=:tenant AND id=:id AND (owner_user_id=:user OR EXISTS (
             SELECT 1 FROM omnichannel_oauth_tokens t
             WHERE t.tenant_id=social_connections.tenant_id
               AND t.platform=social_connections.platform
               AND t.provider_account_id=social_connections.platform_account_id
               AND t.user_id=:user AND t.status='connected') AND social_connections.owner_user_id IS NULL)"""
    ), {"tenant": tenant_id, "id": connection_id, "user": str(user.get("sub") or user.get("user_id") or "")})).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "connection not found")
    capabilities = (await s.execute(text(
        "SELECT action, availability, requires_oauth, notes "
        "FROM platform_capabilities WHERE platform=:platform ORDER BY action"
    ), {"platform": row["platform"]})).mappings().all()
    return {**dict(row), "capabilities": [dict(item) for item in capabilities]}


@router.patch("/connections/{connection_id}")
async def update_connection(connection_id: UUID, body: ConnectionPatch, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    values = body.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(422, "at least one field is required")

    allowed = {
        "account_type": "account_type",
        "username": "username",
        "display_name": "display_name",
    }
    unknown = set(values) - set(allowed)
    if unknown:
        raise HTTPException(422, "unsupported connection field")

    if "account_type" in values and values["account_type"] is None:
        raise HTTPException(422, "account_type cannot be null")
    assignments = []
    params = {"tenant": tenant_id, "id": connection_id,
              "user": str(user.get("sub") or user.get("user_id") or "")}
    for key, column in allowed.items():
        if key not in values:
            continue
        assignments.append(f"{column}=:{key}")
        params[key] = values[key]

    row = (await s.execute(text(
        f"""UPDATE social_connections
            SET {", ".join(assignments)}, updated_at=NOW()
            WHERE tenant_id=:tenant AND id=:id AND (owner_user_id=:user OR EXISTS (
              SELECT 1 FROM omnichannel_oauth_tokens t
              WHERE t.tenant_id=social_connections.tenant_id
                AND t.platform=social_connections.platform
                AND t.provider_account_id=social_connections.platform_account_id
                AND t.user_id=:user AND t.status='connected') AND social_connections.owner_user_id IS NULL)
            RETURNING id, platform, account_type, platform_account_id, username, display_name,
                      status, scopes, token_expires_at, metadata, connected_at, last_sync_at,
                      created_at, updated_at"""
    ), params)).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "connection not found")
    await s.commit()
    return dict(row)


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(connection_id: UUID, user=Depends(current_user), s: AsyncSession = Depends(db)):
    tenant_id = user.get("tenant_id", "default")
    user_id = str(user.get("sub") or user.get("user_id") or "")
    result = await s.execute(text("""
        UPDATE social_connections
        SET status='disconnected', updated_at=NOW()
        WHERE tenant_id=:tenant AND id=:id
          AND (owner_user_id=:user OR EXISTS (
            SELECT 1 FROM omnichannel_oauth_tokens t
            WHERE t.tenant_id=social_connections.tenant_id
              AND t.platform=social_connections.platform
              AND t.provider_account_id=social_connections.platform_account_id
              AND t.user_id=:user) AND social_connections.owner_user_id IS NULL)
        RETURNING id, platform, platform_account_id
    """), {"tenant": tenant_id, "id": connection_id, "user": user_id})
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "connection not found")
    automation_schema_ready = bool((await s.execute(
        text("SELECT to_regclass('public.social_automation_schedules')")
    )).scalar())
    if automation_schema_ready:
        await s.execute(text("""
            UPDATE social_automation_schedules
            SET enabled=FALSE, paused_reason='Account disconnected by user', updated_at=NOW()
            WHERE tenant_id=:tenant AND user_id=:user AND connection_id=:connection
        """), {"tenant": tenant_id, "user": user_id, "connection": row["id"]})
        await s.execute(text("""
            UPDATE social_post_drafts
            SET status='cancelled', error_message='Account disconnected by user.',
                updated_at=NOW()
            WHERE tenant_id=:tenant AND user_id=:user AND connection_id=:connection
              AND status IN ('draft','pending_approval','queued')
        """), {"tenant": tenant_id, "user": user_id, "connection": row["id"]})
    await s.execute(text("""
        UPDATE platform_actions
        SET status='cancelled', error_code='connection_disconnected',
            error_message='Account disconnected by user.',
            completed_at=NOW(), updated_at=NOW()
        WHERE tenant_id=:tenant AND connection_id=:connection AND status='queued'
    """), {"tenant": tenant_id, "connection": row["id"]})
    await s.execute(text("""
        UPDATE omnichannel_oauth_tokens
        SET status='revoked', encrypted_access_token='', encrypted_refresh_token=NULL,
            updated_at=NOW()
        WHERE tenant_id=:tenant AND platform=:platform
          AND provider_account_id=:account AND user_id=:user
    """), {"tenant": tenant_id, "platform": row["platform"],
           "account": row["platform_account_id"], "user": user_id})
    await s.commit()
    return None


@router.post("/connections", status_code=201)
async def add_connection(body: ConnectionIn, user=Depends(registration_user), s: AsyncSession = Depends(db)):
    platform = body.platform.lower().strip()
    if platform not in PLATFORMS:
        raise HTTPException(400, f"unsupported platform: {platform}")
    tenant_id = user.get("tenant_id", "default")
    connection_id = str(uuid4())
    owner_user_id = str(user.get("sub") or user.get("user_id") or "") or None
    existing = (await s.execute(text("""
        SELECT c.owner_user_id,
               (SELECT t.user_id FROM omnichannel_oauth_tokens t
                WHERE t.tenant_id=c.tenant_id AND t.platform=c.platform
                  AND t.provider_account_id=c.platform_account_id
                LIMIT 1) AS token_owner_user_id
        FROM social_connections c
        WHERE c.tenant_id=:tenant AND c.platform=:platform
          AND c.platform_account_id=:account
        FOR UPDATE OF c
    """), {"tenant": tenant_id, "platform": platform,
           "account": body.platform_account_id})).mappings().one_or_none()
    if existing:
        if existing["owner_user_id"] not in (None, owner_user_id):
            raise HTTPException(409, "this platform account is already connected to another user in this tenant")
        if existing["token_owner_user_id"] not in (None, owner_user_id):
            raise HTTPException(409, "this provider account already has an OAuth grant owned by another user")
    row = (await s.execute(text(
        """INSERT INTO social_connections
        (id, tenant_id, owner_user_id, platform, account_type, platform_account_id, username, display_name,
         status, scopes, access_token_ref, refresh_token_ref, token_expires_at, metadata, connected_at)
        VALUES (:id, :tenant, :owner_user, :platform, :account_type, :account_id, :username, :display_name,
                :status, :scopes::jsonb, :access_ref, :refresh_ref,
                NULLIF(:expires, '')::timestamptz, :metadata::jsonb, NOW())
        ON CONFLICT (tenant_id, platform, platform_account_id)
        DO UPDATE SET username=EXCLUDED.username, display_name=EXCLUDED.display_name,
                      status=EXCLUDED.status, scopes=EXCLUDED.scopes,
                      access_token_ref=EXCLUDED.access_token_ref,
                      refresh_token_ref=EXCLUDED.refresh_token_ref,
                      token_expires_at=EXCLUDED.token_expires_at,
                      metadata=EXCLUDED.metadata,
                      owner_user_id=COALESCE(social_connections.owner_user_id, EXCLUDED.owner_user_id),
                      updated_at=NOW()
        WHERE social_connections.owner_user_id IS NULL
           OR social_connections.owner_user_id=EXCLUDED.owner_user_id
        RETURNING id, platform, account_type, platform_account_id, username, display_name,
                  status, scopes, token_expires_at, metadata, connected_at, last_sync_at"""
    ), {
        "id": connection_id, "tenant": tenant_id, "owner_user": owner_user_id,
        "platform": platform, "account_type": body.account_type, "account_id": body.platform_account_id,
        "username": body.username, "display_name": body.display_name, "status": body.status,
        "scopes": __import__("json").dumps(body.scopes),
        "access_ref": body.access_token_ref, "refresh_ref": body.refresh_token_ref,
        "expires": body.token_expires_at or "",
        "metadata": __import__("json").dumps(body.metadata),
    })).mappings().one_or_none()
    if row is None:
        raise HTTPException(409, "this platform account is already connected to another user")
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
    action = _normalize_action(body.action)
    if platform not in PLATFORMS:
        raise HTTPException(400, f"unsupported platform: {platform}")
    tenant_id = user.get("tenant_id", "default")
    capability = (await s.execute(text(
        "SELECT availability FROM platform_capabilities WHERE platform=:platform AND action=:action"
    ), {"platform": platform, "action": action})).scalar_one_or_none()
    if capability is None:
        raise HTTPException(400, f"unsupported action for platform: {platform}/{action}")
    if capability not in {"supported", "provider_dependent"}:
        raise HTTPException(409, f"provider capability is not enabled for platform: {platform}/{action}")

    if requires_human_approval(action) and not is_supported_provider_action(platform, action):
        raise HTTPException(409, "no tested official provider adapter is enabled for this action")
    if (platform, action) in SUPPORTED_PROVIDER_ACTIONS and not settings.omnichannel_executor_enabled:
        raise HTTPException(409, "provider executor is disabled by the server")
    if (platform, action) in SUPPORTED_PROVIDER_ACTIONS and not settings.provider_oauth_encryption_ready:
        raise HTTPException(503, "provider token encryption is not configured")
    if (platform, action) in SUPPORTED_PROVIDER_ACTIONS:
        schema_ready = bool(await s.scalar(text("""
            SELECT to_regclass('public.social_automation_schedules') IS NOT NULL
               AND to_regclass('public.social_post_drafts') IS NOT NULL
               AND to_regclass('public.omnichannel_oauth_tokens') IS NOT NULL
               AND to_regclass('public.platform_actions') IS NOT NULL
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='social_connections'
                     AND column_name='owner_user_id'
               )
               AND EXISTS (
                   SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='social_automation_schedules'
                     AND column_name='paused_reason'
               )
               AND to_regclass('public.ux_social_automation_schedule_owner_slot') IS NOT NULL
        """)))
        if not schema_ready:
            raise HTTPException(503, "social automation database migration 021 is not fully installed")
    if (platform, action) in SUPPORTED_PROVIDER_ACTIONS and not body.connection_id:
        raise HTTPException(422, "connection_id is required for this provider action")
    if (platform, action) in SUPPORTED_PROVIDER_ACTIONS and not (body.idempotency_key or "").strip():
        raise HTTPException(422, "idempotency_key is required for this provider action")

    if body.connection_id:
        user_id = str(user.get("sub") or user.get("user_id") or "")
        connection = (await s.execute(text("""
            SELECT c.platform, c.status
            FROM social_connections c
            WHERE c.tenant_id=:tenant AND c.id=:id
              AND (
                c.owner_user_id=:user
                OR (
                  c.owner_user_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM omnichannel_oauth_tokens t
                    WHERE t.tenant_id=c.tenant_id AND t.platform=c.platform
                      AND t.provider_account_id=c.platform_account_id
                      AND t.user_id=:user AND t.status='connected'
                  )
                )
              )
        """), {"tenant": tenant_id, "id": body.connection_id, "user": user_id})).mappings().one_or_none()
        if connection is None:
            raise HTTPException(404, "connected account not found for this user")
        if connection["platform"] != platform:
            raise HTTPException(409, "connection platform does not match action platform")
        if (platform, action) in SUPPORTED_PROVIDER_ACTIONS:
            if connection["status"] != "connected":
                raise HTTPException(409, "provider connection is not connected")
            owned = (await s.execute(text("""
                SELECT 1
                FROM social_connections c
                JOIN omnichannel_oauth_tokens t
                  ON t.tenant_id=c.tenant_id AND t.platform=c.platform
                 AND t.provider_account_id=c.platform_account_id
                WHERE c.tenant_id=:tenant AND c.id=:id
                  AND (c.owner_user_id=:user OR c.owner_user_id IS NULL)
                  AND t.user_id=:user AND t.status='connected'
                  AND (t.token_expires_at IS NULL OR t.token_expires_at > NOW()
                       OR (t.encrypted_refresh_token IS NOT NULL
                           AND (t.refresh_token_expires_at IS NULL OR t.refresh_token_expires_at > NOW())))
            """), {
                "tenant": tenant_id, "id": body.connection_id, "user": user_id,
            })).scalar_one_or_none()
            if not owned:
                raise HTTPException(404, "active OAuth account not found for this user")

    # Any action with external side effects requires an explicit approval from an
    # authenticated human. The n8n/service tokens are intentionally not approvers.
    payload = dict(body.payload)
    if action in SIDE_EFFECT_ACTIONS:
        if not settings.omnichannel_executor_enabled:
            raise HTTPException(409, "provider action executor is disabled by the server")
        if not settings.provider_oauth_encryption_ready:
            raise HTTPException(503, "provider token encryption is not configured")
        if not body.approved:
            raise HTTPException(403, "explicit human approval is required for provider actions")
        if user.get("automation") or str(user.get("sub") or "").startswith(("n8n-", "automation-")):
            raise HTTPException(403, "automation identities cannot approve provider actions")
        payload["_requested_by"] = str(user.get("sub") or user.get("user_id") or "")
        payload["approval"] = {
            "approved": True,
            "approved_by": str(user.get("sub") or user.get("user_id") or ""),
            "approved_at": datetime.now(UTC).isoformat(),
        }
        if action == "create_post":
            import hashlib
            payload["approval"]["content_sha256"] = hashlib.sha256(
                str(payload.get("text") or "").encode("utf-8")
            ).hexdigest()

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
        "id": action_id, "tenant": tenant_id, "connection_id": str(body.connection_id) if body.connection_id else "",
        "client": body.client_id, "platform": platform, "action": action,
        "target_type": body.target_type, "target_id": body.target_id,
        "idem": body.idempotency_key or action_id,
        "payload": __import__("json").dumps(payload),
    })).mappings().one()
    await s.commit()
    return {**dict(row), "capability": capability}
