#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
W() { mkdir -p "$(dirname "$2")"; printf '%s' "$3" > "$2"; }
H() { mkdir -p "$(dirname "$2")"; cat > "$2" <<HEREDOC_$RANDOM
$3
HEREDOC
}

H "$ROOT/platform/payment-service/Dockerfile" 'FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd -g 10001 shopno && useradd -u 10001 -g shopno -d /app -s /sbin/nologin shopno
WORKDIR /app
COPY platform/payment-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY platform/payment-service/app /app/app
COPY shared/libraries/python /app/shared
USER shopno
EXPOSE 8080
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen(\"http://127.0.0.1:8080/healthz\").read()"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080","--proxy-headers","--forwarded-allow-ips","*"]
'

H "$ROOT/platform/payment-service/requirements.txt" 'fastapi==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.1
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.13.3
redis==5.2.0
httpx==0.27.2
stripe==11.1.0
paypalrestsdk==1.13.3
binance-pay==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.17
prometheus-client==0.21.0
structlog==24.4.0
tenacity==9.0.0
'

H "$ROOT/platform/payment-service/app/main.py" '"""Shopnoltd Payment Service."""
from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
import structlog
from app.api import wallets, deposits, withdrawals, transfers, transactions, webhooks, admin, exchanges
from app.core.config import settings
from app.core.db import engine, Base
from app.core.redis_client import redis_client

log = structlog.get_logger()
REQUESTS = Counter("shopno_payments_http_requests_total", "HTTP requests", ["method","path","code"])
LATENCY = Histogram("shopno_payments_http_latency_seconds", "HTTP latency", ["path"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_client.ping()
    log.info("payment-service.started", env=settings.env, version=settings.version)
    yield
    await engine.dispose()
    await redis_client.aclose()

app = FastAPI(title="Shopnoltd Payment Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def metrics_middleware(request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log.exception("unhandled.error", path=request.url.path, err=str(exc))
        REQUESTS.labels(request.method, request.url.path, "500").inc()
        return JSONResponse({"detail":"Internal error"}, status_code=500)
    elapsed = time.perf_counter() - start
    LATENCY.labels(request.url.path).observe(elapsed)
    REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
    return response

app.include_router(wallets.router,      prefix="/api/v1/wallets",      tags=["wallets"])
app.include_router(deposits.router,     prefix="/api/v1/deposits",     tags=["deposits"])
app.include_router(withdrawals.router,  prefix="/api/v1/withdrawals",  tags=["withdrawals"])
app.include_router(transfers.router,    prefix="/api/v1/transfers",    tags=["transfers"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(exchanges.router,    prefix="/api/v1/exchanges",    tags=["exchanges"])
app.include_router(webhooks.router,     prefix="/api/v1/webhooks",     tags=["webhooks"])
app.include_router(admin.router,        prefix="/api/v1/admin",        tags=["admin"])

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

H "$ROOT/platform/payment-service/app/__init__.py" ''
for d in core models schemas providers api migrations workers; do
  H "$ROOT/platform/payment-service/app/$d/__init__.py" ''
done

H "$ROOT/platform/payment-service/app/core/config.py" 'from pydantic_settings import BaseSettings
from typing import List
class Settings(BaseSettings):
    app_name: str = "shopnoltd-payment-service"
    env: str = "production"
    version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://shopno:shopno@postgres.data.svc.cluster.local:5432/payments"
    redis_url: str = "redis://redis.data.svc.cluster.local:6379/0"
    cors_origins: str = "https://*.shopnoltd.dpdns.org"
    keycloak_issuer: str = "https://auth.shopnoltd.dpdns.org/realms/shopnoltd"
    keycloak_audience: str = "payment-service"
    exchange_service_url: str = "http://exchange-service.shopno-payments.svc.cluster.local:8080"
    billing_engine_url: str = "http://billing-engine.shopno-payments.svc.cluster.local:8080"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    paypal_client_id: str = ""
    paypal_secret: str = ""
    binance_pay_key: str = ""
    binance_pay_secret: str = ""
    payeer_account: str = ""
    payeer_api_key: str = ""
    bkash_app_key: str = ""
    bkash_app_secret: str = ""
    nagad_merchant_id: str = ""
    nagad_merchant_key: str = ""
    rocket_merchant_id: str = ""
    rocket_merchant_key: str = ""
    admin_approval_required: bool = True
    min_deposit: float = 1.0
    max_deposit: float = 100000.0
    min_withdrawal: float = 5.0
    max_withdrawal: float = 50000.0
    platform_fee_pct: float = 1.5
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
settings = Settings()
'

H "$ROOT/platform/payment-service/app/core/db.py" 'from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings
engine = create_async_engine(settings.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True)
Base = declarative_base()
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
'

H "$ROOT/platform/payment-service/app/core/redis_client.py" 'from redis.asyncio import Redis
from app.core.config import settings
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
'

H "$ROOT/platform/payment-service/app/core/security.py" 'import httpx
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
'

H "$ROOT/platform/payment-service/app/models/models.py" 'from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid, enum
from datetime import datetime
from app.core.db import Base
class TxStatus(str, enum.Enum):
    pending="pending"; processing="processing"; completed="completed"; failed="failed"; cancelled="cancelled"; requires_approval="requires_approval"
class TxType(str, enum.Enum):
    deposit="deposit"; withdrawal="withdrawal"; transfer="transfer"; fee="fee"; refund="refund"; exchange="exchange"; subscription="subscription"
class PaymentMethod(str, enum.Enum):
    stripe="stripe"; paypal="paypal"; binance="binance"; payeer="payeer"; bkash="bkash"; nagad="nagad"; rocket="rocket"; bank="bank"; manual="manual"; btc="btc"; eth="eth"; usdt="usdt"; bnb="bnb"; sol="sol"; trx="trx"
class Wallet(Base):
    __tablename__ = "wallets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    currency = Column(String(8), nullable=False)
    balance = Column(Numeric(20, 8), default=0, nullable=False)
    frozen = Column(Numeric(20, 8), default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (Index("ix_wallet_user_currency", "user_id", "currency", unique=True),)
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False)
    type = Column(Enum(TxType), nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(TxStatus), default=TxStatus.pending, nullable=False, index=True)
    amount = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), default=0, nullable=False)
    currency = Column(String(8), nullable=False)
    external_id = Column(String(128), index=True, nullable=True)
    reference = Column(String(128), nullable=True)
    meta = Column(JSONB, default=dict)
    approved_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
'

H "$ROOT/platform/payment-service/app/schemas/schemas.py" 'from pydantic import BaseModel, Field
from typing import Optional
from app.models.models import PaymentMethod, TxType, TxStatus
class WalletOut(BaseModel):
    id: str; currency: str; balance: float; frozen: float
    class Config: from_attributes = True
class DepositIn(BaseModel):
    currency: str = Field(min_length=3, max_length=8)
    amount: float = Field(gt=0)
    method: PaymentMethod
    return_url: Optional[str] = None
    metadata: dict = {}
class WithdrawalIn(BaseModel):
    currency: str = Field(min_length=3, max_length=8)
    amount: float = Field(gt=0)
    method: PaymentMethod
    destination: str
    metadata: dict = {}
class TransferIn(BaseModel):
    to_user_id: str; currency: str; amount: float = Field(gt=0); note: Optional[str] = None
class TxOut(BaseModel):
    id: str; type: TxType; method: PaymentMethod; status: TxStatus
    amount: float; fee: float; currency: str; reference: Optional[str]
    created_at: str; completed_at: Optional[str]
    approval_url: Optional[str] = None
    redirect_url: Optional[str] = None
    qr_code: Optional[str] = None
    address: Optional[str] = None
    class Config: from_attributes = True
'

H "$ROOT/platform/payment-service/app/providers/base.py" 'from abc import ABC, abstractmethod
class BaseProvider(ABC):
    def __init__(self, name: str): self.name = name
    @abstractmethod
    async def create_deposit(self, tx, **kwargs) -> dict: ...
    @abstractmethod
    async def create_withdrawal(self, tx, **kwargs) -> dict: ...
    @abstractmethod
    async def verify_webhook(self, body, headers) -> dict: ...
    @abstractmethod
    async def get_status(self, external_id) -> str: ...
'

H "$ROOT/platform/payment-service/app/providers/stripe_provider.py" 'import stripe
from app.providers.base import BaseProvider
from app.core.config import settings
stripe.api_key = settings.stripe_secret_key
class StripeProvider(BaseProvider):
    def __init__(self): super().__init__("stripe")
    async def create_deposit(self, tx, return_url=None, **kwargs):
        intent = stripe.PaymentIntent.create(amount=int(tx.amount*100), currency=tx.currency.lower(), metadata={"tx_id":str(tx.id),"tenant_id":tx.tenant_id}, automatic_payment_methods={"enabled":True})
        return {"external_id":intent.id, "client_secret":intent.client_secret, "redirect_url":return_url}
    async def create_withdrawal(self, tx, destination, **kwargs):
        tr = stripe.Transfer.create(amount=int(tx.amount*100), currency=tx.currency.lower(), destination=destination)
        return {"external_id":tr.id, "status":tr.status}
    async def verify_webhook(self, body, headers):
        event = stripe.Webhook.construct_event(body, headers.get("stripe-signature",""), settings.stripe_webhook_secret)
        return event.to_dict()
    async def get_status(self, external_id):
        return stripe.PaymentIntent.retrieve(external_id).status
'

H "$ROOT/platform/payment-service/app/providers/binance_pay.py" 'import httpx, hmac, hashlib, json, time
from app.providers.base import BaseProvider
from app.core.config import settings
class BinancePayProvider(BaseProvider):
    BASE = "https://bpay.binanceapi.com"
    def __init__(self): super().__init__("binance")
    def _sign(self, params):
        payload = json.dumps(params, separators=(",",":"), sort_keys=True)
        ts = int(time.time()*1000); nonce = str(ts)
        body = f"{ts}\n{nonce}\n{payload}\n"
        sig = hmac.new(settings.binance_pay_secret.encode(), body.encode(), hashlib.sha512).hexdigest()
        return ts, nonce, sig
    async def create_deposit(self, tx, return_url=None, **kwargs):
        params = {"env":{"terminalType":"WEB"},"orderAmount":float(tx.amount),"currency":tx.currency.upper(),"goods":{"goodsName":f"Shopnoltd deposit {tx.id}","goodsCategory":"1000"},"orderId":str(tx.id),"returnUrl":return_url or "https://shopnoltd.dpdns.org","webhookUrl":"https://api.shopnoltd.dpdns.org/api/v1/webhooks/binance"}
        ts, nonce, sig = self._sign(params)
        headers = {"content-type":"application/json","BinancePay-Timestamp":str(ts),"BinancePay-Nonce":nonce,"BinancePay-Signature":sig}
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{self.BASE}/binancepay/openapi/v2/order", json=params, headers=headers, timeout=20)
        r.raise_for_status(); d = r.json()["data"]
        return {"external_id":d["prepayId"], "qr_code":d["qrCodeLink"], "redirect_url":d.get("universalUrl"), "checkout_url":d.get("universalUrl")}
    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError("Use manual withdrawal with admin approval")
    async def verify_webhook(self, body, headers):
        ts = headers.get("BinancePay-Timestamp"); nonce = headers.get("BinancePay-Nonce"); sig = headers.get("BinancePay-Signature")
        if not (ts and nonce and sig): raise ValueError("missing headers")
        expected = hmac.new(settings.binance_pay_secret.encode(), f"{ts}\n{nonce}\n{body.decode()}\n".encode(), hashlib.sha512).hexdigest()
        if not hmac.compare_digest(expected, sig): raise ValueError("bad signature")
        return json.loads(body)
    async def get_status(self, external_id):
        params = {"prepayId":external_id}; ts, nonce, sig = self._sign(params)
        headers = {"content-type":"application/json","BinancePay-Timestamp":str(ts),"BinancePay-Nonce":nonce,"BinancePay-Signature":sig}
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{self.BASE}/binancepay/openapi/v2/query", json=params, headers=headers, timeout=20)
        r.raise_for_status(); return r.json()["data"]["status"]
'

H "$ROOT/platform/payment-service/app/providers/bkash.py" 'import httpx, json
from app.providers.base import BaseProvider
from app.core.config import settings
TOKEN_URL = "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout/token/grant"
CREATE_URL = "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout/payment/create"
EXEC_URL   = "https://tokenized.pay.bka.sh/v1.2.0-beta/tokenized/checkout/payment/execute"
class BkashProvider(BaseProvider):
    def __init__(self): super().__init__("bkash"); self._tok=None
    async def _token(self):
        async with httpx.AsyncClient() as c:
            r = await c.post(TOKEN_URL, json={"app_key":settings.bkash_app_key,"app_secret":settings.bkash_app_secret}, headers={"username":settings.bkash_app_key,"password":settings.bkash_app_secret}, timeout=20)
        r.raise_for_status(); self._tok = r.json()["id_token"]; return self._tok
    async def create_deposit(self, tx, return_url=None, **kwargs):
        tok = await self._token()
        async with httpx.AsyncClient() as c:
            r = await c.post(CREATE_URL, json={"mode":"0011","payerReference":tx.tenant_id,"callbackURL":"https://api.shopnoltd.dpdns.org/api/v1/webhooks/bkash","amount":f"{float(tx.amount):.2f}","currency":"BDT","intent":"sale","merchantInvoiceNumber":str(tx.id)}, headers={"Authorization":tok,"X-APP-Key":settings.bkash_app_key}, timeout=20)
        r.raise_for_status(); d = r.json()
        return {"external_id":d["paymentID"], "redirect_url":d["bkashURL"], "approval_url":d["bkashURL"]}
    async def create_withdrawal(self, tx, destination, **kwargs):
        raise NotImplementedError("bkash Payout API not enabled in this build")
    async def verify_webhook(self, body, headers): return json.loads(body)
    async def get_status(self, external_id): return "PENDING"
'

H "$ROOT/platform/payment-service/app/providers/crypto.py" 'import secrets
from app.providers.base import BaseProvider
class CryptoProvider(BaseProvider):
    NETWORKS = {"btc":("bitcoin","bc1q"),"eth":("ethereum","0x"),"usdt":("ethereum","0x"),"bnb":("bsc","0x"),"sol":("solana",""),"trx":("tron","T")}
    def __init__(self, asset: str):
        super().__init__(f"crypto-{asset}"); self.asset = asset.upper()
    async def create_deposit(self, tx, **kwargs):
        net, prefix = self.NETWORKS[tx.method.value]
        addr = (prefix + secrets.token_hex(20)) if prefix else secrets.token_hex(32)
        return {"address":addr, "memo":str(tx.id)[:32], "redirect_url":f"https://shopnoltd.dpdns.org/pay/crypto/{tx.id}"}
    async def create_withdrawal(self, tx, destination, **kwargs):
        return {"external_id":f"crypto-wd-{tx.id}", "status":"requires_approval", "address":destination}
    async def verify_webhook(self, body, headers): return {"raw": body.decode("utf-8","ignore")}
    async def get_status(self, external_id): return "pending"
'

H "$ROOT/platform/payment-service/app/providers/manual.py" 'from app.providers.base import BaseProvider
class ManualProvider(BaseProvider):
    def __init__(self, name="manual"): super().__init__(name)
    async def create_deposit(self, tx, **kwargs):
        return {"approval_url":f"https://shopnoltd.dpdns.org/admin/approve/{tx.id}", "instructions":f"Send {tx.amount} {tx.currency} and reference {tx.id}."}
    async def create_withdrawal(self, tx, **kwargs):
        return {"external_id":f"manual-wd-{tx.id}", "status":"requires_approval"}
    async def verify_webhook(self, body, headers): return {"raw":body.decode("utf-8","ignore")}
    async def get_status(self, external_id): return "requires_approval"
'

H "$ROOT/platform/payment-service/app/providers/registry.py" 'from app.providers.stripe_provider import StripeProvider
from app.providers.binance_pay import BinancePayProvider
from app.providers.bkash import BkashProvider
from app.providers.crypto import CryptoProvider
from app.providers.manual import ManualProvider
from app.models.models import PaymentMethod
REG = {
    PaymentMethod.stripe: StripeProvider(),
    PaymentMethod.binance: BinancePayProvider(),
    PaymentMethod.bkash: BkashProvider(),
    PaymentMethod.btc: CryptoProvider("btc"),
    PaymentMethod.eth: CryptoProvider("eth"),
    PaymentMethod.usdt: CryptoProvider("usdt"),
    PaymentMethod.bnb: CryptoProvider("bnb"),
    PaymentMethod.sol: CryptoProvider("sol"),
    PaymentMethod.trx: CryptoProvider("trx"),
    PaymentMethod.bank: ManualProvider("bank"),
    PaymentMethod.manual: ManualProvider("manual"),
    PaymentMethod.payeer: ManualProvider("payeer"),
    PaymentMethod.nagad: ManualProvider("nagad"),
    PaymentMethod.rocket: ManualProvider("rocket"),
    PaymentMethod.paypal: ManualProvider("paypal"),
}
def get_provider(method): 
    if method not in REG: raise ValueError(f"unsupported: {method}")
    return REG[method]
'

H "$ROOT/platform/payment-service/app/providers/exchange_client.py" 'import httpx
from datetime import datetime
from app.core.config import settings
async def get_rate(frm, to):
    if frm == to: return {"rate":1.0, "timestamp":datetime.utcnow().isoformat()}
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{settings.exchange_service_url}/api/v1/rates/{frm}/{to}")
    r.raise_for_status(); return r.json()
async def convert(frm, to, amount):
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.exchange_service_url}/api/v1/convert", json={"from":frm,"to":to,"amount":amount})
    r.raise_for_status(); return r.json()
'

H "$ROOT/platform/payment-service/app/api/wallets.py" 'from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Wallet
from app.schemas.schemas import WalletOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("", response_model=list[WalletOut])
async def list_wallets(user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"]))
    return res.scalars().all()
@router.get("/{currency}", response_model=WalletOut)
async def get_wallet(currency: str, user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == currency.upper()))
    w = res.scalar_one_or_none()
    if not w: raise HTTPException(404, "wallet not found")
    return w
'

H "$ROOT/platform/payment-service/app/api/deposits.py" 'import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Wallet, Transaction, TxType, TxStatus
from app.schemas.schemas import DepositIn, TxOut
from app.providers.registry import get_provider
from app.core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=TxOut, status_code=201)
async def create_deposit(body: DepositIn, user = Depends(current_user), s: AsyncSession = Depends(db)):
    if body.amount < settings.min_deposit or body.amount > settings.max_deposit:
        raise HTTPException(400, "amount out of range")
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == body.currency.upper()))
    w = res.scalar_one_or_none()
    if not w: w = Wallet(tenant_id=user.get("tenant_id","default"), user_id=user["sub"], currency=body.currency.upper(), balance=0); s.add(w); await s.flush()
    tx = Transaction(tenant_id=user.get("tenant_id","default"), wallet_id=w.id, type=TxType.deposit, method=body.method, status=TxStatus.pending, amount=body.amount, fee=0, currency=body.currency.upper(), meta=body.metadata)
    s.add(tx); await s.flush()
    out = await get_provider(body.method).create_deposit(tx, return_url=body.return_url)
    tx.external_id = out.get("external_id")
    await s.commit()
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=0, currency=tx.currency, reference=tx.external_id, created_at=tx.created_at.isoformat(), completed_at=None, redirect_url=out.get("redirect_url"), qr_code=out.get("qr_code"), address=out.get("address"), approval_url=out.get("approval_url"))
@router.get("/{tx_id}", response_model=TxOut)
async def get_deposit(tx_id: str, user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Transaction).where(Transaction.id == uuid.UUID(tx_id), Transaction.tenant_id == user.get("tenant_id","default")))
    tx = res.scalar_one_or_none()
    if not tx: raise HTTPException(404, "tx not found")
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=float(tx.fee), currency=tx.currency, reference=tx.external_id, created_at=tx.created_at.isoformat(), completed_at=tx.completed_at.isoformat() if tx.completed_at else None)
'

