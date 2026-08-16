"""
Keeps launched browser contexts alive in memory, keyed by profile_id, so a
session persists across requests instead of closing immediately after
navigation. A single shared Playwright + Chromium instance runs non-headless
on the container's virtual display (:99), which x11vnc/noVNC expose for
live viewing (see docker/entrypoint.sh).

This is a single-process, in-memory pool — fine for one replica (which is
what the k8s manifest pins anyway, matching the rest of this cluster's
single-node conventions). If this ever needs multiple replicas, sessions
would need to move to a shared broker (e.g. a small Redis-backed registry
mapping profile_id -> pod) with sticky routing.
"""

import asyncio
from datetime import datetime

from app.services.crypto import decrypt_secret
from playwright.async_api import BrowserContext, async_playwright


class SessionPool:
    def __init__(self):
        self._playwright = None
        self._contexts: dict[str, BrowserContext] = {}
        self._meta: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def _ensure_playwright(self):
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def get_or_launch(
        self,
        profile_id: str,
        user_data_dir: str,
        target_url: str,
        proxy=None,
    ) -> dict:
        async with self._lock:
            await self._ensure_playwright()

            existing = self._contexts.get(profile_id)
            if existing is not None:
                page = existing.pages[0] if existing.pages else await existing.new_page()
                await page.goto(target_url)
                self._meta[profile_id]["last_used_at"] = datetime.utcnow().isoformat()
                return {"status": "reused", "vnc_path": "/vnc.html"}

            launch_kwargs = {
                "headless": False,  # runs on the virtual display so it's viewable via VNC
                "user_data_dir": user_data_dir,
                "args": ["--start-maximized"],
            }
            if proxy is not None:
                proxy_cfg = {"server": f"http://{proxy.server}"}
                if proxy.username:
                    proxy_cfg["username"] = proxy.username
                    proxy_cfg["password"] = decrypt_secret(proxy.password_encrypted)
                launch_kwargs["proxy"] = proxy_cfg

            context = await self._playwright.chromium.launch_persistent_context(**launch_kwargs)
            page = await context.new_page()
            await page.goto(target_url)

            self._contexts[profile_id] = context
            self._meta[profile_id] = {
                "launched_at": datetime.utcnow().isoformat(),
                "last_used_at": datetime.utcnow().isoformat(),
            }
            return {"status": "launched", "vnc_path": "/vnc.html"}

    async def close(self, profile_id: str) -> bool:
        async with self._lock:
            context = self._contexts.pop(profile_id, None)
            self._meta.pop(profile_id, None)
            if context is not None:
                await context.close()
                return True
            return False

    def list_active(self) -> dict:
        return dict(self._meta)

    async def shutdown(self):
        async with self._lock:
            for context in self._contexts.values():
                await context.close()
            self._contexts.clear()
            self._meta.clear()
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None


pool = SessionPool()
