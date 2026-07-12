from sqlalchemy import Column, String, DateTime, Integer, Float, Text
import uuid
from datetime import datetime
from app.core.db import Base
class Donor(Base):
    __tablename__ = "donors"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    email = Column(String(256), index=True)
    phone = Column(String(32))
    is_anonymous = Column(Integer, default=0)
    total_donated = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
class Donation(Base):
    __tablename__ = "donations"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    donor_id = Column(String(64), nullable=False, index=True)
    campaign_id = Column(String(64), index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    method = Column(String(32))  # stripe, paypal, bkash, bank, manual, crypto
    status = Column(String(16), default="pending")  # pending, completed, refunded
    receipt_no = Column(String(32))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    goal_amount = Column(Float, default=0)
    raised_amount = Column(Float, default=0)
    starts_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime)
    active = Column(Integer, default=1)
class Grant(Base):
    __tablename__ = "grants"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    funder = Column(String(256))
    amount = Column(Float, default=0)
    currency = Column(String(8), default="USD")
    status = Column(String(16), default="open")  # open, awarded, closed
    description = Column(Text)
    deadline = Column(DateTime)
class Beneficiary(Base):
    __tablename__ = "beneficiaries"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    type = Column(String(32))  # individual, family, community
    location = Column(String(256))
    notes = Column(Text)
    aid_received = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
