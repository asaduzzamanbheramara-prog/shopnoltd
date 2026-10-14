from __future__ import annotations

import base64
import hashlib
import json
import secrets
from uuid import uuid4
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote_plus

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.api.omnichannel import PROVIDER_CONFIG
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()


def _key() -> bytes:
    raw = settings.provider_oauth_encryption_key
    if not raw:
        raise HTTPException(503, "provider OAuth encryption is not configured")
    try:
        Fernet(raw.encode())
    except Exception as exc:
        raise HTTPException(503, "provider OAuth encryption key is invalid") from exc
    return raw.encode()


def _fernet() -> Fernet:
    return Fernet(_key())


def _state_fernet() -> Fernet:
    secret = settings.provider_oauth_state_secret
    if not secret:
        raise HTTPException(503, "provider OAuth state signing is not configured")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def _sign_state(payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":")).encode()
    return _state_fernet().encrypt(body).decode()


def _verify_state(value: str) -> dict:
    try:
        payload = json.loads(_state_fernet().decrypt(value.encode()))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return payload
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(400, "invalid or expired OAuth state") from exc


def _scopes(provider: str, platform: str) -> list[str]:
    base = list(PROVIDER_CONFIG[provider].get("scopes", []))
    extras = {
        ("google", "gmail"): ["https://www.googleapis.com/auth/gmail.send"],
        ("google", "youtube"): ["https://www.googleapis.com/auth/youtube"],
        ("microsoft", "outlook"): ["https://graph.microsoft.com/Mail.Send"],
        ("linkedin", "linkedin"): ["w_member_social"],
        ("x", "x"): ["tweet.write"],
        ("tiktok", "tiktok"): ["video.publish"],
        ("facebook", "facebook"): [
            "pages_show_list", "pages_read_engagement", "pages_manage_posts",
            "pages_messaging", "business_management",
        ],
        ("instagram", "instagram"): [
            "instagram_basic", "instagram_content_publish", "instagram_manage_messages",
            "pages_show_list", "pages_read_engagement",
        ],
    }
    for scope in extras.get((provider, platform), []):
        if scope not in base:
            base.append(scope)
    return base


async def _exchange(provider: str, code: str, verifier: str) -> dict:
    cfg = PROVIDER_CONFIG[provider]
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            cfg["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.provider_oauth_redirect_uri,
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code_verifier": verifier,
            },
        )
    if response.status_code >= 400:
        raise HTTPException(400, "provider token exchange failed")
    return response.json()


async def _identity(provider: str, access_token: str) -> dict:
    urls = {
        "google": ("https://openidconnect.googleapis.com/v1/userinfo", {}),
        "microsoft": ("https://graph.microsoft.com/v1.0/me", {}),
        "linkedin": ("https://api.linkedin.com/v2/userinfo", {}),
        "x": ("https://api.x.com/2/users/me", {"user.fields": "name,username,profile_image_url"}),
        "tiktok": ("https://open.tiktokapis.com/v2/user/info/", {"fields": "open_id,union_id,display_name,avatar_url"}),
        "facebook": ("https://graph.facebook.com/v24.0/me", {"fields": "id,name"}),
        "instagram": ("https://graph.facebook.com/v24.0/me", {"fields": "id,name"}),
    }
    url, params = urls[provider]
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code >= 400:
        raise HTTPException(400, "provider identity lookup failed")
    data = response.json()
    return data.get("data", data)


def _identity_fields(provider: str, data: dict) -> tuple[str, str | None, str | None]:
    if provider == "google":
        return str(data.get("sub") or ""), data.get("email"), data.get("name")
    if provider == "microsoft":
        return str(data.get("id") or ""), data.get("userPrincipalName") or data.get("mail"), data.get("displayName")
    if provider == "linkedin":
        return str(data.get("sub") or ""), data.get("email"), data.get("name")
    if provider == "x":
        return str(data.get("id") or ""), data.get("username"), data.get("name")
    if provider == "tiktok":
        return str(data.get("open_id") or data.get("union_id") or ""), None, data.get("display_name")
    return str(data.get("id") or ""), None, data.get("name")


