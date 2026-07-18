from pydantic import BaseModel


class DomainIn(BaseModel):
    name: str


class MailboxIn(BaseModel):
    local_part: str
    quota_mb: int = 1024
