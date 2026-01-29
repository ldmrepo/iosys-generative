"""API routers."""
from .health import router as health_router
from .search import router as search_router
from .rag import router as rag_router

__all__ = ["health_router", "search_router", "rag_router"]
