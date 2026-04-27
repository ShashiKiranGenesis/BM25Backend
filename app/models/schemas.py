# Re-export schemas from individual modules for backward compatibility
from .requests import (
    QueryRequest,
    FileUploadRequest,
    MetadataUpdateRequest
)
from .responses import (
    ChunkResult,
    QueryResponse,
    StatusResponse,
    UploadResponse,
    MetadataUpdateResponse,
    DocumentDetailResponse,
    DeleteDocumentResponse,
)

__all__ = [
    "QueryRequest",
    "FileUploadRequest",
    "MetadataUpdateRequest",
    "ChunkResult",
    "QueryResponse",
    "StatusResponse",
    "UploadResponse",
    "MetadataUpdateResponse",
    "DocumentDetailResponse",
    "DeleteDocumentResponse",
]
