from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import require_tenant_access, require_customer_self_or_above, verify_token
from app.models.models import Customer
from app.schemas.schemas import CustomerIn, CustomerOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


def _out(c: Customer) -> CustomerOut:
    return CustomerOut(
        id=c.id, tenant_id=c.tenant_id, email=c.email, name=c.name or "",
        phone=c.phone or "", billing_address=c.billing_address or {},
        preferences=c.preferences or {}, active=c.active,
    )


@router.post("/{tenant_id}/customers", response_model=CustomerOut, status_code=201)
async def create(tenant_id: str, body: CustomerIn, creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    """platform_admin or tenant_owner only -- customers don't create their own
    record here (that happens via the normal signup/social-login flow)."""
    await require_tenant_access(creds.credentials, tenant_id)
    payload = await verify_token(creds.credentials)
    c = Customer(tenant_id=tenant_id, keycloak_id=payload["sub"], email=body.email, name=body.name,
                 phone=body.phone, billing_address=body.billing_address, preferences=body.preferences)
    s.add(c); await s.commit(); await s.refresh(c)
    return _out(c)


@router.get("/{tenant_id}/customers", response_model=list[CustomerOut])
async def list_(tenant_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    """platform_admin or tenant_owner -- lists everyone in the tenant.
    (Customers should use GET /{tenant_id}/customers/{id} for their own record.)"""
    await require_tenant_access(creds.credentials, tenant_id)
    res = await s.execute(select(Customer).where(Customer.tenant_id == tenant_id))
    return [_out(c) for c in res.scalars().all()]


@router.get("/{tenant_id}/customers/{customer_id}", response_model=CustomerOut)
async def get(tenant_id: str, customer_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    c = (await s.execute(select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "customer not found")
    await require_customer_self_or_above(creds.credentials, tenant_id, c.keycloak_id)
    return _out(c)


@router.patch("/{tenant_id}/customers/{customer_id}", response_model=CustomerOut)
async def update(tenant_id: str, customer_id: str, body: CustomerIn, creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    """A customer may edit their own name/phone/billing/preferences.
    tenant_owner/platform_admin may edit any customer in the tenant."""
    c = (await s.execute(select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "customer not found")
    await require_customer_self_or_above(creds.credentials, tenant_id, c.keycloak_id)
    c.name, c.phone = body.name, body.phone
    c.billing_address, c.preferences = body.billing_address, body.preferences
    if body.email:
        c.email = body.email
    await s.commit(); await s.refresh(c)
    return _out(c)


@router.delete("/{tenant_id}/customers/{customer_id}", status_code=204)
async def delete(tenant_id: str, customer_id: str, creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    """platform_admin or tenant_owner only -- customers cannot delete themselves here."""
    await require_tenant_access(creds.credentials, tenant_id)
    c = (await s.execute(select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "customer not found")
    await s.delete(c); await s.commit()
