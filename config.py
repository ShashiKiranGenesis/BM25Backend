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
UPLOADS_DIR: str = "data/docs"
CHUNKS_DIR: str = "data/chunks"
METADATA_FILE: str = "metadata.json"

# App info
APP_TITLE: str = "Vectorless RAG API"
APP_DESCRIPTION: str = "BM25 + Reranker + LLM — No vector database needed!"
APP_VERSION: str = "2.0.0"

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
