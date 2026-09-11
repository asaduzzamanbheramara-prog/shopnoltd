"""SQLAlchemy models for payments."""

import enum
import uuid
from datetime import datetime

from app.core.db import Base
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID


class TxStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    requires_approval = "requires_approval"


class TxType(str, enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    transfer = "transfer"
    fee = "fee"
    refund = "refund"
    exchange = "exchange"
    subscription = "subscription"


class PaymentMethod(str, enum.Enum):
    transfer = "transfer"
    stripe = "stripe"
    paypal = "paypal"
    binance = "binance"
    payeer = "payeer"
    bkash = "bkash"
    nagad = "nagad"
    rocket = "rocket"
    bank = "bank"
    manual = "manual"
    btc = "btc"
    eth = "eth"
    usdt = "usdt"
    bnb = "bnb"
    sol = "sol"
    trx = "trx"
    razorpay = "razorpay"
    sslcommerz = "sslcommerz"
    moneybag = "moneybag"
    payoneer = "payoneer"


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
    __table_args__ = (Index("ix_wallet_tenant_user_currency", "tenant_id", "user_id", "currency", unique=True),)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False)
    type = Column(Enum(TxType), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(TxStatus), default=TxStatus.pending, nullable=False, index=True)
    amount = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), default=0, nullable=False)
    currency = Column(String(8), nullable=False)
    external_id = Column(String(128), index=True, nullable=True)
    reference = Column(String(128), nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    meta = Column(JSONB, default=dict)
    approved_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    __table_args__ = (
        Index("uq_transaction_deposit_idempotency", "tenant_id", "user_id", "type", "idempotency_key", unique=True),
        Index("ix_tx_external_method", "external_id", "method"),
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(32), nullable=False)
    event_key = Column(String(128), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)
    status = Column(String(32), nullable=False, default="received")
    payload_hash = Column(String(64), nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    __table_args__ = (Index("uq_webhook_provider_event", "provider", "event_key", unique=True),)


class DirectPaymentAccount(Base):
    __tablename__ = "direct_payment_accounts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    provider = Column(String(16), nullable=False, index=True)
    account_type = Column(String(16), nullable=False)  # personal, agent, merchant
    account_number = Column(String(32), nullable=False)
    display_name = Column(String(128), nullable=True)
    currency = Column(String(8), nullable=False, default="BDT")
    status = Column(String(16), nullable=False, default="active")
    verification_mode = Column(String(32), nullable=False, default="manual")
    instructions = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("uq_direct_account_number", "tenant_id", "provider", "account_number", unique=True),)


class DirectPaymentIntent(Base):
    __tablename__ = "direct_payment_intents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    order_id = Column(String(128), nullable=True, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("direct_payment_accounts.id"), nullable=False)
    provider = Column(String(16), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(8), nullable=False)
    expected_reference = Column(String(64), nullable=False, unique=True)
    status = Column(String(24), nullable=False, default="created", index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DirectPaymentSubmission(Base):
    __tablename__ = "direct_payment_submissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("direct_payment_intents.id"), nullable=False, index=True)
    provider = Column(String(16), nullable=False)
    txid = Column(String(128), nullable=False)
    sender_number = Column(String(32), nullable=True)
    amount_claimed = Column(Numeric(20, 8), nullable=False)
    raw_evidence = Column(JSONB, default=dict)
    verification_data = Column(JSONB, nullable=True)
    status = Column(String(24), nullable=False, default="submitted", index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("uq_direct_submission_provider_txid", "provider", "txid", unique=True),)
