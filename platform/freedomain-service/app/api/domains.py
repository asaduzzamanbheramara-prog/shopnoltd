import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import FreeDomain
from app.schemas.schemas import RegisterIn

router = APIRouter()
bearer = HTTPBearer()

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
RESERVED = {
    "www", "mail", "api", "admin", "shopno", "shopnoltd", "ns1", "ns2", "mx", "ftp", "static", "cdn",
}
PUBLIC_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


def preferred_subdomain(user: dict) -> str:
    raw = str(user.get("preferred_username") or user.get("username") or "").strip().lower()
    if "@" in raw:
        raw = raw.split("@", 1)[0]
    raw = re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")
    raw = re.sub(r"-{2,}", "-", raw)
    if not raw or not NAME_RE.match(raw) or raw in RESERVED:
        raw = f"user-{str(user.get('sub', 'unknown')).lower().replace('_', '-')}"
    return raw[:63].rstrip("-")


async def ensure_free_domain_schema():
    async with SessionLocal() as s:
        # Existing installations used create_all(), so add the invariant
        # explicitly and repair historical duplicate active rows before it.
        await s.execute(text("""
            CREATE TABLE IF NOT EXISTS freedomain (
                id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(64) NOT NULL,
                subdomain VARCHAR(128) NOT NULL UNIQUE,
                target VARCHAR(256) NOT NULL,
                record_type VARCHAR(8) DEFAULT 'CNAME',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP NULL,
                last_check TIMESTAMP NULL,
                last_status VARCHAR(16) NULL
            )
        """))
        await s.execute(text("""
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY user_id ORDER BY created_at NULLS LAST, id
                ) AS rn
                FROM freedomain
                WHERE active = 1
            )
            UPDATE freedomain
            SET active = 0
            WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """))
        await s.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_freedomain_one_active_user
            ON freedomain (user_id)
            WHERE active = 1
        """))
        await s.commit()


async def rdap_domain_available(domain: str):
    domain = domain.lower().rstrip(".")
    tld = domain.rsplit(".", 1)[-1]
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=4.0),
            follow_redirects=True,
        ) as c:
            bootstrap = await c.get("https://data.iana.org/rdap/dns.json")
            bootstrap.raise_for_status()
            services = bootstrap.json().get("services", [])
            rdap_base = None
            for service in services:
                if len(service) != 2:
                    continue
                tlds, urls = service
                if tld in [str(x).lower() for x in tlds] and urls:
                    rdap_base = urls[0].rstrip("/")
                    break
            if not rdap_base:
                return None
            r = await c.get(f"{rdap_base}/domain/{domain}")
            if r.status_code == 404:
                return True
            if 200 <= r.status_code < 300:
                return False
            return None
    except Exception:
        return None


async def _create_dns_record(subdomain: str, target: str, record_type: str, *, allow_wildcard_fallback: bool = False):
    # The recovered cluster uses an existing Cloudflare wildcard for free Shopnoltd subdomains.
    # When explicitly enabled, keep the entitlement/database row without requiring the retired
    # per-record PowerDNS backend. Paid/custom DNS flows remain provider-backed.
    if allow_wildcard_fallback and settings.wildcard_dns_fallback and target == settings.default_target and record_type.upper() == settings.default_record_type.upper():
        return
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        follow_redirects=True,
    ) as c:
        response = await c.post(
            f"{settings.domain_service_url}/api/v1/records",
            json={
                "zone_id": settings.parent_zone,
                "name": subdomain,
                "type": record_type,
                "content": target,
                "ttl": 300,
            },
            headers={"Authorization": f"Bearer {settings.freedomain_internal_key}"},
        )
        response.raise_for_status()


async def provision_for_user(user: dict, s: AsyncSession) -> FreeDomain:
    existing = (
        await s.execute(
            select(FreeDomain)
            .where(FreeDomain.user_id == user["sub"], FreeDomain.active == 1)
            .order_by(FreeDomain.created_at.asc())
        )
    ).scalars().first()
    if existing:
        return existing

    label = preferred_subdomain(user)
    candidate = f"{label}.{settings.parent_zone}"
    occupied = await s.scalar(select(FreeDomain).where(FreeDomain.subdomain == candidate))
    if occupied:
        # Keycloak usernames are normally unique; this fallback handles
        # historical records or a username that collides with a reserved label.
        suffix = str(user["sub"]).replace("-", "")[-8:].lower()
        label = f"{label[:63-len(suffix)-1].rstrip('-')}-{suffix}"
        candidate = f"{label}.{settings.parent_zone}"

    try:
        await _create_dns_record(candidate, settings.default_target, settings.default_record_type, allow_wildcard_fallback=True)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"DNS provider rejected free-domain provisioning: HTTP {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="DNS provider is unavailable") from exc

    fd = FreeDomain(
        user_id=user["sub"],
        subdomain=candidate,
        target=settings.default_target,
        record_type=settings.default_record_type,
    )
    s.add(fd)
    try:
        await s.commit()
        await s.refresh(fd)
    except IntegrityError:
        await s.rollback()
        existing = await s.scalar(
            select(FreeDomain).where(FreeDomain.user_id == user["sub"], FreeDomain.active == 1)
        )
        if existing:
            return existing
        raise HTTPException(status_code=409, detail="free domain is already being provisioned") from None
    return fd


@router.get("/search")
async def search_domains(name: str = Query(..., min_length=1, max_length=253)):
    name = name.strip().lower().rstrip(".")
    if "." in name:
        if not PUBLIC_DOMAIN_RE.match(name):
            raise HTTPException(400, "invalid domain name")
        available = await rdap_domain_available(name)
        return {
            "query": name,
            "results": [{
                "domain": name,
                "available": available,
                "status": "available" if available is True else "registered" if available is False else "unknown",
            }],
        }
    if not NAME_RE.match(name):
        raise HTTPException(400, "invalid domain name")
    tlds = ["com", "org", "net", "info", "biz", "xyz", "online", "store", "site"]
    results = []
    for tld in tlds:
        domain = f"{name}.{tld}"
        available = await rdap_domain_available(domain)
        results.append({
            "domain": domain,
            "available": available,
            "status": "available" if available is True else "registered" if available is False else "unknown",
        })
    return {"query": name, "results": results}


@router.post("", status_code=201)
async def register(body: RegisterIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    # One active free Shopnoltd subdomain is the entitlement per unique user.
    existing = await s.scalar(
        select(FreeDomain).where(FreeDomain.user_id == user["sub"], FreeDomain.active == 1)
    )
    if existing:
        raise HTTPException(
            409,
            "each user receives one free Shopnoltd subdomain; use the existing address or register a paid domain",
        )

    sub = body.subdomain.lower()
    if not NAME_RE.match(sub):
        raise HTTPException(400, "invalid subdomain")
    if sub in RESERVED:
        raise HTTPException(400, "subdomain reserved")
    full = f"{sub}.{settings.parent_zone}"
    if await s.scalar(select(FreeDomain).where(FreeDomain.subdomain == full)):
        raise HTTPException(409, "subdomain already taken")

    try:
        await _create_dns_record(full, body.target, body.record_type)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"DNS provider rejected domain registration: HTTP {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="DNS provider is unavailable") from exc

    fd = FreeDomain(
        user_id=user["sub"], subdomain=full, target=body.target, record_type=body.record_type
    )
    s.add(fd)
    try:
        await s.commit()
        await s.refresh(fd)
    except IntegrityError:
        await s.rollback()
        raise HTTPException(status_code=409, detail="each user may have only one active free Shopnoltd subdomain") from None

    return {
        "id": fd.id,
        "subdomain": full,
        "target": fd.target,
        "record_type": fd.record_type,
        "active": True,
    }


@router.get("/me")
async def mine(user=Depends(current_user), s: AsyncSession = Depends(db)):
    # Lazy provisioning makes the entitlement apply to existing and newly
    # registered users without coupling DNS provisioning to Keycloak itself.
    fd = await provision_for_user(user, s)
    return [{
        "id": fd.id,
        "subdomain": fd.subdomain,
        "target": fd.target,
        "record_type": fd.record_type,
        "active": bool(fd.active),
        "last_status": fd.last_status,
        "created_at": fd.created_at.isoformat() if fd.created_at else None,
    }]


@router.get("/check-availability")
async def check(subdomain: str, s: AsyncSession = Depends(db)):
    sub = subdomain.lower()
    if not NAME_RE.match(sub) or sub in RESERVED:
        return {"available": False, "reason": "invalid or reserved"}
    full = f"{sub}.{settings.parent_zone}"
    exists = await s.scalar(select(FreeDomain).where(FreeDomain.subdomain == full))
    return {"available": exists is None, "subdomain": full}


@router.delete("/{dom_id}")
async def delete(dom_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    fd = await s.scalar(
        select(FreeDomain).where(FreeDomain.id == dom_id, FreeDomain.user_id == user["sub"], FreeDomain.active == 1)
    )
    if not fd:
        raise HTTPException(404, "not found")
    fd.active = 0
    await s.commit()
    return {"ok": True}
