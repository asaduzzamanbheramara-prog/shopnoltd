from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from uuid import UUID, uuid4
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote_plus

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
        ("google", "youtube"): ["https://www.googleapis.com/auth/youtube.readonly"],
        ("microsoft", "outlook"): ["https://graph.microsoft.com/Mail.Send"],
        ("linkedin", "linkedin"): ["w_member_social"],
        ("x", "x"): ["tweet.write"],
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
        if provider == "tiktok":
            # TikTok's v2 token API wraps credentials in a data object.
            # Web Login Kit does not use PKCE; the confidential client is authenticated by client_key/secret.
            response = await client.post(
                cfg["token_url"],
                data={
                    "client_key": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.provider_oauth_redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        elif provider == "github":
            # GitHub returns JSON only when the client explicitly requests it.
            response = await client.post(
                cfg["token_url"],
                data={
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "code": code,
                    "redirect_uri": settings.provider_oauth_redirect_uri,
                    "code_verifier": verifier,
                },
                headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            )
        elif provider == "x":
            # X Web App is a confidential client: authenticate with HTTP Basic.
            response = await client.post(
                cfg["token_url"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.provider_oauth_redirect_uri,
                    "code_verifier": verifier,
                },
                auth=(cfg["client_id"], cfg["client_secret"]),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        elif provider in {"facebook", "instagram"}:
            # Meta's manual code exchange uses the documented GET parameters;
            # state protects the web flow (Meta's manual flow does not use PKCE).
            response = await client.get(
                cfg["token_url"],
                params={
                    "code": code,
                    "redirect_uri": settings.provider_oauth_redirect_uri,
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                },
            )
        else:
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
    data = response.json()
    if provider == "tiktok":
        token_data = data.get("data") or {}
        # TikTok v2 reports token errors inside data.error_code.
        error_code = token_data.get("error_code")
        if (data.get("error") and data.get("error") != "ok") or error_code not in (None, 0, "0"):
            raise HTTPException(400, "TikTok token exchange was rejected")
        return token_data
    return data


def _meta_token_exchange_request(provider: str, short_lived: str) -> tuple[str, dict]:
    cfg = PROVIDER_CONFIG.get(provider) or {}
    if not cfg.get("client_id") or not cfg.get("client_secret") or not cfg.get("token_url"):
        raise HTTPException(503, "Meta provider credentials are not configured")
    if not short_lived:
        raise HTTPException(400, "Meta did not return an access token")
    return cfg["token_url"], {
        "grant_type": "fb_exchange_token",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "fb_exchange_token": short_lived,
    }


async def _exchange_meta_long_lived_token(tokens: dict, provider: str) -> dict:
    token_url, params = _meta_token_exchange_request(provider, tokens.get("access_token"))
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(token_url, params=params)
    if response.status_code >= 400:
        raise HTTPException(400, "Meta long-lived token exchange failed")
    result = response.json()
    if not result.get("access_token"):
        raise HTTPException(400, "Meta did not return a long-lived access token")
    return result


def _account_choice(candidates: list[dict], empty_message: str) -> dict:
    # Provider APIs can return repeated or incomplete entries; never present
    # duplicate IDs or allow a blank ID to reach the persistence layer.
    unique = {}
    for candidate in candidates:
        account_id = str(candidate.get("id") or "").strip()
        if account_id and account_id not in unique:
            unique[account_id] = candidate
    candidates = list(unique.values())
    if not candidates:
        raise HTTPException(409, empty_message)
    if len(candidates) > 1:
        return {"_choices": candidates}
    return candidates[0]


async def _identity(provider: str, access_token: str, platform: str) -> dict:
    urls = {
        "google": ("https://openidconnect.googleapis.com/v1/userinfo", {}),
        "microsoft": ("https://graph.microsoft.com/v1.0/me", {}),
        "linkedin": ("https://api.linkedin.com/v2/userinfo", {}),
        "github": ("https://api.github.com/user", {}),
        "x": ("https://api.x.com/2/users/me", {"user.fields": "name,username,profile_image_url"}),
        "tiktok": ("https://open.tiktokapis.com/v2/user/info/", {"fields": "open_id,union_id,display_name,avatar_url"}),
        "facebook": ("https://graph.facebook.com/v24.0/me", {"fields": "id,name"}),
        "instagram": ("https://graph.facebook.com/v24.0/me", {"fields": "id,name"}),
    }
    if provider == "google" and platform == "youtube":
        # A YouTube connection must identify a channel, not merely the Google login.
        channels = []
        params = {"part": "id,snippet", "mine": "true", "maxResults": 50}
        async with httpx.AsyncClient(timeout=20) as client:
            for _ in range(10):
                response = await client.get(
                    "https://youtube.googleapis.com/youtube/v3/channels",
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code >= 400:
                    raise HTTPException(400, "YouTube channel discovery failed; verify YouTube Data API access and granted scope")
                page = response.json()
                channels.extend(page.get("items") or [])
                next_page = page.get("nextPageToken")
                if not next_page:
                    break
                params["pageToken"] = next_page
        candidates = [
            {
                "id": str(channel.get("id") or ""),
                "name": (channel.get("snippet") or {}).get("title"),
                "username": (channel.get("snippet") or {}).get("customUrl"),
            }
            for channel in channels if channel.get("id")
        ]
        return _account_choice(candidates, "no YouTube channel was found for this Google account")

    if provider in {"facebook", "instagram"}:
        # Platform connections must represent managed Pages / linked IG professional
        # accounts, not the operator's personal Facebook user profile.
        fields = "id,name,access_token"
        if platform == "instagram":
            fields += ",instagram_business_account{id,username}"
        pages = []
        params = {"fields": fields, "limit": 100}
        async with httpx.AsyncClient(timeout=20) as client:
            # /me/accounts is cursor-paginated; include every manageable Page.
            for _ in range(10):
                response = await client.get(
                    "https://graph.facebook.com/v24.0/me/accounts",
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if response.status_code >= 400:
                    raise HTTPException(400, "Meta Page discovery failed; verify pages_show_list and Page access")
                page = response.json()
                pages.extend(page.get("data") or [])
                after = ((page.get("paging") or {}).get("cursors") or {}).get("after")
                if not after:
                    break
                params["after"] = after
        async with httpx.AsyncClient(timeout=20) as permission_client:
            permission_response = await permission_client.get(
                "https://graph.facebook.com/v24.0/me/permissions",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if permission_response.status_code >= 400:
            raise HTTPException(400, "Meta permission verification failed")
        granted_scopes = [
            str(item.get("permission"))
            for item in (permission_response.json().get("data") or [])
            if item.get("status") == "granted" and item.get("permission")
        ]
        candidates = []
        for page in pages:
            if platform == "instagram":
                ig = page.get("instagram_business_account")
                if ig and ig.get("id") and page.get("access_token"):
                    candidates.append({
                        "id": str(ig.get("id") or ""),
                        "username": ig.get("username"),
                        "name": ig.get("username") or page.get("name"),
                        "_access_token": page["access_token"],
                        "_granted_scopes": granted_scopes,
                        "page_id": str(page.get("id") or ""),
                    })
            elif page.get("id") and page.get("access_token"):
                candidates.append({
                    "id": str(page["id"]),
                    "name": page.get("name"),
                    "_access_token": page["access_token"],
                    "_granted_scopes": granted_scopes,
                })
        return _account_choice(candidates, "no eligible Facebook Page or linked Instagram professional account was found")

    url, params = urls[provider]
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code >= 400:
        raise HTTPException(400, "provider identity lookup failed")
    data = response.json()
    if provider == "tiktok":
        return (data.get("data") or {}).get("user") or {}
    return data.get("data", data)


def _selected_account_ids(body: dict) -> list[str]:
    raw_ids = body.get("account_ids")
    if raw_ids is None:
        raw_ids = [body.get("account_id")]
    if not isinstance(raw_ids, list):
        raise HTTPException(422, "account_ids must be a list")
    selected_ids = list(dict.fromkeys(
        str(value or "").strip() for value in raw_ids if str(value or "").strip()
    ))
    if not selected_ids:
        raise HTTPException(422, "select at least one account")
    if len(selected_ids) > 100:
        raise HTTPException(422, "at most 100 accounts may be connected at once")
    return selected_ids


def _parse_scopes(returned: str | list | None, fallback: list[str]) -> list[str]:
    if isinstance(returned, str):
        return [scope for scope in re.split(r"[,\s]+", returned.strip()) if scope]
    if isinstance(returned, list):
        return [str(scope) for scope in returned if str(scope).strip()]
    return list(fallback)


def _identity_fields(provider: str, data: dict, platform: str | None = None) -> tuple[str, str | None, str | None]:
    if provider == "google" and platform == "youtube":
        return str(data.get("id") or ""), data.get("username"), data.get("name")
    if provider == "google":
        return str(data.get("sub") or ""), data.get("email"), data.get("name")
    if provider == "microsoft":
        return str(data.get("id") or ""), data.get("userPrincipalName") or data.get("mail"), data.get("displayName")
    if provider == "linkedin":
        return str(data.get("sub") or ""), data.get("email"), data.get("name")
    if provider == "github":
        return str(data.get("id") or ""), data.get("login"), data.get("name") or data.get("login")
    if provider == "x":
        return str(data.get("id") or ""), data.get("username"), data.get("name")
    if provider == "tiktok":
        return str(data.get("open_id") or data.get("union_id") or ""), None, data.get("display_name")
    if provider == "instagram":
        return str(data.get("id") or ""), data.get("username"), data.get("name") or data.get("username")
    return str(data.get("id") or ""), None, data.get("name")


def _authorization_url(provider: str, platform: str, user: dict) -> str:
    provider = provider.lower().strip()
    platform = platform.lower().strip()
    cfg = PROVIDER_CONFIG.get(provider)
    if not cfg or platform not in cfg["platforms"]:
        raise HTTPException(404, "unsupported provider/platform")
    if not (cfg.get("auth_url") and cfg.get("token_url")):
        raise HTTPException(409, "this platform requires provider-specific onboarding")
    if not cfg.get("client_id") or not cfg.get("client_secret"):
        raise HTTPException(409, "provider credentials are not configured")
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = _sign_state({
        "sub": str(user.get("sub") or user.get("user_id") or ""),
        "tenant_id": str(user.get("tenant_id") or "default"),
        "provider": provider, "platform": platform, "verifier": verifier,
        "nonce": secrets.token_urlsafe(18), "exp": int(time.time()) + 600,
    })
    params = {
        "redirect_uri": settings.provider_oauth_redirect_uri,
        "response_type": "code",
        "scope": ("," if provider in {"facebook", "instagram", "tiktok"} else " ").join(_scopes(provider, platform)),
        "state": state,
    }
    if provider == "tiktok":
        params["client_key"] = cfg["client_id"]
    else:
        params["client_id"] = cfg["client_id"]
        if provider not in {"facebook", "instagram"}:
            params["code_challenge"] = challenge
            params["code_challenge_method"] = "S256"
    if provider == "google":
        params["access_type"] = "offline"
        # Reconnecting allows choosing a different Google identity.
        params["prompt"] = "consent select_account"
    elif provider == "microsoft":
        # Microsoft documents select_account for multi-account sign-in.
        params["prompt"] = "select_account"
    return f"{cfg['auth_url']}?{urlencode(params)}"


@router.get("/authorize-url/{provider}/{platform}")
async def authorize_url(provider: str, platform: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    """Return a short-lived provider URL to an authenticated browser client."""
    user = await verify_token(creds.credentials)
    return {"authorization_url": _authorization_url(provider, platform, user)}


@router.get("/start/{provider}/{platform}")
async def start(provider: str, platform: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    user = await verify_token(creds.credentials)
    return RedirectResponse(_authorization_url(provider, platform, user), status_code=302)


async def _save_selected_connection(payload: dict, provider: str, platform: str, identity: dict, tokens: dict, session=None) -> str:
    if session is None:
        async with SessionLocal() as own_session:
            connection_id = await _save_selected_connection(payload, provider, platform, identity, tokens, own_session)
            await own_session.commit()
            return connection_id
    identity = dict(identity)
    identity_access_token = identity.pop("_access_token", tokens["access_token"])
    granted_scopes = identity.pop("_granted_scopes", None)
    account_id, username, display_name = _identity_fields(provider, identity, platform)
    if not account_id:
        raise HTTPException(400, "provider account identity was not returned")
    expires = tokens.get("expires_in")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires)) if expires else None
    f = _fernet()
    encrypted_access = f.encrypt(identity_access_token.encode()).decode()
    encrypted_refresh = f.encrypt(tokens["refresh_token"].encode()).decode() if tokens.get("refresh_token") else None
    s = session
    # Serialize connections for the same tenant/platform/account and reject
    # cross-user or cross-provider takeover before either upsert can overwrite
    # an existing account's credentials.
    lock_key = f"{payload['tenant_id']}:{platform}:{account_id}"
    await s.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"), {"lock_key": lock_key})
    token_owner = (await s.execute(text(
        """SELECT user_id FROM omnichannel_oauth_tokens
           WHERE tenant_id=:tenant AND provider=:provider AND platform=:platform
             AND provider_account_id=:account_id
           FOR UPDATE"""
    ), {
        "tenant": payload["tenant_id"], "provider": provider,
        "platform": platform, "account_id": account_id,
    })).scalar_one_or_none()
    if token_owner and token_owner != str(payload["sub"]):
        raise HTTPException(409, "this provider account is already connected by another owner")
    existing = (await s.execute(text(
        """SELECT c.metadata->>'provider' AS existing_provider, c.owner_user_id, t.user_id
           FROM social_connections c
           LEFT JOIN omnichannel_oauth_tokens t
             ON t.tenant_id=c.tenant_id AND t.platform=c.platform
            AND t.provider_account_id=c.platform_account_id AND t.provider=:provider
           WHERE c.tenant_id=:tenant AND c.platform=:platform
             AND c.platform_account_id=:account_id
           FOR UPDATE OF c"""
    ), {
        "tenant": payload["tenant_id"], "platform": platform,
        "account_id": account_id, "provider": provider,
    })).mappings().first()
    if existing:
        existing_provider = existing.get("existing_provider")
        existing_user = existing.get("owner_user_id") or existing.get("user_id")
        if existing_provider != provider or existing_user != str(payload["sub"]):
            raise HTTPException(409, "this platform account is already connected by another owner or provider")
    proposed_connection_id = str(uuid4())
    requested_scopes = _scopes(provider, platform)
    scopes = _parse_scopes(
        tokens.get("scope"),
        granted_scopes if granted_scopes is not None else requested_scopes,
    )
    row = (await s.execute(text(
        """INSERT INTO social_connections
           (id, tenant_id, owner_user_id, platform, account_type, platform_account_id, username,
            display_name, status, scopes, access_token_ref, refresh_token_ref,
            token_expires_at, metadata, connected_at)
           VALUES (:id, :tenant, :user, :platform, :account_type, :account_id, :username,
                   :display_name, 'connected', :scopes::jsonb,
                   :access_ref, :refresh_ref, :expires, :metadata::jsonb, NOW())
           ON CONFLICT (tenant_id, platform, platform_account_id)
           DO UPDATE SET username=EXCLUDED.username, display_name=EXCLUDED.display_name,
                         status='connected', scopes=EXCLUDED.scopes,
                         access_token_ref=EXCLUDED.access_token_ref,
                         refresh_token_ref=EXCLUDED.refresh_token_ref,
                         token_expires_at=EXCLUDED.token_expires_at,
                         metadata=EXCLUDED.metadata, updated_at=NOW()
           WHERE social_connections.owner_user_id=EXCLUDED.owner_user_id
           RETURNING id"""
    ), {
        "id": proposed_connection_id,
        "tenant": payload["tenant_id"],
        "user": payload["sub"],
        "platform": platform,
        "account_type": (
            "page" if platform == "facebook" else
            "business" if platform == "instagram" else
            "channel" if platform == "youtube" else "user"
        ),
        "account_id": account_id,
        "username": username,
        "display_name": display_name,
        "scopes": json.dumps(scopes),
        "access_ref": "oauth:omnichannel_oauth_tokens",
        "refresh_ref": "oauth:omnichannel_oauth_tokens" if encrypted_refresh else None,
        "expires": expires_at,
        "metadata": json.dumps({k: v for k, v in identity.items() if k not in {"email"}} | {"provider": provider, "email": identity.get("email")}),
    })).scalar_one()
    connection_id = str(row)

    await s.execute(text(
        """INSERT INTO omnichannel_oauth_tokens
           (id, tenant_id, user_id, provider, platform, provider_account_id,
            username, display_name, scopes, encrypted_access_token,
            encrypted_refresh_token, token_expires_at, metadata)
           VALUES (:id, :tenant, :user, :provider, :platform, :account_id,
                   :username, :display_name, :scopes::jsonb, :access,
                   :refresh, :expires, :metadata::jsonb)
           ON CONFLICT (tenant_id, provider, platform, provider_account_id)
           DO UPDATE SET username=EXCLUDED.username,
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
    return connection_id


@router.get("/callback")
async def callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        if not state:
            raise HTTPException(400, "OAuth state is required for provider errors")
        _verify_state(state)
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
    if provider in {"facebook", "instagram"}:
        tokens = await _exchange_meta_long_lived_token(tokens, provider)
    access = tokens.get("access_token")
    if not access:
        raise HTTPException(400, "provider did not return an access token")
    try:
        identity = await _identity(provider, access, platform)
    except HTTPException as exc:
        if exc.status_code == 409:
            detail = str(exc.detail).lower()
            reason = "multiple_accounts" if "multiple" in detail else "no_eligible_account"
            return RedirectResponse(
                f"{settings.provider_oauth_success_redirect_uri}?oauth=error&provider={quote_plus(provider)}&reason={reason}",
                status_code=303,
            )
        raise
    choices = identity.pop("_choices", None)
    if choices:
        pending_id = str(uuid4())
        pending_payload = _fernet().encrypt(json.dumps({"tokens": tokens, "choices": choices}).encode()).decode()
        async with SessionLocal() as s:
            await s.execute(text("DELETE FROM omnichannel_oauth_pending WHERE expires_at <= NOW()"))
            await s.execute(text(
                """INSERT INTO omnichannel_oauth_pending
                   (id, tenant_id, user_id, provider, platform, encrypted_payload, expires_at)
                   VALUES (:id, :tenant, :user, :provider, :platform, :payload, NOW() + INTERVAL '10 minutes')"""
            ), {
                "id": pending_id, "tenant": payload["tenant_id"], "user": payload["sub"],
                "provider": provider, "platform": platform, "payload": pending_payload,
            })
            await s.commit()
        return RedirectResponse(
            f"{settings.provider_oauth_success_redirect_uri}?oauth=pending&provider={quote_plus(provider)}&pending_id={pending_id}",
            status_code=303,
        )

    connection_id = await _save_selected_connection(payload, provider, platform, identity, tokens)

    return RedirectResponse(
        f"{settings.provider_oauth_success_redirect_uri}?oauth=success&provider={provider}&connection_id={connection_id}",
        status_code=303,
    )


@router.get("/pending/{pending_id}")
async def pending_accounts(pending_id: UUID, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    user = await verify_token(creds.credentials)
    tenant = str(user.get("tenant_id") or "default")
    user_id = str(user.get("sub") or user.get("user_id") or "")
    async with SessionLocal() as s:
        row = (await s.execute(text(
            """SELECT provider, platform, encrypted_payload
               FROM omnichannel_oauth_pending
               WHERE id=:id AND tenant_id=:tenant AND user_id=:user AND expires_at > NOW()"""
        ), {"id": pending_id, "tenant": tenant, "user": user_id})).mappings().first()
    if not row:
        raise HTTPException(404, "account selection expired or not found")
    try:
        data = json.loads(_fernet().decrypt(row["encrypted_payload"].encode()))
    except (InvalidToken, ValueError, TypeError) as exc:
        raise HTTPException(410, "account selection is no longer available") from exc
    choices = []
    for item in data.get("choices") or []:
        choices.append({
            "id": str(item.get("id") or ""),
            "name": item.get("name") or item.get("username") or str(item.get("id") or ""),
            "username": item.get("username"),
        })
    return {"provider": row["provider"], "platform": row["platform"], "choices": choices}


@router.post("/pending/{pending_id}/select")
async def select_pending_account(
    pending_id: UUID,
    body: dict = Body(...),
    creds: HTTPAuthorizationCredentials = Depends(bearer),
):
    user = await verify_token(creds.credentials)
    tenant = str(user.get("tenant_id") or "default")
    user_id = str(user.get("sub") or user.get("user_id") or "")
    selected_ids = _selected_account_ids(body)
    async with SessionLocal() as s:
        row = (await s.execute(text(
            """SELECT provider, platform, encrypted_payload
               FROM omnichannel_oauth_pending
               WHERE id=:id AND tenant_id=:tenant AND user_id=:user AND expires_at > NOW()
               FOR UPDATE"""
        ), {"id": pending_id, "tenant": tenant, "user": user_id})).mappings().first()
        if not row:
            raise HTTPException(404, "account selection expired or not found")
        try:
            data = json.loads(_fernet().decrypt(row["encrypted_payload"].encode()))
        except (InvalidToken, ValueError, TypeError) as exc:
            raise HTTPException(410, "account selection is no longer available") from exc
        available = {str(item.get("id") or ""): item for item in data.get("choices", []) if item.get("id")}
        unknown = [account_id for account_id in selected_ids if account_id not in available]
        if unknown:
            raise HTTPException(422, "one or more selected accounts are not in this authorization request")
        payload = {"sub": user_id, "tenant_id": tenant}
        connection_ids = []
        for account_id in selected_ids:
            connection_ids.append(await _save_selected_connection(
                payload, row["provider"], row["platform"], available[account_id], data["tokens"], s
            ))
        await s.execute(text(
            "DELETE FROM omnichannel_oauth_pending WHERE id=:id AND tenant_id=:tenant AND user_id=:user"
        ), {"id": pending_id, "tenant": tenant, "user": user_id})
        await s.commit()
    return {
        "status": "connected", "connection_ids": connection_ids,
        "connection_id": connection_ids[0] if len(connection_ids) == 1 else None,
        "connected_count": len(connection_ids), "provider": row["provider"], "platform": row["platform"],
    }


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
