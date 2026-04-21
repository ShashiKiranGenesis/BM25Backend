from typing import Dict, List, Optional

from app.utils import get_logger
from app.rag.document_manager import DocumentManager
from app.rag.generator import generate_answer
from app.rag.reranker import FlashReranker
from app.rag.retriever import BM25Retriever
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------
doc_manager = DocumentManager()
reranker = FlashReranker()
retriever: Optional[BM25Retriever] = None
vector_store: Optional[VectorStore] = None


def initialize_rag():
    """
    Load all documents, build the BM25 index, and initialise the
    persistent ChromaDB vector store.

    Called once on startup and again after every upload/refresh.
    """
    global retriever, vector_store

    logger.info("Initializing RAG system...")

    # --- Vector store (persistent, survives restarts) -------------------
    if vector_store is None:
        logger.info("Creating persistent ChromaDB vector store...")
        vector_store = VectorStore()
        # Wire the vector store into the document manager so that newly
        # processed documents are automatically upserted.
        doc_manager.set_vector_store(vector_store)

    # --- Load / process documents ---------------------------------------
    all_chunks = doc_manager.load_all_documents()

    if all_chunks:
        # BM25 index is always rebuilt in memory from all chunks
        retriever = BM25Retriever(all_chunks)
        logger.info("RAG system ready — %d chunks loaded", len(all_chunks))
    else:
        logger.warning("No documents loaded. Add PDF files to uploads/ directory.")
        retriever = None


def get_retriever() -> Optional[BM25Retriever]:
    """Return the current BM25 retriever instance."""
    return retriever


def get_vector_store() -> Optional[VectorStore]:
    """Return the current VectorStore instance."""
    return vector_store


def _merge_and_deduplicate(
    bm25_results: List[Dict],
    vector_results: List[Dict],
) -> List[Dict]:
    """
    Merge BM25 and vector results, deduplicating by (source_file, page,
    chunk_index).  When a chunk appears in both result sets the scores are
    averaged, which rewards chunks that rank well in both retrieval modes.
    """
    seen: Dict[str, Dict] = {}

    def _chunk_key(chunk: Dict) -> str:
        idx = chunk.get("metadata", {}).get("chunk_index", 0)
        return f"{chunk.get('source_file', '')}|{chunk.get('page', 0)}|{idx}"

    for chunk in bm25_results:
        key = _chunk_key(chunk)
        seen[key] = {**chunk, "_bm25_score": chunk["score"], "_vec_score": None}

    for chunk in vector_results:
        key = _chunk_key(chunk)
        if key in seen:
            # Average the two scores
            bm25_score = seen[key]["_bm25_score"]
            vec_score = chunk["score"]
            seen[key]["score"] = (bm25_score + vec_score) / 2.0
            seen[key]["_vec_score"] = vec_score
        else:
            seen[key] = {**chunk, "_bm25_score": None, "_vec_score": chunk["score"]}

    merged = list(seen.values())
    # Sort by combined score descending
    merged.sort(key=lambda c: c["score"], reverse=True)
    return merged


async def run_rag_pipeline(
    question: str,
    top_k: int = 15,
    rerank_top_n: int = 5,
    filter_files: Optional[List[str]] = None,
    use_vector: bool = False,
) -> Dict:
    """
    Full RAG pipeline:
      1. BM25 retrieval  (always enabled)
      2. Vector retrieval (optional, enabled when use_vector=True)
      3. Merge + deduplicate results when both are used
      4. FlashRank reranking
      5. LLM answer generation

    Args:
        question:     User question
        top_k:        Candidates to fetch from each retriever
        rerank_top_n: Final chunks to pass to the LLM after reranking
        filter_files: Restrict retrieval to these filenames
        use_vector:   Enable ChromaDB semantic retrieval in addition to BM25

    Returns:
        Dict with 'answer' and 'source_chunks'.
    """
    if retriever is None:
        logger.error("RAG pipeline called but system not initialized")
        raise ValueError("RAG system not initialized. No documents loaded.")

    logger.info(
        "Running RAG pipeline — use_vector=%s, question: %s",
        use_vector,
        question[:100],
    )

    # Step 1 — BM25 Retrieval (always on)
    bm25_results = retriever.retrieve(question, top_k=top_k, filter_files=filter_files)
    logger.debug("BM25 retrieved %d chunks", len(bm25_results))

    if not bm25_results and not use_vector:
        logger.warning("No relevant chunks found for question: %s", question[:100])
        raise LookupError("No relevant chunks found for your question.")

    # Step 2 — Vector Retrieval (optional)
    if use_vector and vector_store is not None and vector_store.count() > 0:
        vector_results = vector_store.query(
            question, top_k=top_k, filter_files=filter_files
        )
        logger.debug("Vector store retrieved %d chunks", len(vector_results))

        # Merge BM25 + vector results
        candidates = _merge_and_deduplicate(bm25_results, vector_results)
        logger.debug("Merged candidate pool: %d unique chunks", len(candidates))
    else:
        if use_vector:
            logger.warning(
                "Vector retrieval requested but vector store is empty or unavailable; "
                "falling back to BM25 only."
            )
        candidates = bm25_results

    if not candidates:
        raise LookupError("No relevant chunks found for your question.")

    # Step 3 — Rerank
    reranked = reranker.rerank(question, candidates, top_n=rerank_top_n)
    logger.debug("Reranked to top %d chunks", len(reranked))

    # Step 4 — Generate Answer
    answer = await generate_answer(question, reranked)
    logger.info("Answer generated successfully (%d chars)", len(answer))

    return {
        "answer": answer,
        "source_chunks": reranked,
    }
