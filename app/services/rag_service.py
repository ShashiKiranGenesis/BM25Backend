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


def initialize_rag(force_reprocess: bool = False):
    """
    Load all documents and build the BM25 index.
    
    Args:
        force_reprocess: If True, recreate all chunks (used by refresh).
                        If False, use cached chunks when available (default).
    
    Called:
        - Once on startup (force_reprocess=False)
        - After refresh (force_reprocess=True)
        - After upload (force_reprocess=False, only new file processed)
    """
    global retriever

    if force_reprocess:
        logger.info("Initializing RAG system (FORCE REPROCESS - recreating all chunks)...")
    else:
        logger.info("Initializing RAG system...")
        
    all_chunks = doc_manager.load_all_documents(force_reprocess=force_reprocess)

    if all_chunks:
        retriever = BM25Retriever(all_chunks)
        logger.info("RAG system ready — %d chunks loaded", len(all_chunks))
    else:
        logger.warning("No documents loaded. Add PDF files to uploads/ directory.")
        retriever = None


def initialize_rag_with_new_file(file_path: str, additional_metadata: dict = None) -> int:
    """
    Process a single new file and add it to the existing RAG system.
    More efficient than reprocessing all files.
    
    Args:
        file_path: Path to the newly uploaded PDF
        additional_metadata: Optional metadata to attach to the document
        
    Returns:
        Number of chunks in the new file
    """
    global retriever
    
    logger.info("Adding new file to RAG system: %s", file_path)
    
    # Process only the new file
    new_chunks = doc_manager.process_single_file(file_path, additional_metadata)
    
    # Reload all chunks (but most will be from cache)
    all_chunks = doc_manager.load_all_documents(force_reprocess=False)
    
    # Rebuild retriever with all chunks
    if all_chunks:
        retriever = BM25Retriever(all_chunks)
        logger.info("RAG system updated — %d total chunks (%d new)", 
                   len(all_chunks), len(new_chunks))
    
    return len(new_chunks)


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
