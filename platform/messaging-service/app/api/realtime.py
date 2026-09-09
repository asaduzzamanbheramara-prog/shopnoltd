import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Participant

router = APIRouter()


async def _member(conv_id: str, user_id: str) -> bool:
    async with SessionLocal() as s:
        row = (await s.execute(select(Participant).where(
            Participant.conversation_id == conv_id, Participant.user_id == user_id
        ))).scalar_one_or_none()
        return row is not None


@router.websocket("/ws/{conv_id}")
async def websocket_chat(ws: WebSocket, conv_id: str):
    token = ws.query_params.get("access_token")
    if not token:
        await ws.close(code=4401)
        return
    try:
        user = await verify_token(token)
        user_id = user["sub"]
        if not await _member(conv_id, user_id):
            await ws.close(code=4403)
            return
    except Exception:
        await ws.close(code=4401)
        return

    await ws.accept()
    await ws.send_json({"type": "connected", "conversation_id": conv_id, "user_id": user_id})
    channel = f"shopnoltd:messaging:{conv_id}"
    pubsub = None
    listener = None
    try:
        pubsub = ws.app.state.redis.pubsub()
        await pubsub.subscribe(channel)

        async def listen():
            while True:
                item = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if item and item.get("type") == "message":
                    await ws.send_text(item["data"])
                await asyncio.sleep(0.05)

        listener = asyncio.create_task(listen())
        while True:
            raw = await ws.receive_text()
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "invalid JSON"})
                continue
            kind = event.get("type")
            if kind not in {"typing", "presence", "message"}:
                await ws.send_json({"type": "error", "message": "unsupported event"})
                continue
            payload = {
                "type": kind,
                "conversation_id": conv_id,
                "user_id": user_id,
                "at": datetime.utcnow().isoformat(),
            }
            if kind == "typing":
                payload["active"] = bool(event.get("active", True))
            elif kind == "presence":
                payload["status"] = event.get("status", "online")
            elif kind == "message":
                payload["message_id"] = event.get("message_id")
            await ws.app.state.redis.publish(channel, json.dumps(payload))
    except WebSocketDisconnect:
        pass
    finally:
        if listener:
            listener.cancel()
        if pubsub:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
