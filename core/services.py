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
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq

from core.interfaces import (
    EmbeddingProvider, VectorStore, VectorCollection, CacheProvider,
    GraphDatabase as GraphDBInterface, LLMProvider, DocumentProcessor,
)
from config.settings import GraphRAGConfig, ChromaConfig, EmbeddingConfig, Neo4jConfig, LLMConfig
from core.code_exceptions import EmbeddingError, ChromaError, Neo4jError, LLMError
from config.logger import log

# 🔥 Observability
from observability.tracing import trace_span
from observability.rag import (
    record_retrieval_metrics,
    record_generation_metrics,
)


class SentenceTransformerEmbedding(EmbeddingProvider):
    """Sentence transformer implementation of EmbeddingProvider."""

    def __init__(self, config: Optional[EmbeddingConfig] = None) -> None:
        """Initialize with configuration.

        Args:
            config: Embedding configuration.
        """
        self._config = config or EmbeddingConfig()
        self._model: Optional[SentenceTransformer] = None

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

    @trace_span("rag.embed.di")
    def embed(self, text: str) -> List[float]:
        """Embed text into vector representation."""
        if not isinstance(text, str):
            raise EmbeddingError(f"Expected string input, got {type(text).__name__}")

        text = text or ""
        if not text:
            log.debug("Embedding empty string")
            return []

        try:
            model = self._get_model()
            log.debug(f"Embedding text (length={len(text)})")
            embedding = model.encode(
                text,
                normalize_embeddings=self._config.normalize_embeddings,
            ).tolist()
            log.debug(f"Generated embedding (dim={len(embedding)})")
            return embedding
        except Exception as exc:
            log.exception("Failed to embed text")
            raise EmbeddingError(f"Embedding failed: {exc}") from exc

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        return {
            "model_name": self._config.model_name,
            "normalize_embeddings": self._config.normalize_embeddings,
            "cache_size": self._config.cache_size,
        }


