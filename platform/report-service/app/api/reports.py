import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Report
from app.schemas.schemas import ReportIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", status_code=201)
async def create(body: ReportIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = Report(
        tenant_id=user.get("tenant_id", "default"),
        user_id=user["sub"],
        name=body.name,
        kind=body.kind,
        query_sql=body.query_sql,
        status="queued",
    )
    s.add(r)
    await s.commit()
    return {"id": r.id, "status": r.status}


@router.post("/{report_id}/csv")
async def make_csv(
    report_id: str, rows: list, user=Depends(current_user), s: AsyncSession = Depends(db)
):
    r = (await s.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "report not found")
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    r.status = "ready"
    r.file_path = f"/tmp/{report_id}.csv"
    await s.commit()
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={r.name}.csv"},
    )


@router.get("/{report_id}")
async def get(report_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = (await s.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "report not found")
    return {
        "id": r.id,
        "name": r.name,
        "kind": r.kind,
        "status": r.status,
        "file_path": r.file_path,
    }


@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Report)
        .where(Report.user_id == user["sub"])
        .order_by(Report.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "kind": r.kind,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in res.scalars().all()
    ]
