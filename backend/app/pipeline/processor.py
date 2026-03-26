import asyncio
import logging

from app.config import settings
from app.pipeline.extractor import create_extractor
from app.pipeline.chunker import TextChunker
from app.pipeline.embedder import TextEmbedder
from app.websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)

_processor = None


class DocumentProcessor:
    def __init__(self):
        self.extractor = create_extractor(settings.extractor)
        self.chunker = TextChunker()
        self.embedder = TextEmbedder()

    async def process_document(
        self,
        file_id: str,
        file_path: str,
        filename: str,
        ws_manager: ConnectionManager,
    ) -> dict:
        try:
            await ws_manager.send_status(file_id, "processing", {"stage": "started"})

            # Extract (CPU-bound, run in thread)
            await ws_manager.send_status(file_id, "processing", {"stage": "extracting"})
            extraction = await asyncio.to_thread(self.extractor.extract, file_path)
            logger.info(f"Extracted {len(extraction.pages)} pages from {filename}")

            # Chunk
            await ws_manager.send_status(file_id, "processing", {"stage": "chunking"})
            chunks = self.chunker.chunk(extraction)
            logger.info(f"Created {len(chunks)} chunks from {filename}")

            # Embed + store
            await ws_manager.send_status(file_id, "processing", {"stage": "embedding"})
            await self.embedder.create_embeddings(chunks, filename)
            logger.info(f"Stored {len(chunks)} embeddings for {filename}")

            await ws_manager.send_status(
                file_id, "completed", {"chunkCount": len(chunks)}
            )

            return {
                "status": "success",
                "document_info": {
                    "filename": filename,
                    "num_pages": len(extraction.pages),
                    "num_chunks": len(chunks),
                },
            }

        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            await ws_manager.send_status(
                file_id, "failed", {"error": str(e)}
            )
            return {"status": "failed", "error": str(e)}


def get_processor() -> DocumentProcessor:
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
