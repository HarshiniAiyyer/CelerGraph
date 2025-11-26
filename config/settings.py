# config.py
"""Configuration management for GraphRAG system.

Centralized configuration using dataclasses for type safety and
environment variable integration. Follows Single Responsibility Principle
by separating configuration logic from business logic.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChromaConfig:
    """ChromaDB configuration settings."""
    path: str = "vectorstore/chroma_db"
    node_collection: str = "node_embeddings"
    code_collection: str = "code_chunks"
    cache_collection: str = "semantic_cache"
    similarity_space: str = "cosine"
    
    @classmethod
    def from_env(cls) -> "ChromaConfig":
        """Create configuration from environment variables."""
        return cls(
            path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"),
            node_collection=os.getenv("CHROMA_NODE_COLLECTION", "node_embeddings"),
            code_collection=os.getenv("CHROMA_CODE_COLLECTION", "code_chunks"),
            cache_collection=os.getenv("CHROMA_CACHE_COLLECTION", "semantic_cache"),
            similarity_space=os.getenv("CHROMA_SIMILARITY_SPACE", "cosine"),
        )


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    model_name: str = "BAAI/bge-small-en"
    cache_size: int = 1
    normalize_embeddings: bool = True
    
    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        """Create configuration from environment variables."""
        return cls(
            model_name=os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en"),
            cache_size=int(os.getenv("EMBEDDING_CACHE_SIZE", "1")),
            normalize_embeddings=os.getenv("EMBEDDING_NORMALIZE", "true").lower() == "true",
        )


@dataclass
class Neo4jConfig:
    """Neo4j database configuration."""
    uri: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_neo4j: bool = False
    
    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """Create configuration from environment variables."""
        return cls(
            uri=os.getenv("NEO4J_URI"),
            username=os.getenv("NEO4J_USERNAME"),
            password=os.getenv("NEO4J_PASSWORD"),
            use_neo4j=os.getenv("USE_NEO4J", "false").lower() == "true",
        )


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    model_name: str = "openai/gpt-oss-120b"
    temperature: float = 0.2
    max_tokens: int = 800
    api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create configuration from environment variables."""
        return cls(
            model_name=os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-120b"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "800")),
            api_key=os.getenv("GROQ_API_KEY"),
        )


@dataclass
class CacheConfig:
    """Semantic cache configuration."""
    threshold: float = 0.9
    
    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Create configuration from environment variables."""
        return cls(
            threshold=float(os.getenv("CACHE_THRESHOLD", "0.9")),
        )


@dataclass
class GraphRAGConfig:
    """Main configuration container for GraphRAG system."""
    chroma: ChromaConfig
    embedding: EmbeddingConfig
    neo4j: Neo4jConfig
    llm: LLMConfig
    cache: CacheConfig
    
    @classmethod
    def from_env(cls) -> "GraphRAGConfig":
        """Create complete configuration from environment variables."""
        return cls(
            chroma=ChromaConfig.from_env(),
            embedding=EmbeddingConfig.from_env(),
            neo4j=Neo4jConfig.from_env(),
            llm=LLMConfig.from_env(),
            cache=CacheConfig.from_env(),
        )
