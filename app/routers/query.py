from fastapi import APIRouter, HTTPException

from app.models import QueryRequest, QueryResponse, ChunkResult
from app.services import run_rag_pipeline

router = APIRouter(tags=["Query"])


@router.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Ask a question — runs BM25 retrieval → reranking → LLM generation."""
    try:
        result = await run_rag_pipeline(
            question=request.question,
            top_k=request.top_k,
            rerank_top_n=request.rerank_top_n,
            filter_files=request.filter_files,
        )

        source_chunks = [
            ChunkResult(
                text=chunk["text"],
                page=chunk["page"],
                score=chunk["score"],
                source_file=chunk.get("source_file", "Unknown"),
                file_path=chunk.get("file_path", ""),
                metadata=chunk.get("metadata", {}),
                document_metadata=chunk.get("document_metadata", {}),
            )
            for chunk in result["source_chunks"]
        ]

        return QueryResponse(
            question=request.question,
            answer=result["answer"],
            source_chunks=source_chunks,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")
