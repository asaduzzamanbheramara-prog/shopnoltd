import re

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import FreeDomain
from app.schemas.schemas import RegisterIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
RESERVED = {
    "www",
    "mail",
    "api",
    "admin",
    "shopno",
    "shopnoltd",
    "ns1",
    "ns2",
    "mx",
    "ftp",
    "static",
    "cdn",
}


PUBLIC_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)


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


@router.get("/search")
async def search_domains(name: str = Query(..., min_length=1, max_length=253)):
    name = name.strip().lower().rstrip(".")

    if "." in name:
        if not PUBLIC_DOMAIN_RE.match(name):
            raise HTTPException(400, "invalid domain name")

        available = await rdap_domain_available(name)

        return {
            "query": name,
            "results": [
                {
                    "domain": name,
                    "available": available,
                    "status": (
                        "available"
                        if available is True
                        else "registered"
                        if available is False
                        else "unknown"
                    ),
                }
            ],
        }

    if not NAME_RE.match(name):
        raise HTTPException(400, "invalid domain name")

    tlds = [
        "com",
        "org",
        "net",
        "info",
        "biz",
        "xyz",
        "online",
        "store",
        "site",
    ]

    results = []

    for tld in tlds:
        domain = f"{name}.{tld}"
        available = await rdap_domain_available(domain)

        results.append(
            {
                "domain": domain,
                "available": available,
                "status": (
                    "available"
                    if available is True
                    else "registered"
                    if available is False
                    else "unknown"
                ),
            }
        )

    return {
        "query": name,
        "results": results,
    }


@router.post("", status_code=201)
async def register(body: RegisterIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    sub = body.subdomain.lower()
    if not NAME_RE.match(sub):
        raise HTTPException(400, "invalid subdomain")
    if sub in RESERVED:
        raise HTTPException(400, "subdomain reserved")
    full = f"{sub}.{settings.parent_zone}"
    if (
        await s.execute(select(FreeDomain).where(FreeDomain.subdomain == full))
    ).scalar_one_or_none():
        raise HTTPException(409, "subdomain already taken")
    fd = FreeDomain(
        user_id=user["sub"], subdomain=full, target=body.target, record_type=body.record_type
    )
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=True,
        ) as c:
            response = await c.post(
                f"{settings.domain_service_url}/api/v1/records",
                json={
                    "zone_id": settings.parent_zone,
                    "name": full,
                    "type": body.record_type,
                    "content": body.target,
                    "ttl": 300,
                },
                headers={
                    "Authorization": f"Bearer {settings.domain_service_token}",
                },
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"DNS provider rejected domain registration: HTTP {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="DNS provider is unavailable",
        ) from exc

    s.add(fd)
    await s.commit()

    return {
        "id": fd.id,
        "subdomain": full,
        "target": body.target,
        "record_type": body.record_type,
        "active": True,
    }


@router.get("/me")
async def mine(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(FreeDomain).where(FreeDomain.user_id == user["sub"]))
    return [
        {
            "id": d.id,
            "subdomain": d.subdomain,
            "target": d.target,
            "record_type": d.record_type,
            "active": bool(d.active),
            "last_status": d.last_status,
            "created_at": d.created_at.isoformat(),
        }
        for d in res.scalars().all()
    ]


@router.get("/check-availability")
async def check(subdomain: str, s: AsyncSession = Depends(db)):
    sub = subdomain.lower()
    if not NAME_RE.match(sub) or sub in RESERVED:
        return {"available": False, "reason": "invalid or reserved"}
    full = f"{sub}.{settings.parent_zone}"
    exists = (
        await s.execute(select(FreeDomain).where(FreeDomain.subdomain == full))
    ).scalar_one_or_none()
    return {"available": exists is None, "subdomain": full}


@router.delete("/{dom_id}")
async def delete(dom_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    fd = (
        await s.execute(
            select(FreeDomain).where(FreeDomain.id == dom_id, FreeDomain.user_id == user["sub"])
        )
    ).scalar_one_or_none()
    if not fd:
        raise HTTPException(404, "not found")
    fd.active = 0
    await s.commit()
    return {"ok": True}
