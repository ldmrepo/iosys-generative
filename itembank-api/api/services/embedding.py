"""
Embedding service for loading and managing embeddings.
"""
import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for managing embeddings from NPZ files."""

    def __init__(self):
        self._embeddings: Optional[np.ndarray] = None
        self._ids: Optional[np.ndarray] = None
        self._id_to_idx: Dict[str, int] = {}
        self._loaded: bool = False

    @property
    def is_loaded(self) -> bool:
        """Check if embeddings are loaded."""
        return self._loaded

    @property
    def count(self) -> int:
        """Get number of loaded embeddings."""
        if self._embeddings is None:
            return 0
        return len(self._embeddings)

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._embeddings is None:
            return 0
        return self._embeddings.shape[1]

    def load_from_npz(self, path: str) -> bool:
        """
        Load embeddings from NPZ file.

        Args:
            path: Path to NPZ file

        Returns:
            True if loaded successfully
        """
        try:
            npz_path = Path(path)
            if not npz_path.exists():
                logger.error(f"NPZ file not found: {path}")
                return False

            logger.info(f"Loading embeddings from {path}")
            data = np.load(path, allow_pickle=True)

            # Handle different NPZ formats
            if "embeddings" in data:
                self._embeddings = data["embeddings"]
            elif "embedding" in data:
                self._embeddings = data["embedding"]
            else:
                # Try first array
                keys = list(data.keys())
                if keys:
                    self._embeddings = data[keys[0]]

            if "ids" in data:
                self._ids = data["ids"]
            elif "id" in data:
                self._ids = data["id"]
            elif "item_ids" in data:
                self._ids = data["item_ids"]

            if self._embeddings is None:
                logger.error("No embeddings found in NPZ file")
                return False

            # Build ID to index mapping
            if self._ids is not None:
                self._id_to_idx = {
                    str(id_): idx for idx, id_ in enumerate(self._ids)
                }

            self._loaded = True
            logger.info(
                f"Loaded {self.count} embeddings with dimension {self.dimension}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            return False

    def get_embedding_by_id(self, item_id: str) -> Optional[np.ndarray]:
        """
        Get embedding vector by item ID.

        Args:
            item_id: Item identifier

        Returns:
            Embedding vector or None
        """
        if not self._loaded:
            return None

        idx = self._id_to_idx.get(item_id)
        if idx is None:
            return None

        return self._embeddings[idx]

    def search_similar_in_memory(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        threshold: float = 0.5,
    ) -> list:
        """
        Search for similar items in memory using cosine similarity.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            threshold: Minimum similarity threshold

        Returns:
            List of (item_id, score) tuples
        """
        if not self._loaded or self._embeddings is None:
            return []

        # Normalize query
        query_norm = query_embedding / np.linalg.norm(query_embedding)

        # Compute cosine similarities
        norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)
        normalized = self._embeddings / norms
        similarities = np.dot(normalized, query_norm)

        # Filter by threshold and get top-k
        mask = similarities >= threshold
        valid_indices = np.where(mask)[0]
        valid_scores = similarities[mask]

        # Sort by score descending
        sorted_indices = np.argsort(valid_scores)[::-1][:top_k]

        results = []
        for idx in sorted_indices:
            original_idx = valid_indices[idx]
            item_id = str(self._ids[original_idx]) if self._ids is not None else str(original_idx)
            score = float(valid_scores[idx])
            results.append((item_id, score))

        return results


# Global embedding service instance
embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    return embedding_service
