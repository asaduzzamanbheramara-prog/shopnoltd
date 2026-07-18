from app.ai.engine import run_conversation
from app.core.deps import get_current_user
from app.database import get_db
from app.models import ChatSession, Message, User
from app.schemas import ChatResponse, ChatSessionOut, MessageCreate, MessageOut
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionOut, status_code=201)
async def create_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = ChatSession(user_id=current_user.id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def list_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    result = await db.scalars(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    return result.all()


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_message(
    session_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    user_msg = Message(session_id=session_id, role="user", content=payload.content)
    db.add(user_msg)
    await db.commit()

    result = await db.scalars(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    history = result.all()
    claude_messages = [
        {"role": m.role, "content": m.content} for m in history if m.role in ("user", "assistant")
    ]

    reply_text, _ = run_conversation(claude_messages)

    assistant_msg = Message(session_id=session_id, role="assistant", content=reply_text)
    db.add(assistant_msg)
    await db.commit()

    return ChatResponse(session_id=session_id, reply=reply_text)
