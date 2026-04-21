from typing import Dict, List, Optional

from app.utils import get_logger
from app.rag.document_manager import DocumentManager
from app.rag.generator import generate_answer
from app.rag.reranker import FlashReranker
from app.rag.retriever import BM25Retriever
from config import VECTOR_BACKEND

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------
doc_manager = DocumentManager()
reranker = FlashReranker()
retriever: Optional[BM25Retriever] = None
vector_store = None  # Will be initialized based on VECTOR_BACKEND


def initialize_rag():
    """
    Load all documents and build the BM25 index.
    Vector store is initialized lazily on first use to avoid blocking
    server startup on model downloads.

    Called once on startup and again after every upload/refresh.
    """
    global retriever

    logger.info("Initializing RAG system...")

    # --- Load / process documents ---------------------------------------
    all_chunks = doc_manager.load_all_documents()

    if all_chunks:
        # BM25 index is always rebuilt in memory from all chunks
        retriever = BM25Retriever(all_chunks)
        logger.info("RAG system ready — %d chunks loaded", len(all_chunks))
    else:
        logger.warning("No documents loaded. Add PDF files to uploads/ directory.")
        retriever = None


def _ensure_vector_store():
    """
    Lazy initialization of vector store. Called only when vector retrieval
    is actually needed. This prevents blocking server startup on model downloads.
    
    Uses VECTOR_BACKEND config to choose between:
    - "tfidf": Lightweight, no download required (default)
    - "transformer": Better quality, requires model download
    """
    global vector_store

    if vector_store is None:
        logger.info(
            "Initializing vector store (first use) — backend: %s",
            VECTOR_BACKEND
        )
        try:
            if VECTOR_BACKEND == "tfidf":
                from app.rag.vector_store_tfidf import TfidfVectorStore
                vector_store = TfidfVectorStore()
            else:
                from app.rag.vector_store import VectorStore
                vector_store = VectorStore()
            
            # Wire the vector store into the document manager so that newly
            # processed documents are automatically upserted.
            doc_manager.set_vector_store(vector_store)
            
            # If we already have chunks loaded, populate the vector store
            if retriever is not None:
                all_chunks = retriever.chunks  # BM25Retriever stores all chunks
                if all_chunks:
                    logger.info(
                        "Populating vector store with %d existing chunks...",
                        len(all_chunks)
                    )
                    vector_store.upsert_chunks(all_chunks)
                    logger.info("Vector store populated successfully")
            
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize vector store: %s", e)
            logger.warning(
                "Vector retrieval will be unavailable. "
                "Check network connection for model download or use VECTOR_BACKEND=tfidf"
            )
            raise


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
    if use_vector:
        try:
            # Lazy initialization on first use
            _ensure_vector_store()
            
            if vector_store is not None and vector_store.count() > 0:
                vector_results = vector_store.query(
                    question, top_k=top_k, filter_files=filter_files
                )
                logger.debug("Vector store retrieved %d chunks", len(vector_results))

                # Merge BM25 + vector results
                candidates = _merge_and_deduplicate(bm25_results, vector_results)
                logger.debug("Merged candidate pool: %d unique chunks", len(candidates))
            else:
                logger.warning(
                    "Vector retrieval requested but vector store is empty; "
                    "falling back to BM25 only."
                )
                candidates = bm25_results
        except Exception as e:
            logger.error("Vector retrieval failed: %s — falling back to BM25 only", e)
            candidates = bm25_results
    else:
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
