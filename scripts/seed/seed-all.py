"""Master seed for ALL Shopnoltd platform services.
Run from project root: python3 scripts/seed/seed-all.py
"""
import os
ROOT = "/mnt/c/Users/asadu/PROJECTS/shopnoltd"

def W(p, c):
    fp = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    if not c.endswith("\n"): c += "\n"
    with open(fp, "w") as f: f.write(c)

def py_service(name, title, port=8080, db=None, routers=""):
    db = db or name.replace("-", "_")
    W(f"platform/{name}/Dockerfile", f"""FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd -g 10001 shopno && useradd -u 10001 -g shopno -d /app -s /sbin/nologin shopno
WORKDIR /app
COPY platform/{name}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY platform/{name}/app /app/app
COPY shared/libraries/python /app/shared
USER shopno
EXPOSE {port}
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:{port}/healthz').read()"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","{port}","--proxy-headers","--forwarded-allow-ips","*"]
""")
    W(f"platform/{name}/requirements.txt", """fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
redis==5.2.0
httpx==0.27.2
prometheus-client==0.21.0
structlog==24.4.0
""")
    W(f"platform/{name}/app/__init__.py", "")
    for d in ("core","api","models","schemas","providers","workers","migrations"):
        W(f"platform/{name}/app/{d}/__init__.py", "")
    W(f"platform/{name}/app/core/config.py", f'''from pydantic_settings import BaseSettings
from typing import List
class Settings(BaseSettings):
    app_name: str = "shopnoltd-{name}"
    env: str = "production"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/{db}"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "{name}"
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
''')
    W(f"platform/{name}/app/core/db.py", '''from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
''')
    W(f"platform/{name}/app/core/redis_client.py", '''from redis.asyncio import Redis
from app.core.config import settings
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
''')
    W(f"platform/{name}/app/core/security.py", '''import httpx
from jose import jwt, JWTError
from app.core.config import settings
_jwks_cache = None
async def _jwks():
    global _jwks_cache
    if _jwks_cache: return _jwks_cache
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{settings.keycloak_issuer}/protocol/openid-connect/certs")
        r.raise_for_status(); _jwks_cache = r.json()
    return _jwks_cache
async def verify_token(token: str) -> dict:
    try:
        h = jwt.get_unverified_header(token)
        keys = await _jwks()
        key = next(k for k in keys["keys"] if k["kid"] == h["kid"])
        return jwt.decode(token, key, algorithms=[key["alg"]], audience=settings.keycloak_audience, options={"verify_aud": True})
    except (JWTError, StopIteration) as e:
        raise ValueError(f"invalid token: {e}")
async def verify_token_admin(token: str) -> dict:
    u = await verify_token(token)
    if "admin" not in u.get("roles", []): raise PermissionError("admin only")
    return u
''')
    W(f"platform/{name}/app/main.py", f'''"""Shopnoltd {title}."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from starlette.responses import Response
import structlog
from app.core.config import settings
from app.core.db import engine, Base
from app.core.redis_client import redis_client
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    log.info("{name}.started", env=settings.env)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(title="Shopnoltd {title}", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
{routers}


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {{"status": "ok"}}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    from sqlalchemy import text
    async with engine.connect() as c:
        await c.execute(text("SELECT 1"))
    await redis_client.ping()
    return {{"status": "ready"}}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
''')

# Helper: append a router import
def router(name, modname, prefix, tag):
    return f'app.include_router(__import__("app.api.{modname}", fromlist=["router"]).router, prefix="{prefix}", tags=["{tag}"])\n'

# ----------------- MESSAGING-SERVICE -----------------
py_service("messaging-service", "Messaging Service", db="messaging",
    routers=router("messaging","conversations","/api/v1/conversations","conversations")
         + router("messaging","messages","/api/v1/messages","messages"))
