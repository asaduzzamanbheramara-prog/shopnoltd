from sqlalchemy import Column, String, DateTime, Integer, Boolean
import uuid
from datetime import datetime
from app.core.db import Base
class Zone(Base):
    __tablename__ = "zones"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), unique=True, nullable=False)
    kind = Column(String(16), default="MASTER")  # MASTER, SLAVE, NATIVE
    ttl = Column(Integer, default=3600)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class Record(Base):
    __tablename__ = "records"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    type = Column(String(16), nullable=False)  # A, AAAA, CNAME, MX, TXT, NS, SRV
    content = Column(String(1024), nullable=False)
    ttl = Column(Integer, default=3600)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
class Registrar(Base):
    __tablename__ = "registrars"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(64), nullable=False)  # namecheap, porkbun, cloudflare
    api_key = Column(String(256))
    api_secret = Column(String(256))
    enabled = Column(Boolean, default=True)
