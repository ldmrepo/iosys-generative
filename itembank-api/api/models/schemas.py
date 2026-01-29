"""
Pydantic schemas for API request/response models.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str


class ReadyResponse(BaseModel):
    """Readiness check response."""

    status: str = "ready"
    database: str = "connected"
    embeddings: str = "loaded"


class SearchRequest(BaseModel):
    """Search request schema."""

    query_text: str = Field(..., min_length=1, description="Query text for search")
    query_image: Optional[str] = Field(
        None, description="Image path for multimodal search (optional)"
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")
    threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum similarity threshold"
    )
    use_model: bool = Field(
        default=False,
        description="If True, use Qwen3VL model for query embedding. If False, treat query_text as item_id.",
    )


class SearchResult(BaseModel):
    """Single search result."""

    item_id: str = Field(..., description="Item identifier")
    score: float = Field(..., ge=0.0, le=1.01, description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Item metadata")


class SearchResponse(BaseModel):
    """Search response schema."""

    results: List[SearchResult] = Field(default_factory=list)
    query_time_ms: float = Field(..., description="Query execution time in milliseconds")
    total_count: int = Field(default=0, description="Total number of results")


class BatchSearchRequest(BaseModel):
    """Batch search request schema."""

    queries: List[SearchRequest] = Field(
        ..., min_length=1, max_length=100, description="List of search queries"
    )


class BatchSearchResponse(BaseModel):
    """Batch search response schema."""

    results: List[SearchResponse] = Field(default_factory=list)
    total_time_ms: float = Field(..., description="Total batch execution time")


class ItemResponse(BaseModel):
    """Single item response."""

    item_id: str
    category: Optional[str] = None
    difficulty: Optional[str] = None
    question_type: Optional[str] = None
    question_text: Optional[str] = None
    has_image: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


class ImlContentResponse(BaseModel):
    """IML content response schema."""

    item_id: str = Field(..., description="Item identifier")
    iml_content: str = Field(..., description="Raw IML XML content")
    source_file: str = Field(..., description="Source file path")
