"""Domain registration API with user self-service and billing.

Full rewrite. The previous version of this file had four endpoints that
were all `# TODO: Wire billing integration` stubs — register_domain_user
returned a fake "pending" status without calling any registrar or moving
any money; list/get claimed to "query the zones table" against a model
(Zone) that has no user/purchase concept at all.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Domain, DomainOrder, Registrar
from app.schemas.schemas import DomainOut, RegisterDomainIn
from app.services.billing_service import BillingService, IdempotencyConflictError, InsufficientFundsError
from app.services.registrar_factory import get_adapter
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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



def _request_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _idempotency_key_hash(key: str) -> str:
    return hashlib.sha256(key.strip().encode("utf-8")).hexdigest()


async def _load_order(
    s: AsyncSession, *, user_id: str, operation: str, key: str, fingerprint: str
) -> DomainOrder | None:
    order = await s.scalar(
        select(DomainOrder).where(
            DomainOrder.user_id == user_id,
            DomainOrder.operation == operation,
            DomainOrder.idempotency_key_hash == _idempotency_key_hash(key),
        )
    )
    if order and order.request_fingerprint != fingerprint:
        raise HTTPException(409, "Idempotency-Key was already used for a different domain request")
    return order


async def _create_order(
    s: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    operation: str,
    key: str,
    fingerprint: str,
    domain: str,
    years: int,
    price: Decimal,
    currency: str,
) -> DomainOrder:
    order = DomainOrder(
        tenant_id=tenant_id,
        user_id=user_id,
        operation=operation,
        idempotency_key_hash=_idempotency_key_hash(key),
        request_fingerprint=fingerprint,
        domain=domain,
        years=years,
        price=price,
        currency=currency,
        status="pending_charge",
    )
    s.add(order)
    try:
        await s.commit()
        await s.refresh(order)
        return order
    except IntegrityError:
        await s.rollback()
        existing = await _load_order(
            s, user_id=user_id, operation=operation, key=key, fingerprint=fingerprint
        )
        if existing:
            return existing
        raise


def _raise_order_reconciliation(order: DomainOrder) -> None:
    raise HTTPException(
        409,
        f"Domain order {order.id} requires reconciliation (status={order.status}); "
        "no additional charge or registrar mutation was attempted.",
    )


async def _completed_domain(s: AsyncSession, order: DomainOrder) -> Domain | None:
    if order.status != "completed":
        return None
    return await s.scalar(
        select(Domain).where(Domain.user_id == order.user_id, Domain.name == order.domain)
    )



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
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    user_and_token=Depends(current_user),
    s: AsyncSession = Depends(db),
):
    user, token = user_and_token
    domain = body.domain.strip().lower()
    if "." not in domain:
        raise HTTPException(400, "Enter a full domain, e.g. example.com")

    fingerprint = _request_fingerprint({
        "domain": domain,
        "years": body.years,
        "contact": body.contact.model_dump(),
    })
    order = await _load_order(
        s, user_id=str(user["sub"]), operation="register",
        key=idempotency_key, fingerprint=fingerprint,
    )
    if order:
        completed = await _completed_domain(s, order)
        if completed:
            return _domain_out(completed)
        if order.status in {"charged", "registrar_in_progress", "reconciliation_required"}:
            _raise_order_reconciliation(order)

    registrar = await _get_registrar(s)
    adapter = get_adapter(registrar)

    if order is None:
        try:
            avail = await adapter.check_availability(domain)
        except (RuntimeError, ValueError) as e:
            raise HTTPException(502, "Registrar availability check failed") from e
        if not avail["available"]:
            raise HTTPException(409, f"{domain} is no longer available")
        try:
            pricing = await adapter.get_pricing(_tld_of(domain), years=body.years)
        except (RuntimeError, ValueError) as e:
            raise HTTPException(502, "Registrar pricing lookup failed") from e
        price = Decimal(str(avail.get("premium_price") or pricing["price"]))
        currency = pricing["currency"]
        order = await _create_order(
            s, tenant_id=user.get("tenant_id", "default"), user_id=str(user["sub"]),
            operation="register", key=idempotency_key, fingerprint=fingerprint,
            domain=domain, years=body.years, price=price, currency=currency,
        )
        completed = await _completed_domain(s, order)
        if completed:
            return _domain_out(completed)
        if order.status != "pending_charge":
            _raise_order_reconciliation(order)
    else:
        price = Decimal(str(order.price))
        currency = order.currency

    billing = _billing()
    try:
        charge = await billing.charge_for_domain(
            token, currency, price, domain, body.years,
            user_id=str(user["sub"]), operation="register", request_key=idempotency_key,
        )
    except InsufficientFundsError as e:
        raise HTTPException(402, "Insufficient available wallet funds") from e
    except IdempotencyConflictError as e:
        raise HTTPException(409, "Idempotency-Key conflicts with a different payment request") from e
    except RuntimeError as e:
        # Leave pending_charge so the same key can safely reconcile an ambiguous
        # payment response through the payment service's own idempotency record.
        raise HTTPException(502, f"Payment status is unconfirmed for order {order.id}; retry with the same Idempotency-Key") from e

    order.charge_transaction_id = str(charge.get("id") or "")
    order.status = "charged"
    order.failure_code = None
    await s.commit()

    # Mark the external side effect as in progress before calling the registrar.
    # If the process dies during the call, retries are blocked for reconciliation
    # rather than risking a second registration or a second charge.
    order.status = "registrar_in_progress"
    await s.commit()
    try:
        avail_now = await adapter.check_availability(domain)
        if not avail_now["available"]:
            order.status = "reconciliation_required"
            order.failure_code = "domain_unavailable_after_charge"
            await s.commit()
            _raise_order_reconciliation(order)
        result = await adapter.register(domain, body.years, body.contact.model_dump())
    except HTTPException:
        raise
    except (RuntimeError, ValueError) as e:
        order.status = "reconciliation_required"
        order.failure_code = "registrar_call_failed"
        await s.commit()
        raise HTTPException(
            502, f"Registration outcome for order {order.id} requires reconciliation; no retry charge was made."
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
        charge_transaction_id=order.charge_transaction_id,
        expires_at=datetime.utcnow() + timedelta(days=365 * body.years),
    )
    order.registrar_order_id = str(result.get("order_id") or "")
    order.status = "completed"
    order.failure_code = None
    s.add(record)
    await s.commit()
    await s.refresh(record)
    return _domain_out(record)


9987@router.get("/domains", response_model=list[DomainOut])
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
