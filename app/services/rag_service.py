from typing import Dict, List, Optional

from app.utils import get_logger
from app.rag.document_manager import DocumentManager
from app.rag.generator import generate_answer
from app.rag.reranker import FlashReranker
from app.rag.retriever import BM25Retriever

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Singletons — shared across the app (like a service layer in Express)
# ---------------------------------------------------------------------------
doc_manager = DocumentManager()
reranker = FlashReranker()
retriever: Optional[BM25Retriever] = None


def initialize_rag():
    """
    Load all documents and build the BM25 index.
    Called once on startup and again after upload/refresh.
    """
    global retriever

    logger.info("Initializing RAG system...")
    all_chunks = doc_manager.load_all_documents()

    if all_chunks:
        retriever = BM25Retriever(all_chunks)
        logger.info("RAG system ready — %d chunks loaded", len(all_chunks))
    else:
        logger.warning("No documents loaded. Add PDF files to uploads/ directory.")
        retriever = None


def get_retriever() -> Optional[BM25Retriever]:
    """Return the current retriever instance."""
    return retriever


async def run_rag_pipeline(
    question: str,
    top_k: int = 15,
    rerank_top_n: int = 5,
    filter_files: Optional[List[str]] = None,
) -> Dict:
    """
    Full RAG pipeline:
      1. BM25 retrieval
      2. FlashRank reranking
      3. LLM answer generation

    Returns a dict with answer and source_chunks.
    """
    if retriever is None:
        logger.error("RAG pipeline called but system not initialized")
        raise ValueError("RAG system not initialized. No documents loaded.")

    logger.info("Running RAG pipeline for question: %s", question[:100])

    # Step 1 — BM25 Retrieval
    bm25_results = retriever.retrieve(question, top_k=top_k, filter_files=filter_files)
    logger.debug("BM25 retrieved %d chunks", len(bm25_results))

    if not bm25_results:
        logger.warning("No relevant chunks found for question: %s", question[:100])
        raise LookupError("No relevant chunks found for your question.")

    # Step 2 — Rerank
    reranked = reranker.rerank(question, bm25_results, top_n=rerank_top_n)
    logger.debug("Reranked to top %d chunks", len(reranked))

    # Step 3 — Generate Answer
    answer = await generate_answer(question, reranked)
    logger.info("Answer generated successfully (%d chars)", len(answer))

    return {
        "answer": answer,
        "source_chunks": reranked,
    }
