"""
Database service for pgvector operations.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import numpy as np

from ..core.deps import get_db_connection

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations with pgvector."""

    @staticmethod
    async def check_connection() -> bool:
        """Check if database connection is available."""
        try:
            async with get_db_connection() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    @staticmethod
    async def search_similar(
        embedding: np.ndarray,
        table_name: str = "qwen_embeddings",
        top_k: int = 10,
        threshold: float = 0.5,
    ) -> List[Tuple[str, float]]:
        """
        Search for similar items using cosine similarity.

        Args:
            embedding: Query embedding vector
            table_name: Table to search in
            top_k: Number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (item_id, similarity_score) tuples
        """
        # Convert numpy array to pgvector string format "[0.1, 0.2, ...]"
        embedding_str = "[" + ",".join(str(x) for x in embedding.tolist()) + "]"

        query = f"""
            SELECT id, 1 - (embedding <=> $1::vector) as similarity
            FROM {table_name}
            WHERE 1 - (embedding <=> $1::vector) >= $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """

        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(query, embedding_str, threshold, top_k)
                return [(row["id"], float(row["similarity"])) for row in rows]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    @staticmethod
    async def get_embedding_by_id(
        item_id: str,
        table_name: str = "qwen_embeddings"
    ) -> Optional[np.ndarray]:
        """
        Get embedding vector by item ID from pgvector.

        Args:
            item_id: Item identifier
            table_name: Table to query

        Returns:
            Embedding vector as numpy array or None
        """
        query = f"SELECT embedding FROM {table_name} WHERE id = $1"

        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow(query, item_id)
                if row:
                    emb_str = row["embedding"]
                    if isinstance(emb_str, str):
                        emb_list = [float(x) for x in emb_str.strip("[]").split(",")]
                        return np.array(emb_list, dtype=np.float32)
                    else:
                        return np.array(emb_str, dtype=np.float32)
                return None
        except Exception as e:
            logger.error(f"Get embedding failed: {e}")
            return None

    @staticmethod
    async def get_item_by_id(item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get item metadata by ID from items table.

        Args:
            item_id: Item identifier

        Returns:
            Item metadata dictionary or None
        """
        query = """
            SELECT id, source_file,
                   question_type, question_type_code, difficulty, difficulty_code,
                   curriculum, school_level, grade, subject, subject_detail,
                   semester, unit_large, unit_medium, unit_small,
                   question_text, choices, answer_text, explanation_text,
                   question_images, explanation_images, has_image,
                   keywords, year, source, exam_name, is_ai_generated
            FROM items
            WHERE id = $1
        """

        try:
            async with get_db_connection() as conn:
                row = await conn.fetchrow(query, item_id)
                if row:
                    result = dict(row)
                    # Add category for backward compatibility
                    result["category"] = "image" if result.get("has_image") else "text_only"
                    return result
                return None
        except Exception as e:
            logger.error(f"Get item failed: {e}")
            raise

    @staticmethod
    async def get_items_by_ids(item_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get multiple items by IDs from items table.

        Args:
            item_ids: List of item identifiers

        Returns:
            Dictionary mapping item_id to metadata
        """
        if not item_ids:
            return {}

        query = """
            SELECT id, source_file,
                   question_type, question_type_code, difficulty, difficulty_code,
                   curriculum, school_level, grade, subject, subject_detail,
                   semester, unit_large, unit_medium, unit_small,
                   question_text, choices, answer_text, explanation_text,
                   question_images, explanation_images, has_image,
                   keywords, year, source, exam_name, is_ai_generated
            FROM items
            WHERE id = ANY($1)
        """

        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(query, item_ids)
                result = {}
                for row in rows:
                    item = dict(row)
                    # Add category for backward compatibility
                    item["category"] = "image" if item.get("has_image") else "text_only"
                    result[row["id"]] = item
                return result
        except Exception as e:
            logger.error(f"Get items failed: {e}")
            raise

    @staticmethod
    async def get_items_count() -> int:
        """Get total number of items in the items table."""
        query = "SELECT COUNT(*) FROM items"

        try:
            async with get_db_connection() as conn:
                return await conn.fetchval(query)
        except Exception as e:
            logger.error(f"Items count failed: {e}")
            return 0

    @staticmethod
    async def get_embedding_count(table_name: str = "qwen_embeddings") -> int:
        """Get total number of embeddings in the table."""
        query = f"SELECT COUNT(*) FROM {table_name}"

        try:
            async with get_db_connection() as conn:
                return await conn.fetchval(query)
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0

    @staticmethod
    async def search_by_keyword(keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search items by keyword in question_text, keywords, or unit fields.

        Args:
            keyword: Search keyword
            limit: Maximum number of results

        Returns:
            List of SearchResult-compatible dictionaries
        """
        query = """
            SELECT id, source_file,
                   question_type, question_type_code, difficulty, difficulty_code,
                   curriculum, school_level, grade, subject, subject_detail,
                   semester, unit_large, unit_medium, unit_small,
                   question_text, choices, answer_text, explanation_text,
                   question_images, explanation_images, has_image,
                   keywords, year, source, exam_name, is_ai_generated
            FROM items
            WHERE question_text ILIKE $1
               OR keywords ILIKE $1
               OR unit_large ILIKE $1
               OR unit_medium ILIKE $1
               OR subject ILIKE $1
            LIMIT $2
        """
        search_pattern = f"%{keyword}%"

        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(query, search_pattern, limit)
                results = []
                for row in rows:
                    item = dict(row)
                    item["category"] = "image" if item.get("has_image") else "text_only"
                    # Return in SearchResult format
                    results.append({
                        "item_id": item["id"],
                        "score": 0.8,  # Fixed score for keyword search
                        "metadata": item
                    })
                return results
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            raise

    @staticmethod
    async def get_ai_generated_items(source_item_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get AI-generated items based on a source item.

        Args:
            source_item_id: The source item ID used for generation
            limit: Maximum number of results

        Returns:
            List of SearchResult-compatible dictionaries
        """
        query = """
            SELECT i.id, i.source_file,
                   i.question_type, i.question_type_code, i.difficulty, i.difficulty_code,
                   i.curriculum, i.school_level, i.grade, i.subject, i.subject_detail,
                   i.semester, i.unit_large, i.unit_medium, i.unit_small,
                   i.question_text, i.choices, i.answer_text, i.explanation_text,
                   i.question_images, i.explanation_images, i.has_image,
                   i.keywords, i.year, i.source, i.exam_name, i.is_ai_generated,
                   a.generation_model, a.variation_type, a.confidence_score, a.created_at
            FROM items i
            JOIN ai_generated_items a ON i.ai_metadata_id = a.id
            WHERE a.source_item_id = $1
            ORDER BY a.created_at DESC
            LIMIT $2
        """

        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(query, source_item_id, limit)
                results = []
                for row in rows:
                    item = dict(row)
                    item["category"] = "image" if item.get("has_image") else "text_only"
                    results.append({
                        "item_id": item["id"],
                        "score": item.get("confidence_score", 0.85),
                        "metadata": item
                    })
                return results
        except Exception as e:
            logger.error(f"Get AI items failed: {e}")
            raise

    @staticmethod
    async def get_all_ai_items(limit: int = 50) -> List[Dict[str, Any]]:
        """Get all AI-generated items with their source item IDs"""
        query = """
            SELECT i.id, i.question_text, a.source_item_id, a.created_at
            FROM items i
            JOIN ai_generated_items a ON i.ai_metadata_id = a.id
            WHERE i.is_ai_generated = TRUE
            ORDER BY a.created_at DESC
            LIMIT $1
        """
        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(query, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get all AI items failed: {e}")
            raise
