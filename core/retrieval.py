# retrieval.py
# retrieval.py
"""Node retrieval system for semantic search in the knowledge graph.

Provides functions to retrieve semantically similar nodes from ChromaDB
based on query embeddings.
"""

from typing import List, Dict, Any
import os
import time

import chromadb
from core.code_exceptions import ChromaError
from config.logger import log
from core.embeddings import embed_text

# Phoenix instrumentation imports
from observability.tracing import trace_span
from observability.rag import record_retrieval_metrics


def get_node_collection() -> chromadb.Collection:
    """Get or create the node embeddings collection in ChromaDB."""
    try:
        log.debug("Connecting to ChromaDB for node retrieval")
        client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"))
        collection = client.get_or_create_collection(
            name="node_embeddings",
            metadata={"hnsw:space": "cosine"},
        )
        log.debug("Node collection ready")
        return collection
    except Exception as exc:
        log.exception("Failed to get/create node collection")
        raise ChromaError(f"Node collection error: {exc}") from exc


# Instrumentation HERE
@trace_span("rag.retrieve")
def retrieve_similar_nodes(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
    """Retrieve the most similar nodes from the knowledge graph."""
    if not query:
        log.warning("Empty query provided for node retrieval")
        return []

    if not isinstance(query, str):
        raise ValueError(f"Query must be a string, got {type(query).__name__}")

    if not 1 <= top_k <= 100:
        raise ValueError("top_k must be between 1 and 100")

    try:
        log.debug(f"Retrieving similar nodes (query: {query[:50]}..., top_k={top_k})")
        t0 = time.perf_counter()

        vec = embed_text(query)
        col = get_node_collection()

        from typing import Sequence, List, Mapping, Any, cast
        query_embeddings: List[Sequence[float]] = [cast(Sequence[float], vec)]
        results = col.query(
            query_embeddings=query_embeddings,
            n_results=top_k,
        )

        nodes: List[Dict[str, Any]] = []
        ids = cast(List[List[str]], results.get("ids", [[]]))[0]
        docs = cast(List[List[str]], results.get("documents", [[]]))[0]
        dists = cast(List[List[float]], results.get("distances", [[]]))[0]
        metas = cast(List[List[Mapping[str, Any]]], results.get("metadatas", [[]]))[0]

        if not ids:
            log.debug("No nodes found for query")
            return []

        for nid, doc, dist, meta in zip(ids, docs, dists, metas):
            similarity = 1 - dist
            nodes.append(
                {
                    "id": nid,
                    "text": doc,
                    "similarity": similarity,
                    "metadata": meta,
                }
            )

        nodes.sort(key=lambda x: x["similarity"], reverse=True)

        # Phoenix retrieval metrics
        retrieval_latency = (time.perf_counter() - t0) * 1000
        record_retrieval_metrics(
            num_candidates=len(ids),
            num_selected=len(nodes),
            retrieval_latency_ms=retrieval_latency,
            avg_score=sum(n["similarity"] for n in nodes) / len(nodes),
        )

        log.info(f"Retrieved {len(nodes)} nodes (best similarity={nodes[0]['similarity']:.3f})")
        log.info(f"Node retrieval took {retrieval_latency/1000:.3f}s")
        return nodes

    except ChromaError:
        raise
    except Exception as exc:
        log.exception("Node retrieval failed")
        raise ChromaError(f"Retrieval error: {exc}") from exc


if __name__ == "__main__":
    q = "How does routing work in this project?"
    nodes = retrieve_similar_nodes(q)

    print("\nTop Retrieved Nodes:")
    for n in nodes:
        print(f"{n['similarity']:.3f} - {n['id']}")
