from pydantic import BaseModel, Field


class ConvIn(BaseModel):
    type: str = Field(default="direct", pattern="^(direct|group|channel)$")
    title: str | None = Field(default=None, max_length=128)
    participants: list[str] = Field(default_factory=list, max_length=500)


class ConvOut(BaseModel):
    id: str
    type: str
    title: str | None
    created_at: str

    class Config:
        from_attributes = True


class MsgIn(BaseModel):
    body: str = Field(default="", max_length=10000)
    attachments: list[dict] = Field(default_factory=list, max_length=20)
    reply_to_id: str | None = None
    client_message_id: str | None = Field(default=None, max_length=128)


class MsgOut(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    body: str
    attachments: list | None = None
    reply_to_id: str | None = None
    created_at: str
    edited_at: str | None = None
    deleted_at: str | None = None
    status: str = "sent"

    class Config:
        from_attributes = True
