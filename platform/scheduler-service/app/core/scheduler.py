import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


async def http_job(url: str, method: str = "POST", body: dict = None):
    async with httpx.AsyncClient(timeout=30) as c:
        await c.request(method, url, json=body)
