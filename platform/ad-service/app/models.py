from datetime import datetime
from uuid import UUID
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass

class Advertiser(Base):
    __tablename__="advertisers"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(255), index=True)
    legal_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Publisher(Base):
    __tablename__="publishers"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    revenue_share_bps: Mapped[int] = mapped_column(Integer, default=7000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class PublisherSite(Base):
    __tablename__="publisher_sites"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    publisher_id: Mapped[UUID] = mapped_column(ForeignKey("publishers.id"), index=True)
    domain: Mapped[str] = mapped_column(Text)
    verification_method: Mapped[str] = mapped_column(String(32), default="pending")
    verification_status: Mapped[str] = mapped_column(String(32), default="pending")
    verification_token: Mapped[str] = mapped_column(String(128), unique=True)

class AdZone(Base):
    __tablename__="ad_zones"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    site_id: Mapped[UUID] = mapped_column(ForeignKey("publisher_sites.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="active")

class Campaign(Base):
    __tablename__="campaigns"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    advertiser_id: Mapped[UUID] = mapped_column(ForeignKey("advertisers.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    pricing_model: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    budget_minor: Mapped[int] = mapped_column(BigInteger)
    spent_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

class Creative(Base):
    __tablename__="creatives"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    asset_url: Mapped[str] = mapped_column(Text)
    click_url: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")

class AdDelivery(Base):
    __tablename__="ad_deliveries"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), index=True)
    site_id: Mapped[UUID] = mapped_column(ForeignKey("publisher_sites.id"))
    zone_id: Mapped[UUID] = mapped_column(ForeignKey("ad_zones.id"))
    campaign_id: Mapped[UUID] = mapped_column(ForeignKey("campaigns.id"))
    creative_id: Mapped[UUID] = mapped_column(ForeignKey("creatives.id"))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    impression_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    click_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
