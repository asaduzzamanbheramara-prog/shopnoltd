#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
H() { mkdir -p "$(dirname "$2")"; cat > "$2" <<HEREDOC_$RANDOM
$3
HEREDOC
}

# exchange-service
H "$ROOT/platform/exchange-service/Dockerfile" 'FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd -g 10001 shopno && useradd -u 10001 -g shopno -d /app -s /sbin/nologin shopno
WORKDIR /app
COPY platform/exchange-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY platform/exchange-service/app /app/app
COPY shared/libraries/python /app/shared
USER shopno
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen(\"http://127.0.0.1:8080/healthz\").read()"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080","--proxy-headers","--forwarded-allow-ips","*"]
'
H "$ROOT/platform/exchange-service/requirements.txt" 'fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
redis==5.2.0
httpx==0.27.2
prometheus-client==0.21.0
structlog==24.4.0
'

H "$ROOT/platform/exchange-service/app/main.py" 'from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from starlette.responses import Response
import structlog
from app.api import rates, convert, providers, history
from app.core.config import settings
from app.core.db import engine, Base
from app.core.redis_client import redis_client
from app.core.rate_updater import RateUpdater

log = structlog.get_logger()
updater = RateUpdater()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    await updater.start()
    log.info("exchange-service.started", env=settings.env)
    yield
    await updater.stop()
    await engine.dispose()
    await redis_client.aclose()

app = FastAPI(title="Shopnoltd Exchange Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(rates.router,    prefix="/api/v1/rates",    tags=["rates"])
app.include_router(convert.router,  prefix="/api/v1/convert",  tags=["convert"])
app.include_router(providers.router,prefix="/api/v1/providers",tags=["providers"])
app.include_router(history.router,  prefix="/api/v1/history",  tags=["history"])

@app.get("/healthz", include_in_schema=False)
async def healthz(): return {"status":"ok"}
@app.get("/readyz", include_in_schema=False)
async def readyz():
    from sqlalchemy import text
    async with engine.connect() as c: await c.execute(text("SELECT 1"))
    await redis_client.ping()
    return {"status":"ready"}
@app.get("/metrics", include_in_schema=False)
def metrics(): return Response(generate_latest(), media_type="text/plain; version=0.0.4")
'

H "$ROOT/platform/exchange-service/app/__init__.py" ''
for d in core api models schemas providers; do H "$ROOT/platform/exchange-service/app/$d/__init__.py" ''; done

H "$ROOT/platform/exchange-service/app/core/config.py" 'from pydantic_settings import BaseSettings
from typing import List
class Settings(BaseSettings):
    app_name: str = "shopnoltd-exchange-service"
    env: str = "production"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/exchange"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/1"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    binance_api: str = "https://api.binance.com"
    coingecko_api: str = "https://api.coingecko.com/api/v3"
    openexchangerates_app_id: str = ""
    rate_refresh_seconds: int = 60
    supported_fiat: str = "USD,EUR,GBP,BDT,INR,PKR,MYR,NGN,ZAR"
    supported_crypto: str = "BTC,ETH,USDT,BNB,SOL,TRX,XRP,ADA,DOGE,USDC"
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    @property
    def fiat_list(self) -> List[str]:
        return [c.strip() for c in self.supported_fiat.split(",")]
    @property
    def crypto_list(self) -> List[str]:
        return [c.strip() for c in self.supported_crypto.split(",")]
settings = Settings()
'

H "$ROOT/platform/exchange-service/app/core/db.py" 'from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
'

H "$ROOT/platform/exchange-service/app/core/redis_client.py" 'from redis.asyncio import Redis
from app.core.config import settings
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
'

H "$ROOT/platform/exchange-service/app/models/models.py" 'from sqlalchemy import Column, String, Numeric, DateTime, Index
import uuid
from datetime import datetime
from app.core.db import Base
class Rate(Base):
    __tablename__ = "rates"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    base = Column(String(8), nullable=False, index=True)
    quote = Column(String(8), nullable=False, index=True)
    rate = Column(Numeric(28, 12), nullable=False)
    source = Column(String(32), nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)
    __table_args__ = (Index("ix_rate_pair_time", "base", "quote", "fetched_at"),)
class Conversion(Base):
    __tablename__ = "conversions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    from_currency = Column(String(8), nullable=False)
    to_currency = Column(String(8), nullable=False)
    from_amount = Column(Numeric(20, 8), nullable=False)
    to_amount = Column(Numeric(20, 8), nullable=False)
    rate = Column(Numeric(28, 12), nullable=False)
    fee = Column(Numeric(20, 8), default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
'

H "$ROOT/platform/exchange-service/app/schemas/schemas.py" 'from pydantic import BaseModel
from typing import Optional
class RateOut(BaseModel):
    base: str; quote: str; rate: float; source: str; fetched_at: str
class ConvertIn(BaseModel):
    from_currency: str; to_currency: str; amount: float; user_id: Optional[str] = None
class ConvertOut(BaseModel):
    from_currency: str; to_currency: str; from_amount: float; to_amount: float
    rate: float; fee: float; source: str; timestamp: str
class ProviderOut(BaseModel):
    name: str; status: str; last_update: Optional[str]; rates_count: int
'

H "$ROOT/platform/exchange-service/app/core/rate_updater.py" '"""Periodically pull rates from multiple sources and store in DB + cache."""
import asyncio, structlog
from datetime import datetime
import httpx
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.redis_client import redis_client
from app.models.models import Rate
log = structlog.get_logger()

class RateUpdater:
    def __init__(self): self._task = None; self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self._task: self._task.cancel()

    async def _loop(self):
        while self._running:
            try:
                await self._pull_all()
            except Exception as e:
                log.exception("rate.update.failed", err=str(e))
            await asyncio.sleep(settings.rate_refresh_seconds)

    async def _pull_all(self):
        crypto, fiat = await asyncio.gather(self._pull_binance(), self._pull_coingecko(), self._pull_openexchangerates())
        async with SessionLocal() as s:
            for base, quote, rate, source in crypto + fiat:
                r = Rate(base=base, quote=quote, rate=rate, source=source, fetched_at=datetime.utcnow())
                s.add(r)
                await redis_client.set(f"rate:{base}:{quote}", f"{rate}|{source}|{datetime.utcnow().isoformat()}", ex=600)
            await s.commit()

    async def _pull_binance(self) -> list:
        out = []
        for c in settings.crypto_list:
            try:
                async with httpx.AsyncClient() as cli:
                    r = await cli.get(f"{settings.binance_api}/api/v3/ticker/price", params={"symbol": f"{c}USDT"}, timeout=10)
                d = r.json()
                if "price" in d:
                    out.append((c, "USDT", float(d["price"]), "binance"))
                    out.append(("USDT", c, 1.0 / float(d["price"]), "binance"))
            except Exception as e:
                log.warning("binance.fetch.failed", coin=c, err=str(e))
        return out

    async def _pull_coingecko(self) -> list:
        out = []
        try:
            ids = {"BTC":"bitcoin","ETH":"ethereum","USDT":"tether","BNB":"binancecoin","SOL":"solana","TRX":"tron","XRP":"ripple","ADA":"cardano","DOGE":"dogecoin","USDC":"usd-coin"}
            vs = ",".join(settings.fiat_list).lower()
            async with httpx.AsyncClient() as cli:
                r = await cli.get(f"{settings.coingecko_api}/simple/price", params={"ids":",".join(ids.values()),"vs_currencies":vs}, timeout=15)
            d = r.json()
            for sym, cid in ids.items():
                for fiat, val in d.get(cid, {}).items():
                    out.append((sym, fiat.upper(), float(val), "coingecko"))
        except Exception as e:
            log.warning("coingecko.fetch.failed", err=str(e))
        return out

    async def _pull_openexchangerates(self) -> list:
        if not settings.openexchangerates_app_id: return []
        out = []
        try:
            async with httpx.AsyncClient() as cli:
                r = await cli.get(f"https://openexchangerates.org/api/latest.json?app_id={settings.openexchangerates_app_id}", timeout=10)
            d = r.json().get("rates", {})
            for f in settings.fiat_list:
                if f != "USD" and f in d:
                    out.append((f, "USD", float(d[f]), "openexchangerates"))
                    out.append(("USD", f, 1.0 / float(d[f]), "openexchangerates"))
        except Exception as e:
            log.warning("openexchangerates.fetch.failed", err=str(e))
        return out
'

H "$ROOT/platform/exchange-service/app/api/rates.py" 'from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc
from app.core.db import SessionLocal
from app.core.redis_client import redis_client
from app.models.models import Rate
from app.schemas.schemas import RateOut
router = APIRouter()
@router.get("/{base}/{quote}", response_model=RateOut)
async def get_rate(base: str, quote: str):
    base, quote = base.upper(), quote.upper()
    if base == quote: return RateOut(base=base, quote=quote, rate=1.0, source="identity", fetched_at="1970-01-01T00:00:00")
    cached = await redis_client.get(f"rate:{base}:{quote}")
    if cached:
        rate, src, ts = cached.split("|"); return RateOut(base=base, quote=quote, rate=float(rate), source=src, fetched_at=ts)
    async with SessionLocal() as s:
        res = await s.execute(select(Rate).where(Rate.base == base, Rate.quote == quote).order_by(desc(Rate.fetched_at)).limit(1))
        r = res.scalar_one_or_none()
        if not r: raise HTTPException(404, f"no rate for {base}/{quote}")
        return RateOut(base=r.base, quote=r.quote, rate=float(r.rate), source=r.source, fetched_at=r.fetched_at.isoformat())
@router.get("", response_model=list[RateOut])
async def list_rates(limit: int = 100):
    async with SessionLocal() as s:
        res = await s.execute(select(Rate).order_by(desc(Rate.fetched_at)).limit(limit))
        return [RateOut(base=r.base, quote=r.quote, rate=float(r.rate), source=r.source, fetched_at=r.fetched_at.isoformat()) for r in res.scalars().all()]
'

H "$ROOT/platform/exchange-service/app/api/convert.py" 'from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy import select, desc
from app.core.db import SessionLocal
from app.models.models import Rate, Conversion
from app.schemas.schemas import ConvertIn, ConvertOut
router = APIRouter()
FEE_PCT = 0.5
async def _resolve_rate(base: str, quote: str) -> tuple[float, str]:
    if base == quote: return 1.0, "identity"
    async with SessionLocal() as s:
        res = await s.execute(select(Rate).where(Rate.base == base, Rate.quote == quote).order_by(desc(Rate.fetched_at)).limit(1))
        r = res.scalar_one_or_none()
        if not r: raise HTTPException(404, f"no rate for {base}/{quote}")
        return float(r.rate), r.source

@router.post("", response_model=ConvertOut)
async def convert(body: ConvertIn):
    rate, src = await _resolve_rate(body.from_currency.upper(), body.to_currency.upper())
    fee = body.amount * FEE_PCT / 100
    to_amount = (body.amount - fee) * rate
    async with SessionLocal() as s:
        s.add(Conversion(tenant_id="default", user_id=body.user_id or "anonymous", from_currency=body.from_currency.upper(), to_currency=body.to_currency.upper(), from_amount=body.amount, to_amount=to_amount, rate=rate, fee=fee))
        await s.commit()
    return ConvertOut(from_currency=body.from_currency.upper(), to_currency=body.to_currency.upper(), from_amount=body.amount, to_amount=to_amount, rate=rate, fee=fee, source=src, timestamp=datetime.utcnow().isoformat())
'

H "$ROOT/platform/exchange-service/app/api/providers.py" 'from fastapi import APIRouter
from sqlalchemy import select, func, desc
from app.core.db import SessionLocal
from app.models.models import Rate
from app.schemas.schemas import ProviderOut
router = APIRouter()
@router.get("", response_model=list[ProviderOut])
async def list_providers():
    async with SessionLocal() as s:
        res = await s.execute(select(Rate.source, func.count(Rate.id).label("c"), func.max(Rate.fetched_at).label("lu")).group_by(Rate.source))
        return [ProviderOut(name=row[0], status="ok", last_update=row[2].isoformat() if row[2] else None, rates_count=row[1]) for row in res.all()]
'

H "$ROOT/platform/exchange-service/app/api/history.py" 'from fastapi import APIRouter, Query
from sqlalchemy import select
from app.core.db import SessionLocal
from app.models.models import Conversion
from app.schemas.schemas import ConvertOut
router = APIRouter()
@router.get("/{user_id}", response_model=list[ConvertOut])
async def history(user_id: str, limit: int = Query(50, le=200)):
    async with SessionLocal() as s:
        res = await s.execute(select(Conversion).where(Conversion.user_id == user_id).order_by(Conversion.created_at.desc()).limit(limit))
        return [ConvertOut(from_currency=c.from_currency, to_currency=c.to_currency, from_amount=float(c.from_amount), to_amount=float(c.to_amount), rate=float(c.rate), fee=float(c.fee), source="history", timestamp=c.created_at.isoformat()) for c in res.scalars().all()]
'

# billing-engine
H "$ROOT/platform/billing-engine/Dockerfile" 'FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd -g 10001 shopno && useradd -u 10001 -g shopno -d /app -s /sbin/nologin shopno
WORKDIR /app
COPY platform/billing-engine/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY platform/billing-engine/app /app/app
COPY shared/libraries/python /app/shared
USER shopno
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen(\"http://127.0.0.1:8080/healthz\").read()"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080","--proxy-headers","--forwarded-allow-ips","*"]
'
H "$ROOT/platform/billing-engine/requirements.txt" 'fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
redis==5.2.0
httpx==0.27.2
jinja2==3.1.4
weasyprint==63.1
prometheus-client==0.21.0
structlog==24.4.0
'
H "$ROOT/platform/billing-engine/app/main.py" 'from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest
from starlette.responses import Response
import structlog
from app.api import plans, subscriptions, invoices, webhooks
from app.core.config import settings
from app.core.db import engine, Base
from app.core.redis_client import redis_client

log = structlog.get_logger()
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    log.info("billing-engine.started")
    yield
    await engine.dispose()
    await redis_client.aclose()

app = FastAPI(title="Shopnoltd Billing Engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(plans.router,         prefix="/api/v1/plans",         tags=["plans"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["subscriptions"])
app.include_router(invoices.router,      prefix="/api/v1/invoices",      tags=["invoices"])
app.include_router(webhooks.router,      prefix="/api/v1/webhooks",      tags=["webhooks"])

@app.get("/healthz", include_in_schema=False)
async def healthz(): return {"status":"ok"}
@app.get("/readyz", include_in_schema=False)
async def readyz():
    from sqlalchemy import text
    async with engine.connect() as c: await c.execute(text("SELECT 1"))
    await redis_client.ping()
    return {"status":"ready"}
@app.get("/metrics", include_in_schema=False)
def metrics(): return Response(generate_latest(), media_type="text/plain; version=0.0.4")
'
H "$ROOT/platform/billing-engine/app/__init__.py" ''
for d in core api models schemas; do H "$ROOT/platform/billing-engine/app/$d/__init__.py" ''; done
H "$ROOT/platform/billing-engine/app/core/config.py" 'from pydantic_settings import BaseSettings
from typing import List
class Settings(BaseSettings):
    app_name: str = "shopnoltd-billing-engine"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/billing"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/2"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    payment_service_url: str = "http://payment-service.shopno-payments.svc.cluster.local:8080"
    default_currency: str = "USD"
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
'
H "$ROOT/platform/billing-engine/app/core/db.py" 'from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
'
H "$ROOT/platform/billing-engine/app/core/redis_client.py" 'from redis.asyncio import Redis
from app.core.config import settings
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
'
H "$ROOT/platform/billing-engine/app/models/models.py" 'from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, JSON, Boolean, Integer
import uuid
from datetime import datetime
from app.core.db import Base
class Plan(Base):
    __tablename__ = "plans"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(String(512))
    price = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(8), default="USD", nullable=False)
    interval = Column(String(16), default="month")  # month, year
    features = Column(JSON, default=dict)
    quotas = Column(JSON, default=dict)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    plan_id = Column(String(64), ForeignKey("plans.id"), nullable=False)
    status = Column(String(16), default="active")  # active, cancelled, past_due
    current_period_start = Column(DateTime, default=datetime.utcnow)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    number = Column(String(32), unique=True, nullable=False)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    subscription_id = Column(String(64), ForeignKey("subscriptions.id"), nullable=True)
    currency = Column(String(8), default="USD")
    subtotal = Column(Numeric(20, 8), nullable=False)
    tax = Column(Numeric(20, 8), default=0)
    total = Column(Numeric(20, 8), nullable=False)
    status = Column(String(16), default="open")  # open, paid, void, uncollectible
    pdf_path = Column(String(256))
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime)
'
H "$ROOT/platform/billing-engine/app/schemas/schemas.py" 'from pydantic import BaseModel
from typing import Optional
class PlanIn(BaseModel):
    code: str; name: str; description: Optional[str] = ""; price: float; currency: str = "USD"
    interval: str = "month"; features: dict = {}; quotas: dict = {}
class PlanOut(PlanIn):
    id: str; active: bool
    class Config: from_attributes = True
class SubOut(BaseModel):
    id: str; plan_code: str; status: str
    current_period_start: str; current_period_end: Optional[str]
    cancel_at_period_end: bool
class InvoiceOut(BaseModel):
    id: str; number: str; currency: str; subtotal: float; tax: float; total: float
    status: str; created_at: str; paid_at: Optional[str]; pdf_url: Optional[str] = None
'
H "$ROOT/platform/billing-engine/app/api/plans.py" 'from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.models.models import Plan
from app.schemas.schemas import PlanIn, PlanOut
from app.core.security import verify_token_admin
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token_admin(creds.credentials)
@router.get("", response_model=list[PlanOut])
async def list_plans(s: AsyncSession = Depends(db)):
    res = await s.execute(select(Plan).where(Plan.active == True))
    return res.scalars().all()
@router.post("", response_model=PlanOut, status_code=201)
async def create_plan(body: PlanIn, user = Depends(admin), s: AsyncSession = Depends(db)):
    p = Plan(**body.model_dump())
    s.add(p); await s.commit(); await s.refresh(p)
    return p
@router.get("/{code}", response_model=PlanOut)
async def get_plan(code: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(Plan).where(Plan.code == code))
    p = res.scalar_one_or_none()
    if not p: raise HTTPException(404, "plan not found")
    return p
'
H "$ROOT/platform/billing-engine/app/api/subscriptions.py" 'from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Plan, Subscription
from app.schemas.schemas import SubOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{plan_code}", response_model=SubOut, status_code=201)
async def subscribe(plan_code: str, user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Plan).where(Plan.code == plan_code, Plan.active == True))
    p = res.scalar_one_or_none()
    if not p: raise HTTPException(404, "plan not found")
    res = await s.execute(select(Subscription).where(Subscription.user_id == user["sub"], Subscription.status == "active"))
    existing = res.scalar_one_or_none()
    if existing: raise HTTPException(400, "already subscribed")
    end = datetime.utcnow() + (timedelta(days=365) if p.interval == "year" else timedelta(days=30))
    sub = Subscription(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], plan_id=p.id, status="active", current_period_start=datetime.utcnow(), current_period_end=end)
    s.add(sub); await s.commit(); await s.refresh(sub)
    return SubOut(id=sub.id, plan_code=p.code, status=sub.status, current_period_start=sub.current_period_start.isoformat(), current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None, cancel_at_period_end=sub.cancel_at_period_end)
@router.get("/me", response_model=SubOut)
async def my_sub(user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Subscription).where(Subscription.user_id == user["sub"], Subscription.status == "active"))
    sub = res.scalar_one_or_none()
    if not sub: raise HTTPException(404, "no subscription")
    res = await s.execute(select(Plan).where(Plan.id == sub.plan_id))
    p = res.scalar_one()
    return SubOut(id=sub.id, plan_code=p.code, status=sub.status, current_period_start=sub.current_period_start.isoformat(), current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None, cancel_at_period_end=sub.cancel_at_period_end)
