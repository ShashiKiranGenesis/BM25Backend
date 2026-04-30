from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import APP_TITLE, APP_DESCRIPTION, APP_VERSION, ALLOWED_ORIGINS
from app.utils import get_logger
from app.routers import documents_router, query_router
from app.services import initialize_rag

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("Starting up Vectorless RAG API v%s", APP_VERSION)
    try:
        initialize_rag()
        logger.info("RAG system initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize RAG system: %s", e)

    yield  # app is running

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("Shutting down Vectorless RAG API")


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI app."""

    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(documents_router, prefix="/v1/documents")
    app.include_router(query_router, prefix="/v1/query")

    logger.info("App created — routers registered")

    # Health
    @app.get("/health")
    def health():
        return {
            "message": "Vectorless RAG API is running!",
            "version": APP_VERSION,
            "docs": "/docs",
            "endpoints": [
                "GET /v1/documents - get status",
                "POST /v1/documents - upload PDF",
                "POST /v1/documents/refresh - refresh all documents",
                "PUT /v1/documents/{filename} - update metadata",
                "POST /v1/query - ask question",
            ],
        }

    return app
