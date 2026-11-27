"""Durable, tenant- and user-owned AI Workspace conversation history."""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import current_user
from app.db.models import AIChatThread
from app.db.session import get_db

router = APIRouter()


def ownership(user: dict) -> tuple[str, str]:
    tenant_id, user_id = user.get("tenant_id"), user.get("sub")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise HTTPException(403, "tenant context required")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(403, "user identity required")
    return tenant_id.strip(), user_id.strip()


class ChatMessage(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(max_length=200_000)


class ChatSnapshot(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(default="New chat", max_length=256)
    model: str | None = Field(default=None, max_length=200)
    modelId: str | None = Field(default=None, max_length=64)
    messages: list[ChatMessage] = Field(default_factory=list, max_length=500)


class ChatSync(BaseModel):
    chats: list[ChatSnapshot] = Field(default_factory=list, max_length=100)


def serialize(row: AIChatThread) -> dict[str, Any]:
    return {"id": row.id, "title": row.title, "model": row.model, "modelId": row.model_id,
            "messages": row.messages or [],
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None}


@router.get("")
async def list_chats(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = ownership(user)
    result = await db.execute(select(AIChatThread).where(
        AIChatThread.tenant_id == tenant_id, AIChatThread.user_id == user_id
    ).order_by(AIChatThread.updated_at.desc()))
    return [serialize(row) for row in result.scalars().all()]


@router.put("/sync")
async def sync_chats(body: ChatSync, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = ownership(user)
    ids = [chat.id for chat in body.chats]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "duplicate conversation ids")
    for chat in body.chats:
        row = await db.get(AIChatThread, chat.id)
        if row and (row.tenant_id != tenant_id or row.user_id != user_id):
            raise HTTPException(404, "conversation not found")
        if row is None:
            row = AIChatThread(id=chat.id, tenant_id=tenant_id, user_id=user_id)
            db.add(row)
        row.title, row.model, row.model_id = chat.title, chat.model, chat.modelId
        row.messages = [message.model_dump() for message in chat.messages]
        row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"saved": len(body.chats)}


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(chat_id: str, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    tenant_id, user_id = ownership(user)
    row = (await db.execute(select(AIChatThread).where(
        AIChatThread.id == chat_id, AIChatThread.tenant_id == tenant_id,
        AIChatThread.user_id == user_id
    ))).scalar_one_or_none()
    if row is not None:
        await db.delete(row)
        await db.commit()
