"""Pydantic schemas."""
from pydantic import BaseModel, Field
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
    to_user_id: str
    currency: str
    amount: float = Field(gt=0)
    note: Optional[str] = None

class TxOut(BaseModel):
    id: str; type: TxType; method: PaymentMethod; status: TxStatus
    amount: float; fee: float; currency: str; reference: Optional[str]
    created_at: str; completed_at: Optional[str]
    approval_url: Optional[str] = None
    redirect_url: Optional[str] = None
    qr_code: Optional[str] = None
    address: Optional[str] = None
    class Config: from_attributes = True

