# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Start postgres (only infrastructure dependency)
docker compose up -d

# First time setup (create venv + install deps)
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Run backend (FastAPI on port 8000)
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Run client (Next.js on port 3500)
cd client && npm run dev

# Stop postgres
docker compose down

# Client lint
cd client && npm run lint

# Connect to database
docker exec -it pdf-rag-postgres-1 psql -U postgres -d ragdb
```

## Architecture

This is a **PDF Retrieval-Augmented Generation (RAG)** system with two services:

**Client** (Next.js 15 / React 19 / Tailwind) -- port 3500
- PDF upload via react-dropzone, real-time processing status via WebSocket
- Chat UI for querying uploaded documents
- API URLs configured via `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` env vars

**Backend** (FastAPI / Python 3.11) -- port 8000
- Single backend handling uploads, processing, chat/RAG, and WebSocket status
- `ChatManager` handles RAG flow: vector search -> context building -> LLM generation (Anthropic or OpenAI)
- Processing pipeline: pdfplumber extraction -> tiktoken chunking -> OpenAI embedding (1536-dim) -> pgvector storage
- WebSocket manager sends per-fileId processing status updates
- Background processing via `asyncio.create_task` (no message queue needed)
- Pluggable PDF extractor: pdfplumber (default, lightweight) or Docling (optional, heavy)

**Infrastructure**
- PostgreSQL + pgvector (port 5438): stores documents and chunks with IVFFlat cosine similarity index
- That's it. No RabbitMQ, no PgAdmin, no separate services.

## Key Data Flow

1. **Upload**: Client -> `POST /api/document/upload` -> Backend saves file + starts background processing task
2. **Process**: Extract text (pdfplumber) -> chunk (tiktoken) -> embed (OpenAI) -> store in PostgreSQL
3. **Status**: Backend pushes WebSocket updates to client per fileId at `/ws/status/{fileId}`
4. **Chat**: Client -> `POST /api/chat/chat` -> Backend does vector search -> builds context with conversation history -> LLM generates response

## Important Implementation Details

- Chat history is **in-memory only** (not persisted to database) in `ChatManager`
- Client uses path alias `@/*` -> `./src/*` (tsconfig)
- Backend uses asyncpg for async database access with pgvector support
- LLM provider is configurable via `LLM_PROVIDER` env var (anthropic or openai)
- PDF extractor is configurable via `EXTRACTOR` env var (pdfplumber or docling)
- Database schema is initialized via `init.sql` (pgvector extension, documents + chunks tables)
- Environment variables are configured in `.env` at root (see `.env.example`)

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app, lifespan, CORS
    config.py            # pydantic-settings configuration
    api/routes/          # REST endpoints (upload, chat, search, documents, health)
    websocket/           # WebSocket connection manager and routes
    services/            # ChatManager, LLM providers, vector search
    pipeline/            # Document processing (extractor, chunker, embedder, processor)
    storage/             # asyncpg database layer
client/                  # Next.js frontend
docker-compose.yml       # Just postgres
init.sql                 # Database schema
```
