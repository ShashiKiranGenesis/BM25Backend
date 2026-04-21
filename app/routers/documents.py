import os
from fastapi import APIRouter, File, HTTPException, UploadFile
from werkzeug.utils import secure_filename

from config import UPLOADS_DIR
from app.models import StatusResponse, UploadResponse, MetadataUpdateResponse
from app.services import initialize_rag, get_retriever, doc_manager

router = APIRouter(tags=["Documents"])


@router.get("/status", response_model=StatusResponse)
def get_status():
    """Check system status and loaded document information."""
    if get_retriever() is None:
        return StatusResponse(
            ready=False,
            message="No documents loaded. Add PDF files to uploads/ directory.",
        )

    doc_info = doc_manager.get_document_info()
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
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOADS_DIR, filename)

        os.makedirs(UPLOADS_DIR, exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        initialize_rag()

        doc_info = doc_manager.get_document_info()
        return UploadResponse(
            success=True,
            message="PDF uploaded successfully!",
            filename=filename,
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.post("/refresh", response_model=UploadResponse)
def refresh_documents():
    """Reload all documents from the uploads directory."""
    try:
        initialize_rag()
        doc_info = doc_manager.get_document_info()
        return UploadResponse(
            success=True,
            message="Documents refreshed successfully!",
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing documents: {str(e)}")


@router.put("/metadata/{filename}", response_model=MetadataUpdateResponse)
def update_metadata(filename: str, metadata: dict):
    """Update metadata for a specific document."""
    try:
        if doc_manager.update_document_metadata(filename, metadata):
            return MetadataUpdateResponse(success=True, message="Metadata updated successfully")
        raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
