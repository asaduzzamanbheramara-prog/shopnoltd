from pydantic import BaseModel


class IndexIn(BaseModel):
    name: str


class DocIn(BaseModel):
    index: str
    id: str
    body: dict


class SearchIn(BaseModel):
    index: str
    query: str
    fields: list | None = None
    size: int = 20
