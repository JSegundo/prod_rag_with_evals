import uuid

from fastapi import APIRouter, HTTPException, Request

from app.storage.db import execute_query

router = APIRouter(prefix="/api")


@router.get("/documents")
async def list_documents(request: Request):
    session_id = getattr(request.state, "session_id", None)
    if session_id:
        rows = await execute_query(
            """SELECT d.id, d.filename, d.share_token, d.created_at,
                      (SELECT count(*) FROM chunks WHERE document_id = d.id) as chunk_count
               FROM documents d
               WHERE d.session_id = $1
               ORDER BY d.created_at DESC""",
            [uuid.UUID(session_id)],
        )
    else:
        rows = await execute_query(
            """SELECT d.id, d.filename, d.share_token, d.created_at,
                      (SELECT count(*) FROM chunks WHERE document_id = d.id) as chunk_count
               FROM documents d
               ORDER BY d.created_at DESC"""
        )

    documents = [
        {
            "id": row["id"],
            "filename": row["filename"],
            "shareToken": row["share_token"],
            "chunkCount": row["chunk_count"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]
    return {"documents": documents, "total": len(documents)}


@router.get("/documents/{share_token}")
async def get_document_by_token(share_token: str):
    row = await execute_query(
        """SELECT d.id, d.filename, d.share_token, d.created_at,
                  (SELECT count(*) FROM chunks WHERE document_id = d.id) as chunk_count
           FROM documents d
           WHERE d.share_token = $1""",
        [share_token],
        fetch_one=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": row["id"],
        "filename": row["filename"],
        "shareToken": row["share_token"],
        "chunkCount": row["chunk_count"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }
