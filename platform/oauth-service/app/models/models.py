import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, LargeBinary, String, Text, UniqueConstraint

from app.core.db import Base


class UserMirror(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    keycloak_id = Column(String(64), unique=True, nullable=False, index=True)
    # Real Keycloak identities use their Keycloak UUID; imported identities use a synthetic import:<uuid> value.
    identity_source = Column(String(32), nullable=False, default="keycloak", index=True)
    source_workbook_id = Column(String(64), index=True)
    source_sheet = Column(String(255))
    source_row = Column(Integer)
    email = Column(String(256), unique=True, nullable=False)
    name = Column(String(256))
    tenant_id = Column(String(64), index=True)
    roles = Column(JSON, default=list)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    first_name = Column(String(128))
    last_name = Column(String(128))
    display_name = Column(String(256))
    gender = Column(String(64))
    birth_month = Column(String(32))
    birth_day = Column(Integer)
    birth_year = Column(Integer)
    phone = Column(String(64))
    recovery_email = Column(String(256))
    avatar_url = Column(String(1024))
    bio = Column(Text)
    source = Column(String(64), nullable=False, default="registration")
    profile_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ImportedWorkbook(Base):
    __tablename__ = "imported_workbooks"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(512), nullable=False)
    source_path = Column(String(1024))
    sha256 = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(32), nullable=False, default="completed")
    sheet_count = Column(Integer, default=0)
    row_count = Column(Integer, default=0)
    imported_at = Column(DateTime, default=datetime.utcnow)


class ImportedExcelRow(Base):
    __tablename__ = "imported_excel_rows"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    workbook_id = Column(String(64), nullable=False, index=True)
    sheet_name = Column(String(255), nullable=False, index=True)
    source_row = Column(Integer, nullable=False)
    values = Column(JSON, nullable=False, default=dict)
    encrypted_source = Column(LargeBinary, nullable=False)
    normalized_type = Column(String(64), index=True)
    normalized_key = Column(String(512), index=True)
    linked_user_id = Column(String(64), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("workbook_id", "sheet_name", "source_row", name="uq_excel_row_source"),)


class SecretVaultEntry(Base):
    __tablename__ = "secret_vault_entries"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_type = Column(String(64), nullable=False, index=True)
    owner_id = Column(String(64), nullable=False, index=True)
    provider = Column(String(64), nullable=False, index=True)
    secret_type = Column(String(64), nullable=False)
    encrypted_value = Column(LargeBinary, nullable=False)
    key_version = Column(String(32), nullable=False, default="v1")
    source_workbook_id = Column(String(64), index=True)
    source_sheet = Column(String(255))
    source_row = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, nullable=False)
    subdomain = Column(String(128), unique=True, nullable=False)
    plan = Column(String(64), default="free")
    settings = Column(JSON, default=dict)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), index=True, nullable=False)
    keycloak_id = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), nullable=False)
    name = Column(String(256))
    phone = Column(String(64))
    billing_address = Column(JSON, default=dict)
    preferences = Column(JSON, default=dict)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
