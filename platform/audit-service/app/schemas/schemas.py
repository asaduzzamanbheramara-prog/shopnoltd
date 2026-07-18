from pydantic import BaseModel


class LogIn(BaseModel):
    action: str
    resource: str = None
    resource_id: str = None
    data: dict = {}
