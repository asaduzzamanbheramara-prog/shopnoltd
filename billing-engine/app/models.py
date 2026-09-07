import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)

from app.database import Base


def gen_id(prefix: str):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("usr"))
    keycloak_id = Column(String(64), nullable=True)
    email = Column(String(256), unique=True, nullable=False)
    name = Column(String(256))
    tenant_id = Column(String(64), nullable=True)
    roles = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=lambda: gen_id("wal"))
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    currency = Column(String(3), default="BDT")
    balance = Column(Numeric(20, 8), default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: gen_id("txn"))
    user_id = Column(String(64), ForeignKey("users.id"))
    gateway = Column(String)
    gateway_reference = Column(Text)
    amount = Column(Numeric(20, 8))
    currency = Column(String(3))
    status = Column(String)
    is_demo = Column(Boolean)
    raw_response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(String, primary_key=True, default=lambda: gen_id("pm"))
    user_id = Column(String(64), ForeignKey("users.id"))
    gateway = Column(String)
    label = Column(Text)
    gateway_token = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: gen_id("sub"))
    tenant_id = Column(String)
    plan = Column(String)
    status = Column(String)
    started_at = Column(DateTime)
    expires_at = Column(DateTime)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String)
    user_id = Column(String)
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class WalletLedgerEntry(Base):
    __tablename__ = "wallet_ledger_entries"

    id = Column(String(64), primary_key=True, default=lambda: gen_id("led"))
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    currency = Column(String(3), nullable=False)
    entry_type = Column(String, nullable=False)
    # Financial amounts are exact decimals; never use binary floating point here.
    amount = Column(Numeric(20, 8), nullable=False)
    balance_after = Column(Numeric(20, 8), nullable=False)
    reason = Column(Text, nullable=False)
    reference = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
