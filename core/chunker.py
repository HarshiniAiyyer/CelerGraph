import os
from pathlib import Path

from tree_sitter import Parser
import warnings

# Suppress FutureWarning from tree_sitter (deprecated Language constructor)
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")
    from tree_sitter_languages import get_language  # type: ignore[import-untyped]

from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb

from core.embeddings import embed_text

# 🔥 Observability
from observability.tracing import trace_span
from opentelemetry import trace as otel_trace

from typing import Optional
from typing import Optional
try:
    # Suppress FutureWarning from tree_sitter (deprecated Language constructor)
    # We filter by message because the module path can be tricky
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning, message=".*Language\\(path, name\\) is deprecated.*")
        PY_LANG = get_language("python")
        
    parser: Optional[Parser] = Parser()
    parser.set_language(PY_LANG)
except Exception as e:
    print(f"Warning: Failed to initialize tree-sitter parser: {e}")
    PY_LANG = None
    parser = None  # runtime fallback when tree-sitter not available

client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"))
collection = client.get_or_create_collection(
    name="code_chunks",
    metadata={"hnsw:space": "cosine"},
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
)


def extract_blocks(code: str) -> list[str]:
    if parser is None:
        return []  # Return empty list if parser not available

    tree = parser.parse(code.encode("utf-8"))
    root = tree.root_node
    blocks: list[str] = []

    def walk(node):
        if node.type in ("function_definition", "class_definition"):
            s, e = node.start_byte, node.end_byte
            blocks.append(code[s:e])
        for child in node.children:
            walk(child)

    walk(root)
    return blocks


@trace_span("rag.chunk.file")
def chunk_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    blocks = extract_blocks(text) or [text]

    chunks: list[str] = []
    for block in blocks:
        if len(block) < 1200:
            chunks.append(block)
        else:
            chunks.extend(splitter.split_text(block))
    return chunks


@trace_span("rag.index.ingest_folder")
def ingest_folder(folder: str):
    root = Path(folder)
    py_files = list(root.rglob("*.py"))
    stored = 0
    indexed_files: set[str] = set()

    # Attach basic indexing stats to current span
    span = otel_trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute("rag.index.num_py_files", len(py_files))
        span.set_attribute("rag.index.root", str(root))

    for file in py_files:
        chunks = chunk_file(file)
        stored_for_file = 0
        for i, chunk in enumerate(chunks):
            cid = f"{file.relative_to(root)}::{i}"
            # Skip empty chunks or failed embeddings to prevent Chroma errors
            if not chunk.strip():
                continue
            vec = embed_text(chunk)
            if not vec:
                continue
            from typing import Sequence, List, cast
            embeddings: List[Sequence[float]] = [cast(Sequence[float], vec)]
            collection.add(
                ids=[cid],
                embeddings=embeddings,
                documents=[chunk],
                metadatas=[{"file": str(file)}],
            )
            stored += 1
            stored_for_file += 1
        if stored_for_file > 0:
            indexed_files.add(str(file))

    # Final indexing metrics on span
    if span and span.is_recording():
        span.set_attribute("rag.index.total_chunks", stored)
        span.set_attribute("rag.index.indexed_files", len(indexed_files))

    print(f"Stored {stored} chunks into code_chunks.")
    return list(indexed_files), stored


if __name__ == "__main__":
    import os
    target_folder = os.getenv("CHUNKER_INPUT_FOLDER", "infos")
    ingest_folder(target_folder)
