"""
Initialize OpenTelemetry tracing and connect it to Arize Phoenix.

Import this module once at application startup (e.g. in api/main.py)
so that the tracer provider is configured before any spans are created.
"""

from __future__ import annotations

import os
from typing import Optional

from opentelemetry import trace
from phoenix.otel import register
from urllib.parse import urlparse
import socket


# You can override these via environment variables if you like.
_DEFAULT_PROJECT_NAME = "rag-app"


# Register Phoenix as the OpenTelemetry backend.
# This sets a global TracerProvider by default so all OTEL instrumentation
# (FastAPI, HTTP, custom spans) will send traces to Phoenix.
_protocol_env = os.getenv("PHOENIX_PROTOCOL")
_endpoint_env = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")

from typing import Optional, Literal

_protocol: Optional[Literal["grpc", "http/protobuf"]] = None
if _protocol_env:
    proto = _protocol_env.lower()
    if proto == "grpc":
        _protocol = "grpc"
    elif proto == "http/protobuf":
        _protocol = "http/protobuf"
    else:
        _protocol = None

_endpoint = _endpoint_env
if not _endpoint:
    if _protocol == "grpc":
        _endpoint = "http://localhost:4317"
    else:
        _endpoint = "http://localhost:6006/v1/traces"

def _can_connect(endpoint: str) -> bool:
    try:
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or (4317 if _protocol == "grpc" else 80)
        with socket.create_connection((host, port), timeout=0.8):
            return True
    except Exception:
        return False

_enabled_env = os.getenv("PHOENIX_ENABLED", "1").lower()
_enabled = _enabled_env not in ("0", "false", "no")

tracer_provider = None
if _enabled and _can_connect(_endpoint):
    tracer_provider = register(
        project_name=os.getenv("PHOENIX_PROJECT_NAME", _DEFAULT_PROJECT_NAME),
        endpoint=_endpoint,
        protocol=_protocol,
        auto_instrument=False,
        batch=False,
    )


def get_tracer(name: Optional[str] = None) -> trace.Tracer:
    """
    Get an OpenTelemetry tracer.

    Use this instead of calling trace.get_tracer() directly so that all
    tracing is consistently configured for Phoenix.

    Example:
        from observability.tracing import get_tracer

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my-span"):
            ...
    """
    tracer_name = name or _DEFAULT_PROJECT_NAME
    return trace.get_tracer(tracer_name)
