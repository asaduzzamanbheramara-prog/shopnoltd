from pydantic import BaseModel
class ReleaseIn(BaseModel):
    code: str; version: str; build: int; apk_path: str
    sha256: str; size_bytes: int
    min_os_version: str = "8.0"; release_notes: str = ""; force_update: bool = False
class ReleaseOut(BaseModel):
    code: str; version: str; build: int
    apk_url: str; sha256: str; size_bytes: int
    min_os_version: str; force_update: bool
    release_notes: str; published_at: str
class ConfigIn(BaseModel):
    code: str; data: dict
