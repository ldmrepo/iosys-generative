"""
Search endpoints for item similarity search.
"""
import logging
import os
import time
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

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
from ..services.qwen3vl import get_qwen3vl_service
from ..services.reranker import get_reranker_service
from utils.iml_reader import read_iml_file, find_iml_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/similar", response_model=SearchResponse)
async def search_similar(request: SearchRequest) -> SearchResponse:
    """
    Search for similar items using text query.

    Uses two-stage retrieval:
    1. Initial retrieval with embedding similarity (Qwen3-VL-Embedding)
    2. Reranking with cross-encoder (Qwen3-VL-Reranker) if enabled

    - If use_model=True: Uses Qwen3VL model to encode query_text (and optionally query_image)
    - If use_model=False: Treats query_text as item_id and looks up its embedding
    """
    start_time = time.perf_counter()
    settings = get_settings()

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
        # Legacy: treat query_text as item_id and look up embedding from pgvector
        query_embedding = await DatabaseService.get_embedding_by_id(request.query_text)

        if query_embedding is None:
            logger.warning(f"Query '{request.query_text}' not found as item ID")
            return SearchResponse(
                results=[],
                query_time_ms=(time.perf_counter() - start_time) * 1000,
                total_count=0,
            )

    # Stage 1: Initial retrieval using pgvector
    # If reranker is enabled, retrieve more candidates for reranking
    reranker_service = get_reranker_service()
    use_reranker = settings.use_reranker and reranker_service is not None and request.use_model

    initial_top_k = settings.reranker_top_k if use_reranker else request.top_k

    # Use pgvector for search (includes AI-generated items)
    results = await DatabaseService.search_similar(
        embedding=query_embedding,
        top_k=initial_top_k,
        threshold=request.threshold,
    )

    # Get metadata for results
    item_ids = [item_id for item_id, _ in results]
    metadata_map = await DatabaseService.get_items_by_ids(item_ids)

    # Stage 2: Reranking (if enabled)
    if use_reranker and results:
        logger.info(f"Reranking {len(results)} candidates...")

        # Prepare items for reranking
        items_for_rerank = [
            (item_id, score, metadata_map.get(item_id, {}))
            for item_id, score in results
        ]

        # Rerank
        final_k = min(request.top_k, settings.reranker_final_k)
        reranked_items = reranker_service.rerank_items(
            query_text=request.query_text,
            items=items_for_rerank,
            top_k=final_k,
        )

        # Build response from reranked results
        search_results = [
            SearchResult(item_id=item_id, score=score, metadata=metadata)
            for item_id, score, metadata in reranked_items
        ]

        logger.info(f"Reranked to {len(search_results)} results")
    else:
        # Build response without reranking
        search_results = []
        for item_id, score in results[:request.top_k]:
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

    This endpoint uses the Qwen3VL model to encode the query text.
    Falls back to keyword search in database if model is unavailable.

    Example:
        POST /search/text
        {"query_text": "삼각형의 넓이를 구하시오", "top_k": 5}
    """
    start_time = time.perf_counter()

    # Try using Qwen3VL model first
    qwen3vl_service = get_qwen3vl_service()
    if qwen3vl_service is not None:
        try:
            query_embedding = qwen3vl_service.encode_text(request.query_text)
            if query_embedding is not None:
                # Model encoding successful - use vector search
                request.use_model = True
                return await search_similar(request)
        except Exception as e:
            logger.warning(f"Qwen3VL encoding failed, falling back to keyword search: {e}")

    # Fallback: search by keyword in database
    logger.info(f"Using keyword fallback search for: {request.query_text}")
    try:
        results_raw = await DatabaseService.search_by_keyword(
            keyword=request.query_text,
            limit=request.top_k
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Convert to SearchResult objects
        results = [
            SearchResult(
                item_id=r["item_id"],
                score=r["score"],
                metadata=r["metadata"]
            )
            for r in results_raw
        ]

        return SearchResponse(
            results=results,
            query_time_ms=elapsed_ms,
            total_count=len(results),
        )
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Search service unavailable. Qwen3VL model not loaded and keyword search failed: {e}"
        )


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


@router.get("/ai-generated/{source_item_id}", response_model=SearchResponse)
async def get_ai_generated_items(source_item_id: str, limit: int = 20) -> SearchResponse:
    """
    Get AI-generated items based on a source item.

    Returns items that were generated using the specified source item.
    """
    start_time = time.perf_counter()

    try:
        results_raw = await DatabaseService.get_ai_generated_items(
            source_item_id=source_item_id,
            limit=limit
        )

        results = [
            SearchResult(
                item_id=r["item_id"],
                score=r["score"],
                metadata=r["metadata"]
            )
            for r in results_raw
        ]

        query_time_ms = (time.perf_counter() - start_time) * 1000

        return SearchResponse(
            results=results,
            query_time_ms=query_time_ms,
            total_count=len(results)
        )
    except Exception as e:
        logger.error(f"Get AI generated items failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get AI generated items: {e}"
        )


@router.get("/ai-generated", response_model=SearchResponse)
async def list_all_ai_generated_items(limit: int = 50) -> SearchResponse:
    """
    List all AI-generated items with their source item IDs.

    Returns recent AI-generated items for discovery purposes.
    """
    start_time = time.perf_counter()

    try:
        results_raw = await DatabaseService.get_all_ai_items(limit=limit)

        # Convert to SearchResult format
        results = []
        for r in results_raw:
            results.append(
                SearchResult(
                    item_id=r["id"],
                    score=1.0,  # No similarity score for listing
                    metadata={
                        "question_text": r.get("question_text", ""),
                        "source_item_id": r.get("source_item_id", ""),
                        "created_at": str(r.get("created_at", "")),
                        "is_ai_generated": True,
                    }
                )
            )

        query_time_ms = (time.perf_counter() - start_time) * 1000

        return SearchResponse(
            results=results,
            query_time_ms=query_time_ms,
            total_count=len(results)
        )
    except Exception as e:
        logger.error(f"List all AI items failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list AI generated items: {e}"
        )


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
        metadata={
            "subject": item.get("subject"),
            "grade": item.get("grade"),
            "school_level": item.get("school_level"),
            "unit_large": item.get("unit_large"),
            "is_ai_generated": item.get("is_ai_generated"),
        },
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


@router.get("/images/{image_path:path}")
async def get_image(image_path: str):
    """
    Serve image files from the IML data directory.

    The image_path is the relative path from the IML data directory.
    IML files may contain Windows-style paths with backslashes.
    Example: /search/images/ItemID/DrawObjPic/image.jpg
    """
    settings = get_settings()

    # Convert Windows backslashes to forward slashes
    image_path = image_path.replace('\\', '/')

    # Security: prevent directory traversal
    normalized_path = os.path.normpath(image_path)
    if normalized_path.startswith('..') or normalized_path.startswith('/'):
        raise HTTPException(status_code=400, detail="Invalid image path")

    # Try to find the image file
    full_path = os.path.join(settings.iml_data_path, normalized_path)

    if not os.path.exists(full_path):
        # Search in data/raw subdirectories (IML files are organized by date folders)
        # Supports both flat (20120918) and nested (2025/10/13) date folder structures
        data_raw_path = os.path.join(settings.iml_data_path, 'data', 'raw')
        if os.path.exists(data_raw_path):
            # Use glob to find the file recursively
            import glob
            search_pattern = os.path.join(data_raw_path, '**', normalized_path)
            matches = glob.glob(search_pattern, recursive=True)
            if matches:
                full_path = matches[0]

    if not os.path.exists(full_path):
        # Try common image subdirectories
        for subdir in ['images', 'img', 'media', 'resources']:
            alt_path = os.path.join(settings.iml_data_path, subdir, normalized_path)
            if os.path.exists(alt_path):
                full_path = alt_path
                break

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        logger.warning(f"Image not found: {image_path} (tried: {full_path})")
        raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")

    # Determine content type based on file extension
    ext = os.path.splitext(full_path)[1].lower()
    content_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
    }
    media_type = content_types.get(ext, 'application/octet-stream')

    return FileResponse(full_path, media_type=media_type)
