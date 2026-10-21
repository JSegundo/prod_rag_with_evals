import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.chat_manager import chat_manager
from app.storage.db import execute_query, get_pool

router = APIRouter(prefix="/api/chat")


class ChatRequest(BaseModel):
    message: str


class FeedbackRequest(BaseModel):
    helpful: bool


@router.post("/chat")
async def chat_message(req: ChatRequest, request: Request):
    session_id = getattr(request.state, "session_id", None)
    response = await chat_manager.handle_message(
        message=req.message,
        session_id=session_id,
    )
    return response


@router.get("/history")
async def get_history(request: Request):
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        return {"history": []}

    rows = await execute_query(
        "SELECT role, content, metadata, created_at FROM messages WHERE session_id = $1 ORDER BY created_at ASC",
        [uuid.UUID(session_id)],
    )
    history = []
    for row in rows:
        msg = {
            "role": row["role"],
            "content": row["content"],
            "timestamp": int(row["created_at"].timestamp() * 1000) if row["created_at"] else None,
        }
        # Parse metadata for assistant messages (citations, confidence, etc.)
        if row["metadata"]:
            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            msg.update({
                "citations": metadata.get("citations", []),
                "confidence": metadata.get("confidence"),
                "topScore": metadata.get("topScore"),
                "wasRefused": metadata.get("wasRefused", False),
                "queryLogId": metadata.get("queryLogId"),
            })
        history.append(msg)

    return {"history": history}


@router.patch("/feedback/{query_log_id}")
async def submit_feedback(query_log_id: int, req: FeedbackRequest):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE query_logs SET user_marked_helpful = $1 WHERE id = $2",
            req.helpful, query_log_id,
        )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Query log not found")
    return {"status": "ok"}
