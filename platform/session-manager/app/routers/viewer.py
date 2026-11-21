"""Owner-bound, short-lived noVNC viewer gateway.

The one-time bootstrap ticket is exchanged in a same-origin POST (never in a URL).
The resulting HttpOnly cookie is scoped to one profile's WebSocket path.
"""
import asyncio
import os
import secrets
import time
import uuid
from typing import Any

import websockets
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.auth import require_user
from app.models.db import Profile, SessionLocal, get_db
from app.services.session_pool import pool

router = APIRouter()
TICKET_TTL_SECONDS = 60
VIEWER_TTL_SECONDS = 600
COOKIE_NAME = "shopno_viewer"
_tickets: dict[str, dict[str, Any]] = {}
_viewers: dict[str, dict[str, Any]] = {}


def _allowed_origins() -> set[str]:
    raw = os.getenv(
        "SESSION_MANAGER_ALLOWED_ORIGINS",
        "https://shopnoltd.dpdns.org,https://www.shopnoltd.dpdns.org,https://sessions.shopnoltd.dpdns.org",
    )
    return {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}


def _purge_expired(now: float | None = None) -> None:
    current = now if now is not None else time.time()
    for key, value in list(_tickets.items()):
        if value["expires_at"] <= current:
            _tickets.pop(key, None)
    for key, value in list(_viewers.items()):
        if value["expires_at"] <= current:
            _viewers.pop(key, None)


def _issue_ticket(profile_id: str, owner: str, now: float | None = None) -> str:
    current = now if now is not None else time.time()
    _purge_expired(current)
    ticket = secrets.token_urlsafe(32)
    _tickets[ticket] = {
        "profile_id": str(profile_id),
        "owner": owner,
        "expires_at": current + TICKET_TTL_SECONDS,
    }
    return ticket


def _consume_ticket(ticket: str, profile_id: str, now: float | None = None) -> dict[str, Any] | None:
    current = now if now is not None else time.time()
    _purge_expired(current)
    record = _tickets.pop(ticket, None)
    if not record or record["profile_id"] != str(profile_id) or record["expires_at"] <= current:
        return None
    return record


def revoke_profile_viewers(profile_id: str) -> None:
    for key, value in list(_viewers.items()):
        if value["profile_id"] == str(profile_id):
            _viewers.pop(key, None)


@router.post("/api/sessions/{profile_id}/viewer-ticket")
def create_viewer_ticket(
    profile_id: str,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.owner == user["sub"]).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    if str(profile.id) not in pool.list_active():
        raise HTTPException(409, "Launch this browser profile before opening its viewer")
    ticket = _issue_ticket(str(profile.id), user["sub"])
    public_url = os.getenv("SESSION_MANAGER_PUBLIC_URL", "https://sessions.shopnoltd.dpdns.org").rstrip("/")
    return {
        "viewer_url": f"{public_url}/viewer/bootstrap#profile_id={profile.id}&ticket={ticket}",
        "expires_in": TICKET_TTL_SECONDS,
    }


@router.get("/viewer/bootstrap", response_class=HTMLResponse)
def viewer_bootstrap():
    html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Shopnoltd Browser</title></head><body>
