from rank_bm25 import BM25Okapi
from typing import List, Dict
import re


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

    def retrieve(self, query: str, top_k: int = 5, filter_files: list = None) -> List[Dict]:
        """
        Retrieve top_k most relevant chunks using BM25.
        Optionally filter to only search within specific files.

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

        # Apply file filter if specified
        if filter_files:
            scored_chunks = [
                c for c in scored_chunks
                if c.get("source_file") in filter_files
            ]

        # Sort by score descending and return top_k
        top_chunks = sorted(scored_chunks, key=lambda x: x["score"], reverse=True)[:top_k]

        return top_chunks