W("platform/messaging-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index
import uuid
from datetime import datetime
from app.core.db import Base
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    type = Column(String(16), default="direct")  # direct, group
    title = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
class Participant(Base):
    __tablename__ = "participants"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_read_at = Column(DateTime)
    __table_args__ = (Index("ix_part_conv_user", "conversation_id", "user_id", unique=True),)
class Message(Base):
    __tablename__ = "messages"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String(64), nullable=False, index=True)
    body = Column(Text, nullable=False)
    attachments = Column(String, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    edited_at = Column(DateTime)
    deleted_at = Column(DateTime)
''')
W("platform/messaging-service/app/schemas/schemas.py", '''from pydantic import BaseModel
from typing import Optional
class ConvIn(BaseModel):
    type: str = "direct"
    title: Optional[str] = None
    participants: list
class ConvOut(BaseModel):
    id: str; type: str; title: Optional[str]; created_at: str
    class Config: from_attributes = True
class MsgIn(BaseModel):
    body: str
    attachments: list = []
class MsgOut(BaseModel):
    id: str; conversation_id: str; sender_id: str; body: str
    created_at: str
    class Config: from_attributes = True
''')
W("platform/messaging-service/app/api/conversations.py", '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Conversation, Participant
from app.schemas.schemas import ConvIn, ConvOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=ConvOut, status_code=201)
async def create(body: ConvIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    c = Conversation(tenant_id=user.get("tenant_id","default"), type=body.type, title=body.title)
    s.add(c); await s.flush()
    s.add(Participant(conversation_id=c.id, user_id=user["sub"], role="owner"))
    for p in body.participants:
        if p != user["sub"]:
            s.add(Participant(conversation_id=c.id, user_id=p))
    await s.commit(); await s.refresh(c)
    return ConvOut(id=c.id, type=c.type, title=c.title, created_at=c.created_at.isoformat())
@router.get("", response_model=list[ConvOut])
async def mine(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Conversation).join(Participant, Participant.conversation_id == Conversation.id)
        .where(Participant.user_id == user["sub"]).order_by(Conversation.created_at.desc())
    )
    return [ConvOut(id=c.id, type=c.type, title=c.title, created_at=c.created_at.isoformat()) for c in res.scalars().all()]
@router.get("/{conv_id}")
async def detail(conv_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Participant).where(Participant.conversation_id == conv_id, Participant.user_id == user["sub"]))
    if not res.scalar_one_or_none(): raise HTTPException(403, "not a participant")
    return {"id": conv_id}
''')
W("platform/messaging-service/app/api/messages.py", '''from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Message, Participant
from app.schemas.schemas import MsgIn, MsgOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/c/{conv_id}", response_model=MsgOut, status_code=201)
async def send(conv_id: str, body: MsgIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (await s.execute(select(Participant).where(Participant.conversation_id == conv_id, Participant.user_id == user["sub"]))).scalar_one_or_none()
    if not p: raise HTTPException(403, "not a participant")
    m = Message(conversation_id=conv_id, sender_id=user["sub"], body=body.body, attachments=body.attachments)
    s.add(m); await s.commit(); await s.refresh(m)
    return MsgOut(id=m.id, conversation_id=m.conversation_id, sender_id=m.sender_id, body=m.body, created_at=m.created_at.isoformat())
@router.get("/c/{conv_id}", response_model=list[MsgOut])
async def list_msgs(conv_id: str, user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    p = (await s.execute(select(Participant).where(Participant.conversation_id == conv_id, Participant.user_id == user["sub"]))).scalar_one_or_none()
    if not p: raise HTTPException(403, "not a participant")
    res = await s.execute(select(Message).where(Message.conversation_id == conv_id, Message.deleted_at == None).order_by(Message.created_at.desc()).limit(limit).offset(offset))
    return [MsgOut(id=m.id, conversation_id=m.conversation_id, sender_id=m.sender_id, body=m.body, created_at=m.created_at.isoformat()) for m in res.scalars().all()]
@router.delete("/{msg_id}")
async def delete(msg_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
    if not m: raise HTTPException(404, "msg not found")
    if m.sender_id != user["sub"]: raise HTTPException(403, "not your message")
    from datetime import datetime
    m.deleted_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
''')

# ----------------- MEET-SERVICE (Jitsi bridge) -----------------
py_service("meet-service", "Meet Service", db="meet",
    routers=router("meet","rooms","/api/v1/rooms","rooms"))
W("platform/meet-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Room(Base):
    __tablename__ = "rooms"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False, unique=True)
    owner_id = Column(String(64), nullable=False, index=True)
    password_hash = Column(String(256))
    is_recording = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
class Participant(Base):
    __tablename__ = "room_participants"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String(64), ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16), default="member")  # moderator, member
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime)
''')
W("platform/meet-service/app/schemas/schemas.py", '''from pydantic import BaseModel
from typing import Optional
class RoomIn(BaseModel):
    name: str
    password: Optional[str] = None
    recording: bool = False
class RoomOut(BaseModel):
    id: str; name: str; owner_id: str; is_recording: bool
    created_at: str; jitsi_url: str; jwt: str
