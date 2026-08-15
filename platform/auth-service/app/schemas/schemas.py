from pydantic import BaseModel


class LoginIn(BaseModel):
    email: str
    password: str
    device: str = "web"


class SignupIn(BaseModel):
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""


class SignupOut(BaseModel):
    ok: bool
    user_id: str | None = None
    message: str


class SocialTokenIn(BaseModel):
    code: str
    redirect_uri: str
    code_verifier: str | None = None
    device: str = "web"


class LoginOut(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    session_id: str
