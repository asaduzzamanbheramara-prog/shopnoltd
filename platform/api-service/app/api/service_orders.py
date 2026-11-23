import json
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.service_order import ServiceOrder, ServiceOrderEvent

router = APIRouter(prefix="/service-orders")
bearer = HTTPBearer()

SERVICE_LABELS = {
    "os_installation": "Operating system installation",
    "startup_recovery": "Startup repair and recovery",
    "software_setup": "Software, drivers and applications",
    "bootable_media": "Bootable USB and recovery media",
    "device_support": "Phone, tablet and device support",
    "troubleshooting": "Technical troubleshooting",
    "business_it_care": "Business IT care subscription",
    "other": "Other software or OS service",
}
ADMIN_ROLES = {"platform_admin", "admin", "tenant_admin", "shopnoltd-admin", "administrator"}
EMAIL_PATTERN = re.compile(r"^[^@\s]{1,128}@[^@\s]{1,120}\.[^@\s]{2,63}$")


class ServiceOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_code: Literal[
        "os_installation", "startup_recovery", "software_setup", "bootable_media",
        "device_support", "troubleshooting", "business_it_care", "other",
    ]
    contact_name: str = Field(min_length=1, max_length=100)
    contact_email: str = Field(min_length=5, max_length=254)
    device_platform: str = Field(default="", max_length=160)
    details: str = Field(min_length=10, max_length=2000)
    request_key: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._:-]+$")

    @field_validator("contact_name", "contact_email", "device_platform", "details")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("contact_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value:
            raise ValueError("contact name is required")
        return value

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("valid reply email required")
        return value

    @field_validator("details")
    @classmethod
    def validate_details(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("please provide at least 10 characters of detail")
        return value


class ServiceOrderQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=Decimal("0"), le=Decimal("10000000"), max_digits=12, decimal_places=2)
    currency: Literal["BDT", "USD"] = "BDT"
    customer_message: str = Field(default="", max_length=2000)
    expires_in_days: int = Field(default=7, ge=1, le=30)

    @field_validator("customer_message")
    @classmethod
    def trim_message(cls, value: str) -> str:
        return value.strip()


async def db():
    async with SessionLocal() as session:
        yield session


async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(credentials.credentials)


def _tenant(user: dict) -> str:
    tenant = str(user.get("tenant_id") or user.get("tenant") or "default").strip()
    if not tenant or len(tenant) > 64:
        raise HTTPException(401, "invalid tenant identity")
    return tenant


def _user_id(user: dict) -> str:
    subject = str(user.get("sub") or "").strip()
    if not subject or len(subject) > 128:
        raise HTTPException(401, "valid account identity required")
    return subject


def _roles(user: dict) -> set[str]:
    roles = set(user.get("roles") or [])
    roles.update((user.get("realm_access") or {}).get("roles") or [])
    return roles


def is_service_admin(user: dict) -> bool:
    return bool(_roles(user).intersection(ADMIN_ROLES) or user.get("is_admin") is True)


def _is_platform_admin(user: dict) -> bool:
    return "platform_admin" in _roles(user)


def _require_admin(user: dict) -> None:
    if not is_service_admin(user):
        raise HTTPException(403, "service order administration requires an admin role")


def _serialize(order: ServiceOrder, include_tenant: bool = False) -> dict:
    result = {
        "id": order.id,

        "service_code": order.service_code,
        "service_label": SERVICE_LABELS.get(order.service_code, "Software and OS service"),
        "contact_name": order.contact_name,
        "contact_email": order.contact_email,
        "device_platform": order.device_platform,
        "details": order.details,
        "status": order.status,
        "quoted_amount": str(order.quoted_amount) if order.quoted_amount is not None else None,
        "quote_currency": order.quote_currency,
        "customer_message": order.customer_message,
        "quote_version": order.quote_version,
        "quoted_at": order.quoted_at.isoformat() if order.quoted_at else None,
        "quote_expires_at": order.quote_expires_at.isoformat() if order.quote_expires_at else None,
        "accepted_at": order.accepted_at.isoformat() if order.accepted_at else None,
        "declined_at": order.declined_at.isoformat() if order.declined_at else None,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        "payment_status": "not_collected",
    }
    if include_tenant:
        result["tenant_id"] = order.tenant_id
    return result


def _same_request(order: ServiceOrder, body: ServiceOrderCreate) -> bool:
    return (
        order.service_code == body.service_code
        and order.contact_name == body.contact_name
        and order.contact_email == body.contact_email
        and order.device_platform == body.device_platform
        and order.details == body.details
    )


def _event(session: AsyncSession, order: ServiceOrder, actor_id: str, event_type: str, details: dict | None = None):
    session.add(ServiceOrderEvent(
        id=str(uuid.uuid4()),
        order_id=order.id,
        tenant_id=order.tenant_id,
        actor_id=actor_id,
        event_type=event_type,
        details=json.dumps(details or {}, separators=(",", ":"), sort_keys=True),
    ))


def _order_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(400, "invalid service order id") from exc


async def _customer_order(session: AsyncSession, order_id: str, user: dict):
    order = await session.scalar(select(ServiceOrder).where(
        ServiceOrder.id == _order_id(order_id),
        ServiceOrder.tenant_id == _tenant(user),
        ServiceOrder.customer_id == _user_id(user),
    ))
    if order is None:
        raise HTTPException(404, "service order not found")
    return order


async def _admin_order(session: AsyncSession, order_id: str, user: dict):
    stmt = select(ServiceOrder).where(ServiceOrder.id == _order_id(order_id))
    if not _is_platform_admin(user):
        stmt = stmt.where(ServiceOrder.tenant_id == _tenant(user))
    order = await session.scalar(stmt)
    if order is None:
        raise HTTPException(404, "service order not found")
    return order


@router.post("", status_code=201)
async def create_service_order(body: ServiceOrderCreate, user=Depends(current_user), session: AsyncSession = Depends(db)):
    tenant_id = _tenant(user)
    customer_id = _user_id(user)
    existing = await session.scalar(select(ServiceOrder).where(
        ServiceOrder.tenant_id == tenant_id,
        ServiceOrder.customer_id == customer_id,
        ServiceOrder.request_key == body.request_key,
    ))
    if existing:
        same_request = _same_request(existing, body)

        if not same_request:
            raise HTTPException(409, "request key was already used for a different service request")
        return _serialize(existing)

    order = ServiceOrder(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        customer_id=customer_id,
        request_key=body.request_key,
        service_code=body.service_code,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        device_platform=body.device_platform,
        details=body.details,
        status="requested",
    )
    session.add(order)
    _event(session, order, customer_id, "request_submitted", {"service_code": body.service_code})
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(select(ServiceOrder).where(
            ServiceOrder.tenant_id == tenant_id,
            ServiceOrder.customer_id == customer_id,
            ServiceOrder.request_key == body.request_key,
        ))
        if existing:
            if not _same_request(existing, body):
                raise HTTPException(409, "request key was already used for a different service request")
            return _serialize(existing)
        raise HTTPException(409, "service request could not be saved; please retry")
    await session.refresh(order)
    return _serialize(order)


@router.get("")
async def list_my_service_orders(user=Depends(current_user), session: AsyncSession = Depends(db)):
    rows = (await session.execute(
        select(ServiceOrder)
        .where(ServiceOrder.tenant_id == _tenant(user), ServiceOrder.customer_id == _user_id(user))
        .order_by(desc(ServiceOrder.created_at))
        .limit(100)
    )).scalars().all()
    return [_serialize(row) for row in rows]


@router.get("/{order_id}")
async def get_my_service_order(order_id: str, user=Depends(current_user), session: AsyncSession = Depends(db)):
    return _serialize(await _customer_order(session, order_id, user))


@router.post("/{order_id}/accept")
async def accept_service_quote(order_id: str, user=Depends(current_user), session: AsyncSession = Depends(db)):
    order = await _customer_order(session, order_id, user)
    if order.status != "quoted" or order.quoted_amount is None:
        raise HTTPException(409, "there is no active quote to accept")
    now = datetime.utcnow()
    if order.quote_expires_at and order.quote_expires_at < now:
        raise HTTPException(409, "this quote has expired; request an updated quote")
    order.status = "accepted"
    order.accepted_at = now
    _event(session, order, _user_id(user), "quote_accepted", {"quote_version": order.quote_version})
    await session.commit()
    await session.refresh(order)
    return _serialize(order)


@router.post("/{order_id}/decline")
async def decline_service_quote(order_id: str, user=Depends(current_user), session: AsyncSession = Depends(db)):
    order = await _customer_order(session, order_id, user)
    if order.status != "quoted":
        raise HTTPException(409, "there is no active quote to decline")
    order.status = "declined"
    order.declined_at = datetime.utcnow()
    _event(session, order, _user_id(user), "quote_declined", {"quote_version": order.quote_version})
    await session.commit()
    await session.refresh(order)
    return _serialize(order)


@router.get("/admin/list", include_in_schema=True)
async def admin_service_orders(status: str | None = None, limit: int = 100, user=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(user)
    if status and status not in {"requested", "quoted", "accepted", "declined", "cancelled"}:
        raise HTTPException(422, "invalid service order status filter")
    stmt = select(ServiceOrder).order_by(desc(ServiceOrder.created_at)).limit(max(1, min(limit, 200)))
    if not _is_platform_admin(user):
        stmt = stmt.where(ServiceOrder.tenant_id == _tenant(user))
    if status:
        stmt = stmt.where(ServiceOrder.status == status)
    rows = (await session.execute(stmt)).scalars().all()
    return [_serialize(row, include_tenant=True) for row in rows]


@router.post("/admin/{order_id}/quote")
async def issue_service_quote(order_id: str, body: ServiceOrderQuote, user=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(user)
    order = await _admin_order(session, order_id, user)
    if order.status not in {"requested", "quoted"}:
        raise HTTPException(409, "quotes can only be issued for new or previously quoted requests")
    now = datetime.utcnow()
    order.quoted_amount = body.amount.quantize(Decimal("0.01"))
    order.quote_currency = body.currency
    order.customer_message = body.customer_message
    order.quote_version = (order.quote_version or 0) + 1
    order.quoted_by = _user_id(user)
    order.quoted_at = now
    order.quote_expires_at = now + timedelta(days=body.expires_in_days)
    order.status = "quoted"
    _event(session, order, _user_id(user), "quote_issued", {
        "quote_version": order.quote_version,
        "amount": str(order.quoted_amount),
        "currency": order.quote_currency,
        "expires_at": order.quote_expires_at.isoformat(),
    })
    await session.commit()
    await session.refresh(order)
    return _serialize(order, include_tenant=True)


@router.post("/admin/{order_id}/cancel")
async def cancel_service_order(order_id: str, user=Depends(current_user), session: AsyncSession = Depends(db)):
    _require_admin(user)
    order = await _admin_order(session, order_id, user)
    if order.status in {"declined", "cancelled"}:
        raise HTTPException(409, "this service request can no longer be cancelled")
    previous = order.status
    order.status = "cancelled"
    _event(session, order, _user_id(user), "request_cancelled", {"previous_status": previous})
    await session.commit()
    await session.refresh(order)
    return _serialize(order, include_tenant=True)
