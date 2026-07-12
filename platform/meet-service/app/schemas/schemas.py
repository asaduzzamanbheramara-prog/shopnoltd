from pydantic import BaseModel
from typing import Optional
class RoomIn(BaseModel):
    name: str
    password: Optional[str] = None
    recording: bool = False
class RoomOut(BaseModel):
    id: str; name: str; owner_id: str; is_recording: bool
    created_at: str; jitsi_url: str; jwt: str
