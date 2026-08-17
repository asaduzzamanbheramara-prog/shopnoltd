"""
app/gateway_admin.py

Adds runtime activate/deactivate for payment gateways on top of the existing
credential-based `enabled` flag in config.py. A gateway is "effectively live"
only if BOTH are true: real credentials are configured AND it hasn't been
administratively disabled.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import Session

from app.database import Base
from app.gateways import REGISTRY


class GatewayOverride(Base):
    __tablename__ = "gateway_overrides"

    name = Column(String, primary_key=True)
    admin_disabled = Column(Boolean, default=False, nullable=False)
    note = Column(Text, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def is_effectively_live(db: Session, name: str) -> bool:
    gw = REGISTRY.get(name)
    if gw is None or not gw.enabled:
        return False
    override = db.query(GatewayOverride).filter(GatewayOverride.name == name).first()
    if override and override.admin_disabled:
        return False
    return True


def set_gateway_enabled(
    db: Session, name: str, enabled: bool, actor: str, note: str | None = None
) -> GatewayOverride:
    if name not in REGISTRY:
        raise KeyError(f"Unknown gateway '{name}'. Available: {list(REGISTRY)}")
    override = db.query(GatewayOverride).filter(GatewayOverride.name == name).first()
    if not override:
        override = GatewayOverride(name=name)
        db.add(override)
    override.admin_disabled = not enabled
    override.note = note
    override.updated_by = actor
    override.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(override)
    return override


def list_gateway_status(db: Session) -> list[dict]:
    overrides = {o.name: o for o in db.query(GatewayOverride).all()}
    out = []
    for name, gw in REGISTRY.items():
        override = overrides.get(name)
        out.append(
            {
                "name": name,
                "credentials_configured": gw.enabled,
                "admin_disabled": bool(override.admin_disabled) if override else False,
                "effectively_live": is_effectively_live(db, name),
                "note": override.note if override else None,
                "updated_at": override.updated_at.isoformat()
                if override and override.updated_at
                else None,
            }
        )
    return out
