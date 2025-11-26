"""
RAG-specific observability helpers.

- `log_rag_event` – log inputs/outputs/contexts as span events.
- `record_retrieval_metrics` – attach retrieval metrics to the current span.
- `record_generation_metrics` – attach generation metrics to the current span.
"""

from .rag_events import log_rag_event
from .rag_metrics import (
    record_retrieval_metrics,
    record_generation_metrics,
)

__all__ = [
    "log_rag_event",
    "record_retrieval_metrics",
    "record_generation_metrics",
]
