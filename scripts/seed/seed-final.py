"""Final block: api, gateway, oauth, tenant-router, auth, mobile-api,
scheduler, worker, storage, admin-portal, web-portal + mobile APK CI."""
import os
ROOT = "/mnt/c/Users/asadu/PROJECTS/shopnoltd"

def W(p, c):
    fp = os.path.join(ROOT, p)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    if not c.endswith("\n"): c += "\n"
    with open(fp, "w") as f: f.write(c)

def py_service(name, title, port=8080, db=None, routers="", extra_reqs=""):
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
""" + extra_reqs)
    W(f"platform/{name}/app/__init__.py", "")
    for d in ("core","api","models","schemas","providers","workers","migrations","routers","db","services"):
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

def router(modname, prefix, tag):
    return f'app.include_router(__import__("app.api.{modname}", fromlist=["router"]).router, prefix="{prefix}", tags=["{tag}"])\n'

# ----------------- API-SERVICE (Unified BFF + GraphQL) -----------------
py_service("api-service", "Unified API Service", port=8080, db="api",
    routers=router("v1","/api/v1","v1") + router("graphql","/graphql","graphql") + router("health","/","health"),
    extra_reqs="strawberry-graphql==0.246.2\n")
W("platform/api-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class HealthAll(BaseModel):
    api_service: str
    auth: str
    payment: str
    billing: str
    exchange: str
    social: str
    messaging: str
    notification: str
    storage: str
''')
W("platform/api-service/app/services/services.py", '''"""Upstream service health checker."""
import httpx, asyncio
SERVICES = {
    "auth":        "http://oauth-service.shopno-identity.svc.cluster.local:8080",
    "payment":     "http://payment-service.shopno-payments.svc.cluster.local:8080",
    "billing":     "http://billing-engine.shopno-payments.svc.cluster.local:8080",
    "exchange":    "http://exchange-service.shopno-payments.svc.cluster.local:8080",
    "social":      "http://social-service.shopno-platform.svc.cluster.local:8080",
    "messaging":   "http://messaging-service.shopno-platform.svc.cluster.local:8080",
    "notification":"http://notification-service.shopno-platform.svc.cluster.local:8080",
    "storage":     "http://storage-service.shopno-platform.svc.cluster.local:8080",
    "ai":          "http://ai-platform.shopno-platform.svc.cluster.local:8000",
    "analytics":   "http://analytics-service.shopno-platform.svc.cluster.local:8080",
}
async def health() -> dict:
    async def check(name, url):
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{url}/healthz")
            return name, "ok" if r.status_code == 200 else f"down:{r.status_code}"
        except Exception as e:
            return name, f"down:{e.__class__.__name__}"
    results = await asyncio.gather(*[check(n, u) for n, u in SERVICES.items()])
    return {n: s for n, s in results}
''')
W("platform/api-service/app/api/health.py", '''from fastapi import APIRouter
from app.services.services import health
router = APIRouter()
@router.get("/services")
async def services():
    return await health()
@router.get("/cluster")
async def cluster():
    h = await health()
    return {"status": "ok" if all(v == "ok" for v in h.values()) else "degraded", "services": h}
''')
W("platform/api-service/app/api/v1.py", '''"""Versioned REST facade that aggregates downstream services."""
from fastapi import APIRouter, Depends, HTTPException
import httpx
from app.core.security import verify_token
from app.core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
async def call(method: str, url: str, user_token: str, **kw):
    headers = {"Authorization": f"Bearer {user_token}"}
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.request(method, url, headers=headers, **kw)
    if r.status_code >= 400: raise HTTPException(r.status_code, r.text)
    return r.json() if r.text else None
@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://oauth-service.shopno-identity.svc.cluster.local:8080/api/v1/users/me", creds.credentials)
@router.get("/wallets")
async def wallets(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://payment-service.shopno-payments.svc.cluster.local:8080/api/v1/wallets", creds.credentials)
@router.get("/feed")
async def feed(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://social-service.shopno-platform.svc.cluster.local:8080/api/v1/feed/me", creds.credentials)
@router.get("/conversations")
async def conversations(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://messaging-service.shopno-platform.svc.cluster.local:8080/api/v1/conversations", creds.credentials)
@router.get("/notifications")
async def notifications(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://notification-service.shopno-platform.svc.cluster.local:8080/api/v1/notifications/me", creds.credentials)
@router.get("/subscription")
async def subscription(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", "http://billing-engine.shopno-payments.svc.cluster.local:8080/api/v1/subscriptions/me", creds.credentials)
@router.get("/rate/{frm}/{to}")
async def rate(frm: str, to: str, creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await call("GET", f"http://exchange-service.shopno-payments.svc.cluster.local:8080/api/v1/rates/{frm}/{to}", creds.credentials)
''')
W("platform/api-service/app/api/graphql.py", '''import strawberry
from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter
@strawberry.type
class Service:
    name: str
    status: str
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str: return "Welcome to Shopnoltd GraphQL"
    @strawberry.field
    async def services(self) -> list[Service]:
        from app.services.services import health
        h = await health()
        return [Service(name=n, status=s) for n, s in h.items()]
schema = strawberry.Schema(query=Query)
router = APIRouter()
router.include_router(GraphQLRouter(schema), prefix="")
''')

# ----------------- GATEWAY (Traefik dynamic config generator) -----------------
py_service("gateway", "API Gateway", port=8000, db="gateway",
    routers=router("routes","/api/routes","routes"))
W("platform/gateway/app/api/routes.py", '''"""Generates Traefik dynamic config from the live service registry."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token_admin
from app.services.services import SERVICES
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
HOSTS = {
    "auth":        "auth.shopnoltd.dpdns.org",
    "payment":     "billing.shopnoltd.dpdns.org",
    "billing":     "billing.shopnoltd.dpdns.org",
    "exchange":    "billing.shopnoltd.dpdns.org",
    "social":      "chat.shopnoltd.dpdns.org",
    "messaging":   "chat.shopnoltd.dpdns.org",
    "notification":"shopnoltd.dpdns.org",
    "storage":     "shopnoltd.dpdns.org",
    "ai":          "api.shopnoltd.dpdns.org",
    "analytics":   "grafana.shopnoltd.dpdns.org",
    "api":         "api.shopnoltd.dpdns.org",
    "search":      "api.shopnoltd.dpdns.org",
    "audit":       "api.shopnoltd.dpdns.org",
}
@router.get("/traefik.yml")
async def traefik_config():
    """Produces Traefik dynamic config that fronts every service."""
    http_routers, http_services, http_middlewares = {}, {}, {}
    for svc, url in SERVICES.items():
        host = HOSTS.get(svc, "api.shopnoltd.dpdns.org")
        rid = f"shopno-{svc}"
        http_routers[rid] = {"rule": f"Host(`{host}`) && PathPrefix(`/{svc}`)", "service": rid, "entryPoints": ["websecure"], "tls": {"certResolver": "letsencrypt"}, "middlewares": [f"{rid}-auth"]}
        http_services[rid] = {"loadBalancer": {"servers": [{"url": url}]}}
        http_middlewares[f"{rid}-auth"] = {"forwardauth": {"address": f"http://oauth-service.shopno-identity.svc.cluster.local:8080/api/v1/verify"}}
    return {"http": {"routers": http_routers, "services": http_services, "middlewares": http_middlewares}, "generated_at": datetime.utcnow().isoformat()}
