import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from werkzeug.utils import secure_filename

from app.utils import get_logger
from app.models import MetadataUpdateResponse, StatusResponse, UploadResponse
from app.services import doc_manager, get_retriever, initialize_rag
from config import UPLOADS_DIR

logger = get_logger(__name__)
router = APIRouter(tags=["Documents"])


@router.get("/status", response_model=StatusResponse)
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


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and reinitialize the RAG system."""
    logger.info("POST /upload — filename: %s", file.filename)

    if not file.filename.endswith(".pdf"):
        logger.warning("Upload rejected — not a PDF: %s", file.filename)
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOADS_DIR, filename)

        os.makedirs(UPLOADS_DIR, exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info("File saved to %s (%d bytes)", file_path, len(content))

        initialize_rag()

        doc_info = doc_manager.get_document_info()
        logger.info(
            "Upload complete — %d documents, %d chunks",
            doc_info["total_documents"],
            doc_info["total_chunks"],
        )
        return UploadResponse(
            success=True,
            message="PDF uploaded successfully!",
            filename=filename,
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"],
        )

    except Exception as e:
        logger.error("Upload failed for %s: %s", file.filename, e)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/refresh", response_model=UploadResponse)
def refresh_documents():
    """Reload all documents from the uploads directory."""
    logger.info("POST /refresh")

    try:
        initialize_rag()
        doc_info = doc_manager.get_document_info()
        logger.info(
            "Refresh complete — %d documents, %d chunks",
            doc_info["total_documents"],
            doc_info["total_chunks"],
        )
        return UploadResponse(
            success=True,
            message="Documents refreshed successfully!",
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"],
        )
    except Exception as e:
        logger.error("Refresh failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Error refreshing documents: {str(e)}")


@router.put("/metadata/{filename}", response_model=MetadataUpdateResponse)
def update_metadata(filename: str, metadata: dict):
    """Update metadata for a specific document."""
    logger.info("PUT /metadata/%s", filename)

    try:
        if doc_manager.update_document_metadata(filename, metadata):
            logger.info("Metadata updated for %s", filename)
            return MetadataUpdateResponse(success=True, message="Metadata updated successfully")
        logger.warning("Metadata update failed — document not found: %s", filename)
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Metadata update error for %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=str(e))
