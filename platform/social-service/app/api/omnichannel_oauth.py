from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import quote_plus, urlencode
from uuid import uuid4

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.api.omnichannel import PROVIDER_CONFIG
from app.core.config import settings
from app.core.db import SessionLocal
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
        ("google", "youtube"): ["https://www.googleapis.com/auth/youtube.readonly"],
        ("microsoft", "outlook"): ["https://graph.microsoft.com/Mail.Send"],
        ("linkedin", "linkedin"): ["w_member_social"],
        ("x", "x"): ["tweet.write"],
        # Facebook profile and Instagram Professional identity lookup only.
        ("facebook", "facebook"): [],
        ("instagram", "instagram"): [
            "instagram_basic", "pages_show_list", "pages_read_engagement",
        ],
    }
    for scope in extras.get((provider, platform), []):
        if scope not in base:
            base.append(scope)
    return base


def _parse_scopes(value: object, fallback: list[str]) -> list[str]:
    if isinstance(value, str):
        return [scope for scope in re.split(r"[\s,]+", value.strip()) if scope]
    if isinstance(value, list):
        return [str(scope) for scope in value if str(scope).strip()]
    return list(fallback)


def _oauth_scope_string(provider: str, platform: str) -> str:
    separator = "," if provider == "tiktok" else " "
    return separator.join(_scopes(provider, platform))


def _refresh_form(provider: str, cfg: dict, refresh_token: str, scopes: list[str]) -> dict:
    if provider not in {"google", "microsoft", "linkedin", "x", "tiktok"}:
        raise ValueError("unsupported_refresh_provider")
    form = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_secret": cfg["client_secret"],
    }
    if provider == "tiktok":
        form["client_key"] = cfg["client_id"]
    else:
        form["client_id"] = cfg["client_id"]
    if provider == "microsoft" and scopes:
        form["scope"] = " ".join(scopes)
    return form


async def _exchange(provider: str, code: str, verifier: str) -> dict:
    cfg = PROVIDER_CONFIG[provider]
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.provider_oauth_redirect_uri,
        "client_secret": cfg["client_secret"],
    }
    if provider == "tiktok":
        # TikTok's web flow uses client_key and does not use PKCE.
        form["client_key"] = cfg["client_id"]
    else:
        form["client_id"] = cfg["client_id"]
        form["code_verifier"] = verifier
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            cfg["token_url"],
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    try:
        result = response.json()
    except ValueError:
        result = {}
    if not isinstance(result, dict) or response.status_code >= 400 or result.get("error"):
        raise HTTPException(400, "provider token exchange failed")
    return result


async def _identity(provider: str, access_token: str, platform: str | None = None) -> dict:
    if provider == "google" and platform == "youtube":
        url = "https://www.googleapis.com/youtube/v3/channels"
        params = {"part": "id,snippet", "mine": "true"}
    elif provider == "instagram":
        # Instagram Professional accounts are connected through a Facebook Page.
        url = "https://graph.facebook.com/v24.0/me/accounts"
        params = {"fields": "id,name,instagram_business_account{id,username}"}
    else:
        urls = {
            "google": ("https://openidconnect.googleapis.com/v1/userinfo", {}),
            "microsoft": ("https://graph.microsoft.com/v1.0/me", {}),
            "linkedin": ("https://api.linkedin.com/v2/userinfo", {}),
            "x": ("https://api.x.com/2/users/me", {"user.fields": "name,username,profile_image_url"}),
            "tiktok": ("https://open.tiktokapis.com/v2/user/info/", {"fields": "open_id,union_id,display_name,avatar_url"}),
            "facebook": ("https://graph.facebook.com/v24.0/me", {"fields": "id,name"}),
        }
        url, params = urls[provider]
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code >= 400:
        raise HTTPException(400, "provider identity lookup failed")
    data = response.json()
    if not isinstance(data, dict):
        raise HTTPException(400, "provider identity lookup returned an invalid response")
    if provider == "tiktok":
        return (data.get("data") or {}).get("user") or {}
    if provider == "google" and platform == "youtube":
        channels = data.get("items") or []
        if len(channels) != 1:
            raise HTTPException(409, "Google account must have exactly one YouTube channel; channel selection is required for multiple channels")
        channel = channels[0]
        snippet = channel.get("snippet") or {}
        return {"id": channel.get("id"), "name": snippet.get("title")}
    if provider == "instagram":
        accounts = []
        for page in data.get("data") or []:
            account = page.get("instagram_business_account") or {}
            if account.get("id"):
                accounts.append({**account, "name": page.get("name")})
        if len(accounts) != 1:
            raise HTTPException(409, "Instagram OAuth requires exactly one linked Instagram Professional account; connect or select the intended Facebook Page first")
        return accounts[0]
    return data.get("data", data)


