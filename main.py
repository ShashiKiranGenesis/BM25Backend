from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
import os
import asyncio

from rag.document_manager import DocumentManager
from rag.retriever import BM25Retriever
from rag.reranker import FlashReranker
from rag.generator import generate_answer

load_dotenv()

app = FastAPI(
    title="Vectorless RAG API",
    description="BM25 + Reranker + LLM — No vector database needed!",
    version="2.0.0"
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
    
    print("🚀 Initializing RAG system...")
    all_chunks = doc_manager.load_all_documents()
    
    if all_chunks:
        retriever = BM25Retriever(all_chunks)
        print("✅ RAG system ready!")
    else:
        print("⚠️  No documents loaded. Add PDF files to uploads/ directory.")
        retriever = None


# Initialize on startup
@app.on_event("startup")
async def startup_event():
    initialize_system()


# ---------------------------------------------------------------------------
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
        
        # Reinitialize system
        initialize_system()
        
        doc_info = doc_manager.get_document_info()
        
        return UploadResponse(
            success=True,
            message=f"PDF uploaded successfully!",
            filename=filename,
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@app.post("/refresh", response_model=UploadResponse)
def refresh_documents():
    """Refresh/reload all documents from uploads directory."""
    try:
        initialize_system()
        doc_info = doc_manager.get_document_info()
        
        return UploadResponse(
            success=True,
            message="Documents refreshed successfully!",
            total_documents=doc_info["total_documents"],
            total_chunks=doc_info["total_chunks"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing documents: {str(e)}")


@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Ask a question using BM25 + Reranker + LLM."""
    
    if retriever is None:
        raise HTTPException(
            status_code=400,
            detail="No documents loaded. Upload a PDF first or add files to uploads/ directory."
        )
    
    try:
        # Step 1 — BM25 Retrieval (with optional file filter)
        bm25_results = retriever.retrieve(
            request.question,
            top_k=request.top_k,
            filter_files=request.filter_files
        )
        
        if not bm25_results:
            raise HTTPException(
                status_code=404,
                detail="No relevant chunks found for your question."
            )
        
        # Step 2 — Rerank
        reranked = reranker.rerank(request.question, bm25_results, top_n=request.rerank_top_n)
        
        # Step 3 — Generate Answer
        answer = await generate_answer(request.question, reranked)
        
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
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.put("/metadata/{filename}")
def update_metadata(filename: str, metadata: dict):
    """Update metadata for a specific document."""
    try:
        if doc_manager.update_document_metadata(filename, metadata):
            return {"success": True, "message": "Metadata updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
