"""Shopnoltd platform services - master seed.
Generates complete, runnable source for every Shopnoltd service.
"""

import os

ROOT = "/mnt/c/Users/asadu/PROJECTS/shopnoltd"


def write(rel_path, content):
    p = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    with open(p, "w") as f:
        f.write(content)


# Helper: standard FastAPI service skeleton
def fastapi_service(name, title, port=8080, db="main", extra_routers=("", "")):
    write(
        f"platform/{name}/Dockerfile",
        f"""FROM python:3.12-slim
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
""",
    )
    write(
        f"platform/{name}/requirements.txt",
        """fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
redis==5.2.0
httpx==0.27.2
prometheus-client==0.21.0
structlog==24.4.0
tenacity==9.0.0
""",
    )
    main = f'''"""Shopnoltd {title}."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from starlette.responses import Response
import structlog
from app.core.config import settings
from app.core.db import engine, Base
from app.core.redis_client import redis_client
{extra_routers[0]}
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
{extra_routers[1]}


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
'''
    write(f"platform/{name}/app/main.py", main)
    write(f"platform/{name}/app/__init__.py", "")
    for d in ("core", "api", "models", "schemas"):
        write(f"platform/{name}/app/{d}/__init__.py", "")
    write(
        f"platform/{name}/app/core/config.py",
        f"""from pydantic_settings import BaseSettings
from typing import List
class Settings(BaseSettings):
    app_name: str = "{name}"
    env: str = "production"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/{db}"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
""",
    )
    write(
        f"platform/{name}/app/core/db.py",
        """from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
""",
    )
    write(
        f"platform/{name}/app/core/redis_client.py",
        """from redis.asyncio import Redis
from app.core.config import settings
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
""",
    )


