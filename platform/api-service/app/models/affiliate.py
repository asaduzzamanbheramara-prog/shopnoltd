from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AffiliateOffer(Base):
    __tablename__ = "affiliate_offers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    network_offer_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    tracking_url: Mapped[str] = mapped_column(Text, nullable=False)
    network_payout: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    user_share_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    incentive_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    countries: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AffiliateClick(Base):
    __tablename__ = "affiliate_clicks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("affiliate_offers.id"), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AffiliateConversion(Base):
    __tablename__ = "affiliate_conversions"
    txn: Mapped[str] = mapped_column(String(200), primary_key=True)
    click_id: Mapped[str] = mapped_column(ForeignKey("affiliate_clicks.id"), nullable=False, index=True)
    network_payout: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    user_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
