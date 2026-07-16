import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Integer,
    Numeric,
)
from app.database import Base


def gen_id(prefix: str):
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ----------------------------------------------------------
# USERS
# ----------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    # Matches PostgreSQL schema exactly

    id = Column(UUID(as_uuid=True), primary_key=True)

    tenant_id = Column(UUID(as_uuid=True), nullable=True)

    email = Column(String, unique=True, nullable=False)

    password_hash = Column(Text)

    role = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)


# ----------------------------------------------------------
# WALLETS
# ----------------------------------------------------------

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String, primary_key=True, default=lambda: gen_id("wal"))

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    currency = Column(String(3), default="BDT")

    balance = Column(Numeric(18, 2), default=0)

    updated_at = Column(DateTime, default=datetime.utcnow)


# ----------------------------------------------------------
# TRANSACTIONS
# ----------------------------------------------------------

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: gen_id("txn"))

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    gateway = Column(String)

    gateway_reference = Column(Text)

    amount = Column(Numeric(18, 2))

    currency = Column(String(3))

    status = Column(String)

    is_demo = Column(Boolean)

    raw_response = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ----------------------------------------------------------
# PAYMENT METHODS
# ----------------------------------------------------------

class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(String, primary_key=True, default=lambda: gen_id("pm"))

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    gateway = Column(String)

    label = Column(Text)

    gateway_token = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


# ----------------------------------------------------------
# SUBSCRIPTIONS
# ----------------------------------------------------------

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: gen_id("sub"))

    tenant_id = Column(String)

    plan = Column(String)

    status = Column(String)

    started_at = Column(DateTime)

    expires_at = Column(DateTime)


# ----------------------------------------------------------
# AUDIT LOG
# ----------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)

    action = Column(String)

    user_id = Column(String)

    details = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


class WalletLedgerEntry(Base):
    __tablename__ = "wallet_ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    currency = Column(String(3), nullable=False)
    entry_type = Column(String, nullable=False)  # deposit|deduction|fine|refund|adjustment_credit|adjustment_debit
    amount = Column(Float, nullable=False)        # signed: positive=credit, negative=debit
    balance_after = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    reference = Column(String, nullable=True)
    created_by = Column(String, nullable=True)     # admin/service actor id, if applicable
    created_at = Column(DateTime, default=datetime.utcnow)
