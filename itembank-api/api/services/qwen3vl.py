"""
Qwen3-VL Embedding Service for natural language query embedding.

Provides text and multimodal (text+image) encoding using Qwen3-VL-Embedding model.
"""
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Singleton instance
_qwen3vl_service: Optional["Qwen3VLService"] = None


class Qwen3VLService:
    """
    Service for generating embeddings using Qwen3-VL-Embedding model.

    Features:
    - Lazy loading: Model loads on first query (not at startup)
    - Text encoding: Convert natural language queries to 2048-dim embeddings
    - Multimodal encoding: Combined text + image encoding (optional)
    """

    def __init__(
        self,
        model_path: str,
        default_instruction: str = "Represent this educational question item for retrieval.",
    ):
        """
        Initialize the service (model is NOT loaded yet).

        Args:
            model_path: Path to Qwen3-VL-Embedding model directory
            default_instruction: Default instruction for embedding generation
        """
        self._model_path = model_path
        self._default_instruction = default_instruction
        self._embedder = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._loaded

    def load_model(self) -> bool:
        """
        Load Qwen3-VL-Embedding model (lazy loading).

        Returns:
            True if model loaded successfully, False otherwise

        Note:
            - Loads model in FP16 (~4.3GB GPU memory)
            - First call takes 20-30 seconds
        """
        if self._loaded:
            logger.info("Qwen3VL model already loaded")
            return True

        try:
            import torch

            # Add the scripts directory to path for importing Qwen3VLEmbedder
            scripts_dir = Path(self._model_path) / "scripts"
            if scripts_dir.exists() and str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))

            from qwen3_vl_embedding import Qwen3VLEmbedder

            logger.info(f"Loading Qwen3VL model from {self._model_path}...")

            self._embedder = Qwen3VLEmbedder(
                model_name_or_path=self._model_path,
                torch_dtype=torch.float16,
                default_instruction=self._default_instruction,
            )

            self._loaded = True
            logger.info("Qwen3VL model loaded successfully")
            return True

        except ImportError as e:
            logger.error(f"Failed to import Qwen3VL dependencies: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load Qwen3VL model: {e}")
            return False

    def encode_text(
        self,
        text: str,
        instruction: Optional[str] = None,
    ) -> Optional[np.ndarray]:
        """
        Encode text query to 2048-dimensional embedding.

        Args:
            text: Natural language query text
            instruction: Optional custom instruction (overrides default)

        Returns:
            numpy array of shape (2048,) or None if encoding fails
        """
        if not self._loaded:
            if not self.load_model():
                logger.error("Cannot encode: model not loaded")
                return None

        try:
            input_data = {"text": text}
            if instruction:
                input_data["instruction"] = instruction

            embeddings = self._embedder.process([input_data], normalize=True)
            return embeddings[0].cpu().numpy()

        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            return None

    def encode_multimodal(
        self,
        text: str,
        image_path: str,
        instruction: Optional[str] = None,
    ) -> Optional[np.ndarray]:
        """
        Encode text + image to 2048-dimensional embedding.

        Args:
            text: Natural language query text
            image_path: Path to image file
            instruction: Optional custom instruction (overrides default)

        Returns:
            numpy array of shape (2048,) or None if encoding fails
        """
        if not self._loaded:
            if not self.load_model():
                logger.error("Cannot encode: model not loaded")
                return None

        try:
            input_data = {
                "text": text,
                "image": image_path,
            }
            if instruction:
                input_data["instruction"] = instruction

            embeddings = self._embedder.process([input_data], normalize=True)
            return embeddings[0].cpu().numpy()

        except Exception as e:
            logger.error(f"Failed to encode multimodal input: {e}")
            return None

    def encode_batch(
        self,
        inputs: List[Dict],
        normalize: bool = True,
    ) -> Optional[np.ndarray]:
        """
        Encode batch of inputs (text or multimodal).

        Args:
            inputs: List of dicts with 'text', optional 'image', 'instruction'
            normalize: Whether to L2-normalize embeddings

        Returns:
            numpy array of shape (batch_size, 2048) or None if encoding fails
        """
        if not self._loaded:
            if not self.load_model():
                logger.error("Cannot encode: model not loaded")
                return None

        try:
            embeddings = self._embedder.process(inputs, normalize=normalize)
            return embeddings.cpu().numpy()

        except Exception as e:
            logger.error(f"Failed to encode batch: {e}")
            return None


def get_qwen3vl_service() -> Optional[Qwen3VLService]:
    """
    Get singleton Qwen3VL service instance.

    Returns:
        Qwen3VLService instance or None if not initialized
    """
    return _qwen3vl_service


def init_qwen3vl_service(
    model_path: str,
    default_instruction: str = "Represent this educational question item for retrieval.",
    lazy_load: bool = True,
) -> Qwen3VLService:
    """
    Initialize the global Qwen3VL service instance.

    Args:
        model_path: Path to Qwen3-VL-Embedding model directory
        default_instruction: Default instruction for embedding generation
        lazy_load: If False, load model immediately (default: True)

    Returns:
        Initialized Qwen3VLService instance
    """
    global _qwen3vl_service

    _qwen3vl_service = Qwen3VLService(
        model_path=model_path,
        default_instruction=default_instruction,
    )

    if not lazy_load:
        _qwen3vl_service.load_model()

    logger.info(f"Qwen3VL service initialized (lazy_load={lazy_load})")
    return _qwen3vl_service
