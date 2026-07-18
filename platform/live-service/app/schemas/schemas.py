from pydantic import BaseModel


class StreamIn(BaseModel):
    name: str
    title: str
    description: str = ""
    recording_enabled: bool = True


class StreamOut(BaseModel):
    id: str
    name: str
    title: str
    description: str
    is_live: bool
    viewer_count: int
    rtmp_url: str
    stream_key: str
    watch_url: str
    recording_storage_path: str
