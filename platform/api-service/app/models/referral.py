import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from app.core.db import Base


class ReferralCode(Base):
    __tablename__ = "referral_codes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id = Column(String(128), nullable=False, unique=True, index=True)
    code = Column(String(32), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Referral(Base):
    __tablename__ = "referrals"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    referrer_id = Column(String(128), nullable=False, index=True)
    referred_id = Column(String(128), nullable=False, unique=True, index=True)
    referral_code = Column(String(32), nullable=False, index=True)
    source = Column(String(24), nullable=False, default="direct")
    claimed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    active = Column(Integer, nullable=False, default=1)
    __table_args__ = (Index("ix_referral_pair", "referrer_id", "referred_id", unique=True),)


class ReferralPolicy(Base):
    __tablename__ = "referral_policies"
    tenant_id = Column(String(64), primary_key=True)
    mode = Column(String(16), nullable=False, default="percent")
    percent = Column(Numeric(12, 6), nullable=False, default=5)
    fixed_amount = Column(Numeric(20, 8), nullable=False, default=0)
    max_amount = Column(Numeric(20, 8), nullable=True)
    currency = Column(String(16), nullable=False, default="MATCH_TASK")
    enabled = Column(Integer, nullable=False, default=1)
    all_users_can_refer = Column(Integer, nullable=False, default=1)
    fallback_referrer_id = Column(String(128), nullable=False, default="admin_office")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReferralReward(Base):
    __tablename__ = "referral_rewards"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    referral_id = Column(String(64), ForeignKey("referrals.id", ondelete="CASCADE"), nullable=False, index=True)
    referred_id = Column(String(128), nullable=False, index=True)
    referrer_id = Column(String(128), nullable=False, index=True)
    work_id = Column(String(64), ForeignKey("works.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(String(64), ForeignKey("work_submissions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    base_amount = Column(Numeric(20, 8), nullable=False)
    reward_amount = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(16), nullable=False)
    status = Column(String(24), nullable=False, default="pending", index=True)
    payment_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    settled_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)
