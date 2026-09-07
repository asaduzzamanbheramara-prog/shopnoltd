import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text

from app.core.db import Base


class Zone(Base):
    __tablename__ = "zones"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), unique=True, nullable=False)
    kind = Column(String(16), default="MASTER")
    ttl = Column(Integer, default=3600)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Record(Base):
    __tablename__ = "records"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    type = Column(String(16), nullable=False)
    content = Column(String(1024), nullable=False)
    ttl = Column(Integer, default=3600)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Registrar(Base):
    __tablename__ = "registrars"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(64), nullable=False)
    api_key = Column(String(256))
    api_secret = Column(String(256))
    enabled = Column(Boolean, default=True)


class DomainRegistration(Base):
    __tablename__ = "domain_registrations"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    email = Column(String(320), nullable=False, index=True)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    registrar = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    years = Column(Integer, nullable=False, default=1)
    currency = Column(String(3), nullable=False, default="USD")
    charged_amount = Column(Numeric(20, 8), nullable=True)
    registrar_order_id = Column(String(128), nullable=True)
    registrar_transaction_id = Column(String(128), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
