from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx
scheduler = AsyncIOScheduler()
async def http_job(url: str, method: str = "POST", body: dict = None):
    async with httpx.AsyncClient(timeout=30) as c:
        await c.request(method, url, json=body)
