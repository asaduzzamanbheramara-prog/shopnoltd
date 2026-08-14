from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import current_user
from app.db.session import get_db
from app.schemas.schemas import InferIn, InferOut
from app.services.model_router import (
    ModelNotAvailableError,
    run_inference,
)

router = APIRouter()


@router.post("", response_model=InferOut)
async def infer(
    body: InferIn,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await run_inference(
            db=db,
            prompt=body.prompt,
            model_name=body.model,
        )

        return InferOut(
            response=result.text,
            model=body.model or "resolved",
            tokens=result.tokens_used,
        )

    except ModelNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI inference failed: {exc}",
        ) from exc
