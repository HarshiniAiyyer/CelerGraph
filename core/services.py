"""Concrete service implementations for GraphRAG system.

Provides concrete implementations of the abstract interfaces defined in
interfaces.py. Each service follows Single Responsibility Principle and
depends on abstractions rather than concrete implementations.
"""

import json
import time
from typing import List, Dict, Any, Optional
from functools import lru_cache

import chromadb
from langchain_groq import ChatGroq

from core.interfaces import (
    EmbeddingProvider, VectorStore, VectorCollection, CacheProvider,
    GraphDatabase, LLMProvider, DocumentProcessor
)
from config.settings import (
    EmbeddingConfig, ChromaConfig, Neo4jConfig, LLMConfig, CacheConfig
)
from config.logger import log
from observability.tracing import trace_span

# Import embeddings module to allow patching in tests
import core.embeddings


class SemanticCacheProvider(CacheProvider):
    """ChromaDB-based implementation of CacheProvider."""
    
    def __init__(self, config: Any):
        self._config = config
        self._collection = self._init_collection()
        
    def _init_collection(self):
        try:
            log.debug("Connecting to ChromaDB for semantic cache")
            chroma_path = self._config.chroma.path if hasattr(self._config, "chroma") else "vectorstore/chroma_db"
            cache_collection_name = self._config.chroma.cache_collection if hasattr(self._config, "chroma") else "semantic_cache"
            
            client = chromadb.PersistentClient(path=chroma_path)
            return client.get_or_create_collection(
                name=cache_collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as exc:
            log.error(f"Failed to initialize semantic cache: {exc}")
            raise

    @trace_span("rag.cache.lookup")
    def lookup(self, question: str) -> Optional[Dict[str, Any]]:
        """Look up cached answer for question."""
        try:
            # Use embed_text helper which is mocked in tests
            vector = core.embeddings.embed_text(question)
            
            results = self._collection.query(
                query_embeddings=[vector],
                n_results=1
            )
            
            if not results["ids"] or not results["ids"][0]:
                return None
                
            distance = results["distances"][0][0]
            threshold = self._config.cache.threshold if hasattr(self._config, "cache") else 0.9
            
            # Chroma cosine distance -> similarity
            similarity = 1 - distance
            
            if similarity >= threshold:
                metadata = results["metadatas"][0][0]
                return {
                    "answer": metadata.get("answer"),
                    "references": json.loads(metadata.get("references", "[]"))
                }
            return None
            
        except Exception as exc:
            log.warning(f"Cache lookup failed: {exc}")
            return None

    @trace_span("rag.cache.store")
    def store(self, question: str, answer: str, references: List[Any] = None) -> None:
        """Store question-answer pair."""
        try:
            # Use embed_text helper which is mocked in tests
            vector = core.embeddings.embed_text(question)
            
            import uuid
            item_id = str(uuid.uuid4())
            
            self._collection.add(
                ids=[item_id],
                embeddings=[vector],
                documents=[question],
                metadatas=[{
                    "answer": answer,
                    "references": json.dumps(references or [])
                }]
            )
        except Exception as exc:
            log.error(f"Failed to store in cache: {exc}")


class GroqLLMProvider(LLMProvider):
    """Groq implementation of LLMProvider."""
    
    def __init__(self, config: LLMConfig):
        self._config = config
        self._llm = self._init_llm()
        
    def _init_llm(self):
        return ChatGroq(
            model=self._config.model_name,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            api_key=self._config.api_key
        )
        
    @trace_span("rag.llm.generate")
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text response."""
        try:
            response = self._llm.invoke(prompt)
            return response.content
        except Exception as exc:
            log.exception("LLM generation failed")
            raise Exception(f"LLM generation failed: {exc}") from exc
            
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the LLM."""
        return {
            "model_name": self._config.model_name,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }


class JSONDocumentProcessor(DocumentProcessor):
    """JSON file implementation of DocumentProcessor."""

    @trace_span("rag.docs.load")
    def load_documents(self, path: str) -> List[Dict[str, Any]]:
        """Load documents from JSON file."""
        try:
            log.info(f"Loading documents from {path}")
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict) and "nodes" in data:
                documents = data["nodes"]
            elif isinstance(data, list):
                documents = data
            else:
                documents = [data]

            log.info(f"Loaded {len(documents)} documents")
            return documents
        except Exception:
            log.exception(f"Failed to load documents from {path}")
            raise

    @trace_span("rag.docs.process")
    def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document."""
        # Basic processing - can be extended
        return document
