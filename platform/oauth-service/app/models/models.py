from sqlalchemy import Column, String, DateTime, JSON, Boolean
import uuid
from datetime import datetime
from app.core.db import Base
class UserMirror(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    keycloak_id = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False)
    name = Column(String(256))
    tenant_id = Column(String(64), index=True)
    roles = Column(JSON, default=list)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, nullable=False)
    subdomain = Column(String(128), unique=True, nullable=False)
    plan = Column(String(64), default="free")
    settings = Column(JSON, default=dict)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