async def refresh_provider_tokens(
    provider: str, refresh_token: str, scopes: list[str]
) -> dict:
    """Refresh a provider grant server-side; never expose tokens to callers/logs."""
    cfg = PROVIDER_CONFIG.get(provider)
    if provider not in {"google", "microsoft", "linkedin", "x", "tiktok"}:
        raise HTTPException(409, "this provider does not support the configured refresh-token flow")
    if not cfg or not cfg.get("client_id") or not cfg.get("client_secret"):
        raise HTTPException(503, "provider refresh credentials are not configured")
    form = _refresh_form(provider, cfg, refresh_token, scopes)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            cfg["token_url"],
            data=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    try:
        result = response.json()
    except ValueError:
        result = {}
    if not isinstance(result, dict) or response.status_code >= 400 or result.get("error"):
        raise HTTPException(409, "provider token refresh failed; reconnect the account")
    access_token = result.get("access_token")
    expires_in = result.get("expires_in")
    if not access_token or not isinstance(expires_in, (int, float)) or expires_in <= 0:
        raise HTTPException(409, "provider returned an invalid refresh response; reconnect the account")
    refreshed_scopes = _parse_scopes(result.get("scope"), scopes)
    refresh_expires_in = result.get("refresh_expires_in")
    refresh_expires_at = None
    if isinstance(refresh_expires_in, (int, float)) and refresh_expires_in > 0:
        refresh_expires_at = datetime.now(UTC) + timedelta(seconds=int(refresh_expires_in))
    return {
        "access_token": str(access_token),
        "refresh_token": str(result.get("refresh_token") or refresh_token),
        "expires_at": datetime.now(UTC) + timedelta(seconds=int(expires_in)),
        "refresh_expires_at": refresh_expires_at,
        "scopes": refreshed_scopes,
    }


def _identity_fields(provider: str, data: dict, platform: str | None = None) -> tuple[str, str | None, str | None]:
    if provider == "google" and platform == "youtube":
        return str(data.get("id") or ""), data.get("customUrl"), data.get("name")
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
    if provider == "instagram":
        return str(data.get("id") or ""), data.get("username"), data.get("name")
    return str(data.get("id") or ""), None, data.get("name")


