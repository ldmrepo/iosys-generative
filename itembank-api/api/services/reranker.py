"""
Qwen3-VL Reranker Service for two-stage retrieval.

Provides cross-encoder based reranking of search results.
"""
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Singleton instance
_reranker_service: Optional["RerankerService"] = None


class RerankerService:
    """
    Service for reranking search results using Qwen3-VL-Reranker model.

    Features:
    - Lazy loading: Model loads on first use
    - Cross-encoder scoring: Evaluates query-document relevance
    - Multimodal support: Text + image reranking (optional)
    """

    def __init__(
        self,
        model_path: str,
        default_instruction: str = "Given a search query, retrieve relevant educational question items.",
    ):
        """
        Initialize the service (model is NOT loaded yet).

        Args:
            model_path: Path to Qwen3-VL-Reranker model directory
            default_instruction: Default instruction for reranking
        """
        self._model_path = model_path
        self._default_instruction = default_instruction
        self._reranker = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded

    def load_model(self) -> bool:
        """
        Load Qwen3-VL-Reranker model (lazy loading).

        Returns:
            True if model loaded successfully, False otherwise

        Note:
            - Loads model in FP16 (~4.3GB GPU memory)
            - First call takes 20-30 seconds
        """
        if self._loaded:
            logger.info("Reranker model already loaded")
            return True

        try:
            import torch

            # Add the scripts directory to path for importing Qwen3VLReranker
            scripts_dir = Path(self._model_path) / "scripts"
            if scripts_dir.exists() and str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))

            from qwen3_vl_reranker import Qwen3VLReranker

            logger.info(f"Loading Reranker model from {self._model_path}...")

            self._reranker = Qwen3VLReranker(
                model_name_or_path=self._model_path,
                torch_dtype=torch.float16,
                default_instruction=self._default_instruction,
            )

            self._loaded = True
            logger.info("Reranker model loaded successfully")
            return True

        except ImportError as e:
            logger.error(f"Failed to import Reranker dependencies: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load Reranker model: {e}")
            return False

    def rerank(
        self,
        query_text: str,
        documents: List[Dict],
        instruction: Optional[str] = None,
        query_image: Optional[str] = None,
    ) -> List[Tuple[int, float]]:
        """
        Rerank documents based on relevance to query.

        Args:
            query_text: Natural language query text
            documents: List of dicts with 'text' key, optional 'image' key
            instruction: Optional custom instruction (overrides default)
            query_image: Optional query image path

        Returns:
            List of (original_index, score) tuples sorted by score descending
        """
        if not self._loaded:
            if not self.load_model():
                logger.error("Cannot rerank: model not loaded")
                return [(i, 0.0) for i in range(len(documents))]

        if not documents:
            return []

        try:
            # Prepare input for reranker
            query = {"text": query_text}
            if query_image:
                query["image"] = query_image

            input_data = {
                "query": query,
                "documents": documents,
                "instruction": instruction or self._default_instruction,
            }

            # Get scores from reranker
            scores = self._reranker.process(input_data)

            # Pair with original indices and sort by score descending
            indexed_scores = [(i, score) for i, score in enumerate(scores)]
            indexed_scores.sort(key=lambda x: x[1], reverse=True)

            return indexed_scores

        except Exception as e:
            logger.error(f"Failed to rerank: {e}")
            # Return original order with zero scores on error
            return [(i, 0.0) for i in range(len(documents))]

    def rerank_items(
        self,
        query_text: str,
        items: List[Tuple[str, float, Dict]],
        top_k: int = 20,
        instruction: Optional[str] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """
        Rerank search result items.

        Args:
            query_text: Natural language query text
            items: List of (item_id, initial_score, metadata) tuples
            top_k: Number of results to return after reranking
            instruction: Optional custom instruction

        Returns:
            Reranked list of (item_id, rerank_score, metadata) tuples
        """
        if not items:
            return []

        # Prepare documents for reranking
        documents = []
        for item_id, score, metadata in items:
            # Build document text from metadata
            doc_text = metadata.get("question_text", "")
            if metadata.get("choices"):
                choices = metadata.get("choices")
                if isinstance(choices, list):
                    doc_text += "\n" + "\n".join(str(c) for c in choices)
                elif isinstance(choices, str):
                    doc_text += "\n" + choices

            documents.append({"text": doc_text})

        # Rerank
        reranked = self.rerank(query_text, documents, instruction)

        # Build result with reranked order
        result = []
        for orig_idx, rerank_score in reranked[:top_k]:
            item_id, _, metadata = items[orig_idx]
            result.append((item_id, rerank_score, metadata))

        return result


def get_reranker_service() -> Optional[RerankerService]:
    """
    Get singleton Reranker service instance.

    Returns:
        RerankerService instance or None if not initialized
    """
    return _reranker_service


def init_reranker_service(
    model_path: str,
    default_instruction: str = "Given a search query, retrieve relevant educational question items.",
    lazy_load: bool = True,
) -> RerankerService:
    """
    Initialize the global Reranker service instance.

    Args:
        model_path: Path to Qwen3-VL-Reranker model directory
        default_instruction: Default instruction for reranking
        lazy_load: If False, load model immediately (default: True)

    Returns:
        Initialized RerankerService instance
    """
    global _reranker_service

    _reranker_service = RerankerService(
        model_path=model_path,
        default_instruction=default_instruction,
    )

    if not lazy_load:
        _reranker_service.load_model()

    logger.info(f"Reranker service initialized (lazy_load={lazy_load})")
    return _reranker_service
