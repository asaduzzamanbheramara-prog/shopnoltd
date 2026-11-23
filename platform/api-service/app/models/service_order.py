import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, Text

from app.core.db import Base


class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    customer_id = Column(String(128), nullable=False, index=True)
    request_key = Column(String(64), nullable=False)
    service_code = Column(String(48), nullable=False, index=True)
    contact_name = Column(String(100), nullable=False)
    contact_email = Column(String(254), nullable=False)
    device_platform = Column(String(160), nullable=False, default="")
    details = Column(Text, nullable=False)
    status = Column(String(24), nullable=False, default="requested", index=True)
    quoted_amount = Column(Numeric(12, 2), nullable=True)
    quote_currency = Column(String(3), nullable=True)
    customer_message = Column(Text, nullable=True)
    quote_version = Column(Integer, nullable=False, default=0)
    quoted_by = Column(String(128), nullable=True)
    quoted_at = Column(DateTime, nullable=True)
    quote_expires_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("uq_service_order_request_key", "tenant_id", "customer_id", "request_key", unique=True),
        Index("ix_service_orders_tenant_status_created", "tenant_id", "status", "created_at"),
    )


class ServiceOrderEvent(Base):
    __tablename__ = "service_order_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(128), nullable=False)
    event_type = Column(String(32), nullable=False)
    details = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
