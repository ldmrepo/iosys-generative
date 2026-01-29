"""
RAG (Retrieval-Augmented Generation) endpoints.
"""
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.database import DatabaseService
from ..services.embedding import get_embedding_service
from ..services.llm import get_llm_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])


class RAGQueryRequest(BaseModel):
    """RAG query request schema."""

    query: str = Field(..., min_length=1, description="User's question")
    item_id: Optional[str] = Field(None, description="Reference item ID for context")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of items to retrieve")
    threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Similarity threshold")
    use_memory: bool = Field(default=False, description="Use conversation memory")
    session_id: Optional[str] = Field(default="default", description="Session ID for memory")


class RAGQueryResponse(BaseModel):
    """RAG query response schema."""

    answer: str = Field(..., description="Generated answer")
    sources: list = Field(default_factory=list, description="Source items used")
    query_time_ms: float = Field(..., description="Total query time")
    retrieval_time_ms: float = Field(..., description="Retrieval time")
    generation_time_ms: float = Field(..., description="LLM generation time")


class GenerateQuestionRequest(BaseModel):
    """Question generation request schema."""

    reference_item_ids: list[str] = Field(
        ..., min_length=1, max_length=10, description="Reference item IDs"
    )
    instructions: Optional[str] = Field(None, description="Specific instructions")


class GenerateQuestionResponse(BaseModel):
    """Question generation response schema."""

    generated_question: str = Field(..., description="Generated question")
    reference_items: list = Field(default_factory=list, description="Reference items used")
    generation_time_ms: float = Field(..., description="Generation time")


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest) -> RAGQueryResponse:
    """
    RAG query endpoint.

    Retrieves relevant items and generates an answer using LLM.
    """
    start_time = time.perf_counter()

    embedding_service = get_embedding_service()
    llm_service = get_llm_service()

    if not llm_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="LLM service not configured. Set OPENAI_API_KEY environment variable.",
        )

    # Retrieval phase
    retrieval_start = time.perf_counter()

    search_results = []
    if request.item_id:
        # Use provided item ID for similarity search
        query_embedding = embedding_service.get_embedding_by_id(request.item_id)
        if query_embedding is not None:
            results = embedding_service.search_similar_in_memory(
                query_embedding=query_embedding,
                top_k=request.top_k,
                threshold=request.threshold,
            )
            item_ids = [item_id for item_id, _ in results]
            metadata_map = await DatabaseService.get_items_by_ids(item_ids)

            for item_id, score in results:
                search_results.append({
                    "item_id": item_id,
                    "score": score,
                    "metadata": metadata_map.get(item_id, {}),
                })

    retrieval_time = (time.perf_counter() - retrieval_start) * 1000

    # Generation phase
    generation_start = time.perf_counter()

    try:
        if request.use_memory:
            answer = await llm_service.generate_response_with_memory(
                query=request.query,
                search_results=search_results,
                session_id=request.session_id or "default",
            )
        else:
            answer = await llm_service.generate_response(
                query=request.query,
                search_results=search_results,
            )
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

    generation_time = (time.perf_counter() - generation_start) * 1000
    total_time = (time.perf_counter() - start_time) * 1000

    return RAGQueryResponse(
        answer=answer,
        sources=[
            {"item_id": r["item_id"], "score": r["score"]}
            for r in search_results
        ],
        query_time_ms=total_time,
        retrieval_time_ms=retrieval_time,
        generation_time_ms=generation_time,
    )


@router.post("/generate", response_model=GenerateQuestionResponse)
async def generate_question(request: GenerateQuestionRequest) -> GenerateQuestionResponse:
    """
    Generate a new question based on reference items.
    """
    start_time = time.perf_counter()

    llm_service = get_llm_service()

    if not llm_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="LLM service not configured. Set OPENAI_API_KEY environment variable.",
        )

    # Get reference items
    metadata_map = await DatabaseService.get_items_by_ids(request.reference_item_ids)

    reference_items = [
        {
            "item_id": item_id,
            "score": 1.0,
            "metadata": metadata_map.get(item_id, {}),
        }
        for item_id in request.reference_item_ids
        if item_id in metadata_map
    ]

    if not reference_items:
        raise HTTPException(status_code=404, detail="No reference items found")

    # Generate new question
    try:
        generated = await llm_service.generate_similar_question(
            reference_items=reference_items,
            instructions=request.instructions,
        )
    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    generation_time = (time.perf_counter() - start_time) * 1000

    return GenerateQuestionResponse(
        generated_question=generated,
        reference_items=[
            {"item_id": r["item_id"]} for r in reference_items
        ],
        generation_time_ms=generation_time,
    )


@router.get("/status")
async def rag_status():
    """Check RAG service status."""
    llm_service = get_llm_service()
    embedding_service = get_embedding_service()

    return {
        "llm_configured": llm_service.is_configured,
        "embeddings_loaded": embedding_service.is_loaded,
        "embedding_count": embedding_service.count,
        "framework": "langchain",
    }


@router.post("/clear-memory")
async def clear_memory():
    """Clear conversation memory."""
    llm_service = get_llm_service()
    llm_service.clear_memory()
    return {"status": "memory cleared"}