H "$ROOT/platform/payment-service/app/api/withdrawals.py" 'import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Wallet, Transaction, TxType, TxStatus
from app.schemas.schemas import WithdrawalIn, TxOut
from app.providers.registry import get_provider
from app.core.config import settings
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=TxOut, status_code=201)
async def create_withdrawal(body: WithdrawalIn, user = Depends(current_user), s: AsyncSession = Depends(db)):
    if body.amount < settings.min_withdrawal or body.amount > settings.max_withdrawal:
        raise HTTPException(400, "amount out of range")
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == body.currency.upper()))
    w = res.scalar_one_or_none()
    if not w: raise HTTPException(404, "wallet not found")
    if Decimal(str(w.balance)) < Decimal(str(body.amount)):
        raise HTTPException(400, "insufficient funds")
    w.frozen = Decimal(str(w.frozen)) + Decimal(str(body.amount))
    tx = Transaction(tenant_id=user.get("tenant_id","default"), wallet_id=w.id, type=TxType.withdrawal, method=body.method, status=TxStatus.requires_approval if settings.admin_approval_required else TxStatus.processing, amount=body.amount, currency=body.currency.upper(), fee=body.amount * settings.platform_fee_pct / 100, meta=body.metadata)
    s.add(tx); await s.flush()
    out = await get_provider(body.method).create_withdrawal(tx, destination=body.destination)
    if out.get("status") == "requires_approval":
        tx.status = TxStatus.requires_approval
    else:
        tx.status = TxStatus.processing
    tx.external_id = out.get("external_id")
    await s.commit()
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=float(tx.fee), currency=tx.currency, reference=tx.external_id, created_at=tx.created_at.isoformat(), completed_at=None, approval_url=out.get("approval_url"))
'

