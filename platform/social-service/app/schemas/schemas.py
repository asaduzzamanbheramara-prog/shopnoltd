from pydantic import BaseModel, Field


class PostIn(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    media: list = Field(default_factory=list, max_length=50)
    visibility: str = Field(default="public", pattern="^(public|tenant|followers|private)$")
    scheduled_at: str | None = None


class PostOut(BaseModel):
    id: str
    user_id: str
    content: str
    media: list
    visibility: str
    published_at: str
    like_count: int
    share_count: int
    comment_count: int

    class Config:
        from_attributes = True


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: str | None = None


class ShareIn(BaseModel):
    target: str = Field(default="internal", pattern="^(internal|copy|twitter|facebook|linkedin)$")


class ReactionIn(BaseModel):
    reaction: str = Field(min_length=1, max_length=32)