''')
W("platform/meet-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-meet-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/meet"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    jitsi_jwt_app_id: str = "shopnoltd"
    jitsi_jwt_secret: str = "CHANGE_ME_JITSI_JWT"
    jitsi_url: str = "https://meet.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "meet-service"
settings = Settings()
''')
W("platform/meet-service/app/api/rooms.py", '''import jwt as pyjwt
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.models.models import Room, Participant
from app.schemas.schemas import RoomIn, RoomOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)

def make_jitsi_jwt(room: str, user_id: str, name: str, moderator: bool) -> str:
    return pyjwt.encode({
        "iss": settings.jitsi_jwt_app_id,
        "aud": settings.jitsi_jwt_app_id,
        "sub": settings.jitsi_url,
        "room": room,
        "exp": datetime.utcnow() + timedelta(hours=8),
        "nbf": datetime.utcnow(),
        "context": {"user": {"id": user_id, "name": name, "moderator": moderator}},
    }, settings.jitsi_jwt_secret, algorithm="HS256")

@router.post("", response_model=RoomOut, status_code=201)
async def create(body: RoomIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = Room(tenant_id=user.get("tenant_id","default"), name=body.name, owner_id=user["sub"], password_hash=secrets.hash(body.password) if body.password else None, is_recording=1 if body.recording else 0)
    s.add(r); await s.commit(); await s.refresh(r)
    s.add(Participant(room_id=r.id, user_id=user["sub"], role="moderator"))
    await s.commit()
    return RoomOut(id=r.id, name=r.name, owner_id=r.owner_id, is_recording=bool(r.is_recording), created_at=r.created_at.isoformat(), jitsi_url=f"{settings.jitsi_url}/{r.name}", jwt=make_jitsi_jwt(r.name, user["sub"], user.get("name", user["sub"]), True))
@router.get("/{name}/join", response_model=RoomOut)
async def join(name: str, password: Optional[str] = None, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Room).where(Room.name == name))
    r = res.scalar_one_or_none()
    if not r: raise HTTPException(404, "room not found")
    if r.password_hash and not secrets.compare_digest(secrets.hash(password) if password else "", r.password_hash):
        raise HTTPException(403, "wrong password")
    p = (await s.execute(select(Participant).where(Participant.room_id == r.id, Participant.user_id == user["sub"]))).scalar_one_or_none()
    if not p:
        s.add(Participant(room_id=r.id, user_id=user["sub"], role="member")); await s.commit()
    return RoomOut(id=r.id, name=r.name, owner_id=r.owner_id, is_recording=bool(r.is_recording), created_at=r.created_at.isoformat(), jitsi_url=f"{settings.jitsi_url}/{r.name}", jwt=make_jitsi_jwt(r.name, user["sub"], user.get("name", user["sub"]), False))
@router.get("", response_model=list[RoomOut])
async def list_rooms(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Room).where(Room.tenant_id == user.get("tenant_id","default")).order_by(Room.created_at.desc()).limit(100))
    return [RoomOut(id=r.id, name=r.name, owner_id=r.owner_id, is_recording=bool(r.is_recording), created_at=r.created_at.isoformat(), jitsi_url=f"{settings.jitsi_url}/{r.name}", jwt=make_jitsi_jwt(r.name, user["sub"], user.get("name", user["sub"]), False)) for r in res.scalars().all()]
@router.delete("/{name}")
async def end(name: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = (await s.execute(select(Room).where(Room.name == name))).scalar_one_or_none()
    if not r: raise HTTPException(404, "room not found")
    if r.owner_id != user["sub"]: raise HTTPException(403, "not owner")
    r.ended_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
''')

# ----------------- LIVE-SERVICE (Owncast bridge) -----------------
py_service("live-service", "Live Streaming Service", db="live",
    routers=router("live","streams","/api/v1/streams","streams"))
W("platform/live-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-live-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/live"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    owncast_admin_url: str = "https://live.shopnoltd.dpdns.org"
    owncast_api_key: str = "CHANGE_ME_OWNCAST_KEY"
    storage_service_url: str = "http://storage-service.shopno-platform.svc.cluster.local:8080"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "live-service"
settings = Settings()
''')
W("platform/live-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Boolean, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Stream(Base):
    __tablename__ = "streams"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    owner_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False, unique=True)
    title = Column(String(256))
    description = Column(String(2000))
    offline_banner = Column(String(256))
    recording_enabled = Column(Boolean, default=True)
    is_live = Column(Boolean, default=False)
    viewer_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
''')
W("platform/live-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class StreamIn(BaseModel):
    name: str; title: str; description: str = ""; recording_enabled: bool = True
class StreamOut(BaseModel):
    id: str; name: str; title: str; description: str
    is_live: bool; viewer_count: int
    rtmp_url: str; stream_key: str
    watch_url: str
    recording_storage_path: str
''')
W("platform/live-service/app/api/streams.py", '''import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.models.models import Stream
from app.schemas.schemas import StreamIn, StreamOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=StreamOut, status_code=201)
async def create(body: StreamIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    sk = secrets.token_urlsafe(24)
    st = Stream(tenant_id=user.get("tenant_id","default"), owner_id=user["sub"], name=body.name, title=body.title, description=body.description, recording_enabled=body.recording_enabled)
    s.add(st); await s.commit(); await s.refresh(st)
    return StreamOut(id=st.id, name=st.name, title=st.title, description=st.description, is_live=False, viewer_count=0, rtmp_url=f"rtmp://live.shopnoltd.dpdns.org/live", stream_key=sk, watch_url=f"https://live.shopnoltd.dpdns.org/{st.name}", recording_storage_path=f"s3://shopnoltd-live/{st.name}/")
@router.get("", response_model=list[StreamOut])
async def list_streams(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Stream).order_by(Stream.created_at.desc()).limit(100))
    out = []
    for st in res.scalars().all():
        out.append(StreamOut(id=st.id, name=st.name, title=st.title, description=st.description, is_live=st.is_live, viewer_count=st.viewer_count, rtmp_url="rtmp://live.shopnoltd.dpdns.org/live", stream_key="***", watch_url=f"https://live.shopnoltd.dpdns.org/{st.name}", recording_storage_path=f"s3://shopnoltd-live/{st.name}/"))
    return out
@router.get("/{name}", response_model=StreamOut)
async def get_stream(name: str, s: AsyncSession = Depends(db)):
    st = (await s.execute(select(Stream).where(Stream.name == name))).scalar_one_or_none()
    if not st: raise HTTPException(404, "stream not found")
    return StreamOut(id=st.id, name=st.name, title=st.title, description=st.description, is_live=st.is_live, viewer_count=st.viewer_count, rtmp_url="rtmp://live.shopnoltd.dpdns.org/live", stream_key="***", watch_url=f"https://live.shopnoltd.dpdns.org/{st.name}", recording_storage_path=f"s3://shopnoltd-live/{st.name}/")
