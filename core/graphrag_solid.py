# graphrag_solid.py
"""GraphRAG main module refactored with SOLID principles.

This is the new main module that demonstrates the SOLID principles
implementation with dependency injection, proper separation of concerns,
and clean architecture.
"""

import re
import sys
from typing import Dict, List, Any

from config.settings import GraphRAGConfig
from core.code_exceptions import GraphRAGError, ChromaError, EmbeddingError, LLMError
from core.factories import initialize_factory
from core.interfaces import (
    EmbeddingProvider, VectorStore, CacheProvider,
    GraphDatabase, LLMProvider
)
from config.logger import log
from dotenv import load_dotenv

load_dotenv()


class GraphRAGSystem:
    """Main GraphRAG system following SOLID principles."""
    
    def __init__(self, config: GraphRAGConfig) -> None:
        """Initialize system with configuration.
        
        Args:
            config: System configuration.
        """
        self._config = config
        self._factory = initialize_factory(config)
        self._services = self._factory.create_all_services()
        
        # Extract services for easier access
        self._embedding_provider: EmbeddingProvider = self._services['embedding_provider']
        self._vector_store: VectorStore = self._services['vector_store']
        self._cache_provider: CacheProvider = self._services['cache_provider']
        self._graph_database: GraphDatabase = self._services['graph_database']
        self._llm_provider: LLMProvider = self._services['llm_provider']
        
        # Initialize connections
        self._initialize_services()
    
    def _initialize_services(self) -> None:
        """Initialize service connections."""
        try:
            log.info("Initializing GraphRAG services")
            
            # Connect to graph database if enabled
            if self._config.neo4j.use_neo4j:
                self._graph_database.connect()
            
            log.info("GraphRAG services initialized successfully")
        except Exception as exc:
            log.exception("Failed to initialize services")
            raise GraphRAGError(f"Service initialization failed: {exc}") from exc
    
    def answer_question(self, question: str) -> str:
        """Answer a question using the RAG pipeline.
        
        Args:
            question: User's question.
            
        Returns:
            Formatted answer with citations.
        """
        if not question:
            log.warning("Empty question provided")
            return "Please provide a valid question."
        
        try:
            log.info(f"Processing question: {question[:50]}...")
            
            # Check cache first
            cached = self._cache_provider.lookup(question)
            if cached:
                log.info("Returning cached answer")
                return cached["answer"]
            
            # Generate new answer
            answer = self._generate_answer(question)
            formatted_answer = self._format_response(answer)
            
            # Cache the result
            self._cache_provider.store(question, formatted_answer)
            log.info("Answer generated and cached successfully")
            return formatted_answer
        except (ChromaError, EmbeddingError, LLMError):
            raise
        except Exception as exc:
            log.exception("Answer generation failed")
            raise GraphRAGError(f"Answer generation failed: {exc}") from exc
    
    def _generate_answer(self, question: str) -> str:
        """Generate answer using RAG pipeline.
        
        Args:
            question: User's question.
            
        Returns:
            Generated answer.
        """
        # Get question embedding
        query_embedding = self._embedding_provider.embed(question)
        
        # Retrieve similar nodes
        node_collection = self._vector_store.get_collection(self._config.chroma.node_collection)
        nodes_results = node_collection.query([query_embedding], n_results=8)
        nodes = self._process_query_results(nodes_results)
        
        # Retrieve similar code chunks
        code_collection = self._vector_store.get_collection(self._config.chroma.code_collection)
        code_results = code_collection.query([query_embedding], n_results=8)
        chunks = self._process_query_results(code_results)
        
        # Expand graph neighbors if enabled
        neighbors = []
        if self._config.neo4j.use_neo4j:
            node_ids = [n["id"] for n in nodes]
            neighbors = self._graph_database.expand_neighbors(node_ids, depth=1)
        
        # Build context
        context = self._build_context(nodes, chunks, neighbors)
        
        # Generate answer
        prompt = self._build_prompt(context, question)
        answer = self._llm_provider.generate(prompt)
        
        return answer
    
    def _process_query_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process ChromaDB query results.
        
        Args:
            results: Query results from ChromaDB.
            
        Returns:
            List of processed documents.
        """
        from typing import List, Dict, Any
        documents: List[Dict[str, Any]] = []
        if not results or not results["ids"]:
            return documents
        
        ids = results["ids"][0]
        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        
        for i, (doc_id, doc, dist, meta) in enumerate(zip(ids, docs, dists, metas)):
            similarity = 1 - dist
            documents.append({
                "id": doc_id,
                "text": doc,
                "similarity": similarity,
                "metadata": meta,
            })
        
        return sorted(documents, key=lambda x: x["similarity"], reverse=True)
    
    def _build_context(self, nodes: List[Dict[str, Any]], chunks: List[Dict[str, Any]], 
                      neighbors: List[str]) -> str:
        """Build context string from retrieved data.
        
        Args:
            nodes: Retrieved nodes.
            chunks: Retrieved code chunks.
            neighbors: Neighbor node IDs.
            
        Returns:
            Formatted context string.
        """
        parts = []

        parts.append("=== Nodes ===")
        for n in nodes[:8]:
            parts.append(f"[node:{n['id']}] score={n['similarity']:.3f}")
            parts.append(n["text"])
            parts.append("")

        parts.append("=== Code Chunks ===")
        for c in chunks[:8]:
            parts.append(f"[chunk:{c['id']}] score={c['similarity']:.3f}")
            parts.append(c["text"])
            parts.append("")

        if neighbors:
            parts.append("=== Neighbor Nodes ===")
            parts.append("\n".join([f"[neighbor:{nid}]" for nid in neighbors]))

        return "\n".join(parts)
    
    def _build_prompt(self, context: str, question: str) -> str:
        """Build LLM prompt.
        
        Args:
            context: Retrieved context.
            question: User's question.
            
        Returns:
            Formatted prompt.
        """
        return f"""
