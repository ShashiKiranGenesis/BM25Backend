import os
from datetime import datetime
from fastapi import APIRouter, File, HTTPException, UploadFile
from werkzeug.utils import secure_filename

from app.utils import get_logger
from app.models import (
    MetadataUpdateResponse,
    StatusResponse,
    UploadResponse,
    DocumentDetailResponse,
    DeleteDocumentResponse,
)
from app.models import FileUploadRequest
from app.services import (
    doc_manager,
    get_retriever,
    initialize_rag,
    initialize_rag_with_new_file,
)
from config import UPLOADS_DIR
from fastapi import Depends
from datetime import datetime


logger = get_logger(__name__)
router = APIRouter(tags=["Documents"])


@router.get("/", response_model=StatusResponse)
def get_status():
    """Check system status and loaded document information."""
    logger.info("GET /status")

    if get_retriever() is None:
        logger.warning("Status check — system not ready, no documents loaded")
        return StatusResponse(
            ready=False,
            message="No documents loaded. Add PDF files to uploads/ directory.",
        )

    doc_info = doc_manager.get_document_info()
    logger.info(
        "Status OK — %d documents, %d chunks",
        doc_info["total_documents"],
        doc_info["total_chunks"],
    )
    return StatusResponse(
        ready=True,
        total_documents=doc_info["total_documents"],
        total_chunks=doc_info["total_chunks"],
        last_updated=doc_info["last_updated"],
        documents=doc_info["documents"],
    )


@router.post("/", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    metadata: FileUploadRequest = Depends(FileUploadRequest.as_form),
):
    logger.info(
        "POST /upload — filename: %s, category: %s, department: %s",
        file.filename,
        metadata.category,
        metadata.department,
    )

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    uploaded_date = datetime.utcnow()
    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOADS_DIR, filename)

        os.makedirs(UPLOADS_DIR, exist_ok=True)

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # Convert metadata to dict for storage
        metadata_dict = {
            "category": metadata.category,
            "department": metadata.department,
            "doc_type": metadata.document_type,
            "version": metadata.version,
            "description": metadata.description or f"Uploaded document: {filename}",
            "effective_date": metadata.effective_date.isoformat(),
            "uploaded_date": uploaded_date.isoformat(),
        }

        new_chunks_count = initialize_rag_with_new_file(file_path, metadata_dict)
        doc_info = doc_manager.get_document_info()
        doc_id = doc_manager.get_document_id_by_filename(filename)

        return UploadResponse(
            success=True,
            message=f"PDF uploaded successfully! Created {new_chunks_count} new chunks.",
            filename=filename,
            doc_id=doc_id,
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"],
        )

    except Exception as e:
        logger.error("Upload failed for %s: %s", file.filename, e)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/refresh", response_model=UploadResponse)
def refresh_documents():
    """Reload all documents from the uploads directory (recreates all chunks)."""
    logger.info("POST /refresh — FORCE REPROCESS ALL")

    try:
        # Force reprocess all documents
        initialize_rag(force_reprocess=True)

        doc_info = doc_manager.get_document_info()
        logger.info(
            "Refresh complete — %d documents, %d chunks (all recreated)",
            doc_info["total_documents"],
            doc_info["total_chunks"],
        )
        return UploadResponse(
            success=True,
            message="Documents refreshed successfully! All chunks recreated.",
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"],
        )
    except Exception as e:
        logger.error("Refresh failed: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Error refreshing documents: {str(e)}"
        )


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document(doc_id: str):
    """Get document details by unique document ID."""
    logger.info("GET /documents/%s", doc_id)

    doc = doc_manager.get_document_by_id(doc_id)
    if not doc:
        logger.warning("Document not found: %s", doc_id)
        raise HTTPException(status_code=404, detail="Document not found")

    logger.info("Retrieved document: %s", doc_id)
    return DocumentDetailResponse(
        doc_id=doc["doc_id"],
        filename=doc["filename"],
        chunks_count=doc["chunks_count"],
        size=doc["size"],
        processed_at=doc["processed_at"],
        author=doc.get("author", "Admin"),
        category=doc.get("category", "General"),
        department=doc.get("department", "Unknown"),
        doc_type=doc.get("doc_type", "PDF Document"),
        version=doc.get("version", "1.0"),
        description=doc.get("description", ""),
        date_uploaded=doc.get("date_uploaded", ""),
        tags=doc.get("tags", []),
    )


@router.put("/{doc_id}", response_model=MetadataUpdateResponse)
def update_document_by_id(doc_id: str, metadata: dict):
    """Update metadata for a specific document by its unique ID."""
    logger.info("PUT /documents/%s", doc_id)

    try:
        if doc_manager.update_document_metadata_by_id(doc_id, metadata):
            logger.info("Metadata updated for document: %s", doc_id)
            return MetadataUpdateResponse(
                success=True, message="Metadata updated successfully"
            )
        logger.warning("Document not found: %s", doc_id)
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Metadata update error for %s: %s", doc_id, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}", response_model=DeleteDocumentResponse)
def delete_document(doc_id: str):
    """Delete a document by its unique ID."""
    logger.info("DELETE /documents/%s", doc_id)

    try:
        if doc_manager.delete_document_by_id(doc_id):
            # Reload RAG system to reflect deletions
            initialize_rag(force_reprocess=False)
            doc_info = doc_manager.get_document_info()
            
            logger.info("Document deleted: %s", doc_id)
            return DeleteDocumentResponse(
                success=True,
                message="Document deleted successfully",
                doc_id=doc_id,
                total_documents=doc_info["total_documents"],
                total_chunks=doc_info["total_chunks"],
            )
        logger.warning("Document not found: %s", doc_id)
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document deletion error for %s: %s", doc_id, e)
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")
