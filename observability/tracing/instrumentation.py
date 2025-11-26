"""
Reusable decorators and helpers for creating spans.

`@trace_span()` on functions like:
- chunking
- embedding
- retrieval
- graph building
"""

from __future__ import annotations

import asyncio
import functools
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .tracer import get_tracer

F = TypeVar("F", bound=Callable[..., Any])


def _set_error_status(exc: BaseException) -> None:
    """Attach error information to the current span."""
    current_span = trace.get_current_span()
    if not current_span or not current_span.is_recording():
        return
    current_span.record_exception(exc)
    current_span.set_status(Status(StatusCode.ERROR, str(exc)))


def trace_span(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Union[str, int, float, bool]]] = None,
) -> Callable[[F], F]:
    """
    Decorator to wrap a function call in a span.

    Works for both sync and async functions.

    Example:
        @trace_span("chunk_documents")
        def chunk_documents(docs): ...

        @trace_span()
        async def embed_nodes(nodes): ...
    """

    def decorator(func: F) -> F:
        span_name = name or func.__qualname__
        tracer = get_tracer(func.__module__)

        is_coroutine = asyncio.iscoroutinefunction(func)

        if not is_coroutine:

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracer.start_as_current_span(span_name) as span:
                    if attributes and span.is_recording():
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    span.set_attribute("code.function", func.__qualname__)
                    span.set_attribute("code.namespace", func.__module__)
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as exc:  # noqa: BLE001
                        _set_error_status(exc)
                        raise

            from typing import cast
            return cast(F, wrapper)

        else:

            @functools.wraps(func)
            async def wrapper_async(*args: Any, **kwargs: Any) -> Any:
                with tracer.start_as_current_span(span_name) as span:
                    if attributes and span.is_recording():
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    span.set_attribute("code.function", func.__qualname__)
                    span.set_attribute("code.namespace", func.__module__)
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    except Exception as exc:  # noqa: BLE001
                        _set_error_status(exc)
                        raise

            from typing import cast
            return cast(F, wrapper_async)

    return decorator


@contextmanager
def traced_block(
    name: str,
    **attrs: Union[str, int, float, bool],
):
    """
    Context manager for ad-hoc traced code blocks.

    Example:
        from observability.tracing import traced_block

        with traced_block("build_kg", repo="fastapi"):
            ...  # any code here
    """
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        if attrs and span.is_recording():
            for key, value in attrs.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:  # noqa: BLE001
            _set_error_status(exc)
            raise