@router.post("/{name}/status")
async def set_status(name: str, is_live: bool, viewer_count: int = 0, s: AsyncSession = Depends(db)):
    """Webhook from Owncast: updates DB and can notify followers."""
    st = (await s.execute(select(Stream).where(Stream.name == name))).scalar_one_or_none()
    if not st: raise HTTPException(404, "stream not found")
    st.is_live = is_live; st.viewer_count = viewer_count
    if is_live:
        async with httpx.AsyncClient() as c:
            await c.post("http://notification-service.shopno-platform.svc.cluster.local:8080/api/v1/notifications/broadcast",
                json={"channel": "push", "title": f"🔴 {st.title} is live", "body": st.description or st.name, "meta": {"stream": st.name}})
    await s.commit()
    return {"ok": True}
''')

# ----------------- MAIL-SERVICE (Mailcow bridge) -----------------
py_service("mail-service", "Mail Service", db="mail",
    routers=router("mail","domains","/api/v1/domains","domains")
         + router("mail","mailboxes","/api/v1/mailboxes","mailboxes")
         + router("mail","messages","/api/v1/messages","messages"))
W("platform/mail-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-mail-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/mail"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    mailcow_api_url: str = "https://mail.shopnoltd.dpdns.org/api/v1"
    mailcow_api_key: str = "CHANGE_ME_MAILCOW_KEY"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "mail-service"
settings = Settings()
''')
W("platform/mail-service/app/core/mailcow.py", '''import httpx
from app.core.config import settings
async def call_mailcow(action: str, payload: dict) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.mailcow_api_url}/{action}", json=payload, headers={"X-API-Key": settings.mailcow_api_key}, timeout=30)
    r.raise_for_status(); return r.json()
''')
W("platform/mail-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Integer, Boolean
import uuid
from datetime import datetime
from app.core.db import Base
class Domain(Base):
    __tablename__ = "domains"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), unique=True, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class Mailbox(Base):
    __tablename__ = "mailboxes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    domain_id = Column(String(64), nullable=False, index=True)
    local_part = Column(String(64), nullable=False)
    full_address = Column(String(256), unique=True, nullable=False)
    quota_mb = Column(Integer, default=1024)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class Message(Base):
    __tablename__ = "mail_messages"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    mailbox_id = Column(String(64), nullable=False, index=True)
    from_addr = Column(String(256), nullable=False)
    to_addrs = Column(String, default=list)
    subject = Column(String(512))
    body = Column(String)
    folder = Column(String(32), default="INBOX")
    read = Column(Boolean, default=False)
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
''')
W("platform/mail-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class DomainIn(BaseModel): name: str
class MailboxIn(BaseModel): local_part: str; quota_mb: int = 1024
''')
W("platform/mail-service/app/api/domains.py", '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.core.mailcow import call_mailcow
from app.models.models import Domain
from app.schemas.schemas import DomainIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", status_code=201)
async def add(body: DomainIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    d = Domain(tenant_id=user.get("tenant_id","default"), name=body.name)
    s.add(d); await s.commit()
    try:
        await call_mailcow("add/domain", {"domain": body.name, "active": "1"})
    except Exception: pass
    return {"id": d.id, "name": d.name}
@router.get("")
async def list_(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Domain))
    return [{"id": d.id, "name": d.name, "active": d.active} for d in res.scalars().all()]
''')
W("platform/mail-service/app/api/mailboxes.py", '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.core.mailcow import call_mailcow
from app.models.models import Mailbox, Domain
from app.schemas.schemas import MailboxIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("/{domain_id}", status_code=201)
async def add(domain_id: str, body: MailboxIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    d = (await s.execute(select(Domain).where(Domain.id == domain_id))).scalar_one_or_none()
    if not d: raise HTTPException(404, "domain not found")
    full = f"{body.local_part}@{d.name}"
    m = Mailbox(tenant_id=user.get("tenant_id","default"), domain_id=d.id, local_part=body.local_part, full_address=full, quota_mb=body.quota_mb)
    s.add(m); await s.commit()
    try:
        await call_mailcow("add/mailbox", {"local_part": body.local_part, "domain": d.name, "password": "change-me-immediately", "password2": "change-me-immediately", "quota": body.quota_mb, "active": "1"})
    except Exception: pass
    return {"id": m.id, "address": full}
@router.get("/{domain_id}")
async def list_mb(domain_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Mailbox).where(Mailbox.domain_id == domain_id))
    return [{"id": m.id, "address": m.full_address, "quota_mb": m.quota_mb, "active": m.active} for m in res.scalars().all()]
''')
W("platform/mail-service/app/api/messages.py", '''from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Message, Mailbox
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("/inbox/{mailbox_id}")
async def inbox(mailbox_id: str, user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    mb = (await s.execute(select(Mailbox).where(Mailbox.id == mailbox_id))).scalar_one_or_none()
    if not mb: raise HTTPException(404, "mailbox not found")
    res = await s.execute(select(Message).where(Message.mailbox_id == mailbox_id, Message.folder == "INBOX").order_by(desc(Message.received_at)).limit(limit).offset(offset))
    return [{"id": m.id, "from": m.from_addr, "subject": m.subject, "read": m.read, "received_at": m.received_at.isoformat()} for m in res.scalars().all()]
@router.get("/{msg_id}")
async def get(msg_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    m = (await s.execute(select(Message).where(Message.id == msg_id))).scalar_one_or_none()
    if not m: raise HTTPException(404, "not found")
    m.read = True; await s.commit()
    return {"id": m.id, "from": m.from_addr, "to": m.to_addrs, "subject": m.subject, "body": m.body, "received_at": m.received_at.isoformat()}
@router.post("/send")
async def send(from_mailbox_id: str, to: str, subject: str, body: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    mb = (await s.execute(select(Mailbox).where(Mailbox.id == from_mailbox_id))).scalar_one_or_none()
    if not mb: raise HTTPException(404, "from mailbox not found")
    from app.core.mailcow import call_mailcow
    try:
        await call_mailcow("add/message", {"from": mb.full_address, "to": to, "subject": subject, "plain": body})
    except Exception as e:
        raise HTTPException(500, f"send failed: {e}")
    return {"ok": True, "from": mb.full_address, "to": to}
''')

