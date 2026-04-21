from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import APP_TITLE, APP_DESCRIPTION, APP_VERSION, ALLOWED_ORIGINS
from app.routers import documents_router, query_router
from app.services import initialize_rag


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI app."""

    app = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
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
    app.include_router(documents_router)
    app.include_router(query_router)

    # Startup
    @app.on_event("startup")
    async def startup_event():
        initialize_rag()

    # Root
    @app.get("/")
    def root():
        return {
            "message": "Vectorless RAG API is running!",
            "version": APP_VERSION,
            "docs": "/docs",
            "endpoints": ["/status", "/upload", "/refresh", "/ask", "/metadata/{filename}"],
        }

    return app
