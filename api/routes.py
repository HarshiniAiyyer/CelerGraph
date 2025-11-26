from fastapi import APIRouter, Body
from api.models import (
    ChatRequest, ChatResponse,
    IndexRequest, IndexResponse,
    HealthResponse, CacheResponse
)
from api.controllers import ChatController, IndexController, HealthController, CacheController
from api.controllers import ChatStreamController, ChatHistoryController

# 🔥 Phoenix instrumentation
from observability.tracing import trace_span

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat (RAG)",
    description="Generate an answer grounded in code chunks and knowledge graph nodes.",
    tags=["Chat"],
)
@trace_span("api.chat")
async def chat_endpoint(
    req: ChatRequest = Body(
        ..., 
        openapi_examples={
            "basic": {
                "summary": "Basic question",
                "value": {
                    "message": "How does routing work?",
                    "max_tokens": 800,
                    "temperature": 0.2,
                    "bypass_cache": false
                },
            },
            "bypassCache": {
                "summary": "Bypass cache",
                "value": {
                    "message": "Explain semantic cache logic",
                    "bypass_cache": true
                },
            },
        },
    )
):
    return await ChatController().handle(req)


@router.post(
    "/index",
    response_model=IndexResponse,
    summary="Index folder",
    description="Chunk + embed Python files under a folder into ChromaDB collections.",
    tags=["Indexing"],
)
@trace_span("api.index")
async def index_endpoint(
    req: IndexRequest = Body(
        ...,
        openapi_examples={
            "default": {
                "summary": "Index infos folder",
                "value": {
                    "path": "infos",
                    "rebuild": false
                },
            }
        },
    )
):
    return await IndexController().run(req)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health",
    description="Service health and readiness.",
    tags=["Health"],
)
@trace_span("api.health")
async def health_endpoint():
    return HealthController().status()


@router.post(
    "/cache/clear",
    response_model=CacheResponse,
    summary="Clear semantic cache",
    description="Deletes all entries from the semantic cache collection.",
    tags=["Cache"],
)
@trace_span("api.cache.clear")
async def cache_clear_endpoint():
    return CacheController().clear()


@router.post(
    "/chat/stream",
    summary="Chat (stream)",
    description="Streams the RAG answer incrementally over the response body.",
    tags=["Streaming"],
)
@trace_span("api.chat.stream")
async def chat_stream_endpoint(
    req: ChatRequest = Body(
        ...,
        openapi_examples={
            "stream": {
                "summary": "Streamed chat",
                "value": {
                    "message": "Walk me through the GraphRAG pipeline",
                    "max_tokens": 1200
                },
            }
        },
    )
):
    return await ChatStreamController().handle(req)


@router.get(
    "/history",
    summary="Get chat history",
    description="Returns persisted chat history items.",
    tags=["History"],
)
@trace_span("api.history.get")
def get_chat_history():
    return ChatHistoryController().get_history()


@router.post(
    "/history",
    summary="Add chat history item",
    description="Persists a chat history entry.",
    tags=["History"],
)
@trace_span("api.history.add")
def add_chat_history(item: dict):
    return ChatHistoryController().add_history(item)

