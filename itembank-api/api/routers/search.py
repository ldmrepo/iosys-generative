"""
Search endpoints for item similarity search.
"""
import logging
import time
from typing import List

from fastapi import APIRouter, HTTPException

from ..core.config import get_settings
from ..models import (
    BatchSearchRequest,
    BatchSearchResponse,
    ImlContentResponse,
    ItemResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from ..services.database import DatabaseService
from ..services.embedding import get_embedding_service
from ..services.qwen3vl import get_qwen3vl_service
from utils.iml_reader import read_iml_file, find_iml_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/similar", response_model=SearchResponse)
async def search_similar(request: SearchRequest) -> SearchResponse:
    """
    Search for similar items using text query.

    Uses in-memory embedding search with cosine similarity.

    - If use_model=True: Uses Qwen3VL model to encode query_text (and optionally query_image)
    - If use_model=False: Treats query_text as item_id and looks up its embedding
    """
    start_time = time.perf_counter()

    embedding_service = get_embedding_service()
    if not embedding_service.is_loaded:
        raise HTTPException(status_code=503, detail="Embedding service not ready")

    query_embedding = None

    if request.use_model:
        # Use Qwen3VL model to encode natural language query
        qwen3vl_service = get_qwen3vl_service()
        if qwen3vl_service is None:
            raise HTTPException(
                status_code=503,
                detail="Qwen3VL service not initialized. Check server configuration.",
            )

        if request.query_image:
            # Multimodal encoding (text + image)
            query_embedding = qwen3vl_service.encode_multimodal(
                text=request.query_text,
                image_path=request.query_image,
            )
        else:
            # Text-only encoding
            query_embedding = qwen3vl_service.encode_text(request.query_text)

        if query_embedding is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to encode query with Qwen3VL model",
            )
    else:
        # Legacy: treat query_text as item_id and look up embedding
        query_embedding = embedding_service.get_embedding_by_id(request.query_text)

        if query_embedding is None:
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
    Search items by natural language text query.

    This endpoint always uses the Qwen3VL model to encode the query text.
    Supports multimodal search when query_image is provided.

    Example:
        POST /search/text
        {"query_text": "삼각형의 넓이를 구하시오", "top_k": 5}
    """
    # Force use_model=True for text search endpoint
    request.use_model = True
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


@router.get("/items/{item_id}/iml", response_model=ImlContentResponse)
async def get_item_iml(item_id: str) -> ImlContentResponse:
    """
    Get raw IML content for an item.

    Returns the original IML XML source file content for client-side parsing.
    """
    item = await DatabaseService.get_item_by_id(item_id)

    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    source_file = item.get("source_file")
    if not source_file:
        raise HTTPException(
            status_code=404, detail=f"Source file not found for item {item_id}"
        )

    settings = get_settings()
    full_path = find_iml_file(settings.iml_data_path, source_file)

    if full_path is None:
        logger.warning(f"IML file not found: {source_file} (base: {settings.iml_data_path})")
        raise HTTPException(
            status_code=404,
            detail=f"IML file not found: {source_file}",
        )

    try:
        iml_content = read_iml_file(full_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"IML file not found: {source_file}",
        )
    except Exception as e:
        logger.error(f"Error reading IML file {full_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading IML file: {str(e)}",
        )

    return ImlContentResponse(
        item_id=item_id,
        iml_content=iml_content,
        source_file=source_file,
    )
