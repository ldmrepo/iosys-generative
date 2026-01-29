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
        embedding_list = embedding.tolist()

        query = f"""
            SELECT id, 1 - (embedding <=> $1::vector) as similarity
            FROM {table_name}
            WHERE 1 - (embedding <=> $1::vector) >= $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """

        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(query, embedding_list, threshold, top_k)
                return [(row["id"], float(row["similarity"])) for row in rows]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

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
                   keywords, year, source, exam_name
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
                   keywords, year, source, exam_name
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
