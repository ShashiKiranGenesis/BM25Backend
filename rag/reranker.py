from flashrank import Ranker, RerankRequest
from typing import List, Dict


class FlashReranker:
    def __init__(self):
        # Lightweight reranker model — no GPU needed
        self.ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")

    def rerank(self, query: str, chunks: List[Dict], top_n: int = 3) -> List[Dict]:
        """
        Rerank BM25 retrieved chunks using cross-encoder model.

        Args:
            query:   The user question
            chunks:  BM25 retrieved chunks (with text, page, score)
            top_n:   How many chunks to keep after reranking

        Returns:
            Top N reranked chunks with updated scores
        """
        # Build passages list for flashrank
        passages = [
            {"id": i, "text": chunk["text"]}
            for i, chunk in enumerate(chunks)
        ]

        rerank_request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(rerank_request)

        # Map back to original chunks with rerank scores
        reranked_chunks = []
        for result in results[:top_n]:
            original_chunk = chunks[result["id"]]
            # Preserve ALL original chunk data, just update the score
            reranked_chunk = {**original_chunk}  # Copy all fields
            reranked_chunk["score"] = float(result["score"])  # Update score
            reranked_chunks.append(reranked_chunk)

        return reranked_chunks
