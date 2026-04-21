"""
Lightweight TF-IDF based vector store - NO MODEL DOWNLOAD REQUIRED.
Uses scikit-learn's TfidfVectorizer for embeddings.
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from config import CHROMA_DIR
from app.utils import get_logger

logger = get_logger(__name__)


class TfidfVectorStore:
    """
    Lightweight vector store using TF-IDF embeddings.
    No external model downloads required - uses scikit-learn only.
    """

    def __init__(self):
        self.storage_dir = Path(CHROMA_DIR)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.vectorizer_path = self.storage_dir / "tfidf_vectorizer.pkl"
        self.chunks_path = self.storage_dir / "chunks_data.pkl"
        self.vectors_path = self.storage_dir / "tfidf_vectors.pkl"
        
        # Initialize or load
        if self.vectorizer_path.exists():
            self._load()
        else:
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                stop_words='english',
                min_df=1,
                max_df=0.95
            )
            self.chunks_data: List[Dict] = []
            self.vectors = None
        
        logger.info(
            "TfidfVectorStore ready — %d documents loaded (path: %s)",
            len(self.chunks_data),
            self.storage_dir,
        )

    def _save(self):
        """Persist vectorizer, chunks, and vectors to disk."""
        with open(self.vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)
        with open(self.chunks_path, 'wb') as f:
            pickle.dump(self.chunks_data, f)
        if self.vectors is not None:
            with open(self.vectors_path, 'wb') as f:
                pickle.dump(self.vectors, f)

    def _load(self):
        """Load vectorizer, chunks, and vectors from disk."""
        with open(self.vectorizer_path, 'rb') as f:
            self.vectorizer = pickle.load(f)
        with open(self.chunks_path, 'rb') as f:
            self.chunks_data = pickle.load(f)
        if self.vectors_path.exists():
            with open(self.vectors_path, 'rb') as f:
                self.vectors = pickle.load(f)
        else:
            self.vectors = None

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert_chunks(self, chunks: List[Dict]) -> int:
        """
        Add or update chunks. Rebuilds the entire index.
        Returns the number of chunks upserted.
        """
        if not chunks:
            return 0

        # Build a map of existing chunks by ID for deduplication
        chunk_map = {self._make_chunk_id(c): c for c in self.chunks_data}
        
        # Add/update new chunks
        for chunk in chunks:
            chunk_id = self._make_chunk_id(chunk)
            chunk_map[chunk_id] = chunk

        # Rebuild chunks list and vectors
        self.chunks_data = list(chunk_map.values())
        
        # Extract texts and fit vectorizer
        texts = [c['text'] for c in self.chunks_data]
        
        if len(self.chunks_data) == 1:
            # Special case: single document
            self.vectorizer.fit(texts)
            self.vectors = self.vectorizer.transform(texts)
        else:
            self.vectors = self.vectorizer.fit_transform(texts)
        
        self._save()
        logger.info("Upserted %d chunks into TF-IDF vector store", len(chunks))
        return len(chunks)

    def delete_document(self, filename: str):
        """Remove all chunks belonging to a specific document."""
        original_count = len(self.chunks_data)
        self.chunks_data = [
            c for c in self.chunks_data 
            if c.get('source_file') != filename
        ]
        
        if len(self.chunks_data) < original_count:
            # Rebuild vectors
            if self.chunks_data:
                texts = [c['text'] for c in self.chunks_data]
                self.vectors = self.vectorizer.fit_transform(texts)
            else:
                self.vectors = None
            
            self._save()
            logger.info("Deleted chunks for '%s' from vector store", filename)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def query(
        self,
        query_text: str,
        top_k: int = 15,
        filter_files: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Semantic similarity search using TF-IDF + cosine similarity.
        Returns a list of chunk-like dicts with a 'score' field.
        """
        if not self.chunks_data or self.vectors is None:
            logger.warning("TF-IDF vector store is empty — no results")
            return []

        # Transform query
        try:
            query_vector = self.vectorizer.transform([query_text])
        except Exception as e:
            logger.error("Failed to vectorize query: %s", e)
            return []

        # Compute cosine similarities
        similarities = cosine_similarity(query_vector, self.vectors)[0]

        # Create results with scores
        results = []
        for idx, score in enumerate(similarities):
            chunk = self.chunks_data[idx].copy()
            chunk['score'] = float(score)
            
            # Apply file filter if specified
            if filter_files and chunk.get('source_file') not in filter_files:
                continue
            
            results.append(chunk)

        # Sort by score descending and take top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        results = results[:top_k]

        logger.debug("TF-IDF vector store returned %d results for query", len(results))
        return results

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def count(self) -> int:
        """Return the number of chunks in the store."""
        return len(self.chunks_data)

    def document_ids_in_store(self) -> List[str]:
        """Return the set of unique source_file values currently stored."""
        files = {c.get('source_file') for c in self.chunks_data if c.get('source_file')}
        return list(files)

    @staticmethod
    def _make_chunk_id(chunk: Dict) -> str:
        """Build a stable, unique ID for a chunk."""
        filename = chunk.get('source_file', 'unknown')
        page = chunk.get('page', 0)
        chunk_index = chunk.get('metadata', {}).get('chunk_index', 0)
        return f"{filename}_p{page}_c{chunk_index}"