# ----------------- AI-PLATFORM -----------------
py_service("ai-platform", "AI Platform", port=8000, db="ai",
    routers=router("ai","inference","/api/v1/inference","inference")
         + router("ai","embeddings","/api/v1/embeddings","embeddings")
         + router("ai","documents","/api/v1/documents","documents")
         + router("ai","agents","/api/v1/agents","agents"))
W("platform/ai-platform/requirements.txt", """fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
redis==5.2.0
httpx==0.27.2
numpy==2.1.3
sentence-transformers==3.2.1
transformers==4.46.2
torch==2.5.0
pgvector==0.3.6
PyPDF2==3.0.1
python-docx==1.1.2
prometheus-client==0.21.0
structlog==24.4.0
""")
W("platform/ai-platform/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-ai-platform"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/ai"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model: str = "microsoft/Phi-3-mini-4k-instruct"
    llm_url: str = "http://localhost:11434"  # Ollama default
    storage_service_url: str = "http://storage-service.shopno-platform.svc.cluster.local:8080"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "ai-platform"
settings = Settings()
''')
W("platform/ai-platform/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.db import Base
class Document(Base):
    __tablename__ = "documents"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(256))
    source_uri = Column(String(512))
    text = Column(Text)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
class Chunk(Base):
    __tablename__ = "chunks"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(64), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    idx = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    # embedding stored as pgvector bytea in production; for simplicity keep as JSON
    embedding = Column(String)
class Agent(Base):
    __tablename__ = "agents"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    system_prompt = Column(Text, default="You are a helpful Shopnoltd assistant.")
    model = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
class Conversation(Base):
    __tablename__ = "ai_conversations"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(64), ForeignKey("agents.id"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16))  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
''')
W("platform/ai-platform/app/schemas/schemas.py", '''from pydantic import BaseModel
from typing import Optional
class InferIn(BaseModel):
    prompt: str
    agent_id: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.7
class InferOut(BaseModel):
    response: str
    model: str
    tokens: int
class EmbedIn(BaseModel):
    texts: list
class EmbedOut(BaseModel):
    embeddings: list
    model: str
    dim: int
class DocIn(BaseModel):
    title: str
    source_uri: Optional[str] = None
    text: Optional[str] = None
class AgentIn(BaseModel):
    name: str
    system_prompt: str = "You are a helpful Shopnoltd assistant."
    model: Optional[str] = None
''')
W("platform/ai-platform/app/api/inference.py", '''import httpx
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token
from app.core.config import settings
from app.schemas.schemas import InferIn, InferOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=InferOut)
async def infer(body: InferIn, user=Depends(current_user)):
    """Call local LLM (Ollama/vLLM) or fall back to stub."""
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{settings.llm_url}/api/generate", json={"model": settings.llm_model, "prompt": body.prompt, "stream": False})
        r.raise_for_status(); d = r.json()
        return InferOut(response=d.get("response", ""), model=settings.llm_model, tokens=d.get("eval_count", 0))
    except Exception as e:
        # Stub for when no LLM is running yet
        return InferOut(response=f"[Stub: would call {settings.llm_model}]: {body.prompt[:200]}", model=settings.llm_model, tokens=0)
''')
W("platform/ai-platform/app/api/embeddings.py", '''from fastapi import APIRouter, Depends
from app.core.security import verify_token
from app.core.config import settings
from app.schemas.schemas import EmbedIn, EmbedOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
_model = None
def load_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.embedding_model)
        except Exception:
            _model = "stub"
    return _model
@router.post("", response_model=EmbedOut)
async def embed(body: EmbedIn, user=Depends(current_user)):
    m = load_model()
    if m == "stub":
        import hashlib
        out = [[int.from_bytes(hashlib.md5(t.encode()).digest()[:4], "big") / 1e9 for _ in range(8)] for t in body.texts]
        return EmbedOut(embeddings=out, model=settings.embedding_model + " (stub)", dim=8)
    vecs = m.encode(body.texts).tolist()
    return EmbedOut(embeddings=vecs, model=settings.embedding_model, dim=len(vecs[0]) if vecs else 0)
''')
W("platform/ai-platform/app/api/documents.py", '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Document, Chunk
from app.schemas.schemas import DocIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
def chunk_text(t: str, size: int = 500) -> list:
    return [t[i:i+size] for i in range(0, len(t), size)]
@router.post("", status_code=201)
async def create(body: DocIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    d = Document(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], title=body.title, source_uri=body.source_uri, text=body.text, chunk_count=0)
    s.add(d); await s.commit(); await s.refresh(d)
    if body.text:
        chunks = chunk_text(body.text)
        for i, c in enumerate(chunks):
            s.add(Chunk(document_id=d.id, idx=i, text=c, embedding="[]"))
        d.chunk_count = len(chunks)
        await s.commit()
    return {"id": d.id, "title": d.title, "chunks": d.chunk_count}
@router.get("")
async def list_docs(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Document).where(Document.user_id == user["sub"]).order_by(Document.created_at.desc()).limit(100))
    return [{"id": d.id, "title": d.title, "chunk_count": d.chunk_count, "created_at": d.created_at.isoformat()} for d in res.scalars().all()]
