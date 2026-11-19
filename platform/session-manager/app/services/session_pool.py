"""
Keeps one persistent Playwright context per profile. The service is deliberately
single-replica; profile tabs and viewer sessions are local to this process.
"""
import asyncio
import uuid
from datetime import datetime

from playwright.async_api import BrowserContext, Page, Route, async_playwright

from app.services.crypto import decrypt_secret
from app.services.url_policy import PublicURLPolicy


class SessionPool:
    def __init__(self):
        self._playwright = None
        self._contexts: dict[str, BrowserContext] = {}
        self._tabs: dict[str, dict[str, Page]] = {}
        self._meta: dict[str, dict] = {}
        self._lock = asyncio.Lock()
        self._url_policy = PublicURLPolicy()

    async def _ensure_playwright(self):
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def _guard_request(self, route: Route):
        if await self._url_policy.is_allowed(route.request.url):
            await route.continue_()
        else:
            await route.abort("blockedbyclient")

    def _remember_tab(self, profile_id: str, page: Page) -> str:
        tabs = self._tabs.setdefault(profile_id, {})
        for tab_id, existing in list(tabs.items()):
            if existing.is_closed():
                tabs.pop(tab_id, None)
            elif existing is page:
                return tab_id
        tab_id = str(uuid.uuid4())
        tabs[tab_id] = page
        return tab_id

    def _get_tab(self, profile_id: str, tab_id: str) -> Page | None:
        page = self._tabs.get(profile_id, {}).get(tab_id)
        if page is not None and page.is_closed():
            self._tabs[profile_id].pop(tab_id, None)
            return None
        return page

    async def get_or_launch(
        self,
        profile_id: str,
        user_data_dir: str,
        target_url: str,
        proxy=None,
    ) -> dict:
        await self._url_policy.require_allowed(target_url)
        async with self._lock:
            await self._ensure_playwright()

            existing = self._contexts.get(profile_id)
            if existing is not None:
                tabs = self._tabs.setdefault(profile_id, {})
                page = next((p for p in tabs.values() if not p.is_closed()), None)
                if page is None:
                    page = await existing.new_page()
                tab_id = self._remember_tab(profile_id, page)
                await page.goto(target_url)
                self._meta[profile_id]["last_used_at"] = datetime.utcnow().isoformat()
                return {"status": "reused", "tab_id": tab_id}

            launch_kwargs = {
                "headless": False,
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
            await context.route("**/*", self._guard_request)
            page = context.pages[0] if context.pages else await context.new_page()
            tab_id = self._remember_tab(profile_id, page)
            try:
                await page.goto(target_url)
            except Exception:
                await context.close()
                raise

            self._contexts[profile_id] = context
            self._meta[profile_id] = {
                "launched_at": datetime.utcnow().isoformat(),
                "last_used_at": datetime.utcnow().isoformat(),
            }
            return {"status": "launched", "tab_id": tab_id}

    async def open_tab(self, profile_id: str, target_url: str = "about:blank") -> dict:
        await self._url_policy.require_allowed(target_url)
        async with self._lock:
            context = self._contexts.get(profile_id)
            if context is None:
                raise ValueError("No active browser session for this profile")
            page = await context.new_page()
            tab_id = self._remember_tab(profile_id, page)
            await page.goto(target_url)
            self._meta[profile_id]["last_used_at"] = datetime.utcnow().isoformat()
            return {"tab_id": tab_id, "url": page.url, "title": await page.title()}

    async def navigate_tab(self, profile_id: str, tab_id: str, target_url: str) -> dict:
        await self._url_policy.require_allowed(target_url)
        async with self._lock:
            page = self._get_tab(profile_id, tab_id)
            if page is None:
                raise ValueError("Browser tab not found")
            await page.goto(target_url)
            self._meta[profile_id]["last_used_at"] = datetime.utcnow().isoformat()
            return {"tab_id": tab_id, "url": page.url, "title": await page.title()}

    async def focus_tab(self, profile_id: str, tab_id: str) -> bool:
        async with self._lock:
            page = self._get_tab(profile_id, tab_id)
            if page is None:
                return False
            await page.bring_to_front()
            self._meta[profile_id]["last_used_at"] = datetime.utcnow().isoformat()
            return True

    async def close_tab(self, profile_id: str, tab_id: str) -> bool:
        async with self._lock:
            page = self._get_tab(profile_id, tab_id)
            if page is None:
                return False
            await page.close()
            self._tabs.get(profile_id, {}).pop(tab_id, None)
            self._meta[profile_id]["last_used_at"] = datetime.utcnow().isoformat()
            return True

    async def list_tabs(self, profile_id: str) -> list[dict]:
        async with self._lock:
            tabs = self._tabs.get(profile_id, {})
            result = []
            for tab_id, page in list(tabs.items()):
                if page.is_closed():
                    tabs.pop(tab_id, None)
                    continue
                try:
                    title = await page.title()
                except Exception:
                    title = ""
                result.append({"id": tab_id, "url": page.url, "title": title})
            return result

    async def close(self, profile_id: str) -> bool:
        async with self._lock:
            context = self._contexts.pop(profile_id, None)
            self._tabs.pop(profile_id, None)
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
            self._tabs.clear()
            self._meta.clear()
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None


pool = SessionPool()
