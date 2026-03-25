# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands

```bash
# Development (Docker-first, all services with hot reload)
npm run dev

# Production
npm run build && npm start

# Stop all services
npm stop

# View logs
npm run logs

# Run individual services outside Docker
cd client && npm run dev          # Next.js on port 3500 (Turbopack)
cd server && npm run dev          # Express on port 3000 (ts-node-dev)
cd processing-service && python src/main.py  # FastAPI on port 8000

# Server tests
cd server && npm test

# Server build check
cd server && npm run build

# Client lint
cd client && npm run lint

# Connect to database
docker exec -it pdf_chat_rag-postgres-1 psql -U postgres -d ragdb
```

## Architecture

This is a **PDF Retrieval-Augmented Generation (RAG)** system with three services communicating via RabbitMQ and HTTP:

**Client** (Next.js 15 / React 19 / Tailwind) -- port 3500
- PDF upload via react-dropzone, real-time processing status via WebSocket
- Chat UI for querying uploaded documents

**Server** (Express / TypeScript / Node 21) -- port 3000
- Orchestrates uploads, chat, and WebSocket connections
- `ChatManager` handles RAG flow: vector search -> context building -> LLM generation (Anthropic or OpenAI)
- `QueueService` publishes document processing jobs to RabbitMQ
- WebSocket server manages per-fileId connections with pending message queues and grace periods

**Processing Service** (FastAPI / Python 3.11) -- port 8000
- Consumes RabbitMQ jobs and runs the pipeline: Docling extraction -> chunking -> OpenAI embedding (1536-dim) -> PostgreSQL storage
- Exposes `/api/search` for vector similarity search and `/api/documents` for listing
- Notifies the server on completion via HTTP callback

**Infrastructure**
- PostgreSQL + pgvector (port 5438): stores documents and chunks with IVFFlat cosine similarity index
- RabbitMQ (port 5672, management on 15672): async document processing queue
- PgAdmin (port 5050): database admin UI

## Key Data Flow

1. **Upload**: Client -> `POST /api/document/upload` -> Server saves file + publishes RabbitMQ message
2. **Process**: Processing service consumes message -> extract -> chunk -> embed -> store in PostgreSQL -> notify server
3. **Status**: Server pushes WebSocket updates to client per fileId
4. **Chat**: Client -> `POST /api/chat/chat` -> Server queries processing service for vector search -> builds context with conversation history -> LLM generates response

## Important Implementation Details

- Chat history is **in-memory only** (not persisted to database) in `ChatManager`
- The processing service has a **7GB memory limit** in docker-compose due to Docling model requirements (~6.5GB)
- Server uses path alias `@/*` -> `./src/*` (tsconfig)
- Client uses path alias `@/*` -> `./src/*` (tsconfig)
- Processing service Python deps are split into `requirements/base.txt` and `requirements/heavy.txt` for Docker layer caching
- WebSocket connections are managed by fileId with a 60s grace period after disconnect
- Service-to-service auth uses `INTERNAL_API_KEY` environment variable
- Database schema is initialized via `init.sql` (pgvector extension, documents + chunks tables)
- Environment variables are configured in `.env` at root (API keys, database credentials, RabbitMQ URL)
