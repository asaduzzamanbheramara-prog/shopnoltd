from pydantic import BaseModel, Field
from typing import Optional
class PostIn(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    media: list = []
    visibility: str = "public"
    scheduled_at: Optional[str] = None
class PostOut(BaseModel):
    id: str; user_id: str; content: str; media: list; visibility: str
    published_at: str; like_count: int; share_count: int; comment_count: int
    class Config: from_attributes = True
class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
class ShareIn(BaseModel):
    target: str = "internal"
