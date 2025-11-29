from api.models import (
    ChatRequest, ChatResponse,
    IndexRequest, IndexResponse,
    HealthResponse, CacheResponse
)
from core.container import get_container
from core.graphrag import answer_question, clear_cache, summarize_question
from core.graphrag import stream_answer
from core.chunker import ingest_folder
import chromadb
import os
import json
from typing import List, Dict
from pathlib import Path

# Phoenix instrumentation
from observability.tracing import trace_span
from observability.rag import log_rag_event, record_generation_metrics


CHAT_HISTORY_PATH = os.getenv("CHAT_HISTORY_PATH", "chat_history.json")


# Chat History Persistence

def load_chat_history() -> List[Dict]:
    if os.path.exists(CHAT_HISTORY_PATH):
        try:
            with open(CHAT_HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_chat_history(history: List[Dict]):
    try:
        with open(CHAT_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f)
    except Exception:
        pass


class ChatHistoryController:
    @trace_span("rag.history.get")
    def get_history(self):
        return load_chat_history()

    @trace_span("rag.history.add")
    def add_history(self, item: Dict):
        # Summarize title if it's the raw question
        title = item.get("title", "")
        # Heuristic: if title is long (> 30 chars) or looks like a question, summarize it
        if len(title) > 30 or "?" in title:
            try:
                summary = summarize_question(title)
                item["title"] = summary
            except Exception:
                pass # Keep original if summarization fails
        
        history = load_chat_history()
        history.append(item)
        save_chat_history(history)
        return item


# Controllers

class ChatController:
    @trace_span("rag.controller.chat")
    async def handle(self, req: ChatRequest) -> ChatResponse:
        """
        Main RAG chat controller.
        Executes:
        - Chroma client & collection setup
        - RAG pipeline via answer_question()
        - Phoenix event & metric logging
        """
        try:
            client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"))
            client.get_or_create_collection(
                name="code_chunks",
                metadata={"hnsw:space": "cosine"},
            )

            # ----- Run RAG pipeline -----
            result = answer_question(
                req.message,
                bypass_cache=req.bypass_cache,
                llm_overrides={
                    "temperature": req.temperature,
                    "max_tokens": req.max_tokens,
                },
            )

            # Safe extraction of response data
            if isinstance(result, dict):
                answer = str(result.get("answer") or "")
                references = result.get("references", [])
                
                prompt_tokens = result.get("prompt_tokens")
                completion_tokens = result.get("completion_tokens")
                total_tokens = result.get("total_tokens")
                latency_ms = result.get("latency_ms")
            else:
                # Handle case where result is a string (error or raw text) or other type
                answer = str(result) if result is not None else ""
                references = []
                prompt_tokens = completion_tokens = total_tokens = latency_ms = None

            # Safe extraction of contexts for logging
            # references can be a list of dicts or a list of strings
            contexts = []
            for r in references:
                if isinstance(r, dict):
                    contexts.append(r.get("text", str(r)))
                else:
                    contexts.append(str(r))

            # ----- Phoenix: log event -----
            log_rag_event(
                name="rag.response",
                query=req.message,
                answer=answer,
                contexts=contexts,
                metadata={
                    "temperature": req.temperature,
                    "max_tokens": req.max_tokens,
                },
            )

            # ----- Phoenix: generation metrics -----
            if prompt_tokens is not None or completion_tokens is not None:
                record_generation_metrics(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    generation_latency_ms=latency_ms,
                )

            return ChatResponse(answer=answer, references=references)

        except Exception as exc:
            import traceback
            traceback.print_exc()
            return ChatResponse(answer=f"Error: {exc}")


class IndexController:
    @trace_span("rag.controller.index")
    async def run(self, req: IndexRequest) -> IndexResponse:
        """
        Takes a folder path, chunk + embed + index its files.
        """
        path = req.path
        indexed_files, chunks = ingest_folder(path)
        return IndexResponse(
            indexed_files=indexed_files,
            chunks_processed=chunks
        )


class HealthController:
    @trace_span("rag.controller.health")
    def status(self) -> HealthResponse:
        """
        Simple health endpoint.
        """
        return HealthResponse(
            status="ok",
            vector_db_status="ready",
            graph_status="connected"
        )


class CacheController:
    @trace_span("rag.controller.cache.clear")
    def clear(self) -> CacheResponse:
        """
        Clears semantic cache.
        """
        try:
            clear_cache()
            return CacheResponse(status="ok", cleared=True)
        except Exception:
            return CacheResponse(status="error", cleared=False)


from starlette.responses import StreamingResponse


class ChatStreamController:
    @trace_span("rag.controller.stream")
    async def handle(self, req: ChatRequest):
        """
        Streaming version of chat controller.
        Sends tokens progressively.
        """
        try:
            client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "vectorstore/chroma_db"))
            client.get_or_create_collection(
                name="code_chunks",
                metadata={"hnsw:space": "cosine"},
            )

            gen = stream_answer(
                req.message,
                bypass_cache=req.bypass_cache,
                llm_overrides={
                    "temperature": req.temperature,
                    "max_tokens": req.max_tokens,
                },
            )

            return StreamingResponse(gen, media_type="text/plain")

        except Exception as exc:
            return StreamingResponse(
                iter([f"Error: {exc}"]),
                media_type="text/plain",
            )
