from pydantic import BaseModel

from app.models.models import NChannel


class SendIn(BaseModel):
    channel: NChannel
    recipient: str
    subject: str | None = None
    body: str
    template_code: str | None = None
    variables: dict = {}
    meta: dict = {}


class Out(BaseModel):
    id: str
    channel: str
    status: str
    recipient: str
    created_at: str
    sent_at: str | None = None

    class Config:
        from_attributes = True


class TemplateIn(BaseModel):
    code: str
    name: str
    channel: NChannel
    subject: str | None = None
    body: str
    variables: list = []
