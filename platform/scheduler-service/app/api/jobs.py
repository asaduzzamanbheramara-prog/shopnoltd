from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.scheduler import http_job, scheduler
from app.core.security import verify_token_admin
from app.models.models import Job
from app.schemas.schemas import JobIn, JobOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)


@router.on_event("startup")
async def load_jobs():
    if not scheduler.running:
        scheduler.start()
    async with SessionLocal() as s:
        res = await s.execute(select(Job).where(Job.active == 1))
        for j in res.scalars().all():
            try:
                scheduler.add_job(
                    http_job,
                    CronTrigger.from_crontab(j.cron),
                    id=j.id,
                    args=[j.url, j.method, j.body],
                    replace_existing=True,
                )
            except Exception:
                pass


@router.post("", status_code=201)
async def create(body: JobIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    j = Job(name=body.name, cron=body.cron, url=body.url, method=body.method, body=body.body)
    s.add(j)
    await s.commit()
    await s.refresh(j)
    scheduler.add_job(
        http_job,
        CronTrigger.from_crontab(j.cron),
        id=j.id,
        args=[j.url, j.method, j.body],
        replace_existing=True,
    )
    return {"id": j.id}


@router.get("")
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Job))
    return [
        JobOut(
            id=j.id,
            name=j.name,
            cron=j.cron,
            url=j.url,
            active=bool(j.active),
            last_run=j.last_run.isoformat() if j.last_run else None,
            last_status=j.last_status,
        )
        for j in res.scalars().all()
    ]


@router.delete("/{job_id}")
async def remove(job_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    j = (await s.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if not j:
        raise HTTPException(404, "not found")
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    await s.delete(j)
    await s.commit()
    return {"ok": True}
