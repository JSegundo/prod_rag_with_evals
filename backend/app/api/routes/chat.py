from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chat_manager import chat_manager

router = APIRouter(prefix="/api/chat")


class ChatRequest(BaseModel):
    message: str
    conversationId: Optional[str] = None


@router.post("/chat")
async def chat_message(req: ChatRequest):
    response = await chat_manager.handle_message(
        message=req.message,
        conversation_id=req.conversationId,
    )
    return response


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str):
    history = chat_manager.get_conversation_history(conversation_id)
    return {"history": history}
