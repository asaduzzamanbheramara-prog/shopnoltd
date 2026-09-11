"""Pydantic schemas."""

from app.models.models import PaymentMethod, TxStatus, TxType
from pydantic import BaseModel, ConfigDict, Field


class WalletOut(BaseModel):
    id: str
    currency: str
    balance: float
    frozen: float
    model_config = ConfigDict(from_attributes=True)


class DepositIn(BaseModel):
    currency: str = Field(min_length=3, max_length=8)
    amount: float = Field(gt=0)
    method: PaymentMethod
    return_url: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)
    metadata: dict = Field(default_factory=dict)


class WithdrawalIn(BaseModel):
    currency: str = Field(min_length=3, max_length=8)
    amount: float = Field(gt=0)
    method: PaymentMethod
    destination: str
    metadata: dict = Field(default_factory=dict)


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
    model_config = ConfigDict(from_attributes=True)


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
    """Admin/manual verification evidence.

    This is deliberately an attestation surface, not an automatic provider API.
    Automatic verification must be implemented by a trusted provider adapter or
    signed machine-to-machine feed before the transaction is credited.
    """

    manual_review_reason: str = Field(min_length=8, max_length=500)
    txid: str | None = Field(default=None, min_length=4, max_length=128)
    amount: float = Field(gt=0)
    receiver_number: str = Field(min_length=5, max_length=32)
    provider_transaction_id: str | None = Field(default=None, min_length=4, max_length=128)
    evidence: dict = Field(default_factory=dict)
