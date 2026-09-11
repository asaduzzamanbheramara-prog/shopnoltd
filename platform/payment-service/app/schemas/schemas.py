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
    idempotency_key: str = Field(min_length=8, max_length=128)
    metadata: dict = {}


class WithdrawalIn(BaseModel):
    currency: str = Field(min_length=3, max_length=8)
    amount: float = Field(gt=0)
    method: PaymentMethod
    destination: str
    metadata: dict = {}


class TransferIn(BaseModel):
    to_user_id: str
    currency: str = Field(min_length=3, max_length=8)
    amount: float = Field(gt=0)
    note: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)


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


class DirectPaymentIntentIn(BaseModel):
    provider: str = Field(pattern=r"^(bkash|nagad|rocket)$")
    amount: float = Field(gt=0)
    currency: str = Field(default="BDT", min_length=3, max_length=8)
    account_id: str | None = None
    order_id: str | None = Field(default=None, max_length=128)


class DirectPaymentSubmissionIn(BaseModel):
    txid: str = Field(min_length=4, max_length=128)
    sender_number: str | None = Field(default=None, max_length=32)
    amount: float | None = Field(default=None, gt=0)
    reference: str | None = Field(default=None, max_length=128)


class DirectPaymentVerificationIn(BaseModel):
    authorized_evidence: bool = False
    txid: str | None = None
    amount: float | None = Field(default=None, gt=0)
    receiver_number: str
    provider_transaction_id: str | None = None
    evidence: dict = {}
