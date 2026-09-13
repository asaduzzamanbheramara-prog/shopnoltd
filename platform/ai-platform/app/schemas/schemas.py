from pydantic import BaseModel, Field


class InferAttachment(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=128)
    data: str | None = None
    text: str | None = None


class InferIn(BaseModel):
    prompt: str
    model: str | None = None
    agent_id: str | None = None
    max_tokens: int = 512
    temperature: float = 0.7
    attachments: list[InferAttachment] = Field(default_factory=list)


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
    source_uri: str | None = None
    text: str | None = None


class AgentIn(BaseModel):
    name: str
    system_prompt: str = "You are a helpful Shopnoltd assistant."
    model: str | None = None