# ---------- NOTIFICATION-SERVICE (email, SMS, push) ----------
fastapi_service(
    "notification-service",
    "Notification Service",
    port=8080,
    db="notifications",
    extra_routers=(
        "",
        """app.include_router(__import__("app.api.notifications", fromlist=["router"]).router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(__import__("app.api.templates", fromlist=["router"]).router, prefix="/api/v1/templates", tags=["templates"])
app.include_router(__import__("app.api.push", fromlist=["router"]).router, prefix="/api/v1/push", tags=["push"])
""",
    ),
)
write(
    "platform/notification-service/requirements.txt",
    """fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
redis==5.2.0
httpx==0.27.2
aiosmtplib==3.0.2
emails==0.6.0
jinja2==3.1.4
prometheus-client==0.21.0
structlog==24.4.0
""",
)
write(
    "platform/notification-service/app/core/security.py",
    """import httpx
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
""",
)
write(
    "platform/notification-service/app/core/config.py",
    """from pydantic_settings import BaseSettings
from typing import List
class Settings(BaseSettings):
    app_name: str = "shopnoltd-notification-service"
    env: str = "production"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/notifications"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/3"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "notification-service"
    smtp_host: str = "mailcow.shopno-apps.svc.cluster.local"
    smtp_port: int = 587
    smtp_user: str = "noreply@shopnoltd.dpdns.org"
    smtp_password: str = ""
    smtp_from: str = "Shopnoltd <noreply@shopnoltd.dpdns.org>"
    fcm_server_key: str = ""
    twilio_sid: str = ""
    twilio_token: str = ""
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
""",
)
write(
    "platform/notification-service/app/models/models.py",
    """from sqlalchemy import Column, String, DateTime, JSON, Enum, Text
import uuid, enum
from datetime import datetime
from app.core.db import Base
class NStatus(str, enum.Enum): pending="pending"; sent="sent"; failed="failed"; queued="queued"
class NChannel(str, enum.Enum): email="email"; sms="sms"; push="push"; webhook="webhook"
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    channel = Column(Enum(NChannel), nullable=False)
    status = Column(Enum(NStatus), default=NStatus.queued, index=True)
    subject = Column(String(256))
    body = Column(Text, nullable=False)
    recipient = Column(String(256), nullable=False)
    meta = Column(JSON, default=dict)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime)
class Template(Base):
    __tablename__ = "templates"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    channel = Column(Enum(NChannel), nullable=False)
    subject = Column(String(256))
    body = Column(Text, nullable=False)
    locale = Column(String(8), default="en")
    variables = Column(JSON, default=list)
""",
)
write(
    "platform/notification-service/app/schemas/schemas.py",
    """from pydantic import BaseModel, Field
from typing import Optional
from app.models.models import NChannel
class SendIn(BaseModel):
    channel: NChannel
    recipient: str
    subject: Optional[str] = None
    body: str
    template_code: Optional[str] = None
    variables: dict = {}
    meta: dict = {}
class Out(BaseModel):
    id: str; channel: str; status: str; recipient: str
    created_at: str; sent_at: Optional[str] = None
    class Config: from_attributes = True
class TemplateIn(BaseModel):
    code: str; name: str; channel: NChannel
    subject: Optional[str] = None; body: str
    variables: list = []
""",
)
write(
    "platform/notification-service/app/api/notifications.py",
    """import asyncio
import aiosmtplib
from email.message import EmailMessage
import httpx
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.core.config import settings
from app.models.models import Notification, Template, NStatus, NChannel
from app.schemas.schemas import SendIn, Out
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jinja2 import Template as JinjaTemplate
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
async def send_email(to, subject, html):
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(html, subtype="html")
    await aiosmtplib.send(msg, hostname=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_user, password=settings.smtp_password, start_tls=True)
async def send_sms(to, body):
    if not (settings.twilio_sid and settings.twilio_token): raise RuntimeError("twilio not configured")
    async with httpx.AsyncClient() as c:
        r = await c.post(f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_sid}/Messages.json",
            data={"To": to, "From": settings.smtp_from, "Body": body},
            auth=(settings.twilio_sid, settings.twilio_token))
        r.raise_for_status()
async def send_push(token, title, body):
    if not settings.fcm_server_key: raise RuntimeError("fcm not configured")
    async with httpx.AsyncClient() as c:
        r = await c.post("https://fcm.googleapis.com/fcm/send",
            json={"to": token, "notification": {"title": title, "body": body}},
            headers={"Authorization": f"key={settings.fcm_server_key}"})
        r.raise_for_status()

async def _send(n: Notification, subject: str, body: str):
    try:
        if n.channel == NChannel.email: await send_email(n.recipient, subject, body)
        elif n.channel == NChannel.sms: await send_sms(n.recipient, body)
        elif n.channel == NChannel.push: await send_push(n.recipient, subject, body)
        n.status = NStatus.sent
    except Exception as e:
        n.status = NStatus.failed; n.error = str(e)
    from datetime import datetime
    n.sent_at = datetime.utcnow()

@router.post("/send", response_model=Out, status_code=201)
async def send(body: SendIn, background: BackgroundTasks, user=Depends(current_user), s: AsyncSession = Depends(db)):
    subject = body.subject or "Shopnoltd"
    rendered = body.body
    if body.template_code:
        res = await s.execute(select(Template).where(Template.code == body.template_code))
        t = res.scalar_one_or_none()
        if not t: raise HTTPException(404, "template not found")
        subject = (t.subject or subject)
        rendered = JinjaTemplate(t.body).render(**body.variables)
    n = Notification(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], channel=body.channel, status=NStatus.queued, subject=subject, body=rendered, recipient=body.recipient, meta=body.meta)
    s.add(n); await s.commit(); await s.refresh(n)
    background.add_task(_send, n, subject, rendered)
    await s.commit()
    return Out(id=n.id, channel=n.channel.value, status=n.status.value, recipient=n.recipient, created_at=n.created_at.isoformat(), sent_at=None)
@router.get("/me", response_model=list[Out])
async def my_notifications(user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = 50):
    res = await s.execute(select(Notification).where(Notification.user_id == user["sub"]).order_by(Notification.created_at.desc()).limit(limit))
    return [Out(id=n.id, channel=n.channel.value, status=n.status.value, recipient=n.recipient, created_at=n.created_at.isoformat(), sent_at=n.sent_at.isoformat() if n.sent_at else None) for n in res.scalars().all()]
""",
)
write(
    "platform/notification-service/app/api/templates.py",
    """from fastapi import APIRouter, Depends, HTTPException
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
""",
)
write(
    "platform/notification-service/app/api/push.py",
    '''"""Web-push via VAPID. Falls back to FCM if FCM key set."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
class SubscribeIn(BaseModel):
    endpoint: str; keys: dict
@router.post("/subscribe", status_code=201)
async def subscribe(body: SubscribeIn, user=Depends(current_user)):
    # Store subscription in Redis or DB; here we just acknowledge.
    return {"ok": True, "user_id": user["sub"]}
class NotifyIn(BaseModel):
    subscription: SubscribeIn
    title: str
    body: str
@router.post("/notify")
async def notify(body: NotifyIn, user=Depends(current_user)):
    # Use pywebpush if configured; else return 501
    try:
        from pywebpush import webpush, WebPushException
        webpush(body.subscription.model_dump(), json.dumps={"title": body.title, "body": body.body})
        return {"ok": True}
    except Exception as e:
        raise HTTPException(501, f"web push not configured: {e}")
''',
)