@router.get("/list")
async def list_routes(user=Depends(admin)):
    return [{"service": s, "url": u, "host": HOSTS.get(s, "")} for s, u in SERVICES.items()]
''')

# ----------------- OAUTH-SERVICE (OIDC broker + Keycloak admin) -----------------
py_service("oauth-service", "OAuth Service", port=3000, db="oauth",
    routers=router("users","/api/v1/users","users") + router("tenants","/api/v1/tenants","tenants") + router("roles","/api/v1/roles","roles") + router("verify","/api/v1/verify","verify"))
W("platform/oauth-service/requirements.txt", """fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
redis==5.2.0
httpx==0.27.2
python-keycloak==4.7.0
prometheus-client==0.21.0
structlog==24.4.0
""")
W("platform/oauth-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-oauth-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/oauth"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_url: str = "https://auth.shopnoltd.dpdns.org"
    keycloak_admin_user: str = "admin"
    keycloak_admin_password: str = "CHANGE_ME"
    keycloak_realm: str = "shopnoltd"
    keycloak_audience: str = "oauth-service"
    @property
    def cors_origins_list(self): return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
''')
W("platform/oauth-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, JSON, Boolean
import uuid
from datetime import datetime
from app.core.db import Base
class UserMirror(Base):
    __tablename__ = "users"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    keycloak_id = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False)
    name = Column(String(256))
    tenant_id = Column(String(64), index=True)
    roles = Column(JSON, default=list)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, nullable=False)
    subdomain = Column(String(128), unique=True, nullable=False)
    plan = Column(String(64), default="free")
    settings = Column(JSON, default=dict)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
''')
W("platform/oauth-service/app/schemas/schemas.py", '''from pydantic import BaseModel
from typing import Optional
class UserIn(BaseModel):
    email: str; name: str = ""; password: str = ""; tenant_id: Optional[str] = None
class UserOut(BaseModel):
    id: str; email: str; name: str; tenant_id: Optional[str]; roles: list
    class Config: from_attributes = True
class TenantIn(BaseModel):
    name: str; subdomain: str; plan: str = "free"
class TenantOut(BaseModel):
    id: str; name: str; subdomain: str; plan: str
    class Config: from_attributes = True
''')
W("platform/oauth-service/app/api/users.py", '''import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token_admin
from app.models.models import UserMirror
from app.schemas.schemas import UserIn, UserOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
ADMIN_URL = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"
async def kc_token():
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli", "username": settings.keycloak_admin_user, "password": settings.keycloak_admin_password})
    r.raise_for_status(); return r.json()["access_token"]
@router.post("", response_model=UserOut, status_code=201)
async def create(body: UserIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    tok = await kc_token()
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{ADMIN_URL}/users", headers={"Authorization": f"Bearer {tok}"}, json={"email": body.email, "username": body.email, "firstName": body.name, "enabled": True, "emailVerified": False, "credentials": [{"type": "password", "value": body.password, "temporary": False}] if body.password else []})
    if r.status_code == 409: raise HTTPException(409, "user already exists")
    r.raise_for_status()
    # Find keycloak id
    async with httpx.AsyncClient() as c:
        r2 = await c.get(f"{ADMIN_URL}/users?email={body.email}", headers={"Authorization": f"Bearer {tok}"})
    kc_id = r2.json()[0]["id"]
    u = UserMirror(keycloak_id=kc_id, email=body.email, name=body.name, tenant_id=body.tenant_id)
    s.add(u); await s.commit(); await s.refresh(u)
    return UserOut(id=u.id, email=u.email, name=u.name, tenant_id=u.tenant_id, roles=u.roles or [])
@router.get("", response_model=list[UserOut])
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(UserMirror).limit(500))
    return [UserOut(id=u.id, email=u.email, name=u.name, tenant_id=u.tenant_id, roles=u.roles or []) for u in res.scalars().all()]
@router.get("/me")
async def me(creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    from app.core.security import verify_token
    payload = await verify_token(creds.credentials)
    u = (await s.execute(select(UserMirror).where(UserMirror.keycloak_id == payload["sub"]))).scalar_one_or_none()
    if not u: return {"id": payload["sub"], "email": payload.get("email"), "tenant_id": payload.get("tenant_id"), "roles": payload.get("roles", [])}
    return UserOut(id=u.id, email=u.email, name=u.name, tenant_id=u.tenant_id, roles=u.roles or [])
''')
W("platform/oauth-service/app/api/tenants.py", '''import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token_admin
from app.models.models import Tenant
from app.schemas.schemas import TenantIn, TenantOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", response_model=TenantOut, status_code=201)
async def create(body: TenantIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    t = Tenant(name=body.name, subdomain=body.subdomain, plan=body.plan)
    s.add(t); await s.commit(); await s.refresh(t)
    return TenantOut(id=t.id, name=t.name, subdomain=t.subdomain, plan=t.plan)
@router.get("", response_model=list[TenantOut])
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Tenant))
    return [TenantOut(id=t.id, name=t.name, subdomain=t.subdomain, plan=t.plan) for t in res.scalars().all()]
@router.get("/{subdomain}", response_model=TenantOut)
async def by_subdomain(subdomain: str, s: AsyncSession = Depends(db)):
    t = (await s.execute(select(Tenant).where(Tenant.subdomain == subdomain))).scalar_one_or_none()
    if not t: raise HTTPException(404, "tenant not found")
    return TenantOut(id=t.id, name=t.name, subdomain=t.subdomain, plan=t.plan)
''')
W("platform/oauth-service/app/api/roles.py", '''import httpx
from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from app.core.security import verify_token_admin
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
ADMIN_URL = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"
async def kc_token():
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "admin-cli", "username": settings.keycloak_admin_user, "password": settings.keycloak_admin_password})
    r.raise_for_status(); return r.json()["access_token"]
@router.get("")
async def list_(user=Depends(admin)):
    tok = await kc_token()
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{ADMIN_URL}/roles", headers={"Authorization": f"Bearer {tok}"})
    r.raise_for_status(); return r.json()
@router.post("")
async def create(name: str, description: str = "", user=Depends(admin)):
    tok = await kc_token()
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{ADMIN_URL}/roles", headers={"Authorization": f"Bearer {tok}"}, json={"name": name, "description": description})
    if r.status_code == 409: raise HTTPException(409, "role exists")
    r.raise_for_status(); return {"name": name}
