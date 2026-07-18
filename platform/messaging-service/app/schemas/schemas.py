from pydantic import BaseModel


class ConvIn(BaseModel):
    type: str = "direct"
    title: str | None = None
    participants: list


class ConvOut(BaseModel):
    id: str
    type: str
    title: str | None
    created_at: str

    class Config:
        from_attributes = True


class MsgIn(BaseModel):
    body: str
    attachments: list = []


class MsgOut(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    body: str
    created_at: str

    class Config:
        from_attributes = True
