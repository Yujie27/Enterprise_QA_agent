from pydantic import BaseModel, Field
from typing import Any

class IngestResponse(BaseModel):
    ok: bool
    num_chunks: int
    message: str

class AskRequest(BaseModel):
    question: str
    top_k: int = Field(4, ge=1, le=20)
    use_llm: bool = False

class Citation(BaseModel):
    source: str
    doc_type: str
    chunk_id: str
    score: float
    text: str

class AskResponse(BaseModel):
    answer: str
    route: str = "ask"
    citations: list[Citation]

class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(5, ge=1, le=20)

class SearchResponse(BaseModel):
    route: str
    matches: list[Citation]

class ExperimentQueryRequest(BaseModel):
    query: str = ""
    top_k: int = Field(5, ge=1, le=50)

class ExperimentRecord(BaseModel):
    data: dict[str, Any]

class ExperimentQueryResponse(BaseModel):
    route: str = "experiments"
    records: list[ExperimentRecord]
    summary: str

class AgentRequest(BaseModel):
    question: str
    top_k: int = Field(5, ge=1, le=20)
    use_llm: bool = False
