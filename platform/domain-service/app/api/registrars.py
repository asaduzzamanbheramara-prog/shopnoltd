"""Authenticated domain registration and renewal API."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import DomainRegistration
from app.services.billing_service import BillingService
from app.services.registrars.namecheap import NamecheapAdapter

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


def registrar() -> NamecheapAdapter:
    if not settings.namecheap_api_key or not settings.namecheap_username or not settings.namecheap_client_ip:
        raise HTTPException(503, "Namecheap registrar is not configured")
    return NamecheapAdapter(
        api_key=settings.namecheap_api_key,
        username=settings.namecheap_username,
        client_ip=settings.namecheap_client_ip,
        sandbox=settings.namecheap_sandbox,
    )


def billing() -> BillingService:
    return BillingService(settings.billing_engine_url, settings.billing_internal_key, settings.billing_currency)


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return await verify_token(creds.credentials)


@router.get("/domains/check")
async def check_domain(domain: str, user=Depends(current_user)):
    return await registrar().check_availability(domain)


@router.get("/domains/pricing")
async def domain_pricing(tld: str, years: int = 1, user=Depends(current_user)):
    if years < 1 or years > 10:
        raise HTTPException(400, "years must be between 1 and 10")
    return await registrar().get_pricing(tld, years)


@router.post("/domains/register")
async def register_domain_user(
    domain: str,
    years: int = 1,
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    if years < 1 or years > 10:
        raise HTTPException(400, "years must be between 1 and 10")
    email = user.get("email")
    if not email:
        raise HTTPException(400, "Authenticated account has no email claim")
    domain = domain.lower().rstrip(".")

    contact_fields = ("given_name", "family_name", "address1", "city", "state", "postal_code", "country", "phone")
    missing = [field for field in contact_fields if not user.get(field)]
    if missing:
        raise HTTPException(400, f"registrant profile is incomplete: missing {', '.join(missing)}")

    existing = (await s.execute(select(DomainRegistration).where(DomainRegistration.domain == domain))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "domain already exists in Shopnoltd registry")

    reg = registrar()
    availability = await reg.check_availability(domain)
    if not availability.get("available"):
        raise HTTPException(409, "domain is not available")

    tld = domain.rsplit(".", 1)[-1]
    pricing = await reg.get_pricing(tld, years)
    amount = Decimal(str(pricing["price"]))
    currency = str(pricing.get("currency", settings.billing_currency)).upper()
    if currency != settings.billing_currency.upper():
        raise HTTPException(409, f"registrar price currency {currency} is not enabled for billing")

    funds = await billing().check_wallet_balance(email, amount)
    if not funds["sufficient"]:
        raise HTTPException(402, f"insufficient {currency} wallet balance")

    row = DomainRegistration(
        tenant_id=user.get("tenant_id", "default"),
        user_id=str(user["sub"]),
        email=email,
        domain=domain,
        registrar="namecheap",
        status="pending",
        years=years,
        currency=currency,
        charged_amount=amount,
    )
    s.add(row)
    await s.flush()
    reference_id = f"domain-registration:{row.id}"

    try:
        await billing().deduct_credit(email, amount, domain, years, reference_id)
        row.status = "billing_charged"
        await s.commit()

        contact = {
            "first_name": user["given_name"],
            "last_name": user["family_name"],
            "address1": user["address1"],
            "city": user["city"],
            "state": user["state"],
            "postal_code": user["postal_code"],
            "country": user["country"],
            "phone": user["phone"],
            "email": email,
        }
        result = await reg.register(domain, years, contact)
        row.status = "active"
        row.registrar_order_id = result.get("order_id")
        row.registrar_transaction_id = result.get("transaction_id")
        await s.commit()
    except Exception as exc:
        row.status = "failed"
        row.error = str(exc)[:2000]
        await s.commit()
        try:
            await billing().refund_credit(email, amount, f"Refund failed domain registration: {domain}", f"domain-refund:{row.id}")
        except Exception as refund_exc:
            row.status = "refund_required"
            row.error = f"{row.error}; refund failed: {refund_exc}"[:2000]
            await s.commit()
        raise HTTPException(502, "domain registration failed; billing reconciliation recorded") from exc

    return {
        "id": row.id,
        "domain": row.domain,
        "status": row.status,
        "years": years,
        "currency": currency,
        "charged_amount": str(amount),
        "registrar_order_id": row.registrar_order_id,
    }


@router.post("/domains/{domain}/renew")
async def renew_domain_user(
    domain: str,
    years: int = 1,
    user=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    if years < 1 or years > 10:
        raise HTTPException(400, "years must be between 1 and 10")
    email = user.get("email")
    domain = domain.lower().rstrip(".")
    row = (await s.execute(select(DomainRegistration).where(
        DomainRegistration.domain == domain,
        DomainRegistration.tenant_id == user.get("tenant_id", "default"),
    ))).scalar_one_or_none()
    if not row or row.status != "active":
        raise HTTPException(404, "active domain registration not found")

    pricing = await registrar().get_pricing(domain.rsplit(".", 1)[-1], years)
    amount = Decimal(str(pricing["price"]))
    funds = await billing().check_wallet_balance(email, amount)
    if not funds["sufficient"]:
        raise HTTPException(402, "insufficient wallet balance")
    await billing().deduct_credit(email, amount, f"Renewal {domain}", years, f"domain-renewal:{row.id}:{years}")
    try:
        result = await registrar().renew(domain, years)
    except Exception as exc:
        try:
            await billing().refund_credit(email, amount, f"Refund failed domain renewal: {domain}", f"domain-renew-refund:{row.id}:{years}")
        except Exception:
            row.status = "refund_required"
            await s.commit()
        raise HTTPException(502, "domain renewal failed; billing reconciliation recorded") from exc

    row.registrar_order_id = result.get("order_id")
    row.registrar_transaction_id = result.get("transaction_id")
    await s.commit()
    return {"domain": domain, "status": "renewed", "years": years, "charged_amount": str(amount)}


@router.get("/domains")
async def list_user_domains(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(DomainRegistration)
        .where(
            DomainRegistration.tenant_id == user.get("tenant_id", "default"),
            DomainRegistration.user_id == str(user["sub"]),
        )
        .order_by(desc(DomainRegistration.created_at))
    )
    return {"domains": [
        {"id": d.id, "domain": d.domain, "status": d.status, "years": d.years, "expires_at": d.expires_at.isoformat() if d.expires_at else None}
        for d in res.scalars().all()
    ]}


@router.get("/domains/{domain}")
async def get_domain(domain: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    domain = domain.lower().rstrip(".")
    row = (await s.execute(select(DomainRegistration).where(
        DomainRegistration.domain == domain,
        DomainRegistration.tenant_id == user.get("tenant_id", "default"),
        DomainRegistration.user_id == str(user["sub"]),
    ))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "domain not found")
    return {
        "id": row.id,
        "domain": row.domain,
        "status": row.status,
        "years": row.years,
        "currency": row.currency,
        "charged_amount": str(row.charged_amount) if row.charged_amount is not None else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "registrar_order_id": row.registrar_order_id,
        "error": row.error,
    }
