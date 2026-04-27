from fastapi import APIRouter, HTTPException

from app.utils import get_logger
from app.models import ChunkResult, QueryRequest, QueryResponse
from app.services import run_rag_pipeline

logger = get_logger(__name__)
router = APIRouter(tags=["Query"])


@router.post("/", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Ask a question — runs BM25 retrieval → reranking → LLM generation."""
    logger.info("POST /ask — question: %s", request.question[:100])

    try:
        result = await run_rag_pipeline(
            question=request.question,
            top_k=request.top_k,
            rerank_top_n=request.rerank_top_n,
            category=request.category,
            department=request.department,
            doc_type=request.doc_type,
            region=request.region,
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

        logger.info(
            "Question answered — %d source chunks returned",
            len(source_chunks),
        )
        return QueryResponse(
            question=request.question,
            answer=result["answer"],
            source_chunks=source_chunks,
        )

    except ValueError as e:
        logger.warning("Bad request for /ask: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        logger.warning("No results for /ask: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in /ask: %s", e)
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")
