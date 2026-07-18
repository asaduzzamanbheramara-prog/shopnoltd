import httpx
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import verify_token
from app.schemas.schemas import SearchIn

router = APIRouter()
bearer = HTTPBearer()


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("")
async def search(body: SearchIn, user=Depends(current_user)):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                f"{settings.opensearch_url}/{body.index}/_search",
                auth=(settings.opensearch_user, settings.opensearch_password),
                json={
                    "query": {
                        "multi_match": {
                            "query": body.query,
                            "fields": body.fields or ["title^2", "body"],
                        }
                    },
                    "size": body.size,
                },
                timeout=10,
            )
        r.raise_for_status()
        d = r.json()
        return {
            "total": d.get("hits", {}).get("total", {}).get("value", 0),
            "hits": [h["_source"] for h in d.get("hits", {}).get("hits", [])],
        }
    except Exception as e:
        return {"total": 0, "hits": [], "error": str(e)}
