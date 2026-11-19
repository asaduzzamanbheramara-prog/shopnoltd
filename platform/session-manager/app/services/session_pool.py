"""
Keeps one persistent Playwright context per profile. The service is deliberately
single-replica; profile tabs and viewer sessions are local to this process.
"""
import asyncio
import re
import uuid
from datetime import datetime
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Route, Download, async_playwright

from app.services.crypto import decrypt_secret
from app.services.url_policy import PublicURLPolicy


class SessionPool:
    def __init__(self):
        self._playwright = None
        self._contexts: dict[str, BrowserContext] = {}
        self._tabs: dict[str, dict[str, Page]] = {}
        self._meta: dict[str, dict] = {}
        self._download_dirs: dict[str, Path] = {}
        self._download_tasks: dict[str, set[asyncio.Task]] = {}
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

    def _watch_page(self, profile_id: str, page: Page, download_dir: Path):
        async def save_download(download: Download):
            download_dir.mkdir(parents=True, exist_ok=True)
            original_name = str(download.suggested_filename or "download").replace("\\", "/").split("/")[-1]
            safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", original_name).strip(" .")[:120] or "download"
            download_id = str(uuid.uuid4())
            temporary_path = download_dir / f".{download_id}.part"
            final_path = download_dir / f"{download_id}__{safe_name}"
            try:
                await download.save_as(str(temporary_path))
                temporary_path.replace(final_path)
            except Exception:
                temporary_path.unlink(missing_ok=True)
                raise

        def on_download(download: Download):
            task = asyncio.create_task(save_download(download))
            tasks = self._download_tasks.setdefault(profile_id, set())
            tasks.add(task)
            task.add_done_callback(lambda finished: tasks.discard(finished))

        page.on("download", on_download)

    def list_downloads(self, user_data_dir: str) -> list[dict]:
        directory = (Path(user_data_dir) / "downloads").resolve()
        if not directory.is_dir():
            return []
        results = []
        for path in directory.iterdir():
            if path.is_symlink() or not path.is_file() or "__" not in path.name:
                continue
            download_id, filename = path.name.split("__", 1)
            try:
                uuid.UUID(download_id)
                resolved = path.resolve()
                if resolved.parent != directory:
                    continue
                stat = resolved.stat()
                results.append({
                    "id": download_id,
                    "filename": filename,
                    "size": stat.st_size,
                    "modified_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                })
            except (ValueError, OSError):
                continue
        return sorted(results, key=lambda item: item["modified_at"], reverse=True)

    def get_download(self, user_data_dir: str, download_id: str) -> tuple[Path, str]:
        try:
            normalized_id = str(uuid.UUID(download_id))
        except ValueError:
            raise FileNotFoundError("Download not found")
        directory = (Path(user_data_dir) / "downloads").resolve()
        for path in directory.glob(f"{normalized_id}__*"):
            if path.is_symlink() or not path.is_file():
                continue
            resolved = path.resolve()
            if resolved.parent == directory:
                return resolved, path.name.split("__", 1)[1]
        raise FileNotFoundError("Download not found")

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

            download_dir = Path(user_data_dir) / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)
            self._download_dirs[profile_id] = download_dir

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
                "accept_downloads": True,
                "downloads_path": str(download_dir),
            }
            if proxy is not None:
                proxy_cfg = {"server": f"http://{proxy.server}"}
                if proxy.username:
                    proxy_cfg["username"] = proxy.username
                    proxy_cfg["password"] = decrypt_secret(proxy.password_encrypted)
                launch_kwargs["proxy"] = proxy_cfg

            context = await self._playwright.chromium.launch_persistent_context(**launch_kwargs)
            await context.route("**/*", self._guard_request)
            context.on("page", lambda page: self._watch_page(profile_id, page, download_dir))
            for existing_page in context.pages:
                self._watch_page(profile_id, existing_page, download_dir)
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
            self._download_dirs.pop(profile_id, None)
            if context is not None:
                tasks = list(self._download_tasks.pop(profile_id, set()))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                await context.close()
                return True
            return False

    def list_active(self) -> dict:
        return dict(self._meta)

    async def shutdown(self):
        async with self._lock:
            for profile_id, context in self._contexts.items():
                tasks = list(self._download_tasks.get(profile_id, set()))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                await context.close()
            self._contexts.clear()
            self._tabs.clear()
            self._meta.clear()
            self._download_dirs.clear()
            self._download_tasks.clear()
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None


pool = SessionPool()
