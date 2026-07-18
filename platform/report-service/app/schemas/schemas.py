from pydantic import BaseModel


class ReportIn(BaseModel):
    name: str
    kind: str = "pdf"
    query_sql: str = None