H "$ROOT/platform/payment-service/app/api/transfers.py" 'import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Wallet, Transaction, TxType, TxStatus
from app.schemas.schemas import TransferIn, TxOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("", response_model=TxOut, status_code=201)
async def internal_transfer(body: TransferIn, user = Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Wallet).where(Wallet.user_id == user["sub"], Wallet.currency == body.currency.upper()))
    src = res.scalar_one_or_none()
    if not src: raise HTTPException(404, "source wallet not found")
    if Decimal(str(src.balance)) < Decimal(str(body.amount)):
        raise HTTPException(400, "insufficient funds")
    res = await s.execute(select(Wallet).where(Wallet.user_id == body.to_user_id, Wallet.currency == body.currency.upper()))
    dst = res.scalar_one_or_none()
    if not dst:
        dst = Wallet(tenant_id=user.get("tenant_id","default"), user_id=body.to_user_id, currency=body.currency.upper(), balance=0); s.add(dst); await s.flush()
    src.balance = Decimal(str(src.balance)) - Decimal(str(body.amount))
    dst.balance = Decimal(str(dst.balance)) + Decimal(str(body.amount))
    tx = Transaction(tenant_id=user.get("tenant_id","default"), wallet_id=src.id, type=TxType.transfer, method="transfer", status=TxStatus.completed, amount=body.amount, currency=body.currency.upper(), fee=0, meta={"to":body.to_user_id, "note":body.note})
    s.add(tx); await s.commit()
    return TxOut(id=str(tx.id), type=tx.type, method=tx.method, status=tx.status, amount=float(tx.amount), fee=0, currency=tx.currency, reference=None, created_at=tx.created_at.isoformat(), completed_at=tx.created_at.isoformat())
