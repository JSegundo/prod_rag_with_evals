import json
import logging
import re
import time
import uuid

from app.config import settings
from app.services.llm.base import LLMMessage
from app.services.llm.factory import create_llm_provider
from app.services.vector_search import vector_search
from app.storage.db import execute_query, get_pool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided document context.
Use the context below to answer the user's question. If the context doesn't contain relevant information,
say so honestly rather than making up an answer.

IMPORTANT: Always cite your sources using [Source N] notation when using information from the context.
For example: "The policy requires 30 days notice [Source 1]."

Context from documents:
{context}"""


class ChatManager:
    def __init__(self):
        self.llm = create_llm_provider()

    async def handle_message(
        self, message: str, session_id: str | None = None
    ) -> dict:
        # Store user message in DB
        await self._save_message(session_id, "user", message)

        # Unscoped: searches every document, not just one.
        try:
            search_results = await vector_search(
                query=message, top_k=5, min_score=0.1
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            search_results = []

        # Compute confidence
        top_score = search_results[0]["score"] if search_results else 0.0
        confidence = self._compute_confidence(top_score)
        was_refused = top_score < settings.similarity_threshold

        if was_refused:
            # Hard refusal — do not call LLM
            closest_doc = search_results[0]["doc_title"] if search_results else "unknown"
            response_text = (
                f"I don't have enough information in the document to answer that question. "
                f"The closest match I found was from: \"{closest_doc}\"."
            )
            citations = []
        else:
            # Build context and generate response
            context = self._build_context(search_results)
            system_prompt = SYSTEM_PROMPT.format(context=context)
            messages = [LLMMessage(role="system", content=system_prompt)]

            history = await execute_query(
                "SELECT role, content FROM messages WHERE session_id = $1 ORDER BY created_at DESC LIMIT 11",
                [uuid.UUID(session_id) if session_id else None],
            )
            history = list(reversed(history))[:-1] if len(history) > 1 else []
            for msg in history[-10:]:
                messages.append(LLMMessage(role=msg["role"], content=msg["content"]))

            messages.append(LLMMessage(role="user", content=message))

            response_text = await self.llm.generate(messages)

            # Extract citations from response
            citations = self._extract_citations(response_text, search_results)

        # Log query
        query_log_id = await self._log_query(
            session_id=session_id,
            question=message,
            answer=response_text,
            search_results=search_results,
            top_score=top_score,
            confidence=confidence,
            was_refused=was_refused,
        )

        # Build metadata for assistant message persistence
        msg_metadata = {
            "citations": citations,
            "confidence": confidence,
            "topScore": top_score,
            "wasRefused": was_refused,
            "queryLogId": query_log_id,
        }

        # Store assistant message with metadata
        await self._save_message(session_id, "assistant", response_text, metadata=msg_metadata)

        return {
            "message": response_text,
            "timestamp": int(time.time() * 1000),
            "citations": citations,
            "confidence": confidence,
            "topScore": top_score,
            "wasRefused": was_refused,
            "queryLogId": query_log_id,
        }

    def _compute_confidence(self, top_score: float) -> str:
        if top_score >= settings.confidence_high:
            return "high"
        elif top_score >= settings.confidence_medium:
            return "medium"
        return "low"

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
            label_parts = [f'Source {i}']
            label_parts.append(f'"{result["doc_title"]}"')
            if result.get("page_numbers"):
                pages = ", ".join(str(p) for p in result["page_numbers"])
                label_parts.append(f"Page {pages}")
            if result.get("section_header"):
                label_parts.append(f'Section: {result["section_header"]}')
            label = " | ".join(label_parts)
            parts.append(f"[{label}]:\n{result['text']}")

        return "\n\n".join(parts)

    def _extract_citations(self, response_text: str, search_results: list[dict]) -> list[dict]:
        """Match [Source N] references in the LLM response to search results."""
        # Deduplicate results first (same logic as _build_context)
        seen = set()
        unique = []
        for result in search_results:
            if result["text"] not in seen:
                seen.add(result["text"])
                unique.append(result)

        # Find all [Source N] references
        referenced_indices = set()
        for match in re.finditer(r'\[Source\s+(\d+)\]', response_text):
            referenced_indices.add(int(match.group(1)))

        # If no explicit references, include all sources used in context
        if not referenced_indices:
            referenced_indices = set(range(1, len(unique) + 1))

        citations = []
        for idx in sorted(referenced_indices):
            if 1 <= idx <= len(unique):
                result = unique[idx - 1]
                citations.append({
                    "sourceIndex": idx,
                    "docTitle": result["doc_title"],
                    "pageNumbers": result.get("page_numbers", []),
                    "sectionHeader": result.get("section_header"),
                    "score": round(result["score"], 3),
                })

        return citations

    async def _log_query(
        self,
        session_id: str | None,
        question: str,
        answer: str,
        search_results: list[dict],
        top_score: float,
        confidence: str,
        was_refused: bool,
    ) -> int:
        """Insert into query_logs and return the log ID."""
        pool = get_pool()
        chunk_ids = [r["id"] for r in search_results]
        doc_titles = list({r["doc_title"] for r in search_results})

        async with pool.acquire() as conn:
            # No document_id: a query can span several documents now, so
            # retrieved_doc_titles/retrieved_chunk_ids are the real record.
            row = await conn.fetchrow(
                """INSERT INTO query_logs
                   (session_id, question, answer, retrieved_chunk_ids,
                    retrieved_doc_titles, top_similarity_score, confidence_level, was_refused)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                   RETURNING id""",
                uuid.UUID(session_id) if session_id else None,
                question,
                answer,
                chunk_ids,
                doc_titles,
                top_score,
                confidence,
                was_refused,
            )
        return row["id"]

    async def _save_message(
        self, session_id: str | None, role: str, content: str, metadata: dict | None = None
    ):
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata) VALUES ($1, $2, $3, $4)",
                uuid.UUID(session_id) if session_id else None, role, content,
                json.dumps(metadata) if metadata else None,
            )


chat_manager = ChatManager()
