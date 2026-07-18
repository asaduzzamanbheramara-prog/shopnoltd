"""Pydantic schemas."""

from app.models.models import PaymentMethod, TxStatus, TxType
from pydantic import BaseModel, Field


class WalletOut(BaseModel):
    id: str
    currency: str
    balance: float
    frozen: float

    class Config:
        from_attributes = True


class DepositIn(BaseModel):
    currency: str = Field(min_length=3, max_length=8)
    amount: float = Field(gt=0)
    method: PaymentMethod
    return_url: str | None = None
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
    note: str | None = None


class TxOut(BaseModel):
    id: str
    type: TxType
    method: PaymentMethod
    status: TxStatus
    amount: float
    fee: float
    currency: str
    reference: str | None
    created_at: str
    completed_at: str | None
    approval_url: str | None = None
    redirect_url: str | None = None
    qr_code: str | None = None
    address: str | None = None

    class Config:
        from_attributes = True
