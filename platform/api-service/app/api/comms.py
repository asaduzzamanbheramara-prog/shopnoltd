"""Unified communications facade: browser talks to api.shopnoltd only."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token

router = APIRouter()
bearer = HTTPBearer()
MESSAGING = "http://messaging-service.shopno-platform.svc.cluster.local:80"
MEET = "http://meet-service.shopno-platform.svc.cluster.local:80"
LIVE = "http://live-service.shopno-platform.svc.cluster.local:80"
SOCIAL = "http://social-service.shopno-platform.svc.cluster.local:80"


async def auth(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        user = await verify_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(401, "Invalid authentication token") from exc
    return creds.credentials, user


async def relay(method: str, base: str, path: str, token: str, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(method, f"{base}{path}", headers={"Authorization": f"Bearer {token}"}, **kwargs)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise HTTPException(503, "Communications service unavailable") from exc
    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:1000]
        raise HTTPException(response.status_code, detail=detail)
    return response.json() if response.content else None


@router.get("/conversations")
async def conversations(credentials=Depends(auth)):
    token, _ = credentials
    return await relay("GET", MESSAGING, "/api/v1/conversations", token)


@router.post("/conversations")
async def create_conversation(body: dict, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("POST", MESSAGING, "/api/v1/conversations", token, json=body)


@router.get("/conversations/{conversation_id}")
async def conversation(conversation_id: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("GET", MESSAGING, f"/api/v1/conversations/{conversation_id}", token)


@router.get("/conversations/{conversation_id}/messages")
async def messages(conversation_id: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("GET", MESSAGING, f"/api/v1/messages/c/{conversation_id}", token)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, body: dict, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("POST", MESSAGING, f"/api/v1/messages/c/{conversation_id}", token, json=body)


@router.post("/conversations/{conversation_id}/read")
async def read_conversation(conversation_id: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("POST", MESSAGING, f"/api/v1/messages/c/{conversation_id}/read", token)


@router.patch("/messages/{message_id}")
async def edit_message(message_id: str, body: dict, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("PATCH", MESSAGING, f"/api/v1/messages/{message_id}", token, json=body)


@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("DELETE", MESSAGING, f"/api/v1/messages/{message_id}", token)


@router.post("/messages/{message_id}/reaction")
async def react_message(message_id: str, reaction: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("POST", MESSAGING, f"/api/v1/messages/{message_id}/reactions", token, params={"reaction": reaction})


@router.delete("/messages/{message_id}/reaction")
async def unreact_message(message_id: str, reaction: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("DELETE", MESSAGING, f"/api/v1/messages/{message_id}/reactions", token, params={"reaction": reaction})


@router.post("/calls/rooms/{room_name}")
async def start_call(room_name: str, call_type: str = "video", credentials=Depends(auth)):
    token, _ = credentials
    return await relay("POST", MEET, f"/api/v1/calls/rooms/{room_name}", token, params={"call_type": call_type})


@router.post("/calls/{call_id}/{action}")
async def call_action(call_id: str, action: str, credentials=Depends(auth)):
    if action not in {"accept", "reject", "end"}:
        raise HTTPException(404, "unsupported call action")
    token, _ = credentials
    return await relay("POST", MEET, f"/api/v1/calls/{call_id}/{action}", token)


@router.get("/calls/{call_id}")
async def call_status(call_id: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("GET", MEET, f"/api/v1/calls/{call_id}", token)


@router.get("/live")
async def live_status(credentials=Depends(auth)):
    token, _ = credentials
    return await relay("GET", LIVE, "/api/v1/streams", token)


@router.get("/social/reactions/{post_id}")
async def post_reactions(post_id: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("GET", SOCIAL, f"/api/v1/reactions/{post_id}", token)


@router.put("/social/reactions/{post_id}")
async def add_post_reaction(post_id: str, reaction: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("PUT", SOCIAL, f"/api/v1/reactions/{post_id}", token, params={"reaction": reaction})


@router.delete("/social/reactions/{post_id}")
async def remove_post_reaction(post_id: str, reaction: str, credentials=Depends(auth)):
    token, _ = credentials
    return await relay("DELETE", SOCIAL, f"/api/v1/reactions/{post_id}", token, params={"reaction": reaction})