You are a codebase analysis assistant.

Use only the following context. Format your response as follows:
1. First, provide a comprehensive answer in natural sentence structure, weaving in the information naturally.
2. Then, on a new line with "References:", list all the citations used in the format [node:ID] or [chunk:ID] with their locations.

If information is missing, say:
"The context does not contain the required information."

---------------------
CONTEXT:
{context}
---------------------

Question:
{question}

Answer:
"""
    
    def _format_response(self, answer: str) -> str:
        """Format response with citations.
        
        Args:
            answer: Raw LLM response.
            
        Returns:
            Formatted response.
        """
        # If response already has References section, return as-is
        if "References:" in answer or "references:" in answer:
            return answer
        
        # Extract citations and reorganize
        lines = answer.split("\n")
        citations: List[str] = []
        body_lines: List[str] = []
        
        for line in lines:
            if "[node:" in line or "[chunk:" in line:
                refs = re.findall(r'\[(?:node|chunk):[^\]]+\]', line)
                citations.extend(refs)
                body_lines.append(line)
            else:
                body_lines.append(line)
        
        # If we found citations, reorganize
        if citations:
            body = "\n".join(body_lines).strip()
            unique_citations = list(dict.fromkeys(citations))
            references = "\n".join([f"- {cite}" for cite in unique_citations])
            return f"{body}\n\nReferences:\n{references}"
        
        return answer
    
    def close(self) -> None:
        """Close system connections."""
        try:
            if self._config.neo4j.use_neo4j:
                self._graph_database.close()
            log.info("GraphRAG system closed")
        except Exception:
            pass


def create_system_from_env() -> GraphRAGSystem:
    """Create GraphRAG system from environment variables.
    
    Returns:
        Configured GraphRAG system.
    """
    config = GraphRAGConfig.from_env()
    return GraphRAGSystem(config)


def main() -> None:
    """Main CLI interface."""
    print("Initializing GraphRAG (SOLID Edition)...")
    print("  • Loading configuration...")
    print("  • Setting up services...")
    print("  • Establishing connections...")
    print("\nGraphRAG Ready. Type 'exit' to stop.\n")
    
    try:
        system = create_system_from_env()
        
        while True:
            q = input("\nAsk: ").strip()
            if q.lower() in {"exit", "quit"}:
                break
            if not q:
                continue
            
            try:
                answer = system.answer_question(q)
                print("\n" + answer + "\n")
                
                # Ask if user wants to continue
                while True:
                    follow_up = input("Would you like to ask another question? [yes/no]: ").strip().lower()
                    if follow_up in {"yes", "y"}:
                        break
                    elif follow_up in {"no", "n"}:
                        print("Goodbye! See you soon!")
                        sys.exit(0)
                    else:
                        print("Please enter 'yes' or 'no'.")
            except GraphRAGError as exc:
                log.error(f"Failed to answer question: {exc}")
                print(f"\nSorry, I encountered an error: {exc}\n")
                continue
            except KeyboardInterrupt:
                print("\nGoodbye! See you soon!")
                sys.exit(0)
                
    except KeyboardInterrupt:
        print("\nGoodbye! See you soon!")
        sys.exit(0)
    except Exception as exc:
        log.exception("Unexpected error in CLI")
        print(f"\nUnexpected error: {exc}")
        sys.exit(1)
    finally:
        if 'system' in locals():
            system.close()


if __name__ == "__main__":
    main()
