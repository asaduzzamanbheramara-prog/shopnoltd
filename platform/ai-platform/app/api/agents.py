from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Agent, Conversation
from app.schemas.schemas import AgentIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def create(body: AgentIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    a = Agent(tenant_id=user.get("tenant_id","default"), name=body.name, system_prompt=body.system_prompt, model=body.model)
    s.add(a); await s.commit()
    return {"id": a.id, "name": a.name}
@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Agent).where(Agent.tenant_id == user.get("tenant_id","default")))
    return [{"id": a.id, "name": a.name, "model": a.model} for a in res.scalars().all()]
@router.post("/{agent_id}/chat")
async def chat(agent_id: str, message: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    a = (await s.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not a: raise HTTPException(404, "agent not found")
    s.add(Conversation(agent_id=a.id, user_id=user["sub"], role="user", content=message)); await s.commit()
    from app.api.inference import infer
    from app.schemas.schemas import InferIn
    r = await infer(InferIn(prompt=f"{a.system_prompt}\n\nUser: {message}\nAssistant:", agent_id=a.id), user)
    s.add(Conversation(agent_id=a.id, user_id=user["sub"], role="assistant", content=r.response)); await s.commit()
    return {"response": r.response}
