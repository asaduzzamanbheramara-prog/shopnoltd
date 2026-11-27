"""User-controlled AI memory CRUD; memories are never inferred or saved implicitly."""
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import current_user
from app.db.models import AIPersonalMemory, AIPersonalMemorySettings
from app.db.session import get_db

router = APIRouter()


def ownership(user: dict) -> tuple[str, str]:
    tenant_id, user_id = user.get("tenant_id"), user.get("sub")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise HTTPException(403, "tenant context required")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(403, "user identity required")
    return tenant_id.strip(), user_id.strip()


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    category: str = Field(default="general", min_length=1, max_length=60)


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    category: str | None = Field(default=None, min_length=1, max_length=60)


def serialize(row: AIPersonalMemory) -> dict:
    return {
        "id": row.id,
        "category": row.category,
        "content": row.content,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
async def list_memories(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = ownership(user)
    result = await db.execute(
        select(AIPersonalMemory)
        .where(AIPersonalMemory.tenant_id == tenant_id, AIPersonalMemory.user_id == user_id)
        .order_by(AIPersonalMemory.updated_at.desc())
        .limit(200)
    )
    return [serialize(row) for row in result.scalars().all()]


@router.post("", status_code=201)
async def create_memory(body: MemoryCreate, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = ownership(user)
    count = await db.scalar(
        select(func.count()).select_from(AIPersonalMemory).where(
            AIPersonalMemory.tenant_id == tenant_id, AIPersonalMemory.user_id == user_id
        )
    )
    if count >= 200:
        raise HTTPException(409, "memory limit reached; delete an existing memory first")
    row = AIPersonalMemory(
        id=str(uuid.uuid4()), tenant_id=tenant_id, user_id=user_id,
        category=body.category.strip(), content=body.content.strip()
    )
    if not row.content or not row.category:
        raise HTTPException(422, "memory content and category must not be blank")
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return serialize(row)


class MemorySettingsUpdate(BaseModel):
    enabled: bool


@router.get("/settings")
async def get_memory_settings(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = ownership(user)
    row = await db.get(AIPersonalMemorySettings, (tenant_id, user_id))
    return {"enabled": row.memory_enabled if row is not None else True}


@router.patch("/settings")
async def update_memory_settings(
    body: MemorySettingsUpdate,
    user=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id, user_id = ownership(user)
    row = await db.get(AIPersonalMemorySettings, (tenant_id, user_id))
    if row is None:
        row = AIPersonalMemorySettings(
            tenant_id=tenant_id, user_id=user_id, memory_enabled=body.enabled
        )
        db.add(row)
    else:
        row.memory_enabled = body.enabled
        row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"enabled": row.memory_enabled}


@router.patch("/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = ownership(user)
    row = (await db.execute(
        select(AIPersonalMemory).where(
            AIPersonalMemory.id == memory_id,
            AIPersonalMemory.tenant_id == tenant_id,
            AIPersonalMemory.user_id == user_id,
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "memory not found")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(422, "provide content or category to update")
    if "content" in changes:
        if changes["content"] is None or not changes["content"].strip():
            raise HTTPException(422, "memory content must not be blank")
        row.content = changes["content"].strip()
    if "category" in changes:
        if changes["category"] is None or not changes["category"].strip():
            raise HTTPException(422, "memory category must not be blank")
        row.category = changes["category"].strip()
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return serialize(row)


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = ownership(user)
    row = (await db.execute(
        select(AIPersonalMemory).where(
            AIPersonalMemory.id == memory_id,
            AIPersonalMemory.tenant_id == tenant_id,
            AIPersonalMemory.user_id == user_id,
        )
    )).scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.commit()
