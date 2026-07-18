import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.models.models import Index

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.post("", status_code=201)
async def create(name: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    i = Index(tenant_id=user.get("tenant_id", "default"), name=name)
    s.add(i)
    await s.commit()
    try:
        async with httpx.AsyncClient() as c:
            await c.put(
                f"{settings.opensearch_url}/{name}",
                auth=(settings.opensearch_user, settings.opensearch_password),
                json={
                    "mappings": {
                        "properties": {
                            "title": {"type": "text"},
                            "body": {"type": "text"},
                            "tenant_id": {"type": "keyword"},
                        }
                    }
                },
                timeout=10,
            )
    except Exception:
        pass
    return {"id": i.id, "name": i.name}


@router.post("/doc")
async def add_doc(index: str, id: str, body: dict, s: AsyncSession = Depends(db)):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.put(
                f"{settings.opensearch_url}/{index}/_doc/{id}",
                auth=(settings.opensearch_user, settings.opensearch_password),
                json=body,
                timeout=10,
            )
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(500, f"opensearch: {e}")
    return {"ok": True}
