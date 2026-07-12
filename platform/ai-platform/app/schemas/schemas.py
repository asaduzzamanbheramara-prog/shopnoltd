from pydantic import BaseModel
from typing import Optional
class InferIn(BaseModel):
    prompt: str
    agent_id: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.7
class InferOut(BaseModel):
    response: str
    model: str
    tokens: int
class EmbedIn(BaseModel):
    texts: list
class EmbedOut(BaseModel):
    embeddings: list
    model: str
    dim: int
class DocIn(BaseModel):
    title: str
    source_uri: Optional[str] = None
    text: Optional[str] = None
class AgentIn(BaseModel):
    name: str
    system_prompt: str = "You are a helpful Shopnoltd assistant."
    model: Optional[str] = None
