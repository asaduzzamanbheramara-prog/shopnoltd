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
