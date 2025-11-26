"""
Tracing utilities for the RAG application.

This package exposes:
- `get_tracer` – central way to get a tracer.
- `trace_span` – decorator/context wrapper for spans.
- `instrument_fastapi` – helper to instrument FastAPI with OTEL.
"""

from .tracer import get_tracer, tracer_provider
from .instrumentation import trace_span, traced_block
from .fastapi_middleware import instrument_fastapi

__all__ = [
    "get_tracer",
    "tracer_provider",
    "trace_span",
    "traced_block",
    "instrument_fastapi",
]
