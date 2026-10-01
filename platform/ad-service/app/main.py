from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db

app = FastAPI(title="Shopnoltd Ad Service", version="0.2.0")

@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok", "service": "ad-service"}

@app.get("/readyz", include_in_schema=False)
async def readyz(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ready", "service": "ad-service", "database": "ok"}

@app.get("/v1/network")
async def network_info():
    return {
        "service": "shopnoltd-ad-network",
        "mode": "publisher-authorized",
        "status": "database-foundation",
        "supported_pricing": ["CPM", "CPC", "CPA", "FLAT"],
        "inventory_requires_site_verification": True,
        "paid_serving_enabled": False,
    }

@app.get("/v1/db-check")
async def db_check(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT current_database() AS database"))
    return {"database": result.scalar_one(), "status": "ok"}

@app.post("/v1/serve")
async def serve(site_id: str, zone_id: str, db: AsyncSession = Depends(get_db)):
    # Fail closed. Even verified inventory receives no paid creative until
    # authenticated CRUD, funding/ledger integration, consent and fraud
    # controls are implemented and tested.
    eligible = await db.scalar(text("""
      SELECT 1
      FROM ad_zones z
      JOIN publisher_sites s ON s.id=z.site_id
      JOIN publishers p ON p.id=s.publisher_id
      WHERE z.id=:zone_id AND s.id=:site_id
        AND z.status='active'
        AND s.verification_status='verified'
        AND p.status='approved'
      LIMIT 1
    """), {"site_id": site_id, "zone_id": zone_id})
    if not eligible:
        return {"fill": False, "reason": "INVENTORY_NOT_ELIGIBLE"}
    return {"fill": False, "reason": "PAID_SERVING_NOT_ENABLED"}
