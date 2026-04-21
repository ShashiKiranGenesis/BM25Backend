from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os
import asyncio
import logging

from rag.document_manager import DocumentManager
from rag.retriever import BM25Retriever
from rag.reranker import FlashReranker
from rag.generator import generate_answer

# Configure logging with UTF-8 encoding for Windows compatibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application startup and shutdown."""
    # Startup
    logger.info("[STARTUP] Starting up FastAPI application")
    initialize_system()
    logger.info("[STARTUP] Application startup complete")
    yield
    # Shutdown
    logger.info("[SHUTDOWN] Application shutting down")


app = FastAPI(
    title="Vectorless RAG API",
    description="BM25 + Reranker + LLM — No vector database needed!",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS so frontend can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],  # Flask frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Document management and RAG components
# ---------------------------------------------------------------------------
doc_manager = DocumentManager()
retriever: BM25Retriever = None
reranker: FlashReranker = FlashReranker()


def initialize_system():
    """Initialize the RAG system by loading all documents."""
    global retriever
    
    logger.info("[INIT] Initializing RAG system...")
    all_chunks = doc_manager.load_all_documents()
    
    if all_chunks:
        retriever = BM25Retriever(all_chunks)
        logger.info("[OK] RAG system ready!")
    else:
        logger.warning("[WARN] No documents loaded. Add PDF files to uploads/ directory.")
        retriever = None


# `---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 15
    rerank_top_n: Optional[int] = 5
    filter_files: Optional[List[str]] = None


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Vectorless RAG API is running!",
        "version": "2.0.0",
        "docs": "/docs",
        "endpoints": ["/status", "/upload", "/ask", "/refresh"]
    }


@app.get("/status", response_model=StatusResponse)
def get_status():
    """Check system status and document information."""
    if retriever is None:
        return StatusResponse(
            ready=False,
            message="No documents loaded. Add PDF files to uploads/ directory."
        )
    
    doc_info = doc_manager.get_document_info()
    return StatusResponse(
        ready=True,
        total_documents=doc_info["total_documents"],
        total_chunks=doc_info["total_chunks"],
        last_updated=doc_info["last_updated"],
        documents=doc_info["documents"]
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and reinitialize the system."""
    
    if not file.filename.endswith(".pdf"):
        logger.warning(f"Rejected upload: {file.filename} - not a PDF")
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    try:
        # Save uploaded file
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        file_path = os.path.join("uploads", filename)
        
        os.makedirs("uploads", exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Uploaded PDF: {filename}, size: {len(content)} bytes")
        
        # Reinitialize system
        initialize_system()
        
        doc_info = doc_manager.get_document_info()
        
        logger.info(f"System reinitialized after upload. Total documents: {doc_info['total_documents']}, chunks: {doc_info['total_chunks']}")
        
        return UploadResponse(
            success=True,
            message=f"PDF uploaded successfully!",
            filename=filename,
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"]
        )
    
    except Exception as e:
        logger.error(f"Error processing PDF upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.post("/refresh", response_model=UploadResponse)
def refresh_documents():
    """Refresh/reload all documents from uploads directory."""
    try:
        logger.info("Refreshing documents...")
        initialize_system()
        doc_info = doc_manager.get_document_info()
        
        logger.info(f"Documents refreshed. Total documents: {doc_info['total_documents']}, chunks: {doc_info['total_chunks']}")
        
        return UploadResponse(
            success=True,
            message="Documents refreshed successfully!",
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"]
        )
    except Exception as e:
        logger.error(f"Error refreshing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error refreshing documents: {str(e)}")


@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Ask a question using BM25 + Reranker + LLM."""
    
    logger.info(f"Processing question: '{request.question}' (top_k={request.top_k}, rerank_top_n={request.rerank_top_n})")
    
    if retriever is None:
        logger.warning("No documents loaded - rejecting question")
        raise HTTPException(
            status_code=400,
            detail="No documents loaded. Upload a PDF first or add files to uploads/ directory."
        )
    
    try:
        # Step 1 — BM25 Retrieval (with optional file filter)
        logger.debug("Starting BM25 retrieval")
        bm25_results = retriever.retrieve(
            request.question,
            top_k=request.top_k,
            filter_files=request.filter_files
        )
        
        if not bm25_results:
            logger.warning("No relevant chunks found for question")
            raise HTTPException(
                status_code=404,
                detail="No relevant chunks found for your question."
            )
        
        logger.info(f"BM25 retrieved {len(bm25_results)} chunks")
        
        # Step 2 — Rerank
        logger.debug("Starting reranking")
        reranked = reranker.rerank(request.question, bm25_results, top_n=request.rerank_top_n)
        
        logger.info(f"Reranked to top {len(reranked)} chunks")
        
        # Step 3 — Generate Answer
        logger.debug("Starting answer generation")
        answer = await generate_answer(request.question, reranked)
        
        logger.info("Answer generated successfully")
        
        # Build response
        source_chunks = [
            ChunkResult(
                text=chunk["text"],
                page=chunk["page"],
                score=chunk["score"],
                source_file=chunk.get("source_file", "Unknown"),
                file_path=chunk.get("file_path", ""),
                metadata=chunk.get("metadata", {}),
                document_metadata=chunk.get("document_metadata", {})
            )
            for chunk in reranked
        ]
        
        return QueryResponse(
            question=request.question,
            answer=answer,
            source_chunks=source_chunks
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.put("/metadata/{filename}")
def update_metadata(filename: str, metadata: dict):
    """Update metadata for a specific document."""
    try:
        logger.info(f"Updating metadata for document: {filename}")
        if doc_manager.update_document_metadata(filename, metadata):
            logger.info(f"Metadata updated successfully for {filename}")
            return {"success": True, "message": "Metadata updated successfully"}
        else:
            logger.warning(f"Document not found: {filename}")
            raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating metadata for {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
