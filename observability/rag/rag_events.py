"""
Helpers for logging high-level RAG events to the current span.

Phoenix will surface these events in the trace timeline so you can
inspect query, retrieved contexts, and generated answer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from opentelemetry import trace


def log_rag_event(
    *,
    name: str,
    query: str,
    answer: Optional[str] = None,
    contexts: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a RAG event on the current span.

    Call this once per user query, after you retrieve contexts and
    generate the answer.

    Example:
        log_rag_event(
            name="rag.response",
            query=user_query,
            answer=final_answer,
            contexts=[c.text for c in retrieved_nodes],
            metadata={"model": "gpt-4.1-mini"},
        )
    """
    current_span = trace.get_current_span()
    if not current_span or not current_span.is_recording():
        return

    attributes: Dict[str, Any] = {
        "rag.query": query,
        "rag.answer": answer,
        "rag.num_contexts": len(contexts) if contexts is not None else 0,
    }

    if contexts is not None:
        # Truncate if needed in your own code; this keeps it simple here.
        attributes["rag.contexts"] = contexts

    if metadata:
        for key, value in metadata.items():
            # Namespace metadata under rag.metadata.*
            attributes[f"rag.metadata.{key}"] = value

    current_span.add_event(name, attributes=attributes)
