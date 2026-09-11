"""Direct-number payment models.

Customer-submitted TxIDs are evidence only and cannot credit a wallet without
provider verification or an authenticated admin review.
"""

import enum
import uuid
from datetime import datetime

from app.core.db import Base
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID


class DirectAccountType(str, enum.Enum):
    personal = "personal"
    agent = "agent"
    merchant = "merchant"


class DirectVerificationMode(str, enum.Enum):
    manual = "manual"
    authorized_api = "authorized_api"
    authorized_feed = "authorized_feed"


class DirectAccountStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"


class DirectPaymentStatus(str, enum.Enum):
    created = "created"
    awaiting_payment = "awaiting_payment"
    submitted = "submitted"
    verifying = "verifying"
    verified = "verified"
    failed = "failed"
    expired = "expired"
    cancelled = "cancelled"
    manual_review = "manual_review"


class DirectPaymentAccount(Base):
    __tablename__ = "direct_payment_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    provider = Column(String(32), nullable=False)
    account_type = Column(Enum(DirectAccountType), nullable=False)
    account_number = Column(String(32), nullable=False)
    display_name = Column(String(128), nullable=False)
    currency = Column(String(8), nullable=False, default="BDT")
    verification_mode = Column(Enum(DirectVerificationMode), nullable=False, default=DirectVerificationMode.manual)
    status = Column(Enum(DirectAccountStatus), nullable=False, default=DirectAccountStatus.active)
    instructions = Column(Text, nullable=True)
    metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("ix_direct_account_tenant_provider_currency", "tenant_id", "provider", "currency"),
    )


class DirectPaymentIntent(Base):
    __tablename__ = "direct_payment_intents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    order_id = Column(String(128), nullable=True, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("direct_payment_accounts.id"), nullable=False)
    provider = Column(String(32), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(8), nullable=False)
    expected_reference = Column(String(128), nullable=False, unique=True)
    status = Column(Enum(DirectPaymentStatus), nullable=False, default=DirectPaymentStatus.created, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DirectPaymentSubmission(Base):
    __tablename__ = "direct_payment_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("direct_payment_intents.id'), nullable=False, index=True)
    provider = Column(String(32), nullable=False)
    sender_number = Column(String(32), nullable=True)
    transaction_id = Column(String(128), nullable=False)
    submitted_amount = Column(Numeric(20, 8), nullable=False)
    submitted_currency = Column(String(8), nullable=False)
    evidence = Column(JSONB, default=dict)
    status = Column(Enum(DirectPaymentStatus), nullable=False, default=DirectPaymentStatus.submitted, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    __table_args__ = (
        Index("uq_direct_submission_provider_tx", "provider", "transaction_id", unique=True),
    )