@router.delete("/me")
async def cancel(user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Subscription).where(Subscription.user_id == user["sub"], Subscription.status == "active"))
    sub = res.scalar_one_or_none()
    if not sub: raise HTTPException(404, "no subscription")
    sub.cancel_at_period_end = True; sub.updated_at = datetime.utcnow()
    await s.commit()
    return {"ok": True, "cancel_at_period_end": True}
'
H "$ROOT/platform/billing-engine/app/api/invoices.py" 'from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Invoice, Subscription, Plan
from app.schemas.schemas import InvoiceOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/generate", response_model=InvoiceOut)
async def generate(user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Subscription).where(Subscription.user_id == user["sub"], Subscription.status == "active"))
    sub = res.scalar_one_or_none()
    if not sub: raise HTTPException(404, "no subscription")
    res = await s.execute(select(Plan).where(Plan.id == sub.plan_id))
    p = res.scalar_one()
    inv = Invoice(number=f"INV-{uuid.uuid4().hex[:10].upper()}", tenant_id=user.get("tenant_id","default"), user_id=user["sub"], subscription_id=sub.id, currency=p.currency, subtotal=p.price, tax=0, total=p.price, status="open")
    s.add(inv); await s.commit(); await s.refresh(inv)
    return InvoiceOut(id=inv.id, number=inv.number, currency=inv.currency, subtotal=float(inv.subtotal), tax=float(inv.tax), total=float(inv.total), status=inv.status, created_at=inv.created_at.isoformat(), paid_at=None)
