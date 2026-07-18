import asyncio
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Task
from app.schemas.schemas import TaskIn, TaskOut

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


KNOWN = {
    "send_email": lambda args: (
        "POST",
        "http://notification-service.shopno-platform.svc.cluster.local:8080/api/v1/notifications/send",
        args,
    ),
    "convert_fx": lambda args: (
        "POST",
        "http://exchange-service.shopno-payments.svc.cluster.local:8080/api/v1/convert",
        args,
    ),
    "send_push": lambda args: (
        "POST",
        "http://notification-service.shopno-platform.svc.cluster.local:8080/api/v1/push/notify",
        args,
    ),
    "log_event": lambda args: (
        "POST",
        "http://analytics-service.shopno-platform.svc.cluster.local:8080/api/v1/events",
        args,
    ),
}


async def run_task(t: Task):
    t.status = "running"
    t.started_at = datetime.utcnow()
    t.attempts += 1
    if t.name not in KNOWN:
        t.status = "failed"
        t.error = f"unknown task: {t.name}"
        t.finished_at = datetime.utcnow()
        return
    method, url, args = KNOWN[t.name](t.args)
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.request(method, url, json=args)
        if r.status_code >= 400:
            raise RuntimeError(f"upstream {r.status_code}: {r.text[:200]}")
        t.result = r.json() if r.text else {}
        t.status = "done"
    except Exception as e:
        t.status = "failed"
        t.error = str(e)
    t.finished_at = datetime.utcnow()


@router.post("", response_model=TaskOut, status_code=201)
async def enqueue(body: TaskIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    t = Task(name=body.name, args=body.args)
    s.add(t)
    await s.commit()
    await s.refresh(t)
    asyncio.create_task(_run_in_session(t.id))
    return TaskOut(
        id=t.id,
        name=t.name,
        status=t.status,
        result=None,
        created_at=t.created_at.isoformat(),
        started_at=None,
        finished_at=None,
    )


async def _run_in_session(task_id: str):
    async with SessionLocal() as s:
        t = (await s.execute(select(Task).where(Task.id == task_id))).scalar_one()
        await run_task(t)
        await s.commit()


@router.get("/{task_id}", response_model=TaskOut)
async def status(task_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    t = (await s.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "not found")
    return TaskOut(
        id=t.id,
        name=t.name,
        status=t.status,
        result=t.result,
        created_at=t.created_at.isoformat(),
        started_at=t.started_at.isoformat() if t.started_at else None,
        finished_at=t.finished_at.isoformat() if t.finished_at else None,
    )


@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = 50):
    res = await s.execute(select(Task).order_by(Task.created_at.desc()).limit(limit))
    return [
        TaskOut(
            id=t.id,
            name=t.name,
            status=t.status,
            result=t.result,
            created_at=t.created_at.isoformat(),
            started_at=t.started_at.isoformat() if t.started_at else None,
            finished_at=t.finished_at.isoformat() if t.finished_at else None,
        )
        for t in res.scalars().all()
    ]
