from pydantic import BaseModel, Field
from typing import Optional
from app.models.models import NChannel
class SendIn(BaseModel):
    channel: NChannel
    recipient: str
    subject: Optional[str] = None
    body: str
    template_code: Optional[str] = None
    variables: dict = {}
    meta: dict = {}
class Out(BaseModel):
    id: str; channel: str; status: str; recipient: str
    created_at: str; sent_at: Optional[str] = None
    class Config: from_attributes = True
class TemplateIn(BaseModel):
    code: str; name: str; channel: NChannel
    subject: Optional[str] = None; body: str
    variables: list = []
