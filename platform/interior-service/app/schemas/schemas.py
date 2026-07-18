from pydantic import BaseModel


class ProjectIn(BaseModel):
    name: str
    description: str | None = ""
    style: str = "modern"
    budget: float = 0


class RoomIn(BaseModel):
    name: str
    width_m: float = 4
    length_m: float = 5
    height_m: float = 2.7
    color: str = "#ffffff"
