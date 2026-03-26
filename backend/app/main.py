import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.storage.db import init_pool, close_pool
from app.api.routes import upload, chat, documents, search, health
from app.websocket.routes import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs(settings.uploads_dir, exist_ok=True)
    await init_pool()
    print(f"Database connected, server ready on port {settings.port}")
    yield
    # Shutdown
    await close_pool()
    print("Database pool closed")


app = FastAPI(title="PDF RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(search.router)

# WebSocket
app.include_router(ws_router)
