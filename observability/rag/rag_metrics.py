"""
Helpers to attach simple RAG metrics as span attributes.

These are not full OTEL metrics; instead they are numeric attributes on
spans that Phoenix can aggregate and visualize.
"""

from __future__ import annotations

from typing import Optional

from opentelemetry import trace


def _safe_set_attribute(key: str, value) -> None:
    span = trace.get_current_span()
    if not span or not span.is_recording():
        return
    span.set_attribute(key, value)


def record_retrieval_metrics(
    *,
    num_candidates: int,
    num_selected: Optional[int] = None,
    retrieval_latency_ms: Optional[float] = None,
    avg_score: Optional[float] = None,
) -> None:
    """
    Attach retrieval-related metrics to the current span.

    Example:
        record_retrieval_metrics(
            num_candidates=len(all_hits),
            num_selected=len(top_k),
            retrieval_latency_ms=12.3,
            avg_score=0.78,
        )
    """
    _safe_set_attribute("rag.retrieval.num_candidates", num_candidates)

    if num_selected is not None:
        _safe_set_attribute("rag.retrieval.num_selected", num_selected)
    if retrieval_latency_ms is not None:
        _safe_set_attribute("rag.retrieval.latency_ms", retrieval_latency_ms)
    if avg_score is not None:
        _safe_set_attribute("rag.retrieval.avg_score", avg_score)


def record_generation_metrics(
    *,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    generation_latency_ms: Optional[float] = None,
) -> None:
    """
    Attach generation-related metrics to the current span.

    Example:
        record_generation_metrics(
            prompt_tokens=120,
            completion_tokens=300,
            generation_latency_ms=850.5,
        )
    """
    if prompt_tokens is not None:
        _safe_set_attribute("rag.generation.prompt_tokens", prompt_tokens)
    if completion_tokens is not None:
        _safe_set_attribute("rag.generation.completion_tokens", completion_tokens)
    if total_tokens is not None:
        _safe_set_attribute("rag.generation.total_tokens", total_tokens)
    if generation_latency_ms is not None:
        _safe_set_attribute("rag.generation.latency_ms", generation_latency_ms)

