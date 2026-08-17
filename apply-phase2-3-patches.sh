#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")" 2>/dev/null || true

echo "=== Phase 2/3 patch: billing-engine gateway toggles + auth-service OAuth ==="
echo

if [ ! -d "billing-engine" ] || [ ! -d "platform/auth-service" ]; then
  echo "ERROR: run this from the shopnoltd repo root (/mnt/c/Users/asadu/PROJECTS/shopnoltd)."
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. billing-engine/app/gateway_admin.py  (new file)
# ---------------------------------------------------------------------------
echo "1) Writing billing-engine/app/gateway_admin.py"
cat > billing-engine/app/gateway_admin.py <<'PYEOF'
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


def set_gateway_enabled(db: Session, name: str, enabled: bool, actor: str, note: str | None = None) -> GatewayOverride:
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
        out.append({
            "name": name,
            "credentials_configured": gw.enabled,
            "admin_disabled": bool(override.admin_disabled) if override else False,
            "effectively_live": is_effectively_live(db, name),
            "note": override.note if override else None,
            "updated_at": override.updated_at.isoformat() if override and override.updated_at else None,
        })
    return out
PYEOF

# ---------------------------------------------------------------------------
# 2. billing-engine/app/main.py -- exact string-replacement patches
# ---------------------------------------------------------------------------
echo "2) Patching billing-engine/app/main.py"
python3 <<'PYEOF'
import re, sys

path = "billing-engine/app/main.py"
with open(path) as f:
    src = f.read()

orig = src

# --- patch A: add import ---
old_import = "from app.security import require_internal_key\n"
new_import = old_import + "from app.gateway_admin import is_effectively_live, list_gateway_status, set_gateway_enabled\n"
if "gateway_admin" not in src:
    if old_import not in src:
        print("ABORT: import anchor not found -- main.py may have changed since last read. No changes written.")
        sys.exit(1)
    src = src.replace(old_import, new_import, 1)

# --- patch B: replace /gateways endpoint body ---
old_gateways = '''@app.get("/gateways")
def list_gateways():
    """
    Honest status of every gateway: whether real credentials are configured
    (`live: true`) or it is currently running in demo mode (`live: false`).
    """
    out = []
    for name, gw in REGISTRY.items():
        out.append(
            {
                "name": name,
                "live": gw.enabled,
                "currencies": {
                    "stripe": ["USD", "EUR", "GBP", "AUD", "CAD", "SGD", "and more"],
                    "paypal": ["USD", "EUR", "GBP", "AUD", "CAD"],
                    "razorpay": ["INR", "USD"],
                    "sslcommerz": ["BDT"],
                    "bkash": ["BDT"],
                    "nagad": ["BDT"],
                    "crypto": ["BTC", "ETH", "USDT", "and ~200 more via NOWPayments"],
                }.get(name, []),
            }
        )
    return {"gateways": out}'''

new_gateways = '''@app.get("/gateways")
def list_gateways(db: Session = Depends(get_db)):
    """
    Honest status of every gateway: whether real credentials are configured,
    whether an admin has disabled it at runtime, and the combined effective
    live status.
    """
    status = {s["name"]: s for s in list_gateway_status(db)}
    out = []
    for name, gw in REGISTRY.items():
        s = status[name]
        out.append(
            {
                "name": name,
                "live": s["effectively_live"],
                "credentials_configured": s["credentials_configured"],
                "admin_disabled": s["admin_disabled"],
                "currencies": {
                    "stripe": ["USD", "EUR", "GBP", "AUD", "CAD", "SGD", "and more"],
                    "paypal": ["USD", "EUR", "GBP", "AUD", "CAD"],
                    "razorpay": ["INR", "USD"],
                    "sslcommerz": ["BDT"],
                    "bkash": ["BDT"],
                    "nagad": ["BDT"],
                    "crypto": ["BTC", "ETH", "USDT", "and ~200 more via NOWPayments"],
                }.get(name, []),
            }
        )
    return {"gateways": out}'''

if old_gateways in orig:
    src = src.replace(old_gateways, new_gateways, 1)
elif new_gateways not in src:
    print("ABORT: /gateways endpoint anchor not found -- main.py may have changed. No changes written.")
    sys.exit(1)

# --- patch C: block checkout on admin-disabled gateway ---
old_checkout_start = '''    try:
        gw = get_gateway(req.gateway)
    except KeyError as e:
        raise HTTPException(400, str(e)) from e

    user = get_or_create_user(db, req.customer_email)'''

new_checkout_start = '''    try:
        gw = get_gateway(req.gateway)
    except KeyError as e:
        raise HTTPException(400, str(e)) from e

    if gw.enabled and not is_effectively_live(db, req.gateway):
        raise HTTPException(503, f"Gateway '{req.gateway}' is currently disabled by an administrator.")

    user = get_or_create_user(db, req.customer_email)'''

if old_checkout_start in orig:
    src = src.replace(old_checkout_start, new_checkout_start, 1)
elif new_checkout_start not in src:
    print("ABORT: /checkout anchor not found -- main.py may have changed. No changes written.")
    sys.exit(1)

