from rank_bm25 import BM25Okapi
from typing import List, Dict
import re
from app.utils.logger import get_logger

logger = get_logger(__name__)


def tokenize(text: str) -> List[str]:
    """Simple lowercase word tokenizer."""
    return re.findall(r'\w+', text.lower())


class BM25Retriever:
    def __init__(self, chunks: List[Dict]):
        """
        Args:
            chunks: List of {"text": ..., "page": ...}
        """
        self.chunks = chunks
        tokenized_corpus = [tokenize(chunk["text"]) for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def retrieve(self, query: str, top_k: int = 5, metadata_filters: dict = None) -> List[Dict]:
        """
        Retrieve top_k most relevant chunks using BM25.
        Optionally filter by metadata (category, department, doc_type, region).

        Args:
            query: The search query
            top_k: Number of top chunks to return
            metadata_filters: Dict with optional keys: category, department, doc_type, region

        Returns:
            List of chunks with BM25 scores added
        """
        tokenized_query = tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # Pair each chunk with its score
        scored_chunks = [
            {**self.chunks[i], "score": float(scores[i])}
            for i in range(len(self.chunks))
        ]
        
        logger.debug(f"BM25 retrieved {len(scored_chunks)} total chunks before filtering")

        # Apply metadata filters if specified
        if metadata_filters:
            logger.debug(f"Applying metadata filters: {metadata_filters}")
            for key, value in metadata_filters.items():
                before_count = len(scored_chunks)
                scored_chunks = [
                    c for c in scored_chunks
                    if c.get("document_metadata", {}).get(key) == value
                ]
                after_count = len(scored_chunks)
                # Debug: log actual values in chunks
                actual_values = set(c.get("document_metadata", {}).get(key) for c in self.chunks)
                logger.debug(f"Filter '{key}' == '{value}': {before_count} -> {after_count} chunks. Available values: {actual_values}")

        # Sort by score descending and return top_k
        top_chunks = sorted(scored_chunks, key=lambda x: x["score"], reverse=True)[:top_k]

        return top_chunks
