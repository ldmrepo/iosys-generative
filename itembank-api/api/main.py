"""
IOSYS ItemBank AI - FastAPI Application
Main entry point for the API service.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.deps import close_db_pool, init_db_pool
from .routers import health_router, search_router, rag_router
from .services.embedding import get_embedding_service
from .services.qwen3vl import init_qwen3vl_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()

    # Startup
    logger.info("Starting IOSYS ItemBank AI API...")

    # Initialize database pool
    try:
        await init_db_pool(settings)
        logger.info("Database pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    # Load embeddings
    embedding_service = get_embedding_service()
    if embedding_service.load_from_npz(settings.embeddings_path):
        logger.info(f"Loaded {embedding_service.count} embeddings")
    else:
        logger.warning("Failed to load embeddings, search will be limited")

    # Initialize Qwen3VL service (lazy loading by default)
    init_qwen3vl_service(
        model_path=settings.qwen3vl_model_path,
        default_instruction=settings.qwen3vl_instruction,
        lazy_load=settings.qwen3vl_lazy_load,
    )
    logger.info(f"Qwen3VL service initialized (lazy_load={settings.qwen3vl_lazy_load})")

    yield

    # Shutdown
    logger.info("Shutting down IOSYS ItemBank AI API...")
    await close_db_pool()
    logger.info("Database pool closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered item bank search API with semantic similarity",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(rag_router)

    return app


# Create application instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
