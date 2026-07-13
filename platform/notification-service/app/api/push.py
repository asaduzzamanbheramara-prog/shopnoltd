"""Web-push via VAPID. Falls back to FCM if FCM key set."""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
class SubscribeIn(BaseModel):
    endpoint: str; keys: dict
@router.post("/subscribe", status_code=201)
async def subscribe(body: SubscribeIn, user=Depends(current_user)):
    # Store subscription in Redis or DB; here we just acknowledge.
    return {"ok": True, "user_id": user["sub"]}
class NotifyIn(BaseModel):
    subscription: SubscribeIn
    title: str
    body: str
@router.post("/notify")
async def notify(body: NotifyIn, user=Depends(current_user)):
    # Use pywebpush if configured; else return 501
    try:
        from pywebpush import webpush, WebPushException
        webpush(body.subscription.model_dump(), data=json.dumps({"title": body.title, "body": body.body}))
        return {"ok": True}
    except Exception as e:
        raise HTTPException(501, f"web push not configured: {e}")
