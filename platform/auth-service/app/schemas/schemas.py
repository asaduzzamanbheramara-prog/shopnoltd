from pydantic import BaseModel
class LoginIn(BaseModel):
    email: str
    password: str
    device: str = "web"
class LoginOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    session_id: str
