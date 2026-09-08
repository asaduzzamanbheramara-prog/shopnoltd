import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String

from app.core.db import Base


class Zone(Base):
    __tablename__ = "zones"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), unique=True, nullable=False)
    kind = Column(String(16), default="MASTER")  # MASTER, SLAVE, NATIVE
    ttl = Column(Integer, default=3600)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Record(Base):
    __tablename__ = "records"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    type = Column(String(16), nullable=False)  # A, AAAA, CNAME, MX, TXT, NS, SRV
    content = Column(String(1024), nullable=False)
    ttl = Column(Integer, default=3600)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Registrar(Base):
    __tablename__ = "registrars"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(64), nullable=False)  # namecheap, porkbun, cloudflare
    api_key = Column(String(256))
    api_secret = Column(String(256))
    enabled = Column(Boolean, default=True)


class Domain(Base):
    """A user-purchased domain via a registrar (Namecheap, etc).

    This didn't exist before — registrars.py's list/get endpoints were
    stubs that claimed to "query the zones table" for this, but Zone has
    no owner/expiry/purchase concept at all. This is the actual record.
    """

    __tablename__ = "domains"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(128), nullable=False, index=True)
    name = Column(String(256), unique=True, nullable=False)
    registrar_name = Column(String(64), nullable=False)
    years = Column(Integer, default=1)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    status = Column(String(32), default="active")  # active, pending, expired, transfer_pending
    order_id = Column(String(128))
    charge_transaction_id = Column(String(128))
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
