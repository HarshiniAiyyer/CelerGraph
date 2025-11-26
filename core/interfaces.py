# interfaces.py
"""Abstract interfaces for GraphRAG services.

Defines contracts for all major services following the Interface Segregation
and Dependency Inversion principles. Enables loose coupling and testability.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from config.settings import GraphRAGConfig


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding services."""
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Embed text into vector representation.
        
        Args:
            text: Text to embed.
            
        Returns:
            Vector representation of the text.
            
        Raises:
            EmbeddingError: If embedding fails.
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model.
        
        Returns:
            Dictionary with model details.
        """
        pass


class VectorStore(ABC):
    """Abstract interface for vector storage and retrieval."""
    
    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Add documents to the vector store.
        
        Args:
            documents: List of documents with embeddings and metadata.
            
        Returns:
            List of document IDs.
        """
        pass
    
    @abstractmethod
    def similarity_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 8,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.
        
        Args:
            query_embedding: Query vector.
            top_k: Number of results to return.
            filter_dict: Optional metadata filters.
            
        Returns:
            List of similar documents with scores.
        """
        pass
    
    @abstractmethod
    def get_collection(self, name: str) -> "VectorCollection":
        """Get or create a collection.
        
        Args:
            name: Collection name.
            
        Returns:
            Vector collection instance.
        """
        pass


class VectorCollection(ABC):
    """Abstract interface for vector collections."""
    
    @abstractmethod
    def add(self, ids: List[str], embeddings: List[List[float]], 
            documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Add items to collection."""
        pass
    
    @abstractmethod
    def query(self, query_embeddings: List[List[float]], 
              n_results: int) -> Dict[str, Any]:
        """Query the collection."""
        pass
    
    @abstractmethod
    def upsert(self, ids: List[str], embeddings: List[List[float]], 
               documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Update or insert items in collection."""
        pass


class CacheProvider(ABC):
    """Abstract interface for semantic caching."""
    
    @abstractmethod
    def lookup(self, question: str) -> Optional[Dict[str, Any]]:
        """Look up cached answer for question.
        
        Args:
            question: Query string.
            
        Returns:
            Cached response if found, None otherwise.
        """
        pass
    
    @abstractmethod
    def store(self, question: str, answer: str) -> None:
        """Store question-answer pair.
        
        Args:
            question: Query string.
            answer: Response to cache.
        """
        pass


class GraphDatabase(ABC):
    """Abstract interface for graph database operations."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to database."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        pass
    
    @abstractmethod
    def expand_neighbors(self, node_ids: List[str], depth: int = 1) -> List[str]:
        """Find neighbor nodes for given node IDs.
        
        Args:
            node_ids: List of node identifiers.
            depth: Search depth.
            
        Returns:
            List of neighbor node IDs.
        """
        pass
    
    @abstractmethod
    def execute_query(self, query: str, **kwargs) -> Any:
        """Execute a Cypher query.
        
        Args:
            query: Cypher query string.
            **kwargs: Query parameters.
            
        Returns:
            Query results.
        """
        pass


class LLMProvider(ABC):
    """Abstract interface for Large Language Model providers."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text response.
        
        Args:
            prompt: Input prompt.
            **kwargs: Additional generation parameters.
            
        Returns:
            Generated text response.
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the LLM.
        
        Returns:
            Dictionary with model details.
        """
        pass


class DocumentProcessor(ABC):
    """Abstract interface for document processing."""
    
    @abstractmethod
    def load_documents(self, path: str) -> List[Dict[str, Any]]:
        """Load documents from file.
        
        Args:
            path: File path.
            
        Returns:
            List of document dictionaries.
        """
        pass
    
    @abstractmethod
    def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document.
        
        Args:
            document: Raw document.
            
        Returns:
            Processed document.
        """
        pass


class ServiceContainer(ABC):
    """Abstract interface for dependency injection container."""
    
    @abstractmethod
    def register(self, interface: type, implementation: type) -> None:
        """Register a service implementation.
        
        Args:
            interface: Service interface class.
            implementation: Service implementation class.
        """
        pass
    
    @abstractmethod
    def get(self, interface: type) -> Any:
        """Get a service instance.
        
        Args:
            interface: Service interface class.
            
        Returns:
            Service instance.
        """
        pass
    
    @abstractmethod
    def configure(self, config: GraphRAGConfig) -> None:
        """Configure services with settings.
        
        Args:
            config: Configuration object.
        """
        pass