# --- patch D: append admin endpoints at end of file, guarded ---
admin_block = '''


class GatewayToggleRequest(BaseModel):
    enabled: bool
    note: str | None = None
    actor: str = "admin"


@app.post("/admin/gateways/{name}/toggle", dependencies=[Depends(require_internal_key)])
def toggle_gateway(name: str, req: GatewayToggleRequest, db: Session = Depends(get_db)):
    try:
        override = set_gateway_enabled(db, name, req.enabled, req.actor, req.note)
    except KeyError as e:
        raise HTTPException(400, str(e)) from e
    log_action(db, "gateway_toggled", req.actor, {"gateway": name, "enabled": req.enabled})
    return {
        "gateway": name,
        "admin_disabled": override.admin_disabled,
        "effectively_live": is_effectively_live(db, name),
    }


@app.get("/admin/gateways", dependencies=[Depends(require_internal_key)])
def admin_gateway_status(db: Session = Depends(get_db)):
    return {"gateways": list_gateway_status(db)}
'''

if "def toggle_gateway(" not in src:
    src = src.rstrip("\n") + admin_block

if src != orig:
    with open(path, "w") as f:
        f.write(src)
    print("  billing-engine/app/main.py patched successfully.")
else:
    print("  billing-engine/app/main.py already patched, no changes needed.")
PYEOF

# ---------------------------------------------------------------------------
# 3. platform/auth-service/app/api/oauth.py  (new file)
# ---------------------------------------------------------------------------
echo "3) Writing platform/auth-service/app/api/oauth.py"
cat > platform/auth-service/app/api/oauth.py <<'PYEOF'
"""
app/api/oauth.py

Google/Facebook/GitHub login. Keycloak brokers the actual OAuth handshake
with each provider (configured as Identity Providers via
keycloak_idp_setup.sh); this router redirects the browser to Keycloak and,
on the way back, exchanges the code exactly like the existing password
login() does, producing the same LoginOut shape and Session record.
"""
import base64
import json as _json
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.models import Session as SessionModel

router = APIRouter()

SUPPORTED_PROVIDERS = {"google", "facebook", "github"}


async def db():
    async with SessionLocal() as s:
        yield s


def _redirect_uri() -> str:
    return f"{settings.public_base_url}/api/v1/auth/oauth/callback"


@router.get("/oauth/{provider}/login")
async def oauth_login(provider: str, redirect_after: str = Query(default="/")):
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(400, f"Unsupported provider '{provider}'. Use one of {sorted(SUPPORTED_PROVIDERS)}")

    params = {
        "client_id": "shopnoltd-web",
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid profile email",
        "kc_idp_hint": provider,
        "state": redirect_after,
    }
    auth_url = (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/auth?{urlencode(params)}"
    )
    return RedirectResponse(auth_url, status_code=302)


@router.get("/oauth/callback")
async def oauth_callback(request: Request, code: str, state: str = "/", s: AsyncSession = Depends(db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "shopnoltd-web",
                "code": code,
                "redirect_uri": _redirect_uri(),
            },
        )
    if r.status_code != 200:
        raise HTTPException(401, f"OAuth code exchange failed: {r.text}")
    d = r.json()

    payload_b64 = d["access_token"].split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    claims = _json.loads(base64.urlsafe_b64decode(payload_b64))
    subject = claims.get("email", claims.get("sub"))

    sess = SessionModel(
        user_id=subject,
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        device=f"oauth:{claims.get('idp', 'unknown')}" if claims.get("idp") else "oauth",
    )
    s.add(sess)
    await s.commit()

    frontend_target = (
        f"{state}#access_token={d['access_token']}&refresh_token={d['refresh_token']}"
        f"&expires_in={d.get('expires_in', 300)}&session_id={sess.id}"
    )
    return RedirectResponse(frontend_target, status_code=302)
PYEOF

# ---------------------------------------------------------------------------
# 4. platform/auth-service/app/core/config.py -- append public_base_url
# ---------------------------------------------------------------------------
echo "4) Patching platform/auth-service/app/core/config.py"
python3 <<'PYEOF'
path = "platform/auth-service/app/core/config.py"
with open(path) as f:
    src = f.read()

if "public_base_url" not in src:
    old = '    keycloak_audience: str = "auth-service"\n'
    if old not in src:
        print("ABORT: config.py anchor not found -- file may have changed. No changes written.")
    else:
        new = old + '    public_base_url: str = "https://auth.shopnoltd.dpdns.org"  # CONFIRM this matches your real ingress host\n'
        src = src.replace(old, new, 1)
        with open(path, "w") as f:
            f.write(src)
        print("  config.py patched -- public_base_url added with a guessed default, CONFIRM/CORRECT it.")
else:
    print("  config.py already has public_base_url, no changes needed.")
PYEOF

# ---------------------------------------------------------------------------
# 5. platform/auth-service/app/main.py -- NOT auto-patched (unseen content)
# ---------------------------------------------------------------------------
echo "5) platform/auth-service/app/main.py — showing its current router registrations for you to extend manually:"
grep -n "include_router\|^from app.api\|^app = FastAPI" platform/auth-service/app/main.py || echo "  (pattern not found -- paste full main.py content back so I can give an exact patch)"
echo
echo "   Add these two lines near the other router registrations:"
echo '     from app.api import oauth'
echo '     app.include_router(oauth.router, prefix="/api/v1/auth")'

echo
echo "=== Done. Review with: git diff billing-engine/app/main.py platform/auth-service/app/core/config.py ==="
echo "=== Then: git status ==="
