from pydantic import BaseModel
class JobIn(BaseModel):
    name: str; cron: str; url: str
    method: str = "POST"; body: dict = {}
class JobOut(BaseModel):
    id: str; name: str; cron: str; url: str
    active: bool; last_run: str | None; last_status: int | None
