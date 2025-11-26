"""embed_nodes.py

Embeds all nodes from a JSON knowledge graph into ChromaDB for fast semantic
search. Each node is converted into a text blob, embedded with a sentence
transformer, and stored in the `node_embeddings` collection.
"""

import json
import os

import chromadb
from core.code_exceptions import ChromaError, EmbeddingError
from config.logger import log
from core.embeddings import embed_text


def load_kg(path: str) -> dict:
    """Load the knowledge-graph JSON file.

    Args:
        path: Path to ``knowledge_graph.json``.
    
    Returns:
        Parsed JSON dictionary.
    
    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the JSON is malformed.
    """
    try:
        log.info(f"Loading knowledge graph from {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info("Knowledge graph loaded successfully")
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        log.exception(f"Failed to load knowledge graph from {path}")
        raise


def build_text_blob(node: dict) -> str:
    """Create a searchable text blob from node properties.

    Args:
        node: Node dictionary containing ``id``, ``type`` and ``props``.
    
    Returns:
        Concatenated string of key properties suitable for embedding.
    """
    props = node.get("props", {}) or node.get("properties", {}) or {}
    parts: list[str] = []

    name = props.get("name")
    if name:
        parts.append(f"Name: {name}")

    file_path = props.get("file") or props.get("file_path")
    if file_path:
        parts.append(f"File: {file_path}")

    text = props.get("text")
    if text:
        parts.append(text)

    for k, v in props.items():
        if k in {"name", "file", "file_path", "text"}:
            continue
        parts.append(f"{k}: {v}")

    blob = "\n".join(str(p) for p in parts if p).strip()
    log.debug(f"Built text blob for node {node.get('id', 'unknown')}: {len(blob)} chars")
    return blob


def embed_nodes(kg_path: str, chroma_path: str | None = None) -> None:
    """Embed all nodes from a knowledge graph into ChromaDB.

    Args:
        kg_path: Path to the JSON knowledge-graph file.
        chroma_path: Directory where ChromaDB data is stored.
    
    Raises:
        ChromaError: If ChromaDB operations fail.
        EmbeddingError: If text embedding fails.
    """
    try:
        kg = load_kg(kg_path)
        nodes = kg.get("nodes", [])
        log.info(f"Loaded {len(nodes)} nodes from {kg_path}")

        if not nodes:
            log.warning("No nodes found in knowledge graph")
            return

        # Use environment variable or provided path
        chroma_path = chroma_path or os.getenv("CHROMA_PATH", "vectorstore/chroma_db")
        
        log.info(f"Connecting to ChromaDB at {chroma_path}")
        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_or_create_collection(
            name="node_embeddings",
            metadata={"hnsw:space": "cosine"},
        )
        log.info("ChromaDB collection ready")

        count = 0
        skipped = 0
        
        for node in nodes:
            nid = node.get("id")
            if not nid:
                log.debug("Skipping node without ID")
                skipped += 1
                continue

            blob = build_text_blob(node)
            if not blob:
                log.debug(f"Skipping node {nid}: empty text blob")
                skipped += 1
                continue

            try:
                vec = embed_text(blob)
                if not vec:
                    log.debug(f"Skipping node {nid}: empty embedding")
                    skipped += 1
                    continue
                    
                from typing import Sequence, List, cast
                embeddings: List[Sequence[float]] = [cast(Sequence[float], vec)]
                collection.upsert(
                    ids=[nid],
                    embeddings=embeddings,
                    documents=[blob],
                    metadatas=[{"type": node.get("type", "unknown")}],
                )
                count += 1
                log.debug(f"Embedded node {nid}")
            except EmbeddingError:
                log.warning(f"Failed to embed node {nid}, skipping")
                skipped += 1
                continue

        log.info(f"Embedded {count} nodes into ChromaDB (skipped {skipped})")
        
    except (ChromaError, EmbeddingError):
        raise
    except Exception as exc:
        log.exception("Unexpected error during node embedding")
        raise ChromaError(f"Node embedding failed: {exc}") from exc


if __name__ == "__main__":
    try:
        kg_path = os.getenv("KG_JSON_PATH", "graph_indexing/knowledge_graph.json")
        embed_nodes(kg_path)
        log.info("Node embedding process completed successfully")
    except (ChromaError, EmbeddingError):
        log.error("Node embedding process failed")
        raise SystemExit(1)
    except Exception:
        log.exception("Unexpected error during node embedding")
        raise SystemExit(1)

