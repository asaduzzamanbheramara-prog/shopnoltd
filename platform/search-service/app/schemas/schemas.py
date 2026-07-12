from pydantic import BaseModel
from typing import Optional
class IndexIn(BaseModel): name: str
class DocIn(BaseModel): index: str; id: str; body: dict
class SearchIn(BaseModel):
    index: str
    query: str
    fields: Optional[list] = None
    size: int = 20