'

H "$ROOT/platform/payment-service/app/api/transactions.py" 'from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction
from app.schemas.schemas import TxOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.get("", response_model=list[TxOut])
async def history(user = Depends(current_user), s: AsyncSession = Depends(db), limit: int = Query(50, le=200), offset: int = 0):
    res = await s.execute(select(Transaction).where(Transaction.tenant_id == user.get("tenant_id","default")).order_by(Transaction.created_at.desc()).limit(limit).offset(offset))
    return [TxOut(id=str(t.id), type=t.type, method=t.method, status=t.status, amount=float(t.amount), fee=float(t.fee), currency=t.currency, reference=t.external_id, created_at=t.created_at.isoformat(), completed_at=t.completed_at.isoformat() if t.completed_at else None) for t in res.scalars().all()]
'

H "$ROOT/platform/payment-service/app/api/webhooks.py" 'import json
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.models.models import Transaction, TxStatus, Wallet, PaymentMethod
from app.providers.registry import get_provider
router = APIRouter()
@router.post("/{provider}")
async def webhook(provider: str, request: Request):
    body = await request.body(); headers = dict(request.headers)
    try: method = PaymentMethod(provider)
    except ValueError: raise HTTPException(400, "unknown provider")
    p = get_provider(method)
    try: event = await p.verify_webhook(body, headers)
    except Exception as e: raise HTTPException(400, f"signature: {e}")
    async with SessionLocal() as s:
        external = event.get("external_id") or event.get("paymentID") or event.get("prepayId") or (event.get("data") or {}).get("prepayId")
        if not external: return {"received": True}
        res = await s.execute(select(Transaction).where(Transaction.external_id == str(external)))
        tx = res.scalar_one_or_none()
        if not tx: return {"received": True, "warning":"tx not found"}
        status = (event.get("status") or (event.get("data") or {}).get("status") or event.get("transactionStatus") or "").upper()
        wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id)); w = wr.scalar_one()
        if status in ("COMPLETED","SUCCESS","PAID","CAPTURED","TRADE_SUCCESS"):
            tx.status = TxStatus.completed; tx.completed_at = datetime.utcnow()
            w.balance = Decimal(str(w.balance)) + Decimal(str(tx.amount)) - Decimal(str(tx.fee))
        elif status in ("FAILED","EXPIRED","CANCELED","CANCELLED"):
            tx.status = TxStatus.failed; tx.completed_at = datetime.utcnow()
            if tx.type.value == "withdrawal":
                w.frozen = Decimal(str(w.frozen)) - Decimal(str(tx.amount))
        await s.commit()
    return {"received": True}