@router.post("/{doc_id}/search")
async def search(doc_id: str, query: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Chunk).where(Chunk.document_id == doc_id))
    chunks = res.scalars().all()
    scored = sorted([(c, query.lower().count(c.text.lower()[:50].split()[0] if c.text else "")) for c in chunks], key=lambda x: x[1], reverse=True)
    return [{"idx": c.idx, "text": c.text[:300], "score": score} for c, score in scored[:5]]
''')
W("platform/ai-platform/app/api/agents.py", '''from fastapi import APIRouter, Depends, HTTPException
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
    r = await infer(InferIn(prompt=f"{a.system_prompt}\\n\\nUser: {message}\\nAssistant:", agent_id=a.id), user)
    s.add(Conversation(agent_id=a.id, user_id=user["sub"], role="assistant", content=r.response)); await s.commit()
    return {"response": r.response}
''')

# ----------------- ANALYTICS-SERVICE -----------------
py_service("analytics-service", "Analytics Service", db="analytics",
    routers=router("analytics","events","/api/v1/events","events")
         + router("analytics","reports","/api/v1/reports","reports"))
W("platform/analytics-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-analytics-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/analytics"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "analytics-service"
settings = Settings()
''')
W("platform/analytics-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Integer, Index
import uuid
from datetime import datetime
from app.core.db import Base
class Event(Base):
    __tablename__ = "events"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), index=True)
    name = Column(String(128), nullable=False, index=True)
    properties = Column(String, default="{}")
    source = Column(String(64), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (Index("ix_event_tenant_name_time", "tenant_id", "name", "created_at"),)
''')
W("platform/analytics-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class EventIn(BaseModel):
    name: str
    properties: dict = {}
    source: str = "unknown"
''')
W("platform/analytics-service/app/api/events.py", '''import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Event
from app.schemas.schemas import EventIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def track(body: EventIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    e = Event(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], name=body.name, properties=json.dumps(body.properties), source=body.source)
    s.add(e); await s.commit()
    return {"id": e.id}
@router.get("/count")
async def count(name: str, days: int = 7, user=Depends(current_user), s: AsyncSession = Depends(db)):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(select(func.count(Event.id)).where(Event.tenant_id == user.get("tenant_id","default"), Event.name == name, Event.created_at >= since))
    return {"name": name, "days": days, "count": res.scalar()}
@router.get("/top")
async def top(days: int = 7, limit: int = 20, user=Depends(current_user), s: AsyncSession = Depends(db)):
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(
        select(Event.name, func.count(Event.id).label("c"))
        .where(Event.tenant_id == user.get("tenant_id","default"), Event.created_at >= since)
        .group_by(Event.name).order_by(desc("c")).limit(limit))
    return [{"name": n, "count": c} for n, c in res.all()]
''')
W("platform/analytics-service/app/api/reports.py", '''from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Event
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("/daily-active-users")
async def dau(days: int = 30, user=Depends(current_user), s: AsyncSession = Depends(db)):
    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(
        select(func.date_trunc("day", Event.created_at).label("day"), func.count(func.distinct(Event.user_id)).label("u"))
        .where(Event.tenant_id == user.get("tenant_id","default"), Event.created_at >= since)
        .group_by("day").order_by("day"))
    return [{"day": str(d), "users": u} for d, u in res.all()]
@router.get("/revenue")
async def revenue(days: int = 30, user=Depends(current_user), s: AsyncSession = Depends(db)):
    since = datetime.utcnow() - timedelta(days=days)
    res = await s.execute(
        select(func.date_trunc("day", Event.created_at).label("day"), func.sum(Event.properties.cast(__import__("sqlalchemy").Numeric)).label("r"))
        .where(Event.tenant_id == user.get("tenant_id","default"), Event.name == "payment.completed", Event.created_at >= since)
        .group_by("day").order_by("day"))
    return [{"day": str(d), "revenue": float(r or 0)} for d, r in res.all()]
''')

