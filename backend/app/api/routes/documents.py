from fastapi import APIRouter

from app.storage.db import execute_query

router = APIRouter(prefix="/api")


@router.get("/documents")
async def list_documents():
    rows = await execute_query(
        "SELECT id, filename, created_at FROM documents ORDER BY created_at DESC"
    )
    documents = [
        {
            "id": row["id"],
            "filename": row["filename"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]
    return {"documents": documents, "total": len(documents)}