<p id="status">Securing browser session…</p>
<script>
(async () => {
  const status = document.getElementById('status');
  const values = new URLSearchParams(location.hash.slice(1));
  const profileId = values.get('profile_id') || '';
  const ticket = values.get('ticket') || '';
  history.replaceState(null, '', location.pathname);
  if (!/^[0-9a-f-]{36}$/i.test(profileId) || ticket.length < 32 || ticket.length > 128) {
    status.textContent = 'Invalid or expired viewer link.';
    return;
  }
  try {
    const response = await fetch('/viewer/' + encodeURIComponent(profileId) + '/exchange', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ticket })
    });
    if (!response.ok) throw new Error('Viewer authorization expired. Reopen the viewer.');
    const result = await response.json();
    location.replace(result.redirect);
  } catch (error) {
    status.textContent = error.message || 'Unable to open browser viewer.';
  }
})();
</script></body></html>"""
    return HTMLResponse(
        html,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'self' https://shopnoltd.dpdns.org https://www.shopnoltd.dpdns.org",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/viewer/{profile_id}/exchange")
async def exchange_viewer_ticket(profile_id: str, request: Request):
    origin = request.headers.get("origin", "").rstrip("/")
    if origin not in _allowed_origins():
        raise HTTPException(403, "Viewer origin is not allowed")
    try:
        profile_uuid = uuid.UUID(profile_id)
        payload = await request.json()
        ticket = payload.get("ticket") if isinstance(payload, dict) else None
    except (ValueError, TypeError):
        raise HTTPException(400, "Invalid viewer request")
    if not isinstance(ticket, str) or len(ticket) > 128:
        raise HTTPException(400, "Invalid viewer ticket")
    record = _consume_ticket(ticket, str(profile_uuid))
    if not record:
        raise HTTPException(401, "Viewer ticket is invalid, expired, or already used")

    with SessionLocal() as db:
        profile = db.query(Profile).filter(
            Profile.id == profile_uuid,
            Profile.owner == record["owner"],
        ).first()
        if not profile or str(profile_uuid) not in pool.list_active():
            raise HTTPException(404, "Active browser session not found")

    viewer_id = secrets.token_urlsafe(32)
    _viewers[viewer_id] = {
        "profile_id": str(profile_uuid),
        "owner": record["owner"],
        "expires_at": time.time() + VIEWER_TTL_SECONDS,
    }
    response = JSONResponse({
        "redirect": f"/viewer-assets/vnc.html?autoconnect=true&resize=remote&path=viewer/{profile_uuid}/websockify",
        "expires_in": VIEWER_TTL_SECONDS,
    })
    response.set_cookie(
        key=COOKIE_NAME,
        value=viewer_id,
        max_age=VIEWER_TTL_SECONDS,
        path=f"/viewer/{profile_uuid}/",
        secure=os.getenv("SESSION_MANAGER_COOKIE_SECURE", "true").lower() == "true",
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.websocket("/viewer/{profile_id}/websockify")
async def viewer_websocket(websocket: WebSocket, profile_id: str):
    origin = websocket.headers.get("origin", "").rstrip("/")
    if origin not in _allowed_origins():
        await websocket.close(code=4403)
        return
    viewer_id = websocket.cookies.get(COOKIE_NAME)
    _purge_expired()
    viewer = _viewers.get(viewer_id or "")
    if not viewer or viewer["profile_id"] != profile_id:
        await websocket.close(code=4401)
        return
    with SessionLocal() as db:
        profile = db.query(Profile).filter(
            Profile.id == profile_id,
            Profile.owner == viewer["owner"],
        ).first()
    if not profile or profile_id not in pool.list_active():
        _viewers.pop(viewer_id, None)
        await websocket.close(code=4404)
        return

    await websocket.accept()
    try:
        async with websockets.connect(
            "ws://127.0.0.1:6080/websockify",
            max_size=None,
            ping_interval=20,
            ping_timeout=20,
            open_timeout=10,
        ) as upstream:
            async def browser_to_vnc():
                while True:
                    message = await websocket.receive()
                    if message["type"] == "websocket.disconnect":
                        return
                    if message.get("text") is not None:
                        await upstream.send(message["text"])
                    elif message.get("bytes") is not None:
                        await upstream.send(message["bytes"])

            async def vnc_to_browser():
                while True:
                    message = await upstream.recv()
                    if isinstance(message, bytes):
                        await websocket.send_bytes(message)
                    else:
                        await websocket.send_text(message)

            tasks = {
                asyncio.create_task(browser_to_vnc()),
                asyncio.create_task(vnc_to_browser()),
            }
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                task.result()
    except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
        pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
