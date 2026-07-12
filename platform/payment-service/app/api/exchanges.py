from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_token
from app.providers.exchange_client import get_rate, convert
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter()
bearer = HTTPBearer()
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

