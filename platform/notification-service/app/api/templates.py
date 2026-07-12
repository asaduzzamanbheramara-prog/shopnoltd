from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Template
from app.schemas.schemas import TemplateIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    u = await verify_token(creds.credentials)
    if "admin" not in u.get("roles", []): raise HTTPException(403, "admin only")
    return u
@router.get("")
async def list_t(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Template))
    return [{"id":t.id,"code":t.code,"name":t.name,"channel":t.channel.value,"subject":t.subject,"locale":t.locale} for t in res.scalars().all()]
@router.post("", status_code=201)
async def create_t(body: TemplateIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    t = Template(code=body.code, name=body.name, channel=body.channel, subject=body.subject, body=body.body, variables=body.variables)
    s.add(t); await s.commit()
    return {"id": t.id, "code": t.code}
@router.post("/{code}/render")
async def render(code: str, variables: dict, s: AsyncSession = Depends(db)):
    from jinja2 import Template as J
    res = await s.execute(select(Template).where(Template.code == code))
    t = res.scalar_one_or_none()
    if not t: raise HTTPException(404, "template not found")
    return {"subject": t.subject, "body": J(t.body).render(**variables)}
