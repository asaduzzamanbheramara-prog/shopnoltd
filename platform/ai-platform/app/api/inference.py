import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import current_user
from app.db.models import AIModel, AIProvider
from app.db.session import get_db
from app.schemas.schemas import InferIn, InferOut
from app.services.model_router import ModelNotAvailableError, ProviderInferenceError, run_inference

router = APIRouter()


@router.get("/models")
async def list_active_models(
    _user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIModel, AIProvider)
        .join(AIProvider)
        .where(AIModel.is_active, AIProvider.is_active)
        .order_by(AIModel.is_default.desc(), AIModel.priority.asc(), AIModel.display_name.asc())
    )
    return [
        {
            "id": model.id,
            "model_name": model.model_name,
            "display_name": model.display_name,
            "provider_name": provider.name,
            "provider_type": provider.provider_type,
            "is_default": model.is_default,
            "priority": model.priority,
            "capabilities": model.capabilities,
        }
        for model, provider in result.all()
    ]


async def _stream_result(body: InferIn, db: AsyncSession):
    task = asyncio.create_task(
        run_inference(
            db=db,
            prompt=body.prompt,
            model_name=body.model,
            model_id=body.model_id,
            attachments=body.attachments,
            history=body.history,
        )
    )
    try:
        yield ": keep-alive\\n\\n"
        while not task.done():
            await asyncio.sleep(15)
            if not task.done():
                yield ": keep-alive\\n\\n"
        try:
            result, resolved_model = await task
            payload = InferOut(
                response=result.text,
                model=resolved_model.model_name,
                tokens=result.tokens_used,
            ).model_dump(mode="json")
            yield f"event: result\\ndata: {json.dumps(payload)}\\n\\n"
        except ProviderInferenceError as exc:
            yield f"event: error\\ndata: {json.dumps({'status': exc.status_code, 'detail': str(exc)})}\\n\\n"
        except ModelNotAvailableError as exc:
            yield f"event: error\\ndata: {json.dumps({'status': 503, 'detail': str(exc)})}\\n\\n"
        except Exception as exc:
            yield f"event: error\\ndata: {json.dumps({'status': 502, 'detail': f'AI inference failed: {exc}'})}\\n\\n"
    except asyncio.CancelledError:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise


@router.post("/stream")
async def infer_stream(
    body: InferIn,
    _user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        _stream_result(body, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@router.post("", response_model=InferOut)
async def infer(
    body: InferIn,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result, resolved_model = await run_inference(
            db=db,
            prompt=body.prompt,
            model_name=body.model,
            model_id=body.model_id,
            attachments=body.attachments,
            history=body.history,
        )
        return InferOut(
            response=result.text,
            model=resolved_model.model_name,
            tokens=result.tokens_used,
        )
    except ProviderInferenceError as exc:
        code = exc.status_code if 400 <= exc.status_code < 500 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except ModelNotAvailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI inference failed: {exc}") from exc