@router.post("/start/{provider}/{platform}")
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
    if not settings.provider_oauth_state_secret or not settings.provider_oauth_encryption_ready:
        raise HTTPException(503, "secure OAuth state and token encryption must be configured before connecting accounts")
    user = await verify_token(creds.credentials)
    if not str(user.get("sub") or user.get("user_id") or "").strip():
        raise HTTPException(401, "authenticated user identity is missing")
    verifier = None
    challenge = None
    if provider != "tiktok":
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
        "client_key" if provider == "tiktok" else "client_id": cfg["client_id"],
        "redirect_uri": settings.provider_oauth_redirect_uri,
        "response_type": "code",
        "scope": _oauth_scope_string(provider, platform),
        "state": state,
    }
    if challenge:
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"
    if provider == "google":
        params.update({"access_type": "offline", "prompt": "consent"})
    return {"authorization_url": f"{cfg['auth_url']}?{urlencode(params)}"}


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
    if not cfg or platform not in cfg.get("platforms", []) or not cfg.get("client_id"):
        raise HTTPException(400, "provider/platform is not configured")
    tokens = await _exchange(provider, code, payload["verifier"])
    access = tokens.get("access_token")
    if not access:
        raise HTTPException(400, "provider did not return an access token")
    identity = await _identity(provider, access, platform)
    account_id, username, display_name = _identity_fields(provider, identity, platform)
    if not account_id:
        raise HTTPException(400, "provider account identity was not returned")

    expires = tokens.get("expires_in")
    expires_at = None
    if expires:
        expires_at = datetime.now(UTC) + timedelta(seconds=int(expires))
    refresh_expires = tokens.get("refresh_expires_in")
    refresh_expires_at = None
    if refresh_expires:
        refresh_expires_at = datetime.now(UTC) + timedelta(seconds=int(refresh_expires))

    f = _fernet()
    encrypted_access = f.encrypt(access.encode()).decode()
    encrypted_refresh = None
    if tokens.get("refresh_token"):
        encrypted_refresh = f.encrypt(tokens["refresh_token"].encode()).decode()

    async with SessionLocal() as s:
        connection_id = str(uuid4())
        requested_scopes = _scopes(provider, platform)
        scopes = _parse_scopes(tokens.get("scope"), requested_scopes)
        row = (await s.execute(text(
            """INSERT INTO social_connections
               (id, tenant_id, owner_user_id, platform, account_type, platform_account_id, username,
                display_name, status, scopes, access_token_ref, refresh_token_ref,
                token_expires_at, metadata, connected_at)
               VALUES (:id, :tenant, :owner_user, :platform, :account_type, :account_id, :username,
                       :display_name, 'connected', :scopes::jsonb,
                       :access_ref, :refresh_ref, :expires, :metadata::jsonb, NOW())
               ON CONFLICT (tenant_id, platform, platform_account_id)
               DO UPDATE SET username=EXCLUDED.username, display_name=EXCLUDED.display_name,
                             status='connected', scopes=EXCLUDED.scopes,
                             access_token_ref=EXCLUDED.access_token_ref,
                             refresh_token_ref=COALESCE(EXCLUDED.refresh_token_ref, social_connections.refresh_token_ref),
                             token_expires_at=EXCLUDED.token_expires_at,
                             metadata=EXCLUDED.metadata,
                             owner_user_id=COALESCE(social_connections.owner_user_id, EXCLUDED.owner_user_id),
                             updated_at=NOW()
               WHERE social_connections.owner_user_id IS NULL
                  OR social_connections.owner_user_id=EXCLUDED.owner_user_id
               RETURNING id"""
        ), {
            "id": connection_id,
            "tenant": payload["tenant_id"],
            "owner_user": payload["sub"],
            "platform": platform,
            "account_type": "channel" if platform == "youtube" else ("business" if platform == "instagram" else "user"),
            "account_id": account_id,
            "username": username,
            "display_name": display_name,
            "scopes": json.dumps(scopes),
            "access_ref": "oauth:omnichannel_oauth_tokens",
            "refresh_ref": "oauth:omnichannel_oauth_tokens" if encrypted_refresh else None,
            "expires": expires_at,
            "metadata": json.dumps({"provider": provider, "email": identity.get("email")}),
        })).scalar_one_or_none()
        if row is None:
            raise HTTPException(409, "this provider account is already connected to another Shopnoltd user")
        connection_id = str(row)

        token_row = (await s.execute(text(
            """INSERT INTO omnichannel_oauth_tokens
               (id, tenant_id, user_id, provider, platform, provider_account_id,
                username, display_name, scopes, encrypted_access_token,
                encrypted_refresh_token, token_expires_at, refresh_token_expires_at, metadata)
               VALUES (:id, :tenant, :user, :provider, :platform, :account_id,
                       :username, :display_name, :scopes::jsonb, :access,
                       :refresh, :expires, :refresh_expires, :metadata::jsonb)
               ON CONFLICT (tenant_id, provider, platform, provider_account_id)
               DO UPDATE SET username=EXCLUDED.username,
                             display_name=EXCLUDED.display_name, scopes=EXCLUDED.scopes,
                             encrypted_access_token=EXCLUDED.encrypted_access_token,
                             encrypted_refresh_token=COALESCE(EXCLUDED.encrypted_refresh_token, omnichannel_oauth_tokens.encrypted_refresh_token),
                             token_expires_at=EXCLUDED.token_expires_at, refresh_token_expires_at=COALESCE(EXCLUDED.refresh_token_expires_at, omnichannel_oauth_tokens.refresh_token_expires_at), metadata=EXCLUDED.metadata,
                             status='connected', updated_at=NOW()
               WHERE omnichannel_oauth_tokens.user_id=EXCLUDED.user_id
               RETURNING id"""
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
            "refresh_expires": refresh_expires_at,
            "metadata": json.dumps({"provider_identity": identity}),
        })).scalar_one_or_none()
        if token_row is None:
            raise HTTPException(409, "this provider account is already authorized by another Shopnoltd user")
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
