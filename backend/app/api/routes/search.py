import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.vector_search import vector_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


class SearchRequest(BaseModel):
    query: str
    document_id: Optional[int] = None
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


@router.post("/search")
async def search_documents(req: SearchRequest):
    try:
        results = await vector_search(
            query=req.query,
            document_id=req.document_id,
            top_k=req.top_k,
            min_score=req.min_score,
        )
        return {"results": results, "query": req.query, "total": len(results)}
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
