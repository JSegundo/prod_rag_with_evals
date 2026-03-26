import logging
import time

from app.services.llm.base import LLMMessage
from app.services.llm.factory import create_llm_provider
from app.services.vector_search import vector_search
from app.storage.db import execute_query, get_pool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided document context.
Use the context below to answer the user's question. If the context doesn't contain relevant information,
say so honestly rather than making up an answer.

Context from documents:
{context}"""


class ChatManager:
    def __init__(self):
        self.llm = create_llm_provider()

    async def handle_message(self, message: str, document_id: int) -> dict:
        # Store user message in DB
        await self._save_message(document_id, "user", message)

        # Vector search scoped to this document
        try:
            search_results = await vector_search(
                query=message, document_id=document_id, top_k=5, min_score=0.2
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            search_results = []

        # Build context
        context = self._build_context(search_results)

        # Build messages with real conversation history from DB
        system_prompt = SYSTEM_PROMPT.format(context=context)
        messages = [LLMMessage(role="system", content=system_prompt)]

        # Load last 10 messages from DB (excluding the one we just inserted)
        history = await execute_query(
            "SELECT role, content FROM messages WHERE document_id = $1 ORDER BY created_at DESC LIMIT 11",
            [document_id],
        )
        # Reverse to chronological, skip the current message (first in DESC order)
        history = list(reversed(history))[:-1] if len(history) > 1 else []
        for msg in history[-10:]:
            messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

        messages.append(LLMMessage(role="user", content=message))

        response_text = await self.llm.generate(messages)

        # Store assistant message in DB
        await self._save_message(document_id, "assistant", response_text)

        return {
            "message": response_text,
            "documentId": document_id,
            "timestamp": int(time.time() * 1000),
        }

    async def _save_message(self, document_id: int, role: str, content: str):
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages (document_id, role, content) VALUES ($1, $2, $3)",
                document_id, role, content,
            )

    def _build_context(self, search_results: list[dict]) -> str:
        if not search_results:
            return "No relevant documents found."

        seen = set()
        unique = []
        for result in search_results:
            if result["text"] not in seen:
                seen.add(result["text"])
                unique.append(result)

        parts = []
        for i, result in enumerate(unique, 1):
            score = result.get("score", 0)
            parts.append(f"[Source {i} (relevance: {score:.2f})]:\n{result['text']}")

        return "\n\n".join(parts)


chat_manager = ChatManager()
