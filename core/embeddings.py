# embeddings.py
"""Text embedding utilities using sentence transformers.

This module provides functions for embedding text using the BAAI/bge-small-en
sentence transformer model, optimized for semantic similarity tasks.
Refactored to use dependency injection for better testability.
"""

from functools import lru_cache
from typing import List, Optional
import threading

from config.settings import EmbeddingConfig
from core.code_exceptions import EmbeddingError
from core.interfaces import EmbeddingProvider
from config.logger import log
from sentence_transformers import SentenceTransformer

# Observability
from observability.tracing import trace_span


class SentenceTransformerEmbedding(EmbeddingProvider):
    """Sentence transformer implementation of EmbeddingProvider."""

    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialize with configuration.

        Args:
            config: Embedding configuration.
        """
        self._config = config
        self._model: Optional[SentenceTransformer] = None
        self._lock = threading.Lock()

    @lru_cache(maxsize=1)
    def _get_model(self) -> SentenceTransformer:
        """Get cached model instance."""
        if self._model is None:
            try:
                log.info(f"Loading embedding model: {self._config.model_name}")
                self._model = SentenceTransformer(self._config.model_name)
                log.info("Embedding model loaded successfully")
            except Exception as exc:
                log.exception("Failed to load embedding model")
                raise EmbeddingError(f"Model loading failed: {exc}") from exc
        return self._model

    @trace_span("rag.embed")
    def embed(self, text: str) -> List[float]:
        """Embed text into vector representation.

        Args:
            text: The text to embed. Empty strings are handled gracefully.

        Returns:
            List of floats representing the normalized embedding vector.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        if not isinstance(text, str):
            raise EmbeddingError(f"Expected string input, got {type(text).__name__}")

        text = text or ""
        if not text:
            log.debug("Embedding empty string")
            return []

        try:
            model = self._get_model()
            log.debug(f"Embedding text (length={len(text)})")

            # Use thread lock to prevent concurrent access to the model
            with self._lock:
                # normalize_embeddings=True is good for cosine similarity
                embedding = model.encode(
                    text,
                    normalize_embeddings=self._config.normalize_embeddings,
                ).tolist()

            log.debug(f"Generated embedding (dim={len(embedding)})")
            return embedding
        except Exception as exc:
            log.exception("Failed to embed text")
            raise EmbeddingError(f"Embedding failed: {exc}") from exc

    def get_model_info(self) -> dict:
        """Get information about the embedding model.

        Returns:
            Dictionary with model details.
        """
        return {
            "model_name": self._config.model_name,
            "normalize_embeddings": self._config.normalize_embeddings,
            "cache_size": self._config.cache_size,
        }


# Legacy functions for backward compatibility
# These will be deprecated in favor of the DI approach

# Global instance for backward compatibility
_legacy_config = EmbeddingConfig()
_legacy_provider = SentenceTransformerEmbedding(_legacy_config)
_legacy_lock = threading.Lock()


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load and cache the sentence transformer model.

    DEPRECATED: Use SentenceTransformerEmbedding service instead.

    Returns:
        Cached SentenceTransformer model instance.

    Raises:
        EmbeddingError: If model loading fails.
    """
    return _legacy_provider._get_model()


@trace_span("rag.embed.legacy")
def embed_text(text: str) -> List[float]:
    """Embed text into a vector representation.

    DEPRECATED: Use SentenceTransformerEmbedding service instead.

    Args:
        text: The text to embed. Empty strings are handled gracefully.

    Returns:
        List of floats representing the normalized embedding vector.

    Raises:
        EmbeddingError: If embedding generation fails.
    """
    with _legacy_lock:
        return _legacy_provider.embed(text)