@router.get("/me", response_model=list[InvoiceOut])
async def my_invoices(user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Invoice).where(Invoice.user_id == user["sub"]).order_by(Invoice.created_at.desc()))
    return [InvoiceOut(id=i.id, number=i.number, currency=i.currency, subtotal=float(i.subtotal), tax=float(i.tax), total=float(i.total), status=i.status, created_at=i.created_at.isoformat(), paid_at=i.paid_at.isoformat() if i.paid_at else None) for i in res.scalars().all()]
@router.get("/{inv_id}/pdf")
async def pdf(inv_id: str, user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Invoice).where(Invoice.id == inv_id))
    inv = res.scalar_one_or_none()
    if not inv: raise HTTPException(404, "invoice not found")
    from app.core.pdf import render_invoice_pdf
    pdf_bytes = render_invoice_pdf(inv)
    from fastapi.responses import Response
    return Response(pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={inv.number}.pdf"})
'
H "$ROOT/platform/billing-engine/app/api/webhooks.py" '"""Stripe webhooks → trigger payment-service deposits → mark invoice paid."""
import httpx
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.config import settings
from app.models.models import Invoice
router = APIRouter()
@router.post("/stripe")
async def stripe_hook(request: Request):
    body = await request.body(); sig = request.headers.get("stripe-signature","")
    event = await _verify_stripe(body, sig)
    if event["type"] == "invoice.payment_succeeded":
        inv_id = event["data"]["object"].get("metadata",{}).get("invoice_id")
        if inv_id:
            async with SessionLocal() as s:
                res = await s.execute(select(Invoice).where(Invoice.id == inv_id))
                inv = res.scalar_one_or_none()
                if inv:
                    inv.status = "paid"; inv.paid_at = datetime.utcnow()
                    await s.commit()
    return {"received": True}
async def _verify_stripe(body, sig):
    import stripe
    stripe.api_key = settings.stripe_secret_key
    event = stripe.Webhook.construct_event(body, sig, settings.stripe_webhook_secret)
    return event.to_dict()
'
H "$ROOT/platform/billing-engine/app/core/security.py" '"""Shared JWT verification (local copy of payment-service)."""
import httpx
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
    user = await verify_token(token)
    if "admin" not in user.get("roles", []): raise PermissionError("admin only")
    return user
'
echo "✅ exchange-service + billing-engine seeded"
