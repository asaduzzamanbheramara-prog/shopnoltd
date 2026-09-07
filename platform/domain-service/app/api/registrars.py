"""Domain self-service API boundary.

Registration and renewal are billing-gated operations. A request is never
reported as completed until the registrar confirms success.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _subject(identity: dict) -> str:
    subject = identity.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status_code=403, detail="Authenticated user subject unavailable")
    return subject.strip()


@router.post("/domains/register")
async def register_domain_user(domain: str, years: int = 1, identity: dict = Depends(current_user)):
    """Start a domain registration workflow; do not claim registrar success here."""
    owner = _subject(identity)
    domain = domain.strip().lower()
    if not domain or "." not in domain:
        raise HTTPException(status_code=422, detail="Valid domain is required")
    if years < 1 or years > 10:
        raise HTTPException(status_code=422, detail="years must be between 1 and 10")
    return {
        "domain": domain,
        "years": years,
        "owner_id": owner,
        "status": "billing_required",
        "next_step": "obtain_authoritative_registrar_price_then_create_verified_checkout",
        "completed": False,
    }


@router.post("/domains/{domain}/renew")
async def renew_domain_user(domain: str, years: int = 1, identity: dict = Depends(current_user)):
    """Start a renewal workflow; only a verified registrar response may complete it."""
    owner = _subject(identity)
    domain = domain.strip().lower()
    if not domain or "." not in domain:
        raise HTTPException(status_code=422, detail="Valid domain is required")
    if years < 1 or years > 10:
        raise HTTPException(status_code=422, detail="years must be between 1 and 10")
    return {
        "domain": domain,
        "years": years,
        "owner_id": owner,
        "status": "billing_required",
        "next_step": "obtain_authoritative_registrar_price_then_create_verified_checkout",
        "completed": False,
    }


@router.get("/domains")
async def list_user_domains(identity: dict = Depends(current_user)):
    """List domains owned by the authenticated user."""
    owner = _subject(identity)
    return {"owner_id": owner, "domains": []}


@router.get("/domains/{domain}")
async def get_domain(domain: str, identity: dict = Depends(current_user)):
    """Return domain state without fabricating an active registrar record."""
    owner = _subject(identity)
    domain = domain.strip().lower()
    return {
        "domain": domain,
        "owner_id": owner,
        "status": "unknown",
        "completed": False,
        "expires_at": None,
        "note": "Registrar-backed domain persistence is required before an active state can be returned.",
    }
