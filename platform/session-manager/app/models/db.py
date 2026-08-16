"""SQLAlchemy models + engine setup (Postgres)."""

import os
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/session_manager",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Proxy(Base):
    __tablename__ = "proxies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column(String, nullable=False)
    server = Column(String, nullable=False)  # host:port
    username = Column(String, nullable=True)
    password_encrypted = Column(String, nullable=True)
    country = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profiles = relationship("Profile", back_populates="proxy")


class Profile(Base):
    """
    A named, persistent browser profile. Each profile owns its own
    Playwright user-data-dir, so cookies/localStorage/cache never bleed
    across profiles. This is standard session isolation — not fingerprint
    randomization or anti-detection spoofing.
    """

    __tablename__ = "profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    purpose = Column(String, nullable=False, default="qa")  # qa | staff | scraping
    owner = Column(String, nullable=True)  # staff username/email
    notes = Column(Text, nullable=True)
    proxy_id = Column(UUID(as_uuid=True), ForeignKey("proxies.id"), nullable=True)
    user_data_dir = Column(String, nullable=False)  # relative path under storage volume
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    proxy = relationship("Proxy", back_populates="profiles")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
