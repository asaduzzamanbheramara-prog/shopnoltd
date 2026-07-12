from pydantic import BaseModel
from typing import Optional
class ConvIn(BaseModel):
    type: str = "direct"
    title: Optional[str] = None
    participants: list
class ConvOut(BaseModel):
    id: str; type: str; title: Optional[str]; created_at: str
    class Config: from_attributes = True
class MsgIn(BaseModel):
    body: str
    attachments: list = []
class MsgOut(BaseModel):
    id: str; conversation_id: str; sender_id: str; body: str
    created_at: str
    class Config: from_attributes = True
