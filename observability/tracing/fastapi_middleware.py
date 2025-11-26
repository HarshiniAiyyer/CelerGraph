"""
Helper to instrument your FastAPI app with OpenTelemetry + Phoenix.

Usage in api/main.py:

    from fastapi import FastAPI
    from observability.tracing import instrument_fastapi
    from observability.tracing.tracer import tracer_provider

    app = FastAPI()
    instrument_fastapi(app, tracer_provider=tracer_provider)
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider


def instrument_fastapi(
    app: FastAPI,
    tracer_provider: Optional[TracerProvider] = None,
    excluded_urls: Optional[str] = None,
) -> None:
    """
    Attach OpenTelemetry FastAPI instrumentation to the app.

    - `tracer_provider` should be the one returned by phoenix.otel.register(),
      which we expose as `observability.tracing.tracer.tracer_provider`.
    - `excluded_urls` can be a comma-separated regex string to ignore health checks, etc.
    """
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        excluded_urls=excluded_urls,
    )
