from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 15
    rerank_top_n: Optional[int] = 5
    filter_files: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class ChunkResult(BaseModel):
    text: str
    page: int
    score: float
    source_file: str
    file_path: str
    metadata: dict
    document_metadata: dict


class QueryResponse(BaseModel):
    question: str
    answer: str
    source_chunks: List[ChunkResult]


class StatusResponse(BaseModel):
    ready: bool
    message: Optional[str] = None
    total_documents: Optional[int] = None
    total_chunks: Optional[int] = None
    last_updated: Optional[str] = None
    documents: Optional[dict] = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str] = None
    total_documents: Optional[int] = None
    total_chunks: Optional[int] = None


class MetadataUpdateResponse(BaseModel):
    success: bool
    message: str