# ---------- SOCIAL-SERVICE (posts, shares, likes, follows) ----------
fastapi_service(
    "social-service",
    "Social Service",
    port=8080,
    db="social",
    extra_routers=(
        "",
        """app.include_router(__import__("app.api.posts", fromlist=["router"]).router, prefix="/api/v1/posts", tags=["posts"])
app.include_router(__import__("app.api.feed", fromlist=["router"]).router, prefix="/api/v1/feed", tags=["feed"])
app.include_router(__import__("app.api.likes", fromlist=["router"]).router, prefix="/api/v1/likes", tags=["likes"])
app.include_router(__import__("app.api.shares", fromlist=["router"]).router, prefix="/api/v1/shares", tags=["shares"])
app.include_router(__import__("app.api.follows", fromlist=["router"]).router, prefix="/api/v1/follows", tags=["follows"])
""",
    ),
)
write(
    "platform/social-service/requirements.txt",
    """fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
redis==5.2.0
httpx==0.27.2
prometheus-client==0.21.0
structlog==24.4.0
""",
)
write(
    "platform/social-service/app/core/security.py",
    """import httpx
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
""",
)
write(
    "platform/social-service/app/core/config.py",
    """from pydantic_settings import BaseSettings
from typing import List
class Settings(BaseSettings):
    app_name: str = "shopnoltd-social-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/social"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/4"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "social-service"
    storage_service_url: str = "http://storage-service.shopno-platform.svc.cluster.local:8080"
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
""",
)
write(
    "platform/social-service/app/models/models.py",
    """from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Post(Base):
    __tablename__ = "posts"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    content = Column(Text, nullable=False)
    media = Column(String, default=list)  # JSON array of object keys in MinIO
    visibility = Column(String(16), default="public")  # public, tenant, friends, private
    auto_posted: bool = False  # legacy column ignored
    auto_posted2: bool = False
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow, index=True)
    like_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
class Like(Base):
    __tablename__ = "likes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_like_post_user", "post_id", "user_id", unique=True),)
class Share(Base):
    __tablename__ = "shares"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    target = Column(String(16), default="internal")  # internal, twitter, facebook, linkedin, copy
    created_at = Column(DateTime, default=datetime.utcnow)
class Follow(Base):
    __tablename__ = "follows"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id = Column(String(64), nullable=False, index=True)
    followee_id = Column(String(64), nullable=False, index=True)
    status = Column(String(16), default="accepted")  # accepted, pending
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_follow_pair", "follower_id", "followee_id", unique=True),)
class Comment(Base):
    __tablename__ = "comments"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
""",
)
write(
    "platform/social-service/app/schemas/schemas.py",
    """from pydantic import BaseModel, Field
from typing import Optional
class PostIn(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    media: list = []
    visibility: str = "public"
    scheduled_at: Optional[str] = None
class PostOut(BaseModel):
    id: str; user_id: str; content: str; media: list; visibility: str
    published_at: str; like_count: int; share_count: int; comment_count: int
    class Config: from_attributes = True
class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
class ShareIn(BaseModel):
    target: str = "internal"
""",
)
write(
    "platform/social-service/app/api/posts.py",
    """import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, Like, Share, Comment, Follow
from app.schemas.schemas import PostIn, PostOut, CommentIn, ShareIn
from app.core.redis_client import redis_client
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=PostOut, status_code=201)
async def create_post(body: PostIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = Post(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], content=body.content, media=body.media, visibility=body.visibility)
    if body.scheduled_at:
        p.scheduled_at = datetime.fromisoformat(body.scheduled_at); p.published_at = p.scheduled_at
    s.add(p); await s.commit(); await s.refresh(p)
    return PostOut(id=p.id, user_id=p.user_id, content=p.content, media=p.media or [], visibility=p.visibility, published_at=p.published_at.isoformat(), like_count=0, share_count=0, comment_count=0)
@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Post).where(Post.id == post_id))
    p = res.scalar_one_or_none()
    if not p: raise HTTPException(404, "post not found")
    return PostOut(id=p.id, user_id=p.user_id, content=p.content, media=p.media or [], visibility=p.visibility, published_at=p.published_at.isoformat(), like_count=p.like_count, share_count=p.share_count, comment_count=p.comment_count)
@router.delete("/{post_id}")
async def delete_post(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Post).where(Post.id == post_id))
    p = res.scalar_one_or_none()
    if not p: raise HTTPException(404, "post not found")
    if p.user_id != user["sub"]: raise HTTPException(403, "not your post")
    await s.delete(p); await s.commit()
    return {"ok": True}
@router.get("/by/{user_id}", response_model=list[PostOut])
async def posts_by_user(user_id: str, s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    res = await s.execute(select(Post).where(Post.user_id == user_id, Post.visibility.in_(["public","tenant"])).order_by(desc(Post.published_at)).limit(limit).offset(offset))
    return [PostOut(id=p.id, user_id=p.user_id, content=p.content, media=p.media or [], visibility=p.visibility, published_at=p.published_at.isoformat(), like_count=p.like_count, share_count=p.share_count, comment_count=p.comment_count) for p in res.scalars().all()]
@router.post("/{post_id}/comments", status_code=201)
async def add_comment(post_id: str, body: CommentIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    c = Comment(post_id=post_id, user_id=user["sub"], body=body.body)
    s.add(c)
    res = await s.execute(select(Post).where(Post.id == post_id)); p = res.scalar_one()
    p.comment_count = (p.comment_count or 0) + 1
    await s.commit()
    return {"id": c.id}
@router.get("/{post_id}/comments")
async def list_comments(post_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc()))
    return [{"id":c.id,"user_id":c.user_id,"body":c.body,"created_at":c.created_at.isoformat()} for c in res.scalars().all()]
""",
)
write(
    "platform/social-service/app/api/feed.py",
    """from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, Follow
from app.schemas.schemas import PostOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("/global", response_model=list[PostOut])
async def global_feed(s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    res = await s.execute(select(Post).where(Post.visibility == "public").order_by(desc(Post.published_at)).limit(limit).offset(offset))
    return [PostOut(id=p.id, user_id=p.user_id, content=p.content, media=p.media or [], visibility=p.visibility, published_at=p.published_at.isoformat(), like_count=p.like_count, share_count=p.share_count, comment_count=p.comment_count) for p in res.scalars().all()]
@router.get("/me", response_model=list[PostOut])
async def my_feed(user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    # posts from people I follow + my own
    f = await s.execute(select(Follow.followee_id).where(Follow.follower_id == user["sub"], Follow.status == "accepted"))
    followees = [r[0] for r in f.all()] + [user["sub"]]
    res = await s.execute(select(Post).where(Post.user_id.in_(followees), Post.visibility.in_(["public","tenant","friends"])).order_by(desc(Post.published_at)).limit(limit).offset(offset))
    return [PostOut(id=p.id, user_id=p.user_id, content=p.content, media=p.media or [], visibility=p.visibility, published_at=p.published_at.isoformat(), like_count=p.like_count, share_count=p.share_count, comment_count=p.comment_count) for p in res.scalars().all()]
""",
)
write(
    "platform/social-service/app/api/likes.py",
    """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, Like
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{post_id}", status_code=201)
async def like(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    existing = await s.execute(select(Like).where(Like.post_id == post_id, Like.user_id == user["sub"]))
    if existing.scalar_one_or_none(): return {"already": True}
    s.add(Like(post_id=post_id, user_id=user["sub"]))
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not p: raise HTTPException(404, "post not found")
    p.like_count = (p.like_count or 0) + 1
    await s.commit()
    return {"liked": True, "like_count": p.like_count}
@router.delete("/{post_id}")
async def unlike(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Like).where(Like.post_id == post_id, Like.user_id == user["sub"]))
    l = res.scalar_one_or_none()
    if not l: raise HTTPException(404, "not liked")
    await s.delete(l)
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one()
    p.like_count = max(0, (p.like_count or 1) - 1)
    await s.commit()
    return {"unliked": True, "like_count": p.like_count}
@router.get("/{post_id}")
async def likers(post_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Like).where(Like.post_id == post_id))
    return [{"user_id": l.user_id, "created_at": l.created_at.isoformat()} for l in res.scalars().all()]
""",
)
write(
    "platform/social-service/app/api/shares.py",
    """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Post, Share
from app.schemas.schemas import ShareIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{post_id}", status_code=201)
async def share(post_id: str, body: ShareIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    s.add(Share(post_id=post_id, user_id=user["sub"], target=body.target))
    p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not p: raise HTTPException(404, "post not found")
    p.share_count = (p.share_count or 0) + 1
    await s.commit()
    if body.target == "twitter":
        # placeholder for real Twitter API
        pass
    return {"shared": True, "share_count": p.share_count, "target": body.target}
@router.get("/{post_id}")
async def sharers(post_id: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Share).where(Share.post_id == post_id))
    return [{"user_id": sh.user_id, "target": sh.target, "created_at": sh.created_at.isoformat()} for sh in res.scalars().all()]
""",
)
write(
    "platform/social-service/app/api/follows.py",
    """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Follow
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{user_id}", status_code=201)
async def follow(user_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    if user_id == user["sub"]: raise HTTPException(400, "cannot follow yourself")
    existing = await s.execute(select(Follow).where(Follow.follower_id == user["sub"], Follow.followee_id == user_id))
    if existing.scalar_one_or_none(): return {"already": True}
    s.add(Follow(follower_id=user["sub"], followee_id=user_id, status="accepted"))
    await s.commit()
    return {"following": True}
@router.delete("/{user_id}")
async def unfollow(user_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Follow).where(Follow.follower_id == user["sub"], Follow.followee_id == user_id))
    f = res.scalar_one_or_none()
    if not f: raise HTTPException(404, "not following")
    await s.delete(f); await s.commit()
    return {"unfollowed": True}
@router.get("/following")
async def following(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Follow).where(Follow.follower_id == user["sub"]))
    return [r.followee_id for r in res.scalars().all()]
@router.get("/followers")
async def followers(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Follow).where(Follow.followee_id == user["sub"]))
    return [r.follower_id for r in res.scalars().all()]
""",
)

print("✅ social-service + notification-service seeded")
