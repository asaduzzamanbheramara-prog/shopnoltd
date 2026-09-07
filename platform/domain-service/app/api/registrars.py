"""Domain self-service API boundary.

Registration and renewal are deliberately modeled as billing-gated operations.
A request is never reported as completed until the registrar confirms success.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


def _require_user(user_id: str | None) -> str:
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id.strip()


@router.post("/domains/register")
async def register_domain_user(domain: str, years: int = 1, user_id: str | None = None):
    """Start a domain registration workflow; do not claim registrar success here."""
    owner = _require_user(user_id)
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
async def renew_domain_user(domain: str, years: int = 1, user_id: str | None = None):
    """Start a renewal workflow; only a verified registrar response may complete it."""
    owner = _require_user(user_id)
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
async def list_user_domains(user_id: str | None = None):
    """List domains owned by the authenticated user."""
    owner = _require_user(user_id)
    return {"owner_id": owner, "domains": []}


@router.get("/domains/{domain}")
async def get_domain(domain: str, user_id: str | None = None):
    """Return domain state without fabricating an active registrar record."""
    owner = _require_user(user_id)
    domain = domain.strip().lower()
    return {
        "domain": domain,
        "owner_id": owner,
        "status": "unknown",
        "completed": False,
        "expires_at": None,
        "note": "Registrar-backed domain persistence is required before an active state can be returned.",
    }