# ----------------- SEARCH-SERVICE (OpenSearch bridge) -----------------
py_service("search-service", "Search Service", db="search",
    routers=router("search","search","/api/v1/search","search")
         + router("search","indexes","/api/v1/indexes","indexes"))
W("platform/search-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-search-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/search"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    opensearch_url: str = "https://opensearch.shopno-data.svc.cluster.local:9200"
    opensearch_user: str = "admin"
    opensearch_password: str = "CHANGE_ME"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "search-service"
settings = Settings()
''')
W("platform/search-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Index(Base):
    __tablename__ = "indexes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(64), nullable=False, unique=True)
    doc_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
''')
W("platform/search-service/app/schemas/schemas.py", '''from pydantic import BaseModel
from typing import Optional
class IndexIn(BaseModel): name: str
class DocIn(BaseModel): index: str; id: str; body: dict
class SearchIn(BaseModel):
    index: str
    query: str
    fields: Optional[list] = None
    size: int = 20
''')
W("platform/search-service/app/api/indexes.py", '''import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token_admin
from app.models.models import Index
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", status_code=201)
async def create(name: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    i = Index(tenant_id=user.get("tenant_id","default"), name=name)
    s.add(i); await s.commit()
    try:
        async with httpx.AsyncClient() as c:
            await c.put(f"{settings.opensearch_url}/{name}", auth=(settings.opensearch_user, settings.opensearch_password), json={"mappings": {"properties": {"title": {"type": "text"}, "body": {"type": "text"}, "tenant_id": {"type": "keyword"}}}}, timeout=10)
    except Exception: pass
    return {"id": i.id, "name": i.name}
@router.post("/doc")
async def add_doc(index: str, id: str, body: dict, s: AsyncSession = Depends(db)):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.put(f"{settings.opensearch_url}/{index}/_doc/{id}", auth=(settings.opensearch_user, settings.opensearch_password), json=body, timeout=10)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(500, f"opensearch: {e}")
    return {"ok": True}
''')
W("platform/search-service/app/api/search.py", '''import httpx
from fastapi import APIRouter, Depends
from app.core.config import settings
from app.core.security import verify_token
from app.schemas.schemas import SearchIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("")
async def search(body: SearchIn, user=Depends(current_user)):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{settings.opensearch_url}/{body.index}/_search", auth=(settings.opensearch_user, settings.opensearch_password), json={"query": {"multi_match": {"query": body.query, "fields": body.fields or ["title^2", "body"]}}, "size": body.size}, timeout=10)
        r.raise_for_status(); d = r.json()
        return {"total": d.get("hits",{}).get("total",{}).get("value",0), "hits": [h["_source"] for h in d.get("hits",{}).get("hits",[])]}
    except Exception as e:
        return {"total": 0, "hits": [], "error": str(e)}
''')

# ----------------- AUDIT-SERVICE -----------------
py_service("audit-service", "Audit Service", db="audit",
    routers=router("audit","logs","/api/v1/logs","logs"))
W("platform/audit-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Text, Index
import uuid, hashlib, json
from datetime import datetime
from app.core.db import Base
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(64), index=True)
    action = Column(String(128), nullable=False, index=True)
    resource = Column(String(128))
    resource_id = Column(String(128))
    ip = Column(String(64))
    user_agent = Column(String(256))
    data = Column(Text, default="{}")
    prev_hash = Column(String(64))
    hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (Index("ix_audit_tenant_time", "tenant_id", "created_at"),)
''')
W("platform/audit-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class LogIn(BaseModel):
    action: str
    resource: str = None
    resource_id: str = None
    data: dict = {}
''')
W("platform/audit-service/app/api/logs.py", '''import hashlib, json
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import AuditLog
from app.schemas.schemas import LogIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def log(body: LogIn, request: Request, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(AuditLog).where(AuditLog.tenant_id == user.get("tenant_id","default")).order_by(AuditLog.created_at.desc()).limit(1))
    prev = res.scalar_one_or_none()
    payload = {"tenant_id": user.get("tenant_id","default"), "actor_id": user["sub"], "action": body.action, "resource": body.resource, "data": body.data, "prev_hash": prev.hash if prev else ""}
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    e = AuditLog(tenant_id=payload["tenant_id"], actor_id=payload["actor_id"], action=body.action, resource=body.resource, resource_id=body.resource_id, ip=request.client.host if request.client else "", user_agent=request.headers.get("user-agent",""), data=json.dumps(body.data), prev_hash=payload["prev_hash"], hash=h)
    s.add(e); await s.commit()
    return {"id": e.id, "hash": h}
@router.get("")
async def list_(action: str = None, limit: int = Query(100, le=500), user=Depends(current_user), s: AsyncSession = Depends(db)):
    q = select(AuditLog).where(AuditLog.tenant_id == user.get("tenant_id","default"))
    if action: q = q.where(AuditLog.action == action)
    q = q.order_by(AuditLog.created_at.desc()).limit(limit)
    res = await s.execute(q)
    return [{"id": e.id, "actor_id": e.actor_id, "action": e.action, "resource": e.resource, "created_at": e.created_at.isoformat(), "hash": e.hash[:16]} for e in res.scalars().all()]
@router.get("/verify")
async def verify(limit: int = Query(1000, le=5000), user=Depends(current_user), s: AsyncSession = Depends(db)):
    """Walk the hash chain to prove no tampering."""
    res = await s.execute(select(AuditLog).where(AuditLog.tenant_id == user.get("tenant_id","default")).order_by(AuditLog.created_at.asc()).limit(limit))
    rows = res.scalars().all()
    valid = 0
    for e in rows:
        payload = {"tenant_id": e.tenant_id, "actor_id": e.actor_id, "action": e.action, "resource": e.resource, "data": json.loads(e.data or "{}"), "prev_hash": e.prev_hash}
        h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        if h == e.hash: valid += 1
    return {"checked": len(rows), "valid": valid, "tampered": len(rows) - valid}
''')

