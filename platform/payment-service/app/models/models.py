"""SQLAlchemy models for payments."""
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid, enum
from datetime import datetime
from app.core.db import Base

class TxStatus(str, enum.Enum): pending = "pending"; processing = "processing"; completed = "completed"; failed = "failed"; cancelled = "cancelled"; requires_approval = "requires_approval"
class TxType(str, enum.Enum): deposit = "deposit"; withdrawal = "withdrawal"; transfer = "transfer"; fee = "fee"; refund = "refund"; exchange = "exchange"; subscription = "subscription"
class PaymentMethod(str, enum.Enum): stripe = "stripe"; paypal = "paypal"; binance = "binance"; payeer = "payeer"; bkash = "bkash"; nagad = "nagad"; rocket = "rocket"; bank = "bank"; manual = "manual"; btc = "btc"; eth = "eth"; usdt = "usdt"; bnb = "bnb"; sol = "sol"; trx = "trx"

class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    currency = Column(String(8), nullable=False)
    balance = Column(Numeric(20, 8), default=0, nullable=False)
    frozen = Column(Numeric(20, 8), default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (Index("ix_wallet_user_currency", "user_id", "currency", unique=True),)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False)
    type = Column(Enum(TxType), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(TxStatus), default=TxStatus.pending, nullable=False, index=True)
    amount = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), default=0, nullable=False)
    currency = Column(String(8), nullable=False)
    external_id = Column(String(128), index=True, nullable=True)
    reference = Column(String(128), nullable=True)
    meta = Column(JSONB, default=dict)
    approved_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

