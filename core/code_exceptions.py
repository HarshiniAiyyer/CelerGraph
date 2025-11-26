"""Custom exception hierarchy for GraphRAG."""

class GraphRAGError(Exception):
    """Base exception for all GraphRAG errors."""


class EmbeddingError(GraphRAGError):
    """Raised when text embedding fails."""


class ChromaError(GraphRAGError):
    """Raised when ChromaDB operations fail."""


class Neo4jError(GraphRAGError):
    """Raised when Neo4j operations fail."""


class LLMError(GraphRAGError):
    """Raised when LLM invocation fails."""


class CacheMiss(GraphRAGError):
    """Raised internally to indicate a semantic-cache miss (non-fatal)."""