''')
W("platform/oauth-service/app/api/verify.py", '''"""Traefik forwardAuth endpoint."""
from fastapi import APIRouter, Request
router = APIRouter()
@router.all("")
async def verify(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        from fastapi.responses import Response
        return Response(status_code=401)
    token = auth.split(" ", 1)[1]
    try:
        from app.core.security import verify_token
        payload = await verify_token(token)
        # Forward user info as headers
        from fastapi.responses import Response
        h = {"X-Forwarded-User": payload.get("sub", ""), "X-Forwarded-Email": payload.get("email", ""), "X-Forwarded-Tenant": payload.get("tenant_id", "default"), "X-Forwarded-Roles": ",".join(payload.get("roles", []))}
        return Response(status_code=200, headers=h)
    except Exception:
        from fastapi.responses import Response
        return Response(status_code=401)
''')

# ----------------- TENANT-ROUTER -----------------
py_service("tenant-router", "Tenant Router", port=8080, db="router",
    routers=router("tenants","/api/v1/tenants","tenants"))
W("platform/tenant-router/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-tenant-router"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/router"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_audience: str = "tenant-router"
    base_domain: str = "shopnoltd.dpdns.org"
settings = Settings()
''')
W("platform/tenant-router/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Boolean, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class TenantRoute(Base):
    __tablename__ = "tenant_routes"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    subdomain = Column(String(128), unique=True, nullable=False)
    tenant_id = Column(String(64), nullable=False, index=True)
    namespace = Column(String(64), nullable=False)
    plan = Column(String(64), default="free")
    storage_quota_gb = Column(Integer, default=10)
    user_quota = Column(Integer, default=10)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
''')
W("platform/tenant-router/app/schemas/schemas.py", '''from pydantic import BaseModel
class TenantRouteIn(BaseModel):
    subdomain: str; tenant_id: str; plan: str = "free"
    storage_quota_gb: int = 10; user_quota: int = 10
class TenantRouteOut(BaseModel):
    subdomain: str; tenant_id: str; namespace: str; plan: str
    storage_quota_gb: int; user_quota: int; active: bool
''')
W("platform/tenant-router/app/api/tenants.py", '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token_admin
from app.models.models import TenantRoute
from app.schemas.schemas import TenantRouteIn, TenantRouteOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", response_model=TenantRouteOut, status_code=201)
async def create(body: TenantRouteIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    if (await s.execute(select(TenantRoute).where(TenantRoute.subdomain == body.subdomain))).scalar_one_or_none():
        raise HTTPException(409, "subdomain taken")
    ns = f"shopno-tenant-{body.subdomain}".replace(".", "-").replace("_", "-")
    r = TenantRoute(subdomain=body.subdomain, tenant_id=body.tenant_id, namespace=ns, plan=body.plan, storage_quota_gb=body.storage_quota_gb, user_quota=body.user_quota)
    s.add(r); await s.commit(); await s.refresh(r)
    return TenantRouteOut(subdomain=r.subdomain, tenant_id=r.tenant_id, namespace=r.namespace, plan=r.plan, storage_quota_gb=r.storage_quota_gb, user_quota=r.user_quota, active=r.active)
@router.get("/by-host/{subdomain}", response_model=TenantRouteOut)
async def by_host(subdomain: str, s: AsyncSession = Depends(db)):
    full = subdomain if subdomain.endswith(settings.base_domain) else f"{subdomain}.{settings.base_domain}"
    r = (await s.execute(select(TenantRoute).where(TenantRoute.subdomain == full))).scalar_one_or_none()
    if not r: raise HTTPException(404, "tenant not found")
    return TenantRouteOut(subdomain=r.subdomain, tenant_id=r.tenant_id, namespace=r.namespace, plan=r.plan, storage_quota_gb=r.storage_quota_gb, user_quota=r.user_quota, active=r.active)
@router.get("")
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(TenantRoute))
    return [TenantRouteOut(subdomain=r.subdomain, tenant_id=r.tenant_id, namespace=r.namespace, plan=r.plan, storage_quota_gb=r.storage_quota_gb, user_quota=r.user_quota, active=r.active) for r in res.scalars().all()]
''')

# ----------------- AUTH-SERVICE -----------------
py_service("auth-service", "Auth Service", port=8080, db="auth",
    routers=router("auth","/api/v1/auth","auth") + router("sessions","/api/v1/sessions","sessions"))
