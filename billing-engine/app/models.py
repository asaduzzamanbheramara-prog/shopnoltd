import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, ForeignKey, Text, Integer
from app.database import Base


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: gen_id("usr"))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(String, primary_key=True, default=lambda: gen_id("wal"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    currency = Column(String(3), nullable=False, default="BDT")
    balance = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: gen_id("txn"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    gateway = Column(String, nullable=False, index=True)
    gateway_reference = Column(String, nullable=True, index=True)  # session/order/payment ID at the gateway
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending|completed|failed|refunded
    is_demo = Column(Boolean, nullable=False, default=False)
    raw_response = Column(Text, nullable=True)  # JSON string of the last gateway response, for audit/debugging
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    id = Column(String, primary_key=True, default=lambda: gen_id("pm"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    gateway = Column(String, nullable=False)
    label = Column(String, nullable=True)  # e.g. "Visa ****4242" or "bKash 01XXXXXXXXX"
    gateway_token = Column(String, nullable=True)  # gateway-side token/customer id, never raw card/PIN data
    created_at = Column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True, default=lambda: gen_id("sub"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    plan = Column(String, nullable=False)
    gateway = Column(String, nullable=False)
    gateway_subscription_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")  # active|canceled|past_due
    current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String, nullable=False)
    user_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
