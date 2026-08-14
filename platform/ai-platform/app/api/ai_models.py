import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.models import AIModel, AIProvider
from app.db.session import get_db
from app.schemas.ai_provider import ModelCreate, ModelOut, ModelUpdate, ModelWithProviderOut

router = APIRouter(
    prefix="/api/ai/models", tags=["ai-models"], dependencies=[Depends(require_admin)]
)


@router.get("", response_model=list[ModelWithProviderOut])
async def list_models(active_only: bool = False, db: AsyncSession = Depends(get_db)):
    stmt = select(AIModel, AIProvider).join(AIProvider)
    if active_only:
        stmt = stmt.where(AIModel.is_active == True, AIProvider.is_active == True)  # noqa: E712
    stmt = stmt.order_by(AIModel.priority.asc())
    result = await db.execute(stmt)
    out = []
    for model, provider in result.all():
        out.append(
            ModelWithProviderOut(
                **ModelOut.model_validate(model).model_dump(),
                provider_name=provider.name,
                provider_type=provider.provider_type,
            )
        )
    return out


@router.post(
    "/providers/{provider_id}", response_model=ModelOut, status_code=status.HTTP_201_CREATED
)
async def create_model(
    provider_id: uuid.UUID, payload: ModelCreate, db: AsyncSession = Depends(get_db)
):
    provider = await db.get(AIProvider, provider_id)
    if not provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not found")

    existing = await db.execute(
        select(AIModel).where(
            AIModel.provider_id == provider_id, AIModel.model_name == payload.model_name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Model already registered for this provider")

    if payload.is_default:
        await _clear_other_defaults(db)

    model = AIModel(
        provider_id=provider_id,
        model_name=payload.model_name,
        display_name=payload.display_name,
        is_active=payload.is_active,
        is_default=payload.is_default,
        capabilities=payload.capabilities,
        priority=payload.priority,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.patch("/{model_id}", response_model=ModelOut)
async def update_model(
    model_id: uuid.UUID, payload: ModelUpdate, db: AsyncSession = Depends(get_db)
):
    model = await db.get(AIModel, model_id)
    if not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    if payload.display_name is not None:
        model.display_name = payload.display_name
    if payload.capabilities is not None:
        model.capabilities = payload.capabilities
    if payload.priority is not None:
        model.priority = payload.priority
    await db.commit()
    await db.refresh(model)
    return model


@router.post("/{model_id}/activate", response_model=ModelOut)
async def activate_model(model_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    model = await db.get(AIModel, model_id)
    if not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    model.is_active = True
    await db.commit()
    await db.refresh(model)
    return model


@router.post("/{model_id}/deactivate", response_model=ModelOut)
async def deactivate_model(model_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    model = await db.get(AIModel, model_id)
    if not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    model.is_active = False
    if model.is_default:
        model.is_default = False  # don't leave a deactivated model as the default
    await db.commit()
    await db.refresh(model)
    return model


@router.post("/{model_id}/set-default", response_model=ModelOut)
async def set_default_model(model_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    model = await db.get(AIModel, model_id)
    if not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    if not model.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot set an inactive model as default — activate it first",
        )
    await _clear_other_defaults(db)
    model.is_default = True
    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    model = await db.get(AIModel, model_id)
    if not model:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    await db.delete(model)
    await db.commit()


async def _clear_other_defaults(db: AsyncSession) -> None:
    result = await db.execute(select(AIModel).where(AIModel.is_default == True))  # noqa: E712
    for m in result.scalars().all():
        m.is_default = False
