from datetime import datetime

from pydantic import BaseModel


class EventIn(BaseModel):
    name: str
    description: str = ""
    venue: str = ""
    starts_at: datetime
    ends_at: datetime
    timezone: str = "UTC"
    capacity: int = 100
    is_online: bool = False


class SessionIn(BaseModel):
    title: str
    description: str = ""
    starts_at: datetime
    ends_at: datetime
    track: str = ""
    room: str = ""


class TicketIn(BaseModel):
    name: str
    email: str


class SpeakerIn(BaseModel):
    name: str
    bio: str = ""
    company: str = ""
    photo: str = ""
