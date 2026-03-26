import json

import numpy as np
from openai import AsyncOpenAI

from app.config import settings
from app.storage.db import get_pool


class TextEmbedder:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def create_embeddings(
        self, chunks: list[dict], filename: str
    ) -> list[dict]:
        if not chunks:
            return []

        pool = get_pool()

        # Create document record
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO documents (filename) VALUES ($1) RETURNING id",
                filename,
            )
            document_id = row["id"]

        # Batch embed all chunks at once
        texts = [chunk["text"] for chunk in chunks]
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )

        embeddings = [item.embedding for item in response.data]

        # Bulk insert chunks
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO chunks (document_id, chunk_text, embedding, page_numbers, metadata)
                VALUES ($1, $2, $3, $4, $5)
                """,
                [
                    (
                        document_id,
                        chunk["text"],
                        np.array(embedding, dtype=np.float32),
                        chunk.get("page_numbers", []),
                        json.dumps(chunk.get("metadata", {})),
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ],
            )

        return [
            {
                "document_id": document_id,
                "text": chunk["text"],
                "page_numbers": chunk.get("page_numbers", []),
            }
            for chunk in chunks
        ]
