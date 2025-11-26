# api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from core.ratelimit import RateLimitMiddleware
from observability.tracing import instrument_fastapi
from observability.tracing.tracer import tracer_provider
from observability.logging import get_json_logger
import os

app = FastAPI(
    title="GraphRAG API",
    version="1.0.0",
    description="Hybrid GraphRAG with Neo4j + ChromaDB + Groq",
    contact={
        "name": "GraphRAG Team",
        "url": "https://example.com",
        "email": "support@example.com",
    },
    license_info={
        "name": "Apache-2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0",
    },
    terms_of_service="https://example.com/terms",
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 1,
    },
)
instrument_fastapi(app, tracer_provider=tracer_provider)

logger = get_json_logger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except Exception:
        return default

def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except Exception:
        return default

rate_rules = {
    "/api/chat": (
        _env_int("RATE_LIMIT_CHAT_LIMIT", 5),
        _env_float("RATE_LIMIT_CHAT_WINDOW", 10.0),
    ),
    "/api/chat/stream": (
        _env_int("RATE_LIMIT_STREAM_LIMIT", 5),
        _env_float("RATE_LIMIT_STREAM_WINDOW", 10.0),
    ),
    "/api/index": (
        _env_int("RATE_LIMIT_INDEX_LIMIT", 2),
        _env_float("RATE_LIMIT_INDEX_WINDOW", 60.0),
    ),
    "/api/cache/clear": (
        _env_int("RATE_LIMIT_CACHE_CLEAR_LIMIT", 2),
        _env_float("RATE_LIMIT_CACHE_CLEAR_WINDOW", 60.0),
    ),
    "/api/health": (
        _env_int("RATE_LIMIT_HEALTH_LIMIT", 10),
        _env_float("RATE_LIMIT_HEALTH_WINDOW", 5.0),
    ),
}

app.add_middleware(RateLimitMiddleware, rules=rate_rules)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"message": "GraphRAG API is running"}


# For uvicorn:
# uvicorn api.main:app --reload