# ----------------- REPORT-SERVICE -----------------
py_service("report-service", "Report Service", db="reports",
    routers=router("report","reports","/api/v1/reports","reports"))
W("platform/report-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-report-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/reports"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    storage_service_url: str = "http://storage-service.shopno-platform.svc.cluster.local:8080"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "report-service"
settings = Settings()
''')
W("platform/report-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime
import uuid
from datetime import datetime
from app.core.db import Base
class Report(Base):
    __tablename__ = "reports"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    kind = Column(String(32), default="pdf")  # pdf, csv
    query_sql = Column(String)
    status = Column(String(16), default="queued")
    file_path = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow)
''')
W("platform/report-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class ReportIn(BaseModel):
    name: str
    kind: str = "pdf"
    query_sql: str = None
''')
W("platform/report-service/app/api/reports.py", '''import csv, io
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Report
from app.schemas.schemas import ReportIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", status_code=201)
async def create(body: ReportIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = Report(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], name=body.name, kind=body.kind, query_sql=body.query_sql, status="queued")
    s.add(r); await s.commit()
    return {"id": r.id, "status": r.status}
@router.post("/{report_id}/csv")
async def make_csv(report_id: str, rows: list, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = (await s.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if not r: raise HTTPException(404, "report not found")
    buf = io.StringIO()
    if rows: writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys())); writer.writeheader(); writer.writerows(rows)
    r.status = "ready"; r.file_path = f"/tmp/{report_id}.csv"; await s.commit()
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={r.name}.csv"})
@router.get("/{report_id}")
async def get(report_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    r = (await s.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
    if not r: raise HTTPException(404, "report not found")
    return {"id": r.id, "name": r.name, "kind": r.kind, "status": r.status, "file_path": r.file_path}
@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Report).where(Report.user_id == user["sub"]).order_by(Report.created_at.desc()).limit(100))
    return [{"id": r.id, "name": r.name, "kind": r.kind, "status": r.status, "created_at": r.created_at.isoformat()} for r in res.scalars().all()]
''')

# ----------------- LICENSE-SERVICE -----------------
py_service("license-service", "License Service", db="licenses",
    routers=router("license","licenses","/api/v1/licenses","licenses"))
W("platform/license-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Integer, JSON
import uuid
from datetime import datetime
from app.core.db import Base
class License(Base):
    __tablename__ = "licenses"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    key = Column(String(128), unique=True, nullable=False)
    plan = Column(String(64), nullable=False)
    features = Column(JSON, default=dict)
    seats = Column(Integer, default=1)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
''')
W("platform/license-service/app/schemas/schemas.py", '''from pydantic import BaseModel
from datetime import datetime
class LicenseIn(BaseModel):
    plan: str; features: dict = {}; seats: int = 1; expires_at: datetime
class LicenseOut(BaseModel):
    key: str; plan: str; seats: int; expires_at: datetime; features: dict
''')
W("platform/license-service/app/api/licenses.py", '''import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token_admin
from app.models.models import License
from app.schemas.schemas import LicenseIn, LicenseOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", response_model=LicenseOut, status_code=201)
async def create(body: LicenseIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    k = f"SHOPNO-{secrets.token_urlsafe(16).upper()}"
    lic = License(tenant_id=user.get("tenant_id","default"), key=k, plan=body.plan, features=body.features, seats=body.seats, expires_at=body.expires_at)
    s.add(lic); await s.commit()
    return LicenseOut(key=lic.key, plan=lic.plan, seats=lic.seats, expires_at=lic.expires_at, features=lic.features)
@router.post("/verify")
async def verify(key: str, s: AsyncSession = Depends(db)):
    lic = (await s.execute(select(License).where(License.key == key, License.revoked == 0))).scalar_one_or_none()
    if not lic: raise HTTPException(404, "invalid license")
    if lic.expires_at < datetime.utcnow(): raise HTTPException(403, "license expired")
    return {"valid": True, "plan": lic.plan, "seats": lic.seats, "features": lic.features, "expires_at": lic.expires_at.isoformat()}
@router.get("")
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(License).where(License.tenant_id == user.get("tenant_id","default")))
    return [{"key": l.key, "plan": l.plan, "seats": l.seats, "expires_at": l.expires_at.isoformat(), "revoked": bool(l.revoked)} for l in res.scalars().all()]
''')

print("✅ messaging, meet, live, mail, ai, analytics, search, audit, report, license seeded")