class ChromaVectorStore(VectorStore):
    """ChromaDB implementation of VectorStore."""

    def __init__(self, config: Optional[ChromaConfig] = None) -> None:
        """Initialize with configuration.

        Args:
            config: ChromaDB configuration.
        """
        self._config = config or ChromaConfig()
        self._client = chromadb.PersistentClient(path=self._config.path)
        self._collections: Dict[str, ChromaVectorCollection] = {}

    def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Add documents to the vector store."""
        # Implementation depends on specific use case
        raise NotImplementedError("Use specific collection methods")

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 8,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        # Implementation depends on specific collection
        raise NotImplementedError("Use specific collection methods")

    def get_collection(self, name: str) -> "ChromaVectorCollection":
        """Get or create a collection."""
        if name not in self._collections:
            try:
                collection = self._client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": self._config.similarity_space},
                )
                self._collections[name] = ChromaVectorCollection(collection)
                log.debug(f"Created/retrieued collection: {name}")
            except Exception as exc:
                log.exception(f"Failed to get collection: {name}")
                raise ChromaError(f"Collection error: {exc}") from exc

        return self._collections[name]


class ChromaVectorCollection(VectorCollection):
    """ChromaDB collection wrapper."""

    def __init__(self, collection) -> None:
        """Initialize with ChromaDB collection."""
        self._collection = collection

    @trace_span("rag.vector.add")
    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Add items to collection."""
        try:
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            log.debug(f"Added {len(ids)} items to collection")
        except Exception as exc:
            log.exception("Failed to add items to collection")
            raise ChromaError(f"Add operation failed: {exc}") from exc

    @trace_span("rag.vector.query")
    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int,
    ) -> Dict[str, Any]:
        """Query the collection."""
        t0 = time.perf_counter()
        try:
            results = self._collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                include=["documents", "distances", "metadatas"],
            )
            log.debug(f"Queried collection for {n_results} results")

            # Basic retrieval metrics
            ids = results.get("ids", [[]])[0] if results else []
            num = len(ids)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            if num > 0:
                record_retrieval_metrics(
                    num_candidates=num,
                    num_selected=num,
                    retrieval_latency_ms=latency_ms,
                )

            return results
        except Exception as exc:
            log.exception("Failed to query collection")
            raise ChromaError(f"Query operation failed: {exc}") from exc

    @trace_span("rag.vector.upsert")
    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Update or insert items in collection."""
        try:
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            log.debug(f"Upserted {len(ids)} items to collection")
        except Exception as exc:
            log.exception("Failed to upsert items to collection")
            raise ChromaError(f"Upsert operation failed: {exc}") from exc


class SemanticCacheProvider(CacheProvider):
    """ChromaDB-based semantic cache implementation."""

    def __init__(self, config: GraphRAGConfig) -> None:
        """Initialize with configuration.

        Args:
            config: GraphRAG configuration.
        """
        self._config = config
        self._vector_store = ChromaVectorStore(config.chroma)
        self._collection = self._vector_store.get_collection(config.chroma.cache_collection)
        self._threshold = config.cache.threshold

    @trace_span("rag.cache.lookup")
    def lookup(self, question: str) -> Optional[Dict[str, Any]]:
        """Look up cached answer for question."""
        if not question:
            log.debug("Skipping cache lookup for empty question")
            return None

        try:
            from core.embeddings import embed_text
            log.debug(f"Cache lookup for question: {question[:50]}...")
            t0 = time.perf_counter()
            vec = embed_text(question)
            results = self._collection.query(query_embeddings=[vec], n_results=1)
            latency_ms = (time.perf_counter() - t0) * 1000.0

            if not results or not results["ids"] or not results["distances"][0]:
                log.debug("No results found in cache")
                record_retrieval_metrics(
                    num_candidates=0,
                    num_selected=0,
                    retrieval_latency_ms=latency_ms,
                )
                return None

            distance = results["distances"][0][0]
            similarity = 1 - distance
            doc = results["documents"][0][0]
            meta = results["metadatas"][0][0]
            answer = meta.get("answer")

            if not answer:
                log.info("[CACHE BYPASS] empty cached answer")
                record_retrieval_metrics(
                    num_candidates=1,
                    num_selected=0,
                    retrieval_latency_ms=latency_ms,
                    avg_score=similarity,
                )
                return None

            if isinstance(answer, str) and answer.startswith("Generated answer for:"):
                log.info("[CACHE BYPASS] placeholder cached answer detected")
                record_retrieval_metrics(
                    num_candidates=1,
                    num_selected=0,
                    retrieval_latency_ms=latency_ms,
                    avg_score=similarity,
                )
                return None

            import re

            def _tokens(text: str) -> set:
                s = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
                words = [
                    w
                    for w in s.split()
                    if w
                    and w
                    not in {
                        "the",
                        "a",
                        "an",
                        "and",
                        "or",
                        "of",
                        "to",
                        "in",
                        "on",
                        "for",
                        "with",
                        "by",
                        "how",
                        "does",
                        "is",
                        "are",
                        "be",
                        "from",
                        "this",
                        "that",
                        "it",
                        "as",
                        "about",
                    }
                ]
                return set(words)

            oq = _tokens(question)
            od = _tokens(doc)
            overlap = 0.0
            if oq and od:
                inter = len(oq & od)
                union = len(oq | od)
                overlap = inter / union

            if similarity >= self._threshold and overlap >= 0.3:
                log.info(f"[CACHE HIT] similarity={similarity:.3f}")
                record_retrieval_metrics(
                    num_candidates=1,
                    num_selected=1,
                    retrieval_latency_ms=latency_ms,
                    avg_score=similarity,
                )
                return {
                    "question": doc,
                    "answer": answer,
                    "similarity": similarity,
                }

            log.info(
                f"[CACHE MISS] best similarity={similarity:.3f}, lexical_overlap={overlap:.3f}"
            )
            record_retrieval_metrics(
                num_candidates=1,
                num_selected=0,
                retrieval_latency_ms=latency_ms,
                avg_score=similarity,
            )
            return None
        except Exception as exc:
            log.exception("Cache lookup failed")
            raise ChromaError(f"Cache lookup error: {exc}") from exc

    @trace_span("rag.cache.store")
    def store(self, question: str, answer: str) -> None:
        """Store question-answer pair."""
        if not question or not answer:
            log.warning("Skipping cache store for empty question or answer")
            return

        try:
            from core.embeddings import embed_text
            log.debug(f"Caching question: {question[:50]}...")
            vec = embed_text(question)
            self._collection.upsert(
                ids=[question],
                embeddings=[vec],
                documents=[question],
                metadatas=[{"answer": answer}],
            )
            log.info("[CACHE STORE] saved.")
        except Exception as exc:
            log.exception("Cache store failed")
            raise ChromaError(f"Cache store error: {exc}") from exc


class Neo4jGraphDatabase(GraphDBInterface):
    """Neo4j implementation of GraphDatabase."""

    def __init__(self, config: Optional[Neo4jConfig] = None) -> None:
        """Initialize with configuration.

        Args:
            config: Neo4j configuration.
        """
        self._config = config or Neo4jConfig()
        self._driver: Optional[Any] = None

    @trace_span("rag.neo4j.connect")
    def connect(self) -> None:
        """Establish connection to database."""
        if not self._config.use_neo4j:
            log.debug("Neo4j disabled in configuration")
            return

        if not self._config.uri or not self._config.username or not self._config.password:
            raise Neo4jError("Neo4j credentials not provided")

        try:
            log.info(f"Connecting to Neo4j at {self._config.uri}")
            self._driver = GraphDatabase.driver(
                self._config.uri,
                auth=(self._config.username, self._config.password),
            )
            self._driver.verify_connectivity()
            log.info("Neo4j connection established")
        except Exception as exc:
            log.exception("Failed to connect to Neo4j")
            raise Neo4jError(f"Neo4j connection failed: {exc}") from exc

    def close(self) -> None:
        """Close database connection."""
        if self._driver:
            try:
                self._driver.close()
                log.info("Neo4j connection closed")
            except Exception:
                pass

    @trace_span("rag.neo4j.expand_neighbors")
    def expand_neighbors(self, node_ids: List[str], depth: int = 1) -> List[str]:
        """Find neighbor nodes for given node IDs."""
        if not self._config.use_neo4j or not self._driver:
            log.debug("Neo4j expansion disabled")
            return []

        try:
            log.debug(f"Expanding graph for {len(node_ids)} nodes (depth={depth})")
            query = """
            UNWIND $ids AS id
            MATCH (n {id: id})-[*1..$depth]-(m)
            RETURN DISTINCT m.id AS id
            """
            with self._driver.session() as session:
                result = session.run(query, ids=node_ids, depth=depth)
                neighbors = [r["id"] for r in result]
                log.debug(f"Found {len(neighbors)} neighbor nodes")
                return neighbors
        except Exception as exc:
            log.exception("Graph expansion failed")
            raise Neo4jError(f"Graph expansion failed: {exc}") from exc

    @trace_span("rag.neo4j.execute_query")
    def execute_query(self, query: str, **kwargs) -> Any:
        """Execute a Cypher query.

        Args:
            query: Cypher query string.
            **kwargs: Query parameters.

        Returns:
            Query results.
        """
        if not self._config.use_neo4j or not self._driver:
            raise Neo4jError("Neo4j not connected")

        try:
            with self._driver.session() as session:
                result = session.run(query, **kwargs)
                return result.data()
        except Exception as exc:
            log.exception(f"Query execution failed: {query}")
            raise Neo4jError(f"Query execution failed: {exc}") from exc

    @trace_span("rag.neo4j.batch_import")
    def batch_import(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
        """Import nodes and edges in batches."""
        if not self._config.use_neo4j or not self._driver:
            raise Neo4jError("Neo4j not connected")

        # Implementation would go here - similar to loadneo.py logic
        # For brevity, this is a placeholder
        log.info(f"Importing {len(nodes)} nodes and {len(edges)} edges")
        pass


class GroqLLMProvider(LLMProvider):
    """Groq implementation of LLMProvider."""

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        """Initialize with configuration.

        Args:
            config: LLM configuration.
        """
        self._config = config or LLMConfig()
        self._llm: Optional[ChatGroq] = None

    def _get_llm(self) -> ChatGroq:
        """Get LLM instance."""
        if self._llm is None:
            try:
                log.info("Initializing Groq LLM")
                self._llm = ChatGroq(
                    model=self._config.model_name,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                )
                log.info("Groq LLM initialized successfully")
            except Exception as exc:
                log.exception("Failed to initialize Groq LLM")
                raise LLMError(f"LLM initialization failed: {exc}") from exc
        return self._llm

    @trace_span("rag.llm.generate")
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text response."""
        t0 = time.perf_counter()
        try:
            llm = self._get_llm()
            log.debug("Generating LLM response")
            response = llm.invoke(prompt, **kwargs)
            log.debug("LLM response generated")

            latency_ms = (time.perf_counter() - t0) * 1000.0
            # We don't have token counts here, but we still track latency
            record_generation_metrics(
                generation_latency_ms=latency_ms,
            )

            return str(response)
        except Exception as exc:
            log.exception("LLM generation failed")
            raise LLMError(f"LLM generation failed: {exc}") from exc

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