W("platform/auth-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-auth-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/auth"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_url: str = "https://auth.shopnoltd.dpdns.org"
    keycloak_realm: str = "shopnoltd"
    keycloak_audience: str = "auth-service"
    @property
    def cors_origins_list(self): return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
''')
W("platform/auth-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Boolean
import uuid
from datetime import datetime
from app.core.db import Base
class Session(Base):
    __tablename__ = "sessions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), nullable=False, index=True)
    ip = Column(String(64))
    user_agent = Column(String(256))
    device = Column(String(64))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)
''')
W("platform/auth-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class LoginIn(BaseModel):
    email: str
    password: str
    device: str = "web"
class LoginOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    session_id: str
''')
W("platform/auth-service/app/api/auth.py", '''import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.models.models import Session
from app.schemas.schemas import LoginIn, LoginOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/login", response_model=LoginOut)
async def login(body: LoginIn, request: Request, s: AsyncSession = Depends(db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
            data={"grant_type": "password", "client_id": "shopnoltd-web", "username": body.email, "password": body.password})
    if r.status_code != 200: raise HTTPException(401, "invalid credentials")
    d = r.json()
    sess = Session(user_id=body.email, ip=request.client.host if request.client else "", user_agent=request.headers.get("user-agent",""), device=body.device)
    s.add(sess); await s.commit()
    return LoginOut(access_token=d["access_token"], refresh_token=d["refresh_token"], expires_in=d.get("expires_in", 300), session_id=sess.id)
@router.post("/refresh")
async def refresh(refresh_token: str, s: AsyncSession = Depends(db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/token",
            data={"grant_type": "refresh_token", "client_id": "shopnoltd-web", "refresh_token": refresh_token})
    r.raise_for_status(); return r.json()
@router.post("/logout")
async def logout(creds: HTTPAuthorizationCredentials = Depends(bearer), s: AsyncSession = Depends(db)):
    payload = await verify_token(creds.credentials)
    res = await s.execute(select(Session).where(Session.user_id == payload.get("email", payload["sub"]), Session.active == True))
    for sess in res.scalars().all():
        sess.active = False; sess.revoked_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
''')
W("platform/auth-service/app/api/sessions.py", '''from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Session).where(Session.user_id == user.get("email", user["sub"]), Session.active == True))
    return [{"id": x.id, "device": x.device, "ip": x.ip, "user_agent": x.user_agent, "created_at": x.created_at.isoformat(), "last_seen": x.last_seen.isoformat()} for x in res.scalars().all()]
@router.delete("/{sess_id}")
async def revoke(sess_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    sess = (await s.execute(select(Session).where(Session.id == sess_id))).scalar_one_or_none()
    if not sess: from fastapi import HTTPException; raise HTTPException(404, "not found")
    sess.active = False; sess.revoked_at = datetime.utcnow()
    await s.commit()
    return {"ok": True}
''')

# ----------------- MOBILE-API (BFF for mobile) -----------------
py_service("mobile-api", "Mobile API", port=8080, db="mobile",
    routers=router("apps","/api/v1/apps","apps") + router("updates","/api/v1/updates","updates") + router("config","/api/v1/config","config"))
W("platform/mobile-api/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Integer, JSON
import uuid
from datetime import datetime
from app.core.db import Base
class AppRelease(Base):
    __tablename__ = "app_releases"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), nullable=False, index=True)  # shopno-survey, shopno-chat, ...
    version = Column(String(32), nullable=False)  # 1.0.0
    build = Column(Integer, nullable=False, default=1)
    apk_path = Column(String(512))
    sha256 = Column(String(128))
    size_bytes = Column(Integer)
    min_os_version = Column(String(16), default="8.0")
    release_notes = Column(String)
    force_update = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
class AppConfig(Base):
    __tablename__ = "app_config"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, nullable=False)
    data = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
''')
W("platform/mobile-api/app/schemas/schemas.py", '''from pydantic import BaseModel
class ReleaseIn(BaseModel):
    code: str; version: str; build: int; apk_path: str
    sha256: str; size_bytes: int
    min_os_version: str = "8.0"; release_notes: str = ""; force_update: bool = False
class ReleaseOut(BaseModel):
    code: str; version: str; build: int
    apk_url: str; sha256: str; size_bytes: int
    min_os_version: str; force_update: bool
    release_notes: str; published_at: str
class ConfigIn(BaseModel):
    code: str; data: dict
''')
W("platform/mobile-api/app/api/apps.py", '''from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.db import SessionLocal
from app.core.security import verify_token, verify_token_admin
from app.models.models import AppRelease
from app.schemas.schemas import ReleaseIn, ReleaseOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.get("", response_model=list[dict])
async def list_apps():
    """Public endpoint listing all Shopnoltd apps."""
    return [
        {"code": "shopno-survey", "name": "Shopnoltd Survey", "icon": "📋", "description": "Field data collection, forms, and case management."},
        {"code": "shopno-chat",   "name": "Shopnoltd Chat",   "icon": "💬", "description": "Customer chat and support."},
        {"code": "shopno-meet",   "name": "Shopnoltd Meet",   "icon": "📹", "description": "Video conferencing."},
        {"code": "shopno-live",   "name": "Shopnoltd Live",   "icon": "🔴", "description": "Live streaming."},
        {"code": "shopno-drive",  "name": "Shopnoltd Drive",  "icon": "☁️", "description": "Cloud storage and sync."},
        {"code": "shopno-mail",   "name": "Shopnoltd Mail",   "icon": "✉️", "description": "Email client."},
    ]
@router.get("/{code}/latest", response_model=ReleaseOut)
async def latest(code: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(AppRelease).where(AppRelease.code == code).order_by(desc(AppRelease.created_at)).limit(1))
    r = res.scalar_one_or_none()
    if not r: raise HTTPException(404, "no release")
    return ReleaseOut(code=r.code, version=r.version, build=r.build, apk_url=r.apk_path, sha256=r.sha256, size_bytes=r.size_bytes, min_os_version=r.min_os_version, force_update=bool(r.force_update), release_notes=r.release_notes or "", published_at=r.created_at.isoformat())
@router.post("", status_code=201)
async def publish(body: ReleaseIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    r = AppRelease(**body.model_dump())
    s.add(r); await s.commit()
    return {"id": r.id, "version": r.version}
''')
W("platform/mobile-api/app/api/updates.py", '''from fastapi import APIRouter, Depends
from app.core.security import verify_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("/check")
async def check(code: str, version: str, build: int, user=Depends(current_user)):
    from fastapi import HTTPException
    from app.api.apps import latest
    from app.schemas.schemas import ReleaseOut
    from sqlalchemy import desc
    from app.core.db import SessionLocal
    from app.models.models import AppRelease
    from sqlalchemy import select
    async with SessionLocal() as s:
        res = await s.execute(select(AppRelease).where(AppRelease.code == code).order_by(desc(AppRelease.created_at)).limit(1))
        r = res.scalar_one_or_none()
        if not r: return {"update_available": False}
        if r.version != version or r.build > build:
            return {"update_available": True, "force": bool(r.force_update), "latest": ReleaseOut(code=r.code, version=r.version, build=r.build, apk_url=r.apk_path, sha256=r.sha256, size_bytes=r.size_bytes, min_os_version=r.min_os_version, force_update=bool(r.force_update), release_notes=r.release_notes or "", published_at=r.created_at.isoformat()).model_dump()}
    return {"update_available": False}
''')
W("platform/mobile-api/app/api/config.py", '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token, verify_token_admin
from app.models.models import AppConfig
from app.schemas.schemas import ConfigIn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.get("/{code}")
async def get(code: str, s: AsyncSession = Depends(db)):
    cfg = (await s.execute(select(AppConfig).where(AppConfig.code == code))).scalar_one_or_none()
    if not cfg: return {"code": code, "data": {}}
    return {"code": cfg.code, "data": cfg.data, "updated_at": cfg.updated_at.isoformat()}
@router.post("", status_code=201)
async def set_(body: ConfigIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    cfg = (await s.execute(select(AppConfig).where(AppConfig.code == body.code))).scalar_one_or_none()
    if cfg: cfg.data = body.data
    else: s.add(AppConfig(code=body.code, data=body.data))
    await s.commit()
    return {"ok": True, "code": body.code}
''')

# ----------------- SCHEDULER-SERVICE (APScheduler) -----------------
py_service("scheduler-service", "Scheduler Service", port=8080, db="scheduler",
    routers=router("jobs","/api/v1/jobs","jobs"),
    extra_reqs="apscheduler==3.10.4\n")
W("platform/scheduler-service/app/core/scheduler.py", '''from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx
scheduler = AsyncIOScheduler()
async def http_job(url: str, method: str = "POST", body: dict = None):
    async with httpx.AsyncClient(timeout=30) as c:
        await c.request(method, url, json=body)
''')
W("platform/scheduler-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, JSON, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Job(Base):
    __tablename__ = "jobs"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, nullable=False)
    cron = Column(String(64), nullable=False)  # "*/5 * * * *"
    url = Column(String(512), nullable=False)
    method = Column(String(8), default="POST")
    body = Column(JSON, default=dict)
    active = Column(Integer, default=1)
    last_run = Column(DateTime)
    last_status = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
''')
W("platform/scheduler-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class JobIn(BaseModel):
    name: str; cron: str; url: str
    method: str = "POST"; body: dict = {}
class JobOut(BaseModel):
    id: str; name: str; cron: str; url: str
    active: bool; last_run: str | None; last_status: int | None
''')
W("platform/scheduler-service/app/api/jobs.py", '''from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.scheduler import scheduler, http_job
from app.core.security import verify_token_admin
from app.models.models import Job
from app.schemas.schemas import JobIn, JobOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.on_event("startup")
async def load_jobs():
    if not scheduler.running: scheduler.start()
    async with SessionLocal() as s:
        res = await s.execute(select(Job).where(Job.active == 1))
        for j in res.scalars().all():
            try:
                scheduler.add_job(http_job, CronTrigger.from_crontab(j.cron), id=j.id, args=[j.url, j.method, j.body], replace_existing=True)
            except Exception: pass
@router.post("", status_code=201)
async def create(body: JobIn, user=Depends(admin), s: AsyncSession = Depends(db)):
    j = Job(name=body.name, cron=body.cron, url=body.url, method=body.method, body=body.body)
    s.add(j); await s.commit(); await s.refresh(j)
    scheduler.add_job(http_job, CronTrigger.from_crontab(j.cron), id=j.id, args=[j.url, j.method, j.body], replace_existing=True)
    return {"id": j.id}
@router.get("")
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Job))
    return [JobOut(id=j.id, name=j.name, cron=j.cron, url=j.url, active=bool(j.active), last_run=j.last_run.isoformat() if j.last_run else None, last_status=j.last_status) for j in res.scalars().all()]
@router.delete("/{job_id}")
async def remove(job_id: str, user=Depends(admin), s: AsyncSession = Depends(db)):
    j = (await s.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if not j: raise HTTPException(404, "not found")
    try: scheduler.remove_job(job_id)
    except Exception: pass
    await s.delete(j); await s.commit()
    return {"ok": True}
''')

# ----------------- WORKER-SERVICE (Arq) -----------------
py_service("worker-service", "Worker Service", port=8080, db="worker",
    routers=router("tasks","/api/v1/tasks","tasks"),
    extra_reqs="arq==0.25.0\n")
W("platform/worker-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, JSON, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Task(Base):
    __tablename__ = "tasks"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False, index=True)
    args = Column(JSON, default=dict)
    status = Column(String(16), default="queued", index=True)  # queued, running, done, failed
    result = Column(JSON)
    error = Column(String)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
''')
W("platform/worker-service/app/schemas/schemas.py", '''from pydantic import BaseModel
class TaskIn(BaseModel):
    name: str; args: dict = {}
class TaskOut(BaseModel):
    id: str; name: str; status: str; result: dict | None
    created_at: str; started_at: str | None; finished_at: str | None
''')
W("platform/worker-service/app/api/tasks.py", '''from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.models.models import Task
from app.schemas.schemas import TaskIn, TaskOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx, asyncio
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
KNOWN = {
    "send_email": lambda args: ("POST", "http://notification-service.shopno-platform.svc.cluster.local:8080/api/v1/notifications/send", args),
    "convert_fx": lambda args: ("POST", "http://exchange-service.shopno-payments.svc.cluster.local:8080/api/v1/convert", args),
    "send_push": lambda args: ("POST", "http://notification-service.shopno-platform.svc.cluster.local:8080/api/v1/push/notify", args),
    "log_event": lambda args: ("POST", "http://analytics-service.shopno-platform.svc.cluster.local:8080/api/v1/events", args),
}
async def run_task(t: Task):
    t.status = "running"; t.started_at = datetime.utcnow(); t.attempts += 1
    if t.name not in KNOWN:
        t.status = "failed"; t.error = f"unknown task: {t.name}"; t.finished_at = datetime.utcnow(); return
    method, url, args = KNOWN[t.name](t.args)
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.request(method, url, json=args)
        if r.status_code >= 400: raise RuntimeError(f"upstream {r.status_code}: {r.text[:200]}")
        t.result = r.json() if r.text else {}
        t.status = "done"
    except Exception as e:
        t.status = "failed"; t.error = str(e)
    t.finished_at = datetime.utcnow()
@router.post("", response_model=TaskOut, status_code=201)
async def enqueue(body: TaskIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    t = Task(name=body.name, args=body.args)
    s.add(t); await s.commit(); await s.refresh(t)
    asyncio.create_task(_run_in_session(t.id))
    return TaskOut(id=t.id, name=t.name, status=t.status, result=None, created_at=t.created_at.isoformat(), started_at=None, finished_at=None)
async def _run_in_session(task_id: str):
    async with SessionLocal() as s:
        t = (await s.execute(select(Task).where(Task.id == task_id))).scalar_one()
        await run_task(t)
        await s.commit()
@router.get("/{task_id}", response_model=TaskOut)
async def status(task_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    t = (await s.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not t: raise HTTPException(404, "not found")
    return TaskOut(id=t.id, name=t.name, status=t.status, result=t.result, created_at=t.created_at.isoformat(), started_at=t.started_at.isoformat() if t.started_at else None, finished_at=t.finished_at.isoformat() if t.finished_at else None)
@router.get("")
async def list_(user=Depends(current_user), s: AsyncSession = Depends(db), limit: int = 50):
    res = await s.execute(select(Task).order_by(Task.created_at.desc()).limit(limit))
    return [TaskOut(id=t.id, name=t.name, status=t.status, result=t.result, created_at=t.created_at.isoformat(), started_at=t.started_at.isoformat() if t.started_at else None, finished_at=t.finished_at.isoformat() if t.finished_at else None) for t in res.scalars().all()]
''')

# ----------------- STORAGE-SERVICE (S3 over MinIO) -----------------
py_service("storage-service", "Storage Service", port=9000, db="storage",
    routers=router("buckets","/api/v1/buckets","buckets") + router("objects","/api/v1/objects","objects"),
    extra_reqs="minio==7.2.8\n")
W("platform/storage-service/app/core/config.py", '''from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    app_name: str = "shopnoltd-storage-service"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/storage"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    minio_endpoint: str = "minio.data.svc.cluster.local:9000"
    minio_access_key: str = "shopno"
    minio_secret_key: str = "CHANGE_ME"
    minio_secure: bool = False
    keycloak_audience: str = "storage-service"
    @property
    def cors_origins_list(self): return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
''')
W("platform/storage-service/app/models/models.py", '''from sqlalchemy import Column, String, DateTime, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Bucket(Base):
    __tablename__ = "buckets"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(64), nullable=False, unique=True)
    purpose = Column(String(64), default="general")
    created_at = Column(DateTime, default=datetime.utcnow)
class Object(Base):
    __tablename__ = "objects"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    bucket_id = Column(String(64), nullable=False, index=True)
    key = Column(String(512), nullable=False)
    size = Column(Integer, default=0)
    content_type = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
''')
W("platform/storage-service/app/core/minio_client.py", '''from minio import Minio
from app.core.config import settings
client = Minio(settings.minio_endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=settings.minio_secure)
''')
W("platform/storage-service/app/api/buckets.py", '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token, verify_token_admin
from app.core.minio_client import client
from app.models.models import Bucket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.post("", status_code=201)
async def create(name: str, purpose: str = "general", user=Depends(admin), s: AsyncSession = Depends(db)):
    if not client.bucket_exists(name): client.make_bucket(name)
    b = Bucket(tenant_id=user.get("tenant_id","default"), name=name, purpose=purpose)
    s.add(b); await s.commit()
    return {"id": b.id, "name": b.name}
@router.get("")
async def list_(user=Depends(admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Bucket))
    return [{"name": b.name, "purpose": b.purpose} for b in res.scalars().all()]
''')
W("platform/storage-service/app/api/objects.py", '''import io, hashlib, secrets
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.core.security import verify_token
from app.core.minio_client import client
from app.models.models import Object
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.put("/{bucket}/{key:path}")
async def upload(bucket: str, key: str, file: UploadFile = File(...), user=Depends(current_user), s: AsyncSession = Depends(db)):
    data = await file.read()
    size = len(data)
    sha = hashlib.sha256(data).hexdigest()
    client.put_object(bucket, key, io.BytesIO(data), size, content_type=file.content_type)
    o = Object(bucket_id=bucket, key=key, size=size, content_type=file.content_type)
    s.add(o); await s.commit()
    return {"bucket": bucket, "key": key, "size": size, "sha256": sha}
@router.get("/{bucket}/{key:path}/url")
async def presign(bucket: str, key: str, user=Depends(current_user)):
    url = client.presigned_get_object(bucket, key, expires=timedelta(hours=1))
    return {"url": url}
@router.delete("/{bucket}/{key:path}")
async def delete(bucket: str, key: str, user=Depends(current_user)):
    client.remove_object(bucket, key); return {"ok": True}
''')

# ----------------- ADMIN-PORTAL (React) -----------------
W("platform/admin-portal/Dockerfile", """FROM node:20-alpine AS build
WORKDIR /app
COPY platform/admin-portal/package.json platform/admin-portal/package-lock.json* ./
RUN npm ci || npm install
COPY platform/admin-portal/ ./
RUN npm run build
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY platform/admin-portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
HEALTHCHECK CMD wget -qO- http://127.0.0.1:3000/healthz || exit 1
""")
W("platform/admin-portal/package.json", """{
  "name": "shopnoltd-admin-portal",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "recharts": "^2.13.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.3",
    "vite": "^5.4.10"
  }
}
""")
W("platform/admin-portal/nginx.conf", """server {
  listen 3000;
  server_name _;
  root /usr/share/nginx/html;
  location = /healthz { return 200 "ok"; add_header Content-Type text/plain; }
  location / { try_files $uri $uri/ /index.html; }
}
""")
W("platform/admin-portal/vite.config.js", """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  server: { host: '0.0.0.0', port: 5173, proxy: { '/api': 'http://api-service.shopno-platform.svc.cluster.local:8080' } },
  build: { outDir: 'dist' }
})
""")
W("platform/admin-portal/index.html", """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/png" href="/favicon.png" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Shopnoltd Admin</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""")
W("platform/admin-portal/src/main.jsx", """import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import Tenants from './pages/Tenants'
import Payments from './pages/Payments'
import Plans from './pages/Plans'
import Streams from './pages/Streams'
import AppReleases from './pages/AppReleases'
const qc = new QueryClient()
function Layout({ children }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      <nav style={{ width: 220, background: '#0f172a', color: 'white', padding: 20 }}>
        <h2 style={{ color: '#38bdf8' }}>Shopnoltd</h2>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li><Link to="/" style={{ color: 'white' }}>Dashboard</Link></li>
          <li><Link to="/users" style={{ color: 'white' }}>Users</Link></li>
          <li><Link to="/tenants" style={{ color: 'white' }}>Tenants</Link></li>
          <li><Link to="/payments" style={{ color: 'white' }}>Payments</Link></li>
          <li><Link to="/plans" style={{ color: 'white' }}>Plans</Link></li>
          <li><Link to="/streams" style={{ color: 'white' }}>Live Streams</Link></li>
          <li><Link to="/releases" style={{ color: 'white' }}>App Releases</Link></li>
        </ul>
      </nav>
      <main style={{ flex: 1, padding: 32, background: '#f1f5f9' }}>{children}</main>
    </div>
  )
}
function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/users" element={<Users />} />
            <Route path="/tenants" element={<Tenants />} />
            <Route path="/payments" element={<Payments />} />
            <Route path="/plans" element={<Plans />} />
            <Route path="/streams" element={<Streams />} />
            <Route path="/releases" element={<AppReleases />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
""")
W("platform/admin-portal/src/api.js", """import axios from 'axios'
const baseURL = '/api'
export const api = axios.create({ baseURL })
api.interceptors.request.use(c => {
  const tok = localStorage.getItem('shopno_token')
  if (tok) c.headers.Authorization = `Bearer ${tok}`
  return c
})
""")
W("platform/admin-portal/src/pages/Dashboard.jsx", """import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Dashboard() {
  const { data, isLoading } = useQuery({ queryKey: ['services'], queryFn: () => api.get('/services').then(r => r.data) })
  if (isLoading) return <p>Loading…</p>
  const entries = Object.entries(data || {})
  return (
    <div>
      <h1>Cluster Health</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
        {entries.map(([name, status]) => (
          <div key={name} style={{ background: 'white', padding: 20, borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h3 style={{ margin: 0 }}>{name}</h3>
            <p style={{ color: status === 'ok' ? '#10b981' : '#ef4444', fontWeight: 600 }}>{status}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
""")
W("platform/admin-portal/src/pages/Users.jsx", """import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Users() {
  const { data, isLoading } = useQuery({ queryKey: ['users'], queryFn: () => api.get('/users').then(r => r.data) })
  if (isLoading) return <p>Loading…</p>
  return (
    <div>
      <h1>Users</h1>
      <table style={{ width: '100%', background: 'white', borderRadius: 12, overflow: 'hidden' }}>
        <thead style={{ background: '#0f172a', color: 'white' }}>
          <tr><th>Email</th><th>Name</th><th>Tenant</th><th>Roles</th></tr>
        </thead>
        <tbody>
          {(data || []).map(u => (
            <tr key={u.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: 12 }}>{u.email}</td><td>{u.name}</td><td>{u.tenant_id}</td><td>{(u.roles || []).join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
""")
W("platform/admin-portal/src/pages/Payments.jsx", """import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Payments() {
  const { data, isLoading } = useQuery({ queryKey: ['pending'], queryFn: () => api.get('/admin/pending').then(r => r.data) })
  return (
    <div>
      <h1>Pending Approvals</h1>
      {isLoading ? <p>Loading…</p> : (
        <pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  )
}
""")
W("platform/admin-portal/src/pages/Tenants.jsx", """import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Tenants() {
  const { data } = useQuery({ queryKey: ['tenants'], queryFn: () => api.get('/tenants').then(r => r.data) })
  return <div><h1>Tenants</h1><pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre></div>
}
""")
W("platform/admin-portal/src/pages/Plans.jsx", """import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Plans() {
  const { data } = useQuery({ queryKey: ['plans'], queryFn: () => api.get('/plans').then(r => r.data) })
  return <div><h1>Subscription Plans</h1><pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre></div>
}
""")
W("platform/admin-portal/src/pages/Streams.jsx", """import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Streams() {
  const { data } = useQuery({ queryKey: ['streams'], queryFn: () => api.get('/streams').then(r => r.data) })
  return <div><h1>Live Streams</h1><pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre></div>
}
""")
W("platform/admin-portal/src/pages/AppReleases.jsx", """import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function AppReleases() {
  const { data } = useQuery({ queryKey: ['releases'], queryFn: () => api.get('/releases').then(r => r.data) })
  return <div><h1>App Releases</h1><pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre></div>
}
""")

# ----------------- WEB-PORTAL (Customer React site) -----------------
W("platform/web-portal/Dockerfile", """FROM node:20-alpine AS build
WORKDIR /app
COPY platform/web-portal/package.json platform/web-portal/package-lock.json* ./
RUN npm ci || npm install
COPY platform/web-portal/ ./
RUN npm run build
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY platform/web-portal/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
HEALTHCHECK CMD wget -qO- http://127.0.0.1:3000/healthz || exit 1
""")
W("platform/web-portal/package.json", """{
  "name": "shopnoltd-web-portal",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": { "dev": "vite", "build": "vite build", "preview": "vite preview" },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.27.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.3",
    "vite": "^5.4.10"
  }
}
""")
W("platform/web-portal/nginx.conf", """server {
  listen 3000;
  server_name _;
  root /usr/share/nginx/html;
  location = /healthz { return 200 "ok"; add_header Content-Type text/plain; }
  location / { try_files $uri $uri/ /index.html; }
}
""")
W("platform/web-portal/index.html", """<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <link rel="icon" type="image/png" href="/favicon.png" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Shopnoltd</title>
  <meta name="description" content="Shopnoltd — All-in-one platform for surveys, chat, meetings, live streaming, cloud storage, and payments." />
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.jsx"></script>
</body>
</html>
""")
W("platform/web-portal/src/main.jsx", """import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import Pricing from './pages/Pricing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
function Nav() {
  return (
    <nav style={{ display: 'flex', gap: 24, padding: 16, background: '#0ea5e9', color: 'white' }}>
      <Link to="/" style={{ color: 'white', fontWeight: 700, fontSize: 20 }}>Shopnoltd</Link>
      <Link to="/pricing" style={{ color: 'white' }}>Pricing</Link>
      <Link to="/login" style={{ color: 'white' }}>Login</Link>
      <Link to="/dashboard" style={{ color: 'white' }}>Dashboard</Link>
    </nav>
  )
}
function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  )
}
ReactDOM.createRoot(document.getElementById('root')).render(<App />)
""")
W("platform/web-portal/src/pages/Home.jsx", """export default function Home() {
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ color: '#0ea5e9', fontSize: 48 }}>All your tools. One platform.</h1>
      <p style={{ fontSize: 18, color: '#475569' }}>
        Shopnoltd brings together surveys, chat, video meetings, live streaming, cloud storage, and payments —
        under your brand, on your domain, with a single sign-on.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginTop: 32 }}>
        {[
          { i: '📋', t: 'Surveys',     d: 'KoboToolbox-powered data collection.' },
          { i: '💬', t: 'Chat',        d: 'Customer conversations with Chatwoot.' },
          { i: '📹', t: 'Meet',        d: 'Video conferencing with Jitsi.' },
          { i: '🔴', t: 'Live',        d: 'Self-hosted streaming with Owncast.' },
          { i: '☁️', t: 'Drive',       d: 'Files and sync via Nextcloud.' },
          { i: '✉️', t: 'Mail',        d: 'Full email stack with Mailcow.' },
        ].map(x => (
          <div key={x.t} style={{ padding: 20, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ fontSize: 32 }}>{x.i}</div>
            <h3>{x.t}</h3>
            <p style={{ color: '#64748b' }}>{x.d}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
""")
W("platform/web-portal/src/pages/Pricing.jsx", """export default function Pricing() {
  const plans = [
    { name: 'Free',    price: 0,    features: ['1 user', '1 GB storage', 'Community support'] },
    { name: 'Starter', price: 9,    features: ['5 users', '50 GB storage', 'Email support'] },
    { name: 'Pro',     price: 29,   features: ['25 users', '500 GB storage', 'Priority support'] },
    { name: 'Business',price: 99,   features: ['100 users', '5 TB storage', '24/7 support'] },
    { name: 'Enterprise', price: 299, features: ['Unlimited users', 'Unlimited storage', 'Dedicated success manager'] },
  ]
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Pricing</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {plans.map(p => (
          <div key={p.name} style={{ padding: 20, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h2>{p.name}</h2>
            <p style={{ fontSize: 36, fontWeight: 700 }}>${p.price}<span style={{ fontSize: 14, color: '#64748b' }}>/mo</span></p>
            <ul>{p.features.map(f => <li key={f}>{f}</li>)}</ul>
            <button style={{ width: '100%', padding: 10, background: '#0ea5e9', color: 'white', border: 0, borderRadius: 8 }}>Choose</button>
          </div>
        ))}
      </div>
    </div>
  )
}
""")
W("platform/web-portal/src/pages/Login.jsx", """import { useState } from 'react'
export default function Login() {
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  async function submit(e) {
    e.preventDefault()
    const r = await fetch('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password: pw }) })
    const d = await r.json()
    if (d.access_token) { localStorage.setItem('shopno_token', d.access_token); window.location.href = '/dashboard' }
  }
  return (
    <form onSubmit={submit} style={{ maxWidth: 360, margin: '64px auto', padding: 24, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      <h2>Sign in to Shopnoltd</h2>
      <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" style={{ width: '100%', padding: 10, margin: '8px 0' }} />
      <input type="password" value={pw} onChange={e => setPw(e.target.value)} placeholder="Password" style={{ width: '100%', padding: 10, margin: '8px 0' }} />
      <button style={{ width: '100%', padding: 10, background: '#0ea5e9', color: 'white', border: 0, borderRadius: 8 }}>Sign in</button>
    </form>
  )
}
""")
W("platform/web-portal/src/pages/Dashboard.jsx", """import { useEffect, useState } from 'react'
export default function Dashboard() {
  const [me, setMe] = useState(null)
  useEffect(() => {
    const t = localStorage.getItem('shopno_token')
    if (!t) return
    fetch('/api/v1/me', { headers: { Authorization: `Bearer ${t}` } }).then(r => r.json()).then(setMe)
  }, [])
  if (!me) return <div style={{ padding: 32 }}>Please log in.</div>
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Welcome, {me.email || me.id}</h1>
      <p>Tenant: {me.tenant_id || 'default'}</p>
      <p>Roles: {(me.roles || []).join(', ')}</p>
    </div>
  )
}
""")

# ----------------- .github/workflows/build-mobile.yml (Android APKs) -----------------
W(".github/workflows/build-mobile.yml", """name: Build Android APKs
on:
  push:
    branches: [main]
    paths:
      - 'mobile/**'
      - 'branding/**'
      - 'platform/mobile-api/**'
      - '.github/workflows/build-mobile.yml'
  workflow_dispatch:
env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ${{ github.repository_owner }}/shopnoltd
jobs:
  build:
    name: Build ${{ matrix.app }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - { app: shopno-survey, upstream: kobotoolbox/kobocollect, package: com.shopnoltd.survey }
          - { app: shopno-chat,   upstream: chatwoot/chatwoot-mobile, package: com.shopnoltd.chat }
          - { app: shopno-meet,   upstream: jitsi/jitsi-meet-sdk, package: com.shopnoltd.meet }
          - { app: shopno-live,   upstream: owncast/owncast-mobile, package: com.shopnoltd.live }
          - { app: shopno-drive,  upstream: nextcloud/android, package: com.shopnoltd.drive }
          - { app: shopno-mail,   upstream: k9mail/app, package: com.shopnoltd.mail }
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Build & push APK container
        uses: docker/build-push-action@v5
        with:
          context: .
          file: mobile/Dockerfile.android
          build-args: |
            BASE_IMAGE=${{ matrix.upstream }}
            APP_CODE=${{ matrix.app }}
            PACKAGE_NAME=${{ matrix.matrix.package }}
          push: true
          tags: |
            ghcr.io/${{ env.IMAGE_PREFIX }}/${{ matrix.app }}:latest
            ghcr.io/${{ env.IMAGE_PREFIX }}/${{ matrix.app }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Extract APK to release artifact
        run: |
          docker pull ghcr.io/${{ env.IMAGE_PREFIX }}/${{ matrix.app }}:${{ github.sha }}
          docker create --name extract-${{ matrix.app }} ghcr.io/${{ env.IMAGE_PREFIX }}/${{ matrix.app }}:${{ github.sha }}
          mkdir -p dist
          docker cp extract-${{ matrix.app }}:/apk/${{ matrix.app }}.apk dist/${{ matrix.app }}.apk || true
          docker rm extract-${{ matrix.app }}
      - uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.app }}-apk
          path: dist/${{ matrix.app }}.apk
          if-no-files-found: warn
""")
W("mobile/Dockerfile.android", """# syntax=docker/dockerfile:1.7
# Multi-stage Android APK builder for Shopnoltd branded apps.
# ARG: BASE_IMAGE (e.g. kobotoolbox/kobocollect-build), APP_CODE, PACKAGE_NAME
ARG BASE_IMAGE=eclipse-temurin:17-jdk
FROM ubuntu:22.04 AS base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \\
    openjdk-17-jdk-headless wget unzip git ca-certificates curl xz-utils \\
    && rm -rf /var/lib/apt/lists/*
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/34.0.0
RUN mkdir -p $ANDROID_HOME/cmdline-tools && \\
    cd $ANDROID_HOME/cmdline-tools && \\
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmd.zip && \\
    unzip -q cmd.zip && \\
    mv cmdline-tools latest && \\
    rm cmd.zip && \\
    yes | sdkmanager --licenses >/dev/null && \\
    sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0" >/dev/null

FROM base AS builder
ARG BASE_IMAGE
ARG APP_CODE
ARG PACKAGE_NAME
WORKDIR /src
# Clone the upstream mobile project. Each matrix entry sets BASE_IMAGE / APP_CODE.
RUN git clone --depth=1 https://github.com/${{ matrix.upstream }}.git /src/upstream
WORKDIR /src/upstream
# Apply Shopnoltd branding overlays
COPY branding/logos/ app/src/main/res/drawable-xxxhdpi/ 2>/dev/null || true
COPY branding/icons/  app/src/main/res/ 2>/dev/null || true
# Rename package
RUN find . -name "AndroidManifest.xml" -exec sed -i "s/com.kobocollect/$PACKAGE_NAME/g; s/com.chatwoot/$PACKAGE_NAME/g; s/org.jitsi.meet/$PACKAGE_NAME/g; s/com.owncast/$PACKAGE_NAME/g; s/com.nextcloud.client/$PACKAGE_NAME/g; s/com.fsck.k9/$PACKAGE_NAME/g" {} \\;
# Replace strings
RUN find . -name "strings.xml" -exec sed -i "s/KoboCollect/Shopnoltd Survey/g; s/Chatwoot/Shopnoltd Chat/g; s/Jitsi Meet/Shopnoltd Meet/g; s/Owncast/Shopnoltd Live/g; s/Nextcloud/Shopnoltd Drive/g; s/K-9 Mail/Shopnoltd Mail/g" {} \\;
RUN ./gradlew --no-daemon assembleRelease 2>/dev/null || ./gradlew --no-daemon assembleDebug

FROM scratch
ARG APP_CODE
COPY --from=builder /src/upstream/app/build/outputs/apk/release/*.apk /apk/${APP_CODE}.apk
COPY --from=builder /src/upstream/app/build/outputs/apk/debug/*.apk   /apk/${APP_CODE}-debug.apk
""")

# ----------------- Update CI to include new services in build matrix -----------------
import re
wf = os.path.join(ROOT, ".github/workflows/build-platform.yml")
if os.path.exists(wf):
    txt = open(wf).read()
    # Insert new entries before the closing matrix
    new_entries = """          - { service: api-service,         dockerfile: platform/api-service/Dockerfile }
          - { service: gateway,            dockerfile: platform/gateway/Dockerfile }
          - { service: oauth-service,      dockerfile: platform/oauth-service/Dockerfile }
          - { service: tenant-router,      dockerfile: platform/tenant-router/Dockerfile }
          - { service: billing-engine,     dockerfile: platform/billing-engine/Dockerfile }
          - { service: analytics-service,  dockerfile: platform/analytics-service/Dockerfile }
          - { service: search-service,     dockerfile: platform/search-service/Dockerfile }
          - { service: storage-service,    dockerfile: platform/storage-service/Dockerfile }
          - { service: notification-service,dockerfile: platform/notification-service/Dockerfile }
          - { service: scheduler-service,  dockerfile: platform/scheduler-service/Dockerfile }
          - { service: worker-service,     dockerfile: platform/worker-service/Dockerfile }
          - { service: payment-service,    dockerfile: platform/payment-service/Dockerfile }
          - { service: exchange-service,   dockerfile: platform/exchange-service/Dockerfile }
          - { service: auth-service,       dockerfile: platform/auth-service/Dockerfile }
          - { service: audit-service,      dockerfile: platform/audit-service/Dockerfile }
          - { service: report-service,     dockerfile: platform/report-service/Dockerfile }
          - { service: license-service,    dockerfile: platform/license-service/Dockerfile }
          - { service: mobile-api,         dockerfile: platform/mobile-api/Dockerfile }
          - { service: ai-platform,        dockerfile: platform/ai-platform/Dockerfile }
          - { service: admin-portal,       dockerfile: platform/admin-portal/Dockerfile }
          - { service: web-portal,         dockerfile: platform/web-portal/Dockerfile }
          - { service: android-portal,     dockerfile: platform/android-portal/Dockerfile }
          - { service: pc-portal,          dockerfile: platform/pc-portal/Dockerfile }
          - { service: messaging-service,  dockerfile: platform/messaging-service/Dockerfile }
          - { service: meet-service,       dockerfile: platform/meet-service/Dockerfile }
          - { service: live-service,       dockerfile: platform/live-service/Dockerfile }
          - { service: mail-service,       dockerfile: platform/mail-service/Dockerfile }
          - { service: social-service,     dockerfile: platform/social-service/Dockerfile }"""
    txt = re.sub(r"matrix:\s*\n\s*include:\s*\n", "matrix:\n        include:\n" + new_entries + "\n", txt, count=1)
    open(wf, "w").write(txt)

print("✅ final 11 platform services + mobile APK CI seeded")
