"""
Embedding service for loading and managing embeddings.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ..core.config import get_settings

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

    def add_embedding(self, item_id: str, embedding: np.ndarray) -> bool:
        """
        Add a new embedding to the in-memory store.

        Args:
            item_id: Item identifier
            embedding: Embedding vector (must match existing dimension)

        Returns:
            True if added successfully
        """
        if not self._loaded:
            logger.warning("Cannot add embedding: service not loaded")
            return False

        if self._embeddings is None:
            logger.warning("Cannot add embedding: no embeddings loaded")
            return False

        # Check dimension
        if embedding.shape[0] != self.dimension:
            logger.error(
                f"Embedding dimension mismatch: expected {self.dimension}, got {embedding.shape[0]}"
            )
            return False

        # Check if ID already exists
        if item_id in self._id_to_idx:
            # Update existing embedding
            idx = self._id_to_idx[item_id]
            self._embeddings[idx] = embedding
            logger.info(f"Updated embedding for item {item_id}")
            return True

        # Add new embedding
        self._embeddings = np.vstack([self._embeddings, embedding.reshape(1, -1)])
        if self._ids is not None:
            self._ids = np.append(self._ids, item_id)
        new_idx = len(self._embeddings) - 1
        self._id_to_idx[item_id] = new_idx

        logger.info(f"Added embedding for item {item_id} (total: {self.count})")
        return True

    def remove_embedding(self, item_id: str) -> bool:
        """
        Remove an embedding from the in-memory store.

        Args:
            item_id: Item identifier

        Returns:
            True if removed successfully
        """
        if not self._loaded or self._embeddings is None:
            return False

        if item_id not in self._id_to_idx:
            logger.warning(f"Cannot remove embedding: item {item_id} not found")
            return False

        idx = self._id_to_idx[item_id]

        # Remove from embeddings array
        self._embeddings = np.delete(self._embeddings, idx, axis=0)

        # Remove from ids array
        if self._ids is not None:
            self._ids = np.delete(self._ids, idx)

        # Rebuild index mapping
        del self._id_to_idx[item_id]

        # Update indices for items after the removed one
        for id_, old_idx in list(self._id_to_idx.items()):
            if old_idx > idx:
                self._id_to_idx[id_] = old_idx - 1

        logger.info(f"Removed embedding for item {item_id} (total: {self.count})")
        return True


# Global embedding service instance
embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    return embedding_service
