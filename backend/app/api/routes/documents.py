from fastapi import APIRouter

from app.storage.db import execute_query

router = APIRouter(prefix="/api")


@router.get("/documents")
async def list_documents():
    rows = await execute_query(
        """SELECT d.id, d.filename, d.created_at,
                  (SELECT count(*) FROM chunks WHERE document_id = d.id) as chunk_count
           FROM documents d
           ORDER BY d.created_at DESC"""
    )

    documents = [
        {
            "id": row["id"],
            "filename": row["filename"],
            "chunkCount": row["chunk_count"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]
    return {"documents": documents, "total": len(documents)}
