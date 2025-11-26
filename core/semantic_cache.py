# semantic_cache.py
"""Semantic caching system for RAG responses.

Implements a semantic cache that stores and retrieves answers based on
semantic similarity of questions, using ChromaDB and embeddings.
"""

import os
import json
from typing import Optional, Dict, Any, List, Sequence, cast
import re

import chromadb
from core.code_exceptions import ChromaError
from config.logger import log
from core.embeddings import embed_text


def get_cache_collection() -> chromadb.Collection:
    """Get or create the semantic cache collection in ChromaDB.
    
    Returns:
        ChromaDB collection configured for cosine similarity search.
    
    Raises:
        ChromaError: If ChromaDB connection or collection creation fails.
    """
    try:
        log.debug("Connecting to ChromaDB for semantic cache")
        client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"))
        collection = client.get_or_create_collection(
            name="semantic_cache",
            metadata={"hnsw:space": "cosine"},
        )
        log.debug("Semantic cache collection ready")
        return collection
    except Exception as exc:
        log.exception("Failed to get/create semantic cache collection")
        raise ChromaError(f"Cache collection error: {exc}") from exc


class SemanticCache:
    """Semantic cache for storing and retrieving RAG answers.
    
    Uses embeddings and similarity search to find cached answers for
    semantically similar questions, reducing redundant LLM calls.
    
    Attributes:
        collection: ChromaDB collection for storing cached entries.
        threshold: Minimum similarity score (0-1) for cache hits.
    """

    def __init__(self, threshold: float = 0.9) -> None:
        """Initialize the semantic cache.
        
        Args:
            threshold: Minimum similarity score for considering a cache hit.
                      Defaults to 0.9 (90% similarity).
        
        Raises:
            ChromaError: If cache collection cannot be initialized.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        self.threshold = threshold
        try:
            self.collection = get_cache_collection()
            log.info(f"SemanticCache initialized (threshold={threshold})")
        except ChromaError:
            raise
        except Exception as exc:
            log.exception("Failed to initialize SemanticCache")
            raise ChromaError(f"Cache initialization failed: {exc}") from exc

    def _tokens(self, text: str) -> set:
        s = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
        words = [w for w in s.split() if w and w not in {
            "the","a","an","and","or","of","to","in","on","for","with","by","how","does","is","are","be","from","this","that","it","as","about"
        }]
        return set(words)

    def lookup(self, question: str) -> Optional[Dict[str, Any]]:
        """Look up a cached answer for a similar question.
        
        Embeds the question and searches for semantically similar cached
        questions. Returns the cached answer if similarity exceeds threshold.
        
        Args:
            question: The question to look up.
        
        Returns:
            Dictionary with 'question', 'answer', and 'similarity' if found,
            otherwise None.
        
        Raises:
            ChromaError: If query execution fails.
        """
        if not question:
            log.debug("Skipping cache lookup for empty question")
            return None
        
        try:
            log.debug(f"Cache lookup for question: {question[:50]}...")
            vec = embed_text(question)
            from typing import Sequence, cast
            results = self.collection.query(
                query_embeddings=[cast(Sequence[float], vec)],
                n_results=1,
            )

            from typing import List, Mapping
            ids: List[List[str]] = cast(List[List[str]], results.get("ids", [[]]) if hasattr(results, "get") else [[]])
            dists: List[List[float]] = cast(List[List[float]], results.get("distances", [[]]) if hasattr(results, "get") else [[]])
            docs: List[List[str]] = cast(List[List[str]], results.get("documents", [[]]) if hasattr(results, "get") else [[]])
            metas: List[List[Mapping[str, Any]]] = cast(List[List[Mapping[str, Any]]], results.get("metadatas", [[]]) if hasattr(results, "get") else [[]])

            if not ids or not ids[0] or not dists or not dists[0]:
                log.debug("No results found in cache")
                return None

            distance = dists[0][0]
            similarity = 1 - distance
            doc = docs[0][0]
            meta: Mapping[str, Any] = metas[0][0]
            answer = meta.get("answer") if hasattr(meta, "get") else None
            refs_json = meta.get("references_json") if hasattr(meta, "get") else None
            cached_references: List[str] = []
            if isinstance(refs_json, str):
                try:
                    cached_references = json.loads(refs_json)
                except Exception:
                    cached_references = []

            toks_q = self._tokens(question)
            toks_doc = self._tokens(doc)
            overlap = 0.0
            if toks_q and toks_doc:
                inter = len(toks_q & toks_doc)
                union = len(toks_q | toks_doc)
                overlap = inter / union

            if similarity >= self.threshold and overlap >= 0.3:
                log.info(f"[CACHE HIT] similarity={similarity:.3f}")
                return {
                    "question": doc,
                    "answer": answer,
                    "references": cached_references,
                    "similarity": similarity,
                }

            log.info(f"[CACHE MISS] best similarity={similarity:.3f}, lexical_overlap={overlap:.3f}")
            return None
        except Exception as exc:
            log.exception("Cache lookup failed")
            raise ChromaError(f"Cache lookup error: {exc}") from exc

    def store(self, question: str, answer: str, references: List[str]) -> None:
        """Store a question-answer pair in the cache.
        
        Embeds the question and stores both the question and answer
        in ChromaDB for future retrieval.
        
        Args:
            question: The question to cache.
            answer: The answer to cache.
        
        Raises:
            ChromaError: If storage operation fails.
        """
        if not question or not answer:
            log.warning("Skipping cache store for empty question or answer")
            return
        
        try:
            log.debug(f"Caching question: {question[:50]}...")
            vec = embed_text(question)
            embeddings: List[Sequence[float]] = [cast(Sequence[float], vec)]
            metadata: Dict[str, Any] = {"answer": answer, "references_json": json.dumps(references)}
            self.collection.upsert(
                ids=[question],
                embeddings=embeddings,
                documents=[question],
                metadatas=[metadata],
            )
            log.info("[CACHE STORE] saved.")
        except Exception as exc:
            log.exception("Cache store failed")
            raise ChromaError(f"Cache store error: {exc}") from exc

    def clear(self) -> None:
        """Clear all entries from the semantic cache.
        
        Removes all cached question-answer pairs from the underlying
        ChromaDB collection.
        
        Raises:
            ChromaError: If the clear operation fails.
        """
        try:
            # Drop and recreate the collection to ensure full clear
            client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"))
            try:
                client.delete_collection("semantic_cache")
            except Exception:
                # If collection does not exist, ignore
                pass
            self.collection = client.get_or_create_collection(
                name="semantic_cache",
                metadata={"hnsw:space": "cosine"},
            )
            log.info("Semantic cache cleared")
        except Exception as exc:
            log.exception("Cache clear failed")
            raise ChromaError(f"Cache clear error: {exc}") from exc


if __name__ == "__main__":
    cache = SemanticCache(threshold=0.9)
    print("Semantic cache ready. Type 'exit' to quit.")

    while True:
        q = input("\nAsk: ").strip()
        if q.lower() in {"exit", "quit", "q"}:
            print("Bye! See u soon :)")
            break

        hit = cache.lookup(q)
        if hit:
            print("\n[Cached answer]")
            print(hit["answer"])
            continue

        # Placeholder: replace this later with GraphRAG answer generation
        answer = f"Generated answer for: {q}"
        cache.store(q, answer, [])
        print("\n[New answer]")
        print(answer)