@router.get("/start/{provider}/{platform}")
async def start(provider: str, platform: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    provider = provider.lower().strip()
    platform = platform.lower().strip()
    cfg = PROVIDER_CONFIG.get(provider)
    if not cfg or platform not in cfg["platforms"]:
        raise HTTPException(404, "unsupported provider/platform")
    if not (cfg.get("auth_url") and cfg.get("token_url")):
        raise HTTPException(409, "this platform requires provider-specific onboarding")
    if not cfg.get("client_id") or not cfg.get("client_secret"):
        raise HTTPException(409, "provider credentials are not configured")
    user = await verify_token(creds.credentials)
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = _sign_state({
        "sub": str(user.get("sub") or user.get("user_id") or ""),
        "tenant_id": str(user.get("tenant_id") or "default"),
        "provider": provider,
        "platform": platform,
        "verifier": verifier,
        "nonce": secrets.token_urlsafe(18),
        "exp": int(time.time()) + 600,
    })
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": settings.provider_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(_scopes(provider, platform)),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return RedirectResponse(f"{cfg['auth_url']}?{urlencode(params)}", status_code=302)


@router.get("/callback")
async def callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return RedirectResponse(f"{settings.provider_oauth_success_redirect_uri}?oauth=error&reason={quote_plus(error)}", status_code=303)
    if not code or not state:
        raise HTTPException(400, "OAuth code and state are required")
    payload = _verify_state(state)
    provider = payload["provider"]
    platform = payload["platform"]
    cfg = PROVIDER_CONFIG.get(provider)
    if not cfg or not cfg.get("client_id"):
        raise HTTPException(400, "provider is not configured")
    tokens = await _exchange(provider, code, payload["verifier"])
    access = tokens.get("access_token")
    if not access:
        raise HTTPException(400, "provider did not return an access token")
    identity = await _identity(provider, access)
    account_id, username, display_name = _identity_fields(provider, identity)
    if not account_id:
        raise HTTPException(400, "provider account identity was not returned")

    expires = tokens.get("expires_in")
    expires_at = None
    if expires:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires))

    f = _fernet()
    encrypted_access = f.encrypt(access.encode()).decode()
    encrypted_refresh = None
    if tokens.get("refresh_token"):
        encrypted_refresh = f.encrypt(tokens["refresh_token"].encode()).decode()

    async with SessionLocal() as s:
        connection_id = str(uuid4())
        scopes = _scopes(provider, platform)
        row = (await s.execute(text(
            """INSERT INTO social_connections
               (id, tenant_id, platform, account_type, platform_account_id, username,
                display_name, status, scopes, access_token_ref, refresh_token_ref,
                token_expires_at, metadata, connected_at)
               VALUES (:id, :tenant, :platform, 'user', :account_id, :username,
                       :display_name, 'connected', CAST(:scopes AS jsonb),
                       :access_ref, :refresh_ref, :expires, CAST(:metadata AS jsonb), NOW())
               ON CONFLICT (tenant_id, platform, platform_account_id)
               DO UPDATE SET username=EXCLUDED.username, display_name=EXCLUDED.display_name,
                             status='connected', scopes=EXCLUDED.scopes,
                             access_token_ref=EXCLUDED.access_token_ref,
                             refresh_token_ref=EXCLUDED.refresh_token_ref,
                             token_expires_at=EXCLUDED.token_expires_at,
                             metadata=EXCLUDED.metadata, updated_at=NOW()
               RETURNING id"""
        ), {
            "id": connection_id,
            "tenant": payload["tenant_id"],
            "platform": platform,
            "account_id": account_id,
            "username": username,
            "display_name": display_name,
            "scopes": json.dumps(scopes),
            "access_ref": "oauth:omnichannel_oauth_tokens",
            "refresh_ref": "oauth:omnichannel_oauth_tokens" if encrypted_refresh else None,
            "expires": expires_at,
            "metadata": json.dumps({"provider": provider, "email": identity.get("email")}),
        })).scalar_one()

        await s.execute(text(
            """INSERT INTO omnichannel_oauth_tokens
               (id, tenant_id, user_id, provider, platform, provider_account_id,
                username, display_name, scopes, encrypted_access_token,
                encrypted_refresh_token, token_expires_at, metadata)
               VALUES (:id, :tenant, :user, :provider, :platform, :account_id,
                       :username, :display_name, CAST(:scopes AS jsonb), :access,
                       :refresh, :expires, CAST(:metadata AS jsonb))
               ON CONFLICT (tenant_id, provider, platform, provider_account_id)
               DO UPDATE SET user_id=EXCLUDED.user_id, username=EXCLUDED.username,
                             display_name=EXCLUDED.display_name, scopes=EXCLUDED.scopes,
                             encrypted_access_token=EXCLUDED.encrypted_access_token,
                             encrypted_refresh_token=COALESCE(EXCLUDED.encrypted_refresh_token, omnichannel_oauth_tokens.encrypted_refresh_token),
                             token_expires_at=EXCLUDED.token_expires_at, metadata=EXCLUDED.metadata,
                             status='connected', updated_at=NOW()"""
        ), {
            "id": str(uuid4()),
            "tenant": payload["tenant_id"],
            "user": payload["sub"],
            "provider": provider,
            "platform": platform,
            "account_id": account_id,
            "username": username,
            "display_name": display_name,
            "scopes": json.dumps(scopes),
            "access": encrypted_access,
            "refresh": encrypted_refresh,
            "expires": expires_at,
            "metadata": json.dumps({"provider_identity": identity}),
        })
        await s.commit()

    return RedirectResponse(
        f"{settings.provider_oauth_success_redirect_uri}?oauth=success&provider={provider}&connection_id={connection_id}",
        status_code=303,
    )


