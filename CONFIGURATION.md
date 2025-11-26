# Configuration Guide

This project uses environment variables to configure backend services and the frontend. Copy `.env.example` to `.env` at the project root and adjust values. For the frontend, place `VITE_*` variables in `frontend/.env` (dev) or `frontend/.env.production` (build).

## Backend Variables

- `GROQ_API_KEY`
  - Purpose: API key for Groq LLM
  - Used in `core/graphrag.py:57`, `config/myapikeys.py:10`
- `LLM_MODEL_NAME`
  - Purpose: Selects LLM model name
  - Default: `openai/gpt-oss-120b`
  - Used in `core/graphrag.py:51`, `config/settings.py:83-87`
- `LLM_TEMPERATURE`
  - Purpose: Generation temperature for the LLM
  - Default: `0.2`
  - Used in `core/graphrag.py:52`, `config/settings.py:84-87`
- `LLM_MAX_TOKENS`
  - Purpose: Max tokens for responses
  - Default: `800`
  - Used in `core/graphrag.py:53`, `config/settings.py:85-87`

- `EMBEDDING_MODEL`
  - Purpose: SentenceTransformer model for embeddings
  - Default: `BAAI/bge-small-en`
  - Used in `config/settings.py:46-49`, `core/embeddings.py:38-41`
- `EMBEDDING_CACHE_SIZE`
  - Purpose: LRU cache size for model instance
  - Default: `1`
  - Used in `config/settings.py:47-49`
- `EMBEDDING_NORMALIZE`
  - Purpose: Normalize embeddings for cosine similarity
  - Default: `true`
  - Used in `config/settings.py:48-49`, `core/embeddings.py:73-76`

- `CHROMA_PATH`
  - Purpose: Filesystem path for ChromaDB persistent client
  - Default: `vectorstore/chroma_db`
  - Used in `config/settings.py:27-32`, `core/graphrag.py:79`, `core/retrieval.py:28`, `core/semantic_cache.py:27`, `core/chunker.py:19`
- `CHROMA_NODE_COLLECTION`
  - Purpose: Collection for graph node embeddings
  - Default: `node_embeddings`
  - Used in `config/settings.py:28-32`, `core/graphrag.py:86-89`, `core/retrieval.py:30-33`
- `CHROMA_CODE_COLLECTION`
  - Purpose: Collection for code chunks
  - Default: `code_chunks`
  - Used in `config/settings.py:29-32`, `core/graphrag.py:81-85`, `core/chunker.py:20-23`
- `CHROMA_CACHE_COLLECTION`
  - Purpose: Collection for semantic cache entries
  - Default: `semantic_cache`
  - Used in `config/settings.py:30-32`, `core/semantic_cache.py:29-33`
- `CHROMA_SIMILARITY_SPACE`
  - Purpose: Similarity metric for HNSW (`cosine` recommended)
  - Default: `cosine`
  - Used in `config/settings.py:31-32`

- `CACHE_THRESHOLD`
  - Purpose: Minimum vector similarity for cache hits
  - Default: `0.9`
  - Used in `config/settings.py:99-100`, `core/semantic_cache.py:50-67`, `core/services.py:186-195`

- `USE_NEO4J`
  - Purpose: Enables Neo4j features (graph expansion/import)
  - Default: `false`
  - Used in `config/settings.py:67-68`, `core/services.py:276-279`, `core/graphrag.py:96-109`
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
  - Purpose: Neo4j connection settings
  - Used in `config/settings.py:64-68`, `config/myapikeys.py:12-14`, `core/services.py:280-293`

## Frontend Variables

- `VITE_API_BASE_URL`
  - Purpose: Base URL for API calls from the frontend
  - Default: `/api`
  - Example in `frontend/.env.production:1`
  - Used in `frontend/src/main.jsx:4`

## Rate Limiting
Configured with `RateLimitMiddleware` and environment variables (`api/main.py:17`):
- Variables (per-IP):
  - `RATE_LIMIT_CHAT_LIMIT`, `RATE_LIMIT_CHAT_WINDOW`
  - `RATE_LIMIT_STREAM_LIMIT`, `RATE_LIMIT_STREAM_WINDOW`
  - `RATE_LIMIT_INDEX_LIMIT`, `RATE_LIMIT_INDEX_WINDOW`
  - `RATE_LIMIT_CACHE_CLEAR_LIMIT`, `RATE_LIMIT_CACHE_CLEAR_WINDOW`
  - `RATE_LIMIT_HEALTH_LIMIT`, `RATE_LIMIT_HEALTH_WINDOW`
- Defaults match `.env.example`.

## Streaming
- Streaming endpoint `POST /api/chat/stream` returns progressive tokens.
- Implemented in `api/controllers.py:106-140` and `core/graphrag.py:461-491`.

## Indexing Behavior
- When ChromaDB `code_chunks` is empty, the server auto-indexes:
  - `data/infos` and available `fastapi`/`starlette` site-packages
  - See `api/controllers.py:25-33`, `api/controllers.py:39-46`, `api/controllers.py:49-56`

## Notes
- Copy `.env.example` → `.env` at the repo root for backend.
- For the frontend, create `frontend/.env` (dev) or use `frontend/.env.production` (build) and set `VITE_API_BASE_URL`.
