"""
Similar Question Generation API Router
"""
import html
import logging
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.generation import get_generation_service
from ..services.database import DatabaseService
from ..services.qwen3vl import get_qwen3vl_service
from ..core.config import get_settings
from ..core.deps import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["generation"])


def generate_iml_content(item_id: str, item: "SaveGeneratedItemRequest", source_item: dict) -> str:
    """Generate IML XML content for AI-generated item (Korean IML format)."""
    question_text = html.escape(item.question_text or "")
    answer_text = html.escape(item.answer_text or "")
    explanation_text = html.escape(item.explanation_text or "")

    # Build choices XML
    choices_xml = ""
    if item.choices:
        for choice in item.choices:
            choices_xml += f'''<답항>
<단락 justv="0">
<문자열>{html.escape(str(choice))}</문자열>
</단락>
</답항>
'''

    # Get metadata with proper codes
    # Map question types to codes: 11=선택형, 21=진위형, 31=단답형, 34=완결형, 37=연결형, 41=서술형, 51=논술형
    qt_raw = source_item.get("question_type") or "선택형"
    qt_code = source_item.get("question_type_code") or "11"
    qt = f"{qt_code} {qt_raw}"

    df_raw = source_item.get("difficulty") or "중"
    df_code = source_item.get("difficulty_code") or "03"
    df = f"{df_code} {df_raw}"

    grade = source_item.get("grade") or ""
    subject = source_item.get("subject") or "수학"
    unit_large = source_item.get("unit_large") or ""
    unit_medium = source_item.get("unit_medium") or ""

    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<문항종류>
