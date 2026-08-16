from pydantic import BaseModel


class RateOut(BaseModel):
    base: str
    quote: str
    rate: float
    source: str
    fetched_at: str


class ConvertIn(BaseModel):
    from_currency: str
    to_currency: str
    amount: float
    user_id: str | None = None


class ConvertOut(BaseModel):
    from_currency: str
    to_currency: str
    from_amount: float
    to_amount: float
    rate: float
    fee: float
    source: str
    timestamp: str


class ProviderOut(BaseModel):
    name: str
    status: str
    last_update: str | None
    rates_count: int
