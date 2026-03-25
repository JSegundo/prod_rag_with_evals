# processing-service/src/api/routes/documents.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
import logging

from storage.db_manager import DatabaseManager, get_db_manager
from ..models.schemas import DocumentListResponse, Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])

@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(db_manager: DatabaseManager = Depends(get_db_manager)):
    """
    List all uploaded documents
    """
    try:
        sql = "SELECT id, filename, created_at FROM documents ORDER BY created_at DESC"
        results = db_manager.execute_query(sql, dict_cursor=True)
        
        documents = []
        for row in results:
            documents.append(
                Document(
                    id=row['id'],
                    filename=row['filename'],
                    created_at=str(row['created_at'])
                )
            )
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents)
        )
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