<단위문항>
<문항 id="{item_id}" qt="{qt}" df="{df}" cls3="{grade}" cls4="{subject}" cls7="{unit_large}" cls8="{unit_medium}" ai_generated="true" source_item="{item.source_item_id}" generation_model="{item.generation_model}">
<문제>
<물음>
<단락 justv="0">
<문자열 xml:space="preserve">{question_text}</문자열>
</단락>
</물음>
{choices_xml}</문제>
<정답>
<단락 justv="0">
<문자열>{answer_text}</문자열>
</단락>
</정답>
<해설>
<단락 justv="0">
<문자열>{explanation_text}</문자열>
</단락>
</해설>
</문항>
</단위문항>
</문항종류>'''


def save_iml_file(item_id: str, iml_content: str) -> str:
    """Save IML file to disk and return the relative path."""
    settings = get_settings()

    # Create directory if not exists
    ai_generated_dir = Path(settings.iml_data_path) / "data" / "ai_generated"
    ai_generated_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = ai_generated_dir / f"{item_id}.iml"
    file_path.write_text(iml_content, encoding="utf-8")

    logger.info(f"Saved IML file: {file_path}")
    return f"data/ai_generated/{item_id}.iml"


# Request/Response Models

class GenerationOptions(BaseModel):
    """Generation options"""
    variation_type: str = Field(
        default="mixed",
        description="Variation type: numeric, context, structure, mixed, auto"
    )
    additional_prompt: str = Field(
        default="",
        description="Additional instructions for generation"
    )


class GenerateSimilarRequest(BaseModel):
    """Request for generating similar questions"""
    source_item_id: str = Field(..., description="Source item ID to base generation on")
    count: int = Field(default=3, ge=1, le=6, description="Number of items to generate")
    options: GenerationOptions = Field(default_factory=GenerationOptions)


class GeneratedItemMetadata(BaseModel):
    """Metadata for generated item"""
    source_item_id: str
    variation_type: str
    is_ai_generated: bool = True
    generation_model: str
    generation_timestamp: str
    confidence_score: float
    used_vision_api: bool = False


class GeneratedItem(BaseModel):
    """A single generated item in QTI format"""
    temp_id: str
    assessment_item: dict  # QTI AssessmentItem structure
    variation_note: str = ""
    metadata: GeneratedItemMetadata


class GenerateSimilarResponse(BaseModel):
    """Response for similar question generation"""
    generated_items: List[GeneratedItem]
    generation_time_ms: float
    model: str
    tokens_used: Optional[int] = None
    images_used: int = 0


class GenerationStatusResponse(BaseModel):
    """Generation service status"""
    is_configured: bool
    model: str


class SaveGeneratedItemRequest(BaseModel):
    """Request to save a generated item"""
    temp_id: str = Field(..., description="Temporary ID from generation")
    question_text: str = Field(..., description="Question text")
    choices: List[str] = Field(default=[], description="Answer choices")
    answer_text: str = Field(..., description="Answer text")
    explanation_text: str = Field(default="", description="Explanation")
    source_item_id: str = Field(..., description="Source item ID")
    variation_type: str = Field(..., description="Variation type used")
    generation_model: str = Field(..., description="Model used for generation")
    confidence_score: float = Field(default=0.85, description="Confidence score")
    additional_prompt: str = Field(default="", description="Additional prompt used")


class SaveGeneratedItemsRequest(BaseModel):
    """Request to save multiple generated items"""
    items: List[SaveGeneratedItemRequest] = Field(..., description="Items to save")


class SavedItemResponse(BaseModel):
    """Response for a saved item"""
    temp_id: str
    item_id: str
    ai_metadata_id: str
    success: bool
    error: Optional[str] = None


class SaveGeneratedItemsResponse(BaseModel):
    """Response for saving generated items"""
    saved_items: List[SavedItemResponse]
    total_saved: int
    total_failed: int


# Endpoints

@router.post("/similar", response_model=GenerateSimilarResponse)
async def generate_similar(request: GenerateSimilarRequest):
    """
    Generate similar questions based on a source item.

    - **source_item_id**: ID of the source item to base generation on
    - **count**: Number of questions to generate (1-6)
    - **options.variation_type**: Type of variation (numeric/context/structure/mixed/auto)
    - **options.additional_prompt**: Additional instructions for generation
    """
    service = get_generation_service()

    # Check if service is configured
    if not service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Generation service not configured. OpenAI API key is missing."
        )

    # Fetch source item
    source_item = await DatabaseService.get_item_by_id(request.source_item_id)
    if not source_item:
        raise HTTPException(
            status_code=404,
            detail=f"Source item not found: {request.source_item_id}"
        )

    # Convert to dict if needed
    if hasattr(source_item, "dict"):
        source_item = source_item.dict()
    elif hasattr(source_item, "model_dump"):
        source_item = source_item.model_dump()

    try:
        result = await service.generate(
            source_item=source_item,
            count=request.count,
            variation_type=request.options.variation_type,
            additional_prompt=request.options.additional_prompt
        )

        return GenerateSimilarResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=GenerationStatusResponse)
async def get_generation_status():
    """Check generation service status"""
    service = get_generation_service()
    return GenerationStatusResponse(
        is_configured=service.is_configured,
        model=service.model
    )


@router.post("/save", response_model=SaveGeneratedItemsResponse)
async def save_generated_items(request: SaveGeneratedItemsRequest):
    """
    Save generated items to the database.

    - **items**: List of generated items to save
    - Also generates embeddings and stores them in pgvector for similarity search
    """
    saved_items = []
    total_saved = 0
    total_failed = 0

    import json as json_lib

    # Get Qwen3VL service for embedding generation
    qwen3vl_service = get_qwen3vl_service()

    async with get_db_connection() as conn:
        for item in request.items:
            try:
                # Generate new item ID
                import uuid
                item_id = f"AI_{uuid.uuid4().hex[:16].upper()}"

                # Get source item to copy metadata
                source_item = await DatabaseService.get_item_by_id(item.source_item_id)
                if not source_item:
                    raise ValueError(f"Source item not found: {item.source_item_id}")

                # Insert into ai_generated_items table first
                ai_metadata_id = await conn.fetchval("""
                    INSERT INTO ai_generated_items (
                        source_item_id, generation_model, variation_type,
                        additional_prompt, confidence_score, status
                    ) VALUES ($1, $2, $3, $4, $5, 'pending')
                    RETURNING id
                """, item.source_item_id, item.generation_model,
                    item.variation_type, item.additional_prompt, item.confidence_score)

                # Convert choices list to JSON string for JSONB column
                choices_json = json_lib.dumps(item.choices, ensure_ascii=False) if item.choices else None

                # Generate IML content and save to file
                iml_content = generate_iml_content(item_id, item, source_item)
                source_file = save_iml_file(item_id, iml_content)

                # Insert into items table
                await conn.execute("""
                    INSERT INTO items (
                        id, source_file, subject, grade, question_type, difficulty,
                        unit_large, unit_medium, question_text, choices,
                        answer_text, explanation_text, has_image,
                        is_ai_generated, ai_metadata_id
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11, $12, $13, TRUE, $14
                    )
                """,
                    item_id,
                    source_file,
                    source_item.get("subject", ""),
                    source_item.get("grade", ""),
                    source_item.get("question_type", ""),
                    source_item.get("difficulty", ""),
                    source_item.get("unit_large", ""),
                    source_item.get("unit_medium", ""),
                    item.question_text,
                    choices_json,
                    item.answer_text,
                    item.explanation_text,
                    source_item.get("has_image", False),
                    ai_metadata_id
                )

                # Update ai_generated_items with the new item_id
                await conn.execute("""
                    UPDATE ai_generated_items SET item_id = $1 WHERE id = $2
                """, item_id, ai_metadata_id)

                # Generate embedding for the new item and store in pgvector
                embedding_stored = False
                if qwen3vl_service is not None:
                    try:
                        # Create text for embedding (question + choices + answer)
                        embedding_text = item.question_text
                        if item.choices:
                            embedding_text += "\n" + "\n".join(item.choices)

                        # Generate embedding
                        embedding = qwen3vl_service.encode_text(embedding_text)

                        if embedding is not None:
                            # Store in pgvector database
                            # asyncpg requires vector as string format "[0.1, 0.2, ...]"
                            embedding_str = "[" + ",".join(str(x) for x in embedding.tolist()) + "]"
                            await conn.execute("""
                                INSERT INTO qwen_embeddings (id, embedding)
                                VALUES ($1, $2::vector)
                                ON CONFLICT (id) DO UPDATE SET embedding = $2::vector
                            """, item_id, embedding_str)

                            embedding_stored = True
                            logger.info(f"Generated and stored embedding for AI item {item_id}")
                        else:
                            logger.warning(f"Failed to generate embedding for AI item {item_id}")
                    except Exception as emb_err:
                        logger.error(f"Embedding generation failed for {item_id}: {emb_err}")
                else:
                    logger.warning("Qwen3VL service not available - skipping embedding generation")

                saved_items.append(SavedItemResponse(
                    temp_id=item.temp_id,
                    item_id=item_id,
                    ai_metadata_id=str(ai_metadata_id),
                    success=True
                ))
                total_saved += 1

            except Exception as e:
                logger.error(f"Failed to save item {item.temp_id}: {e}")
                saved_items.append(SavedItemResponse(
                    temp_id=item.temp_id,
                    item_id="",
                    ai_metadata_id="",
                    success=False,
                    error=str(e)
                ))
                total_failed += 1

    return SaveGeneratedItemsResponse(
        saved_items=saved_items,
        total_saved=total_saved,
        total_failed=total_failed
    )


class DeleteItemResponse(BaseModel):
    """Response for item deletion"""
    item_id: str
    success: bool
    message: str


@router.delete("/item/{item_id}", response_model=DeleteItemResponse)
async def delete_item(item_id: str):
    """
    Delete an AI-generated item.

    - **item_id**: ID of the item to delete (must start with 'AI_')
    """
    # Only allow deleting AI-generated items for safety
    if not item_id.startswith("AI_"):
        raise HTTPException(
            status_code=403,
            detail="Only AI-generated items can be deleted"
        )

    try:
        async with get_db_connection() as conn:
            # Check if item exists
            item = await conn.fetchrow("SELECT id, source_file FROM items WHERE id = $1", item_id)
            if not item:
                raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")

            # Delete from items table
            await conn.execute("DELETE FROM items WHERE id = $1", item_id)

            # Delete from qwen_embeddings table
            await conn.execute("DELETE FROM qwen_embeddings WHERE id = $1", item_id)

            # Delete from ai_generated_items table
            await conn.execute("DELETE FROM ai_generated_items WHERE item_id = $1", item_id)

        # Delete IML file if exists
        settings = get_settings()
        iml_file = Path(settings.iml_data_path) / "data" / "ai_generated" / f"{item_id}.iml"
        if iml_file.exists():
            iml_file.unlink()
            logger.info(f"Deleted IML file: {iml_file}")

        # Note: Embedding is automatically removed from pgvector when we delete from qwen_embeddings table above

        logger.info(f"Deleted AI item: {item_id}")

        return DeleteItemResponse(
            item_id=item_id,
            success=True,
            message=f"Item {item_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
