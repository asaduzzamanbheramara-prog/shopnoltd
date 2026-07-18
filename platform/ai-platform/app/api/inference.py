import httpx
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import verify_token
from app.schemas.schemas import InferIn, InferOut

router = APIRouter()
bearer = HTTPBearer()


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", response_model=InferOut)
async def infer(body: InferIn, user=Depends(current_user)):
    """Call local LLM (Ollama/vLLM) or fall back to stub."""
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(
                f"{settings.llm_url}/api/generate",
                json={"model": settings.llm_model, "prompt": body.prompt, "stream": False},
            )
        r.raise_for_status()
        d = r.json()
        return InferOut(
            response=d.get("response", ""), model=settings.llm_model, tokens=d.get("eval_count", 0)
        )
    except Exception:
        # Stub for when no LLM is running yet
        return InferOut(
            response=f"[Stub: would call {settings.llm_model}]: {body.prompt[:200]}",
            model=settings.llm_model,
            tokens=0,
        )