'

H "$ROOT/platform/payment-service/app/api/admin.py" 'import uuid
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Transaction, TxStatus, Wallet
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def require_admin(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    user = await verify_token(creds.credentials)
    if "admin" not in user.get("roles", []): raise HTTPException(403, "admin only")
    return user
@router.get("/pending")
async def pending(user = Depends(require_admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Transaction).where(Transaction.status.in_([TxStatus.requires_approval, TxStatus.pending])))
    return [{"id":str(t.id),"type":t.type.value,"method":t.method.value,"amount":float(t.amount),"currency":t.currency,"created_at":t.created_at.isoformat()} for t in res.scalars().all()]
@router.post("/approve/{tx_id}")
async def approve(tx_id: str, user = Depends(require_admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Transaction).where(Transaction.id == uuid.UUID(tx_id)))
    tx = res.scalar_one_or_none()
    if not tx: raise HTTPException(404, "tx not found")
    if tx.status not in (TxStatus.requires_approval, TxStatus.pending): raise HTTPException(400, "tx not pending approval")
    wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id)); w = wr.scalar_one()
    if tx.type.value == "withdrawal":
        w.balance = Decimal(str(w.balance)) - Decimal(str(tx.amount))
        w.frozen = Decimal(str(w.frozen)) - Decimal(str(tx.amount))
    tx.status = TxStatus.completed; tx.completed_at = datetime.utcnow(); tx.approved_by = user["sub"]
    await s.commit(); return {"ok": True}
