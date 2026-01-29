"""
Search endpoints for item similarity search.
"""
import logging
import time
from typing import List

from fastapi import APIRouter, HTTPException

from ..models import (
    BatchSearchRequest,
    BatchSearchResponse,
    ItemResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from ..services.database import DatabaseService
from ..services.embedding import get_embedding_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/similar", response_model=SearchResponse)
async def search_similar(request: SearchRequest) -> SearchResponse:
    """
    Search for similar items using text query.

    Uses in-memory embedding search with cosine similarity.
    """
    start_time = time.perf_counter()

    embedding_service = get_embedding_service()
    if not embedding_service.is_loaded:
        raise HTTPException(status_code=503, detail="Embedding service not ready")

    # For now, we search by item_id if the query matches an existing ID
    # In production, this would use a text encoder to generate query embedding
    query_embedding = embedding_service.get_embedding_by_id(request.query_text)

    if query_embedding is None:
        # If query is not an item ID, return empty results
        # TODO: Implement text encoding for arbitrary queries
        logger.warning(f"Query '{request.query_text}' not found as item ID")
        return SearchResponse(
            results=[],
            query_time_ms=(time.perf_counter() - start_time) * 1000,
            total_count=0,
        )

    # Search in memory
    results = embedding_service.search_similar_in_memory(
        query_embedding=query_embedding,
        top_k=request.top_k,
        threshold=request.threshold,
    )

    # Get metadata for results
    item_ids = [item_id for item_id, _ in results]
    metadata_map = await DatabaseService.get_items_by_ids(item_ids)

    # Build response
    search_results = []
    for item_id, score in results:
        metadata = metadata_map.get(item_id, {})
        search_results.append(
            SearchResult(item_id=item_id, score=score, metadata=metadata)
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return SearchResponse(
        results=search_results,
        query_time_ms=elapsed_ms,
        total_count=len(search_results),
    )


@router.post("/text", response_model=SearchResponse)
async def search_by_text(request: SearchRequest) -> SearchResponse:
    """
    Search items by text query.

    Currently uses item ID lookup. Will be enhanced with text encoding.
    """
    return await search_similar(request)


@router.post("/batch", response_model=BatchSearchResponse)
async def batch_search(request: BatchSearchRequest) -> BatchSearchResponse:
    """
    Batch search for multiple queries.
    """
    start_time = time.perf_counter()

    results: List[SearchResponse] = []
    for query in request.queries:
        try:
            result = await search_similar(query)
            results.append(result)
        except HTTPException as e:
            results.append(
                SearchResponse(
                    results=[],
                    query_time_ms=0,
                    total_count=0,
                )
            )

    total_elapsed_ms = (time.perf_counter() - start_time) * 1000

    return BatchSearchResponse(results=results, total_time_ms=total_elapsed_ms)


@router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str) -> ItemResponse:
    """
    Get item details by ID.
    """
    item = await DatabaseService.get_item_by_id(item_id)

    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    return ItemResponse(
        item_id=item["id"],
        category=item.get("category"),
        difficulty=item.get("difficulty"),
        question_type=item.get("question_type"),
        question_text=item.get("question_text"),
        has_image=item.get("has_image", False),
        metadata=item.get("metadata") or {},
    )
