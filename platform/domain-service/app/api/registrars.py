"""Domain registration API with user self-service and billing.

Full rewrite. The previous version of this file had four endpoints that
were all `# TODO: Wire billing integration` stubs — register_domain_user
returned a fake "pending" status without calling any registrar or moving
any money; list/get claimed to "query the zones table" against a model
(Zone) that has no user/purchase concept at all.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Domain, Registrar
from app.schemas.schemas import DomainOut, RegisterDomainIn
from app.services.billing_service import BillingService
from app.services.registrar_factory import get_adapter
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    """Returns (decoded_claims, raw_token) — the raw token is needed to
    forward to payment-service for the billing charge, since that service
    authenticates by the caller's own JWT rather than a service credential."""
    claims = await verify_token(creds.credentials)
    return claims, creds.credentials


def _billing() -> BillingService:
    return BillingService(
        payment_service_url=settings.payment_service_url,
        platform_wallet_user_id=settings.platform_wallet_user_id,
    )


async def _get_registrar(s: AsyncSession) -> Registrar:
    res = await s.execute(
        select(Registrar).where(
            Registrar.name == settings.default_registrar_name, Registrar.enabled.is_(True)
        )
    )
    registrar = res.scalar_one_or_none()
    if not registrar:
        raise HTTPException(
            503,
            f"No enabled '{settings.default_registrar_name}' registrar configured. "
            "Add a row to the registrars table with a valid api_key/api_secret first.",
        )
    return registrar


def _tld_of(domain: str) -> str:
    return domain.rsplit(".", 1)[-1]


def _domain_out(d: Domain) -> DomainOut:
    return DomainOut(
        id=d.id,
        name=d.name,
        registrar_name=d.registrar_name,
        years=d.years,
        price=float(d.price),
        currency=d.currency,
        status=d.status,
        order_id=d.order_id,
        expires_at=d.expires_at.isoformat() if d.expires_at else None,
        created_at=d.created_at.isoformat(),
    )


@router.get("/domains/check-availability")
async def check_availability(domain: str, years: int = 1, s: AsyncSession = Depends(db)):
    """Public — no auth required, matches the free-subdomain checker's UX.
    Returns availability AND price together so the frontend can show both
    in one round trip."""
    domain = domain.strip().lower()
    if "." not in domain:
        raise HTTPException(400, "Enter a full domain, e.g. example.com")

    registrar = await _get_registrar(s)
    adapter = get_adapter(registrar)

    try:
        avail = await adapter.check_availability(domain)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(502, f"Registrar check failed: {e}") from e

    price = None
    currency = None
    if avail["available"]:
        try:
            pricing = await adapter.get_pricing(_tld_of(domain), years=years)
            price, currency = pricing["price"], pricing["currency"]
        except (RuntimeError, ValueError):
            # Availability is still meaningful even if pricing lookup fails —
            # surface it as available with unknown price rather than erroring
            # the whole request out.
            pass

    return {
        "domain": avail["domain"],
        "available": avail["available"],
        "premium": avail.get("premium", False),
        "price": avail.get("premium_price") or price,
        "currency": currency or "USD",
        "years": years,
    }


