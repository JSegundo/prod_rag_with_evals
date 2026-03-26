from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.chat_manager import chat_manager
from app.storage.db import execute_query

router = APIRouter(prefix="/api/chat")


class ChatRequest(BaseModel):
    message: str
    documentId: Optional[int] = None
    conversationId: Optional[str] = None


@router.post("/chat")
async def chat_message(req: ChatRequest):
    if not req.documentId:
        raise HTTPException(status_code=400, detail="documentId is required")

    response = await chat_manager.handle_message(
        message=req.message,
        document_id=req.documentId,
    )
    return response


@router.get("/history/{document_id}")
async def get_history(document_id: int):
    rows = await execute_query(
        "SELECT role, content, created_at FROM messages WHERE document_id = $1 ORDER BY created_at ASC",
        [document_id],
    )
    return {
        "history": [
            {
                "role": row["role"],
                "content": row["content"],
                "timestamp": int(row["created_at"].timestamp() * 1000) if row["created_at"] else None,
            }
            for row in rows
        ]
    }