@router.post("/reject/{tx_id}")
async def reject(tx_id: str, user = Depends(require_admin), s: AsyncSession = Depends(db)):
    res = await s.execute(select(Transaction).where(Transaction.id == uuid.UUID(tx_id)))
    tx = res.scalar_one_or_none()
    if not tx: raise HTTPException(404, "tx not found")
    if tx.type.value == "withdrawal":
        wr = await s.execute(select(Wallet).where(Wallet.id == tx.wallet_id)); w = wr.scalar_one()
        w.frozen = Decimal(str(w.frozen)) - Decimal(str(tx.amount))
    tx.status = TxStatus.cancelled; tx.completed_at = datetime.utcnow(); tx.approved_by = user["sub"]
    await s.commit(); return {"ok": True}
'

H "$ROOT/platform/payment-service/app/api/exchanges.py" 'from fastapi import APIRouter, Depends
from app.core.security import verify_token
from app.providers.exchange_client import get_rate, convert
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
class RateOut(BaseModel):
    from_currency: str; to_currency: str; rate: float; timestamp: str
@router.get("/rate", response_model=RateOut)
async def rate(from_currency: str, to_currency: str, user = Depends(current_user)):
    r = await get_rate(from_currency.upper(), to_currency.upper())
    return RateOut(from_currency=from_currency.upper(), to_currency=to_currency.upper(), rate=r["rate"], timestamp=r["timestamp"])
