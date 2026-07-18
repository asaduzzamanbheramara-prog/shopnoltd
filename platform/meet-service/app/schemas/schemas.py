from pydantic import BaseModel


class RoomIn(BaseModel):
    name: str
    password: str | None = None
    recording: bool = False


class RoomOut(BaseModel):
    id: str
    name: str
    owner_id: str
    is_recording: bool
    created_at: str
    jitsi_url: str
    jwt: str
