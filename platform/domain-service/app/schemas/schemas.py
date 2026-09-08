from pydantic import BaseModel


class ZoneIn(BaseModel):
    name: str
    kind: str = "MASTER"


class RecordIn(BaseModel):
    zone_id: str
    name: str
    type: str  # A, AAAA, CNAME, MX, TXT, NS, SRV
    content: str
    ttl: int = 3600
    priority: int = 0


class ContactIn(BaseModel):
    """Namecheap (and most registrars) legally require registrant contact
    details for every domain purchase — this had no representation
    anywhere in the frontend or backend before."""

    first_name: str
    last_name: str
    address1: str
    city: str
    state: str
    postal_code: str
    country: str  # ISO 2-letter, e.g. "US", "BD"
    phone: str  # E.164 format, e.g. "+1.5551234567"
    email: str


class RegisterDomainIn(BaseModel):
    domain: str
    years: int = 1
    contact: ContactIn


class DomainOut(BaseModel):
    id: str
    name: str
    registrar_name: str
    years: int
    price: float
    currency: str
    status: str
    order_id: str | None = None
    expires_at: str | None = None
    created_at: str
