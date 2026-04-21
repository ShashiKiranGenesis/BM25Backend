import os
from dotenv import load_dotenv

load_dotenv()

# API settings
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# CORS
ALLOWED_ORIGINS: list = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]

# Directories
UPLOADS_DIR: str = "uploads"
CHUNKS_DIR: str = "chunks"
METADATA_FILE: str = "MetaData.json"

# ChromaDB — persistent vector store
CHROMA_DIR: str = os.getenv("CHROMA_DIR", "chroma_db")
# Vector backend: "tfidf" (no download, lightweight) or "transformer" (better quality, requires download)
VECTOR_BACKEND: str = os.getenv("VECTOR_BACKEND", "tfidf")
# Options: "all-MiniLM-L6-v2" (90MB, best quality) or "paraphrase-MiniLM-L3-v2" (61MB, faster download)
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_COLLECTION: str = "rag_documents"

# App info
APP_TITLE: str = "RAG API"
APP_DESCRIPTION: str = "BM25 + ChromaDB + Reranker + LLM"
APP_VERSION: str = "3.0.0"

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
