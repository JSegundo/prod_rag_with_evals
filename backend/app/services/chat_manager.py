import logging
import time
from uuid import uuid4

from app.services.llm.base import LLMMessage

logger = logging.getLogger(__name__)
from app.services.llm.factory import create_llm_provider
from app.services.vector_search import vector_search


SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided document context.
Use the context below to answer the user's question. If the context doesn't contain relevant information,
say so honestly rather than making up an answer.

Context from documents:
{context}

Previous conversation:
{history}"""


class ChatManager:
    def __init__(self):
        self.message_history: dict[str, list[dict]] = {}
        self.llm = create_llm_provider()

    async def handle_message(
        self, message: str, conversation_id: str | None = None
    ) -> dict:
        if not conversation_id:
            conversation_id = str(uuid4())

        # Store user message
        self._add_message(conversation_id, "user", message)

        # Vector search for relevant context
        try:
            search_results = await vector_search(
                query=message, top_k=5, min_score=0.2
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            search_results = []

        # Build context
        context = self._build_context(search_results)
        history = self._build_history(conversation_id)

        # Generate response
        system_prompt = SYSTEM_PROMPT.format(context=context, history=history)
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=message),
        ]

        response_text = await self.llm.generate(messages)

        # Store assistant message
        self._add_message(conversation_id, "assistant", response_text)

        return {
            "message": response_text,
            "conversationId": conversation_id,
            "timestamp": int(time.time() * 1000),
        }

    def get_conversation_history(self, conversation_id: str) -> list[dict]:
        return self.message_history.get(conversation_id, [])

    def _add_message(self, conversation_id: str, role: str, content: str):
        if conversation_id not in self.message_history:
            self.message_history[conversation_id] = []
        self.message_history[conversation_id].append({
            "role": role,
            "content": content,
            "timestamp": int(time.time() * 1000),
        })

    def _build_context(self, search_results: list[dict]) -> str:
        if not search_results:
            return "No relevant documents found."

        # Deduplicate by text
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

    def _build_history(self, conversation_id: str) -> str:
        messages = self.message_history.get(conversation_id, [])
        # Last 3 messages (excluding the current one we just added)
        recent = messages[-4:-1] if len(messages) > 1 else []
        if not recent:
            return "No previous conversation."

        parts = []
        for msg in recent:
            role = msg["role"].capitalize()
            parts.append(f"{role}: {msg['content']}")

        return "\n".join(parts)


chat_manager = ChatManager()
