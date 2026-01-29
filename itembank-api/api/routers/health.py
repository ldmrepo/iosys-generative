"""
Health check endpoints.
"""
from fastapi import APIRouter, Response

from ..core.config import get_settings
from ..models import HealthResponse, ReadyResponse
from ..services.database import DatabaseService
from ..services.embedding import get_embedding_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    Returns healthy if the service is running.
    """
    settings = get_settings()
    return HealthResponse(status="healthy", version=settings.app_version)


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(response: Response) -> ReadyResponse:
    """
    Readiness check endpoint.
    Verifies database connection and embedding service status.
    """
    db_status = "connected"
    embeddings_status = "loaded"

    # Check database
    try:
        db_ok = await DatabaseService.check_connection()
        if not db_ok:
            db_status = "disconnected"
    except Exception:
        db_status = "error"

    # Check embeddings
    embedding_service = get_embedding_service()
    if not embedding_service.is_loaded:
        embeddings_status = "not_loaded"

    # Set response status
    if db_status != "connected" or embeddings_status != "loaded":
        response.status_code = 503

    return ReadyResponse(
        status="ready" if db_status == "connected" else "not_ready",
        database=db_status,
        embeddings=embeddings_status,
    )
