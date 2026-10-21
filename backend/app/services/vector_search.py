import json

import numpy as np
from openai import AsyncOpenAI

from app.config import settings
from app.storage.db import get_pool

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def vector_search(
    query: str,
    document_id: int | None = None,
    top_k: int = 5,
    min_score: float = 0.0,
) -> list[dict]:
    """Perform vector similarity search on stored chunks."""
    client = _get_client()

    # Generate query embedding
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=query,
        dimensions=settings.embedding_dimensions,
    )
    query_embedding = np.array(response.data[0].embedding, dtype=np.float32)

    # Build query with document title join
    if document_id:
        sql = """
            SELECT c.id, c.document_id, c.chunk_text AS text, c.metadata,
                   c.page_numbers, d.filename AS doc_title,
                   1 - (c.embedding <=> $1) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.document_id = $2
            ORDER BY score DESC
            LIMIT $3
        """
        params = [query_embedding, document_id, top_k]
    else:
        sql = """
            SELECT c.id, c.document_id, c.chunk_text AS text, c.metadata,
                   c.page_numbers, d.filename AS doc_title,
                   1 - (c.embedding <=> $1) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            ORDER BY score DESC
            LIMIT $2
        """
        params = [query_embedding, top_k]

    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    results = []
    for row in rows:
        score = float(row["score"])
        if score < min_score:
            continue

        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        elif metadata is None:
            metadata = {}

        results.append({
            "id": row["id"],
            "document_id": row["document_id"],
            "text": row["text"],
            "score": score,
            "page_numbers": list(row["page_numbers"]) if row["page_numbers"] else [],
            "doc_title": row["doc_title"] or "Unknown",
            "section_header": metadata.get("section_header"),
            "metadata": metadata,
        })

    return results
