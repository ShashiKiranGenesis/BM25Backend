"""
Persistent ChromaDB vector store for semantic retrieval.

Each chunk is stored with:
  - A stable document ID: "{safe_filename}_p{page}_c{chunk_index}"
  - The chunk text as the document
  - A flat metadata dict (ChromaDB only supports str/int/float/bool values)

The collection is persisted to CHROMA_DIR on disk so it survives restarts.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config import CHROMA_DIR, CHROMA_COLLECTION, EMBEDDING_MODEL
from app.utils import get_logger

logger = get_logger(__name__)


def _make_chunk_id(filename: str, page: int, chunk_index: int) -> str:
    """Build a stable, unique ID for a chunk."""
    safe = Path(filename).stem
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", safe)
    return f"{safe}_p{page}_c{chunk_index}"


def _flatten_metadata(chunk: Dict) -> Dict:
    """
    ChromaDB metadata values must be str, int, float, or bool.
    Flatten the nested metadata dicts into a single-level dict.
    """
    meta: Dict = {}

    # Top-level scalar fields
    for key in ("source_file", "file_path", "page"):
        val = chunk.get(key)
        if val is not None:
            meta[key] = val

    # chunk.metadata (doc-level + page-level + chunk-level)
    for key, val in chunk.get("metadata", {}).items():
        if isinstance(val, (str, int, float, bool)):
            meta[f"meta_{key}"] = val

    # chunk.document_metadata (author, category, etc.)
    for key, val in chunk.get("document_metadata", {}).items():
        if isinstance(val, (str, int, float, bool)):
            meta[f"doc_{key}"] = val

    return meta


class VectorStore:
    """Thin wrapper around a persistent ChromaDB collection."""

    def __init__(self):
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=CHROMA_DIR)
        self._ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
        self._collection = self._client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore ready — collection '%s' has %d documents (path: %s)",
            CHROMA_COLLECTION,
            self._collection.count(),
            CHROMA_DIR,
        )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert_chunks(self, chunks: List[Dict]) -> int:
        """
        Upsert a list of chunks into the collection.
        Uses stable IDs so re-uploading the same document is idempotent.
        Returns the number of chunks upserted.
        """
        if not chunks:
            return 0

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict] = []

        for chunk in chunks:
            chunk_index = chunk.get("metadata", {}).get("chunk_index", 0)
            page = chunk.get("page", 0)
            filename = chunk.get("source_file", "unknown")

            chunk_id = _make_chunk_id(filename, page, chunk_index)
            ids.append(chunk_id)
            documents.append(chunk["text"])
            metadatas.append(_flatten_metadata(chunk))

        # ChromaDB upsert in batches of 500 to avoid memory spikes
        batch_size = 500
        for i in range(0, len(ids), batch_size):
            self._collection.upsert(
                ids=ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        logger.info("Upserted %d chunks into vector store", len(ids))
        return len(ids)

    def delete_document(self, filename: str):
        """Remove all chunks belonging to a specific document."""
        self._collection.delete(where={"source_file": filename})
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
        Semantic similarity search.

        Returns a list of chunk-like dicts (same shape as BM25 results)
        with a 'score' field (cosine similarity, 0-1).
        """
        if self._collection.count() == 0:
            logger.warning("Vector store is empty — no results")
            return []

        where: Optional[Dict] = None
        if filter_files:
            if len(filter_files) == 1:
                where = {"source_file": filter_files[0]}
            else:
                where = {"source_file": {"$in": filter_files}}

        query_kwargs: Dict = dict(
            query_texts=[query_text],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        if where:
            query_kwargs["where"] = where

        results = self._collection.query(**query_kwargs)

        chunks: List[Dict] = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB returns cosine *distance* (0=identical, 2=opposite).
            # Convert to similarity score in [0, 1].
            score = max(0.0, 1.0 - dist / 2.0)

            chunk = {
                "text": doc,
                "page": meta.get("page", 0),
                "source_file": meta.get("source_file", "Unknown"),
                "file_path": meta.get("file_path", ""),
                "score": score,
                # Reconstruct nested dicts so downstream code is unchanged
                "metadata": {
                    k[len("meta_"):]: v
                    for k, v in meta.items()
                    if k.startswith("meta_")
                },
                "document_metadata": {
                    k[len("doc_"):]: v
                    for k, v in meta.items()
                    if k.startswith("doc_")
                },
            }
            chunks.append(chunk)

        logger.debug("Vector store returned %d results for query", len(chunks))
        return chunks

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def count(self) -> int:
        return self._collection.count()

    def document_ids_in_store(self) -> List[str]:
        """Return the set of unique source_file values currently stored."""
        if self._collection.count() == 0:
            return []
        # Fetch all metadatas (no documents, just metadata)
        result = self._collection.get(include=["metadatas"])
        files = {m.get("source_file") for m in result["metadatas"] if m.get("source_file")}
        return list(files)
