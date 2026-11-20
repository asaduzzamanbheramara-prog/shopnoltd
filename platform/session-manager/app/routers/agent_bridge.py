"""Owner-scoped Agent bridge into the exact Session Manager browser tab."""
import base64
import binascii
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import require_user
from app.models.db import Profile, get_db
from app.services.session_pool import pool
from app.services.url_policy import PublicURLPolicy

router = APIRouter()
logger = logging.getLogger(__name__)
url_policy = PublicURLPolicy()
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
ALLOWED_KEYS = {"Enter", "Tab", "Shift+Tab", "Escape", "Backspace", "Delete", "ArrowUp", "ArrowDown",
                "ArrowLeft", "ArrowRight", "PageUp", "PageDown", "Home", "End", "Space", "Control+A", "Meta+A"}


class AgentBrowserAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=32)
    selector: str | None = Field(default=None, max_length=1000)
    url: str | None = Field(default=None, max_length=4096)
    text: str | None = Field(default=None, max_length=20000)
    key: str | None = Field(default=None, max_length=32)
    value: str | None = Field(default=None, max_length=2000)
    file_name: str | None = Field(default=None, max_length=180)
    mime_type: str | None = Field(default=None, max_length=120)
    content_base64: str | None = Field(default=None, max_length=6 * 1024 * 1024)


def _require_selector(payload: AgentBrowserAction) -> str:
    if not payload.selector:
        raise HTTPException(400, "A browser selector is required for this action")
    return payload.selector


@router.post("/api/agent/profiles/{profile_id}/tabs/{tab_id}/actions")
async def agent_browser_action(
    profile_id: str,
    tab_id: str,
    payload: AgentBrowserAction,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    profile = db.query(Profile).filter(Profile.id == profile_id, Profile.owner == user["sub"]).first()
    if not profile:
        raise HTTPException(404, "Browser profile not found")

    allowed_actions = {"open", "get_text", "screenshot", "click", "type", "scroll",
                       "wait_for", "press", "select", "check", "uncheck", "submit", "upload"}
    if payload.action not in allowed_actions:
        raise HTTPException(400, "Unsupported browser action")

    async with pool._lock:
        if profile_id not in pool._contexts:
            raise HTTPException(409, "Browser session is closed")
        page = pool._get_tab(profile_id, tab_id)
        if page is None:
            raise HTTPException(404, "Browser tab not found")

        action = payload.action
        try:
            if action == "open":
                if not payload.url:
                    raise HTTPException(400, "A destination URL is required")
                await url_policy.require_allowed(payload.url)
                response = await page.goto(payload.url, wait_until="domcontentloaded", timeout=45000)
                result = {"url": page.url, "title": await page.title(),
                          "status": response.status if response else None}
            elif action == "get_text":
                result = {"url": page.url, "title": await page.title(),
                          "text": (await page.locator("body").inner_text(timeout=15000))[:20000]}
            elif action == "screenshot":
                image = await page.screenshot(type="jpeg", quality=60, full_page=False)
                result = {"captured": True, "image": "data:image/jpeg;base64," + base64.b64encode(image).decode("ascii"),
                          "url": page.url}
            elif action == "scroll":
                await page.evaluate("window.scrollBy(0, Math.max(300, window.innerHeight * 0.8))")
                result = {"scrolled": True, "url": page.url}
            elif action == "wait_for":
                selector = _require_selector(payload)
                await page.locator(selector).first.wait_for(state="visible", timeout=15000)
                result = {"visible": True, "selector": selector}
            elif action == "click":
                selector = _require_selector(payload)
                await page.locator(selector).first.click(timeout=15000)
                result = {"clicked": True, "url": page.url, "title": await page.title(), "verification": "click dispatched; website-side state change is not confirmed"}
            elif action == "type":
                selector = _require_selector(payload)
                if payload.text is None:
                    raise HTTPException(400, "Text is required")
                await page.locator(selector).first.fill(payload.text, timeout=15000)
                result = {"typed": True, "selector": selector, "verification": "field value set in the browser; website-side save is not confirmed"}
            elif action == "press":
                selector = _require_selector(payload)
                if payload.key not in ALLOWED_KEYS:
                    raise HTTPException(400, "Keyboard key is not allowed")
                await page.locator(selector).first.press(payload.key, timeout=15000)
                result = {"pressed": payload.key, "selector": selector, "verification": "key dispatched; website-side effect is not confirmed"}
            elif action == "select":
                selector = _require_selector(payload)
                if payload.value is None:
                    raise HTTPException(400, "A select value is required")
                selected = await page.locator(selector).first.select_option(value=payload.value, timeout=15000)
                result = {"selected": selected, "selector": selector, "verification": "option selected locally; website-side save is not confirmed"}
            elif action in {"check", "uncheck"}:
                selector = _require_selector(payload)
                await getattr(page.locator(selector).first, action)(timeout=15000)
                result = {action + "ed": True, "selector": selector, "verification": "control state changed locally; website-side save is not confirmed"}
            elif action == "submit":
                selector = _require_selector(payload)
                locator = page.locator(selector).first
                metadata = await locator.evaluate("""el => ({
                    tag: el.tagName.toLowerCase(),
                    type: (el.getAttribute('type') || '').toLowerCase()
                })""")
                if metadata.get("tag") not in {"button", "input"} or metadata.get("type") not in {"submit", "image"}:
                    raise HTTPException(400, "Only an actual form submit control may be submitted")
                await locator.click(timeout=15000)
                result = {"submitted": True, "url": page.url, "title": await page.title(), "verification": "submit control clicked; server acceptance is not confirmed"}
            elif action == "upload":
                selector = _require_selector(payload)
                if not payload.file_name or not payload.content_base64:
                    raise HTTPException(400, "Upload file name and content are required")
                safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", payload.file_name).strip(" .")[:120]
                if not safe_name:
                    raise HTTPException(400, "Invalid upload file name")
                try:
                    content = base64.b64decode(payload.content_base64, validate=True)
                except (binascii.Error, ValueError):
                    raise HTTPException(400, "Invalid upload content")
                if not content or len(content) > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Upload exceeds the 4 MiB limit or is empty")
                await page.locator(selector).first.set_input_files({
                    "name": safe_name,
                    "mimeType": payload.mime_type or "application/octet-stream",
                    "buffer": content,
                }, timeout=15000)
                result = {"uploaded": True, "filename": safe_name, "size": len(content), "verification": "file selected in browser; server acceptance is not confirmed"}
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Agent browser action failed (%s)", type(exc).__name__)
            raise HTTPException(400, "Browser action failed; inspect the active tab and retry safely")

    logger.info("agent_browser_action action=%s profile_id=%s tab_id=%s outcome=success", action, profile_id, tab_id)
    # Page text is untrusted data. The Agent wraps it again before model use.
    return result