class ConvertIn(BaseModel):
    from_currency: str; to_currency: str; amount: float
class ConvertOut(BaseModel):
    from_amount: float; to_amount: float; rate: float; fee: float
@router.post("/convert", response_model=ConvertOut)
async def do_convert(body: ConvertIn, user = Depends(current_user)):
    res = await convert(body.from_currency.upper(), body.to_currency.upper(), body.amount)
    return ConvertOut(**res)
'

H "$ROOT/platform/payment-service/alembic.ini" '[alembic]
script_location = migrations
sqlalchemy.url = postgresql+asyncpg://shopno:shopno@postgres:5432/payments
'

H "$ROOT/platform/payment-service/migrations/env.py" 'from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.db import Base
from app.models import models
config = context.config
if config.config_file_name is not None: fileConfig(config.config_file_name)
target_metadata = Base.metadata
'

H "$ROOT/platform/payment-service/migrations/versions/0001_init.py" '"""initial schema
Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa
revision = "0001"; down_revision = None; branch_labels = None; depends_on = None
def upgrade():
    op.create_table("wallets", sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True), sa.Column("user_id", sa.String(64), nullable=False), sa.Column("currency", sa.String(8), nullable=False), sa.Column("balance", sa.Numeric(20, 8), server_default="0"), sa.Column("frozen", sa.Numeric(20, 8), server_default="0"), sa.Column("created_at", sa.DateTime), sa.Column("updated_at", sa.DateTime), sa.UniqueConstraint("user_id", "currency", name="ix_wallet_user_currency"))
    op.create_table("transactions", sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("tenant_id", sa.String(64), nullable=False, index=True), sa.Column("wallet_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id")), sa.Column("type", sa.String(16)), sa.Column("method", sa.String(16)), sa.Column("status", sa.String(16)), sa.Column("amount", sa.Numeric(20, 8)), sa.Column("fee", sa.Numeric(20, 8), server_default="0"), sa.Column("currency", sa.String(8)), sa.Column("external_id", sa.String(128), index=True), sa.Column("reference", sa.String(128)), sa.Column("meta", sa.dialects.postgresql.JSONB), sa.Column("approved_by", sa.String(64)), sa.Column("created_at", sa.DateTime, index=True), sa.Column("completed_at", sa.DateTime))
def downgrade(): op.drop_table("transactions"); op.drop_table("wallets")
'

echo "✅ payment-service seeded"