@router.post("/domains/register", response_model=DomainOut, status_code=201)
async def register_domain_user(
    body: RegisterDomainIn,
    user_and_token=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    user, token = user_and_token
    domain = body.domain.strip().lower()
    if "." not in domain:
        raise HTTPException(400, "Enter a full domain, e.g. example.com")

    registrar = await _get_registrar(s)
    adapter = get_adapter(registrar)

    # Re-check availability server-side right before charging — never trust
    # a client-supplied "it was available a minute ago".
    try:
        avail = await adapter.check_availability(domain)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(502, f"Registrar check failed: {e}") from e
    if not avail["available"]:
        raise HTTPException(409, f"{domain} is no longer available")

    try:
        pricing = await adapter.get_pricing(_tld_of(domain), years=body.years)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(502, f"Registrar pricing lookup failed: {e}") from e
    price = Decimal(str(avail.get("premium_price") or pricing["price"]))
    currency = pricing["currency"]

    billing = _billing()
    balance = await billing.check_wallet_balance(token, currency, price)
    if not balance["sufficient"]:
        raise HTTPException(
            402,
            f"Insufficient {currency} wallet balance: need {price}, have {balance['balance']}",
        )

    charge = await billing.charge_for_domain(token, currency, price, domain, body.years)

    try:
        result = await adapter.register(domain, body.years, body.contact.model_dump())
    except (RuntimeError, ValueError) as e:
        # Money has already left the user's wallet at this point and the
        # registrar call failed. This MUST be refunded — there is currently
        # no automated compensating-transfer path here (payment-service's
        # /transfers is caller-authenticated, and this service has no
        # credential for the platform wallet to transfer back from). Until
        # that's built, this needs a manual admin refund. Failing loudly
        # rather than silently eating the charge.
        raise HTTPException(
            502,
            f"Registration failed AFTER payment was charged (tx {charge.get('id')}). "
            f"This requires a manual refund — registrar error: {e}",
        ) from e

    record = Domain(
        tenant_id=user.get("tenant_id", "default"),
        user_id=user["sub"],
        name=domain,
        registrar_name=registrar.name,
        years=body.years,
        price=price,
        currency=currency,
        status="active",
        order_id=result.get("order_id"),
        charge_transaction_id=charge.get("id"),
        expires_at=datetime.utcnow() + timedelta(days=365 * body.years),
    )
    s.add(record)
    await s.commit()
    await s.refresh(record)
    return _domain_out(record)


@router.post("/domains/{domain}/renew", response_model=DomainOut)
async def renew_domain_user(
    domain: str,
    years: int = 1,
    user_and_token=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    user, token = user_and_token
    domain = domain.strip().lower()

    res = await s.execute(
        select(Domain).where(Domain.name == domain, Domain.user_id == user["sub"])
    )
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Domain not found in your account")

    registrar = await _get_registrar(s)
    adapter = get_adapter(registrar)

    try:
        pricing = await adapter.get_pricing(_tld_of(domain), years=years)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(502, f"Registrar pricing lookup failed: {e}") from e
    price = Decimal(str(pricing["price"]))
    currency = pricing["currency"]

    billing = _billing()
    balance = await billing.check_wallet_balance(token, currency, price)
    if not balance["sufficient"]:
        raise HTTPException(
            402,
            f"Insufficient {currency} wallet balance: need {price}, have {balance['balance']}",
        )
    charge = await billing.charge_for_domain(token, currency, price, domain, years)

    try:
        await adapter.renew(domain, years)
    except (RuntimeError, ValueError) as e:
        raise HTTPException(
            502,
            f"Renewal failed AFTER payment was charged (tx {charge.get('id')}). "
            f"This requires a manual refund — registrar error: {e}",
        ) from e

    record.years += years
    record.expires_at = (record.expires_at or datetime.utcnow()) + timedelta(days=365 * years)
    record.status = "active"
    await s.commit()
    await s.refresh(record)
    return _domain_out(record)


@router.get("/domains", response_model=list[DomainOut])
async def list_user_domains(user_and_token=Depends(current_user), s: AsyncSession = Depends(db)):
    user, _ = user_and_token
    res = await s.execute(select(Domain).where(Domain.user_id == user["sub"]))
    return [_domain_out(d) for d in res.scalars().all()]


@router.get("/domains/{domain}", response_model=DomainOut)
async def get_domain(
    domain: str, user_and_token=Depends(current_user), s: AsyncSession = Depends(db)
):
    user, _ = user_and_token
    res = await s.execute(
        select(Domain).where(Domain.name == domain.strip().lower(), Domain.user_id == user["sub"])
    )
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(404, "Domain not found in your account")
    return _domain_out(record)