@router.get("/status")
async def oauth_status(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    user = await verify_token(creds.credentials)
    tenant = user.get("tenant_id", "default")
    async with SessionLocal() as s:
        rows = (await s.execute(text(
            """SELECT provider, platform, provider_account_id, username, display_name,
                      status, token_expires_at, scopes, created_at, updated_at
               FROM omnichannel_oauth_tokens
               WHERE tenant_id=:tenant AND user_id=:user
               ORDER BY provider, platform, display_name"""
        ), {"tenant": tenant, "user": str(user.get("sub") or user.get("user_id") or "")})).mappings().all()
    return [dict(row) for row in rows]


class TelegramBotConnectIn(BaseModel):
    # Validate length in the handler so request-validation errors never echo the submitted secret.
    bot_token: str


@router.post("/telegram/connect", status_code=201)
async def connect_telegram_bot(
    body: TelegramBotConnectIn,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    """Validate and store a tenant-owned Telegram bot token encrypted at rest."""
    user = await verify_token(creds.credentials)
    tenant_id = str(user.get("tenant_id") or "default")
    user_id = str(user.get("sub") or user.get("user_id") or "")
    if not user_id:
        raise HTTPException(401, "authenticated user identity is missing")
    if not 30 <= len(body.bot_token) <= 512:
        raise HTTPException(400, "invalid Telegram bot credential")

    # Validate the credential with Telegram without logging or returning it.
    try:
        cipher = _fernet()
    except HTTPException:
        raise
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{body.bot_token}/getMe"
            )
    except (httpx.TimeoutException, httpx.NetworkError):
        # Do not chain the HTTP client exception: its request URL contains the bot token.
        raise HTTPException(502, "Telegram credential validation could not be completed")
    if response.status_code != 200:
        raise HTTPException(400, "Telegram rejected the bot credential")
    try:
        provider_result = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "Telegram returned an invalid credential response") from exc
    bot = provider_result.get("result") or {}
    if provider_result.get("ok") is not True or not bot.get("id") or bot.get("is_bot") is not True:
        raise HTTPException(400, "Telegram credential did not identify a bot account")

    account_id = str(bot["id"])
    username = str(bot.get("username") or "")
    display_name = str(bot.get("first_name") or username or f"Telegram bot {account_id}")
    encrypted_token = cipher.encrypt(body.bot_token.encode()).decode()
    async with SessionLocal() as s:
        token_id = (await s.execute(text(
            """INSERT INTO omnichannel_oauth_tokens
               (id, tenant_id, user_id, provider, platform, provider_account_id,
                username, display_name, scopes, encrypted_access_token, metadata, status)
               VALUES (:id, :tenant, :user, 'telegram', 'telegram', :account_id,
                       :username, :display_name, '[]'::jsonb, :encrypted,
                       CAST(:metadata AS jsonb), 'connected')
               ON CONFLICT (tenant_id, provider, platform, provider_account_id)
               DO UPDATE SET user_id=EXCLUDED.user_id, username=EXCLUDED.username,
                             display_name=EXCLUDED.display_name,
                             encrypted_access_token=EXCLUDED.encrypted_access_token,
                             metadata=EXCLUDED.metadata, status='connected', updated_at=NOW()
               RETURNING id"""
        ), {
            "id": str(uuid4()), "tenant": tenant_id, "user": user_id,
            "account_id": account_id, "username": username,
            "display_name": display_name, "encrypted": encrypted_token,
            "metadata": json.dumps({"account_type": "telegram_bot"}),
        })).scalar_one()
        row = (await s.execute(text(
            """INSERT INTO social_connections
               (tenant_id, platform, account_type, platform_account_id, username,
                display_name, status, scopes, access_token_ref, metadata, connected_at)
               VALUES (:tenant, 'telegram', 'bot', :account_id, :username,
                       :display_name, 'connected', '[]'::jsonb, :token_ref,
                       CAST(:metadata AS jsonb), NOW())
               ON CONFLICT (tenant_id, platform, platform_account_id)
               DO UPDATE SET account_type='bot', username=EXCLUDED.username,
                             display_name=EXCLUDED.display_name, status='connected',
                             scopes='[]'::jsonb, access_token_ref=EXCLUDED.access_token_ref,
                             metadata=EXCLUDED.metadata, connected_at=NOW(), updated_at=NOW()
               RETURNING id, platform, account_type, platform_account_id, username,
                         display_name, status, scopes, token_expires_at, metadata,
                         connected_at, last_sync_at"""
        ), {
            "tenant": tenant_id, "account_id": account_id, "username": username,
            "display_name": display_name, "token_ref": str(token_id),
            "metadata": json.dumps({"provider": "telegram", "account_type": "bot"}),
        })).mappings().one()
        await s.commit()
    return dict(row)
