import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Numeric, String

from app.core.db import Base


class Rate(Base):
    __tablename__ = "rates"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    base = Column(String(8), nullable=False, index=True)
    quote = Column(String(8), nullable=False, index=True)
    rate = Column(Numeric(28, 12), nullable=False)
    source = Column(String(32), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (Index("ix_rate_pair_time", "base", "quote", "fetched_at"),)


class Conversion(Base):
    __tablename__ = "conversions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    from_currency = Column(String(8), nullable=False)
    to_currency = Column(String(8), nullable=False)
    from_amount = Column(Numeric(20, 8), nullable=False)
    to_amount = Column(Numeric(20, 8), nullable=False)
    rate = Column(Numeric(28, 12), nullable=False)
    fee = Column(Numeric(20, 8), default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
