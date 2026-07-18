from fastapi import APIRouter

from app.services.services import health

router = APIRouter()


@router.get("/services")
async def services():
    return await health()


@router.get("/cluster")
async def cluster():
    h = await health()
    return {"status": "ok" if all(v == "ok" for v in h.values()) else "degraded", "services": h}
