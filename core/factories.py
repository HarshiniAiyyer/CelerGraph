# factories.py
"""Factory pattern implementation for service creation.

Provides centralized service creation following the Factory pattern.
This ensures consistent object creation and makes it easy to switch
implementations.
"""

from typing import Dict, Type, Any, Optional

from core.interfaces import (
    EmbeddingProvider, VectorStore, CacheProvider,
    GraphDatabase, LLMProvider, DocumentProcessor
)
from core.services import (
    SentenceTransformerEmbedding, ChromaVectorStore, SemanticCacheProvider,
    Neo4jGraphDatabase, GroqLLMProvider, JSONDocumentProcessor
)
from config.settings import GraphRAGConfig
from core.code_exceptions import GraphRAGError
from config.logger import log


class ServiceFactory:
    """Factory for creating service instances."""
    
    def __init__(self, config: GraphRAGConfig) -> None:
        """Initialize factory with configuration.
        
        Args:
            config: GraphRAG configuration.
        """
        self._config = config
        self._service_registry: Dict[Type, Type] = {
            EmbeddingProvider: SentenceTransformerEmbedding,
            VectorStore: ChromaVectorStore,
            CacheProvider: SemanticCacheProvider,
            GraphDatabase: Neo4jGraphDatabase,
            LLMProvider: GroqLLMProvider,
            DocumentProcessor: JSONDocumentProcessor,
        }
    
    def create_embedding_provider(self) -> EmbeddingProvider:
        """Create embedding provider instance.
        
        Returns:
            Configured embedding provider.
        """
        provider_class = self._service_registry[EmbeddingProvider]
        return provider_class(self._config.embedding)
    
    def create_vector_store(self) -> VectorStore:
        """Create vector store instance.
        
        Returns:
            Configured vector store.
        """
        provider_class = self._service_registry[VectorStore]
        return provider_class(self._config.chroma)
    
    def create_cache_provider(self) -> CacheProvider:
        """Create cache provider instance.
        
        Returns:
            Configured cache provider.
        """
        provider_class = self._service_registry[CacheProvider]
        return provider_class(self._config)
    
    def create_graph_database(self) -> GraphDatabase:
        """Create graph database instance.
        
        Returns:
            Configured graph database.
        """
        provider_class = self._service_registry[GraphDatabase]
        return provider_class(self._config.neo4j)
    
    def create_llm_provider(self) -> LLMProvider:
        """Create LLM provider instance.
        
        Returns:
            Configured LLM provider.
        """
        provider_class = self._service_registry[LLMProvider]
        return provider_class(self._config.llm)
    
    def create_document_processor(self) -> DocumentProcessor:
        """Create document processor instance.
        
        Returns:
            Configured document processor.
        """
        provider_class = self._service_registry[DocumentProcessor]
        return provider_class()
    
    def register_service(self, interface: Type, implementation: Type) -> None:
        """Register a custom service implementation.
        
        Args:
            interface: Service interface class.
            implementation: Service implementation class.
        """
        if not issubclass(implementation, interface):
            raise GraphRAGError(f"{implementation.__name__} must implement {interface.__name__}")
        
        self._service_registry[interface] = implementation
        log.info(f"Registered custom implementation: {implementation.__name__} for {interface.__name__}")
    
    def create_all_services(self) -> Dict[str, Any]:
        """Create all service instances.
        
        Returns:
            Dictionary of all configured services.
        """
        try:
            services = {
                'embedding_provider': self.create_embedding_provider(),
                'vector_store': self.create_vector_store(),
                'cache_provider': self.create_cache_provider(),
                'graph_database': self.create_graph_database(),
                'llm_provider': self.create_llm_provider(),
                'document_processor': self.create_document_processor(),
            }
            log.info("All services created successfully")
            return services
        except Exception as exc:
            log.exception("Failed to create services")
            raise GraphRAGError(f"Service creation failed: {exc}") from exc


# Global factory instance
_factory: Optional[ServiceFactory] = None


def get_factory(config: Optional[GraphRAGConfig] = None) -> ServiceFactory:
    """Get the global service factory.
    
    Args:
        config: Optional configuration to set.
        
    Returns:
        Global factory instance.
    """
    global _factory
    if _factory is None and config is not None:
        _factory = ServiceFactory(config)
    elif _factory is None:
        raise GraphRAGError("Factory not initialized. Call get_factory(config) first.")
    return _factory


def initialize_factory(config: GraphRAGConfig) -> ServiceFactory:
    """Initialize the global factory with configuration.
    
    Args:
        config: GraphRAG configuration.
        
    Returns:
        Initialized factory.
    """
    global _factory
    _factory = ServiceFactory(config)
    log.info("Service factory initialized")
    return _factory


# Decorator for service injection
def service(interface: Type):
    """Decorator for automatic service injection.
    
    Args:
        interface: Service interface to inject.
        
    Returns:
        Decorated function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            factory = get_factory()
            
            # Map interfaces to factory methods
            service_map = {
                EmbeddingProvider: factory.create_embedding_provider(),
                VectorStore: factory.create_vector_store(),
                CacheProvider: factory.create_cache_provider(),
                GraphDatabase: factory.create_graph_database(),
                LLMProvider: factory.create_llm_provider(),
                DocumentProcessor: factory.create_document_processor(),
            }
            
            service_instance = service_map.get(interface)
            if service_instance is None:
                raise GraphRAGError(f"No factory method for {interface.__name__}")
            
            return func(service_instance, *args, **kwargs)
        return wrapper
    return decorator
