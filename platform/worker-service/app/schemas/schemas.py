from pydantic import BaseModel


class TaskIn(BaseModel):
    name: str
    args: dict = {}


class TaskOut(BaseModel):
    id: str
    name: str
    status: str
    result: dict | None
    created_at: str
    started_at: str | None
    finished_at: str | None
