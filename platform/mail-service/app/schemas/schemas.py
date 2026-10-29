from pydantic import BaseModel, Field


class DomainIn(BaseModel):
    name: str


class MailboxIn(BaseModel):
    local_part: str
    quota_mb: int = 1024
    owner_user_id: str | None = None


class MailboxOwnerIn(BaseModel):
    owner_user_id: str = Field(min_length=1, max_length=128)
