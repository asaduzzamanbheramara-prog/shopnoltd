from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Shopnoltd Ad Service", version="0.1.0")

class ServeRequest(BaseModel):
    site_id: str = Field(min_length=8, max_length=128)
    zone_id: str = Field(min_length=8, max_length=128)
    width: int | None = Field(default=None, ge=1, le=4096)
    height: int | None = Field(default=None, ge=1, le=4096)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    language: str | None = Field(default=None, max_length=16)
    device: str | None = Field(default=None, max_length=32)

@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status":"ok","service":"ad-service"}

@app.get("/readyz", include_in_schema=False)
async def readyz():
    return {"status":"ready","service":"ad-service"}

@app.get("/v1/network")
async def network_info():
    return {
        "service":"shopnoltd-ad-network",
        "mode":"publisher-authorized",
        "status":"foundation",
        "supported_pricing":["CPM","CPC","CPA","FLAT"],
        "inventory_requires_site_verification":True
    }

@app.post("/v1/serve")
async def serve(req: ServeRequest):
    # Deliberately no fallback creative: until inventory, campaign, budget,
    # consent and eligibility records exist, the safe response is no-fill.
    return {"fill":False,"reason":"NO_ELIGIBLE_CAMPAIGN","site_id":req.site_id,"zone_id":req.zone_id}
