import asyncio
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.pipeline.processor import get_processor
from app.storage.db import execute_query, get_pool
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin")


# ──────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────


@router.get("/documents")
async def list_all_documents(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List all documents (not session-filtered) with chunk and query counts."""
    offset = (page - 1) * per_page

    rows = await execute_query(
        """SELECT d.id, d.filename, d.file_path, d.created_at,
                  (SELECT count(*) FROM chunks WHERE document_id = d.id) AS chunk_count,
                  (SELECT count(*) FROM query_logs WHERE document_id = d.id) AS query_count
           FROM documents d
           ORDER BY d.created_at DESC
           LIMIT $1 OFFSET $2""",
        [per_page, offset],
    )

    total_row = await execute_query(
        "SELECT count(*) AS total FROM documents", fetch_one=True
    )
    total = total_row["total"]

    return {
        "documents": [
            {
                "id": row["id"],
                "filename": row["filename"],
                "filePath": row["file_path"],
                "hasFile": bool(row["file_path"] and os.path.exists(row["file_path"])),
                "chunkCount": row["chunk_count"],
                "queryCount": row["query_count"],
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "perPage": per_page,
    }


@router.post("/documents/{document_id}/reindex")
async def reindex_document(document_id: int):
    """Delete existing chunks and re-process document from stored file path."""
    row = await execute_query(
        "SELECT id, filename, file_path FROM documents WHERE id = $1",
        [document_id],
        fetch_one=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = row["file_path"]
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=410,
            detail="Original file is no longer available on disk. Re-upload the document.",
        )

    # Delete existing chunks
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM chunks WHERE document_id = $1", document_id)

    # Re-run pipeline (extract → chunk → embed)
    processor = get_processor()
    file_id = f"reindex-{document_id}"

    asyncio.create_task(
        _reindex_pipeline(processor, file_id, file_path, row["filename"], document_id)
    )

    return {
        "status": "reindexing",
        "documentId": document_id,
        "fileId": file_id,
        "message": "Reindexing started. Existing chunks deleted, re-processing in background.",
    }


async def _reindex_pipeline(processor, file_id, file_path, filename, document_id):
    """Run extraction + chunking + embedding for an existing document."""
    try:
        await manager.send_status(file_id, "processing", {"stage": "started"})

        extraction = await asyncio.to_thread(processor.extractor.extract, file_path)
        await manager.send_status(file_id, "processing", {"stage": "extracting"})

        chunks = processor.chunker.chunk(extraction)
        await manager.send_status(file_id, "processing", {"stage": "chunking"})

        # Embed and insert chunks directly (document row already exists)
        await manager.send_status(file_id, "processing", {"stage": "embedding"})
        await _embed_into_existing_document(processor.embedder, chunks, document_id)

        await manager.send_status(file_id, "completed", {"chunkCount": len(chunks)})
        logger.info(f"Reindexed document {document_id}: {len(chunks)} chunks")

    except Exception as e:
        logger.error(f"Reindex failed for document {document_id}: {e}")
        await manager.send_status(file_id, "failed", {"error": str(e)})


async def _embed_into_existing_document(embedder, chunks, document_id):
    """Embed chunks and insert into an existing document (skip document creation)."""
    import json
    import numpy as np

    if not chunks:
        return

    texts = [chunk["text"] for chunk in chunks]
    response = await embedder.client.embeddings.create(
        model=embedder.model, input=texts, dimensions=embedder.dimensions,
    )
    embeddings = [item.embedding for item in response.data]

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO chunks (document_id, chunk_text, embedding, page_numbers, metadata)
               VALUES ($1, $2, $3, $4, $5)""",
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


@router.post("/documents/reindex-all")
async def reindex_all_documents():
    """Reindex all documents that have a valid file_path."""
    rows = await execute_query(
        "SELECT id, filename, file_path FROM documents WHERE file_path IS NOT NULL ORDER BY id"
    )

    eligible = [r for r in rows if r["file_path"] and os.path.exists(r["file_path"])]
    skipped = len(rows) - len(eligible)

    async def _reindex_all():
        for row in eligible:
            processor = get_processor()
            file_id = f"reindex-{row['id']}"
            await _reindex_pipeline(processor, file_id, row["file_path"], row["filename"], row["id"])

    asyncio.create_task(_reindex_all())

    return {
        "status": "reindexing",
        "total": len(eligible),
        "skipped": skipped,
        "message": f"Reindexing {len(eligible)} documents in background. {skipped} skipped (no file on disk).",
    }


# ──────────────────────────────────────────────
# Query Logs
# ──────────────────────────────────────────────


@router.get("/query-logs")
async def list_query_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    refused: Optional[bool] = None,
    unhelpful: Optional[bool] = None,
    search: Optional[str] = None,
):
    """Paginated query logs with optional filters."""
    offset = (page - 1) * per_page
    conditions = []
    params: list = []
    param_idx = 1

    if refused is not None:
        conditions.append(f"ql.was_refused = ${param_idx}")
        params.append(refused)
        param_idx += 1

    if unhelpful is True:
        conditions.append(f"ql.user_marked_helpful = ${param_idx}")
        params.append(False)
        param_idx += 1

    if search:
        conditions.append(f"(ql.question ILIKE ${param_idx} OR ql.answer ILIKE ${param_idx})")
        params.append(f"%{search}%")
        param_idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # Get total count
    count_row = await execute_query(
        f"SELECT count(*) AS total FROM query_logs ql {where}",
        params if params else None,
        fetch_one=True,
    )
    total = count_row["total"]

    # Get rows
    params_with_pagination = params + [per_page, offset]
    rows = await execute_query(
        f"""SELECT ql.id, ql.document_id, ql.question, ql.answer,
                   ql.retrieved_doc_titles, ql.top_similarity_score,
                   ql.confidence_level, ql.was_refused, ql.user_marked_helpful,
                   ql.created_at, d.filename
            FROM query_logs ql
            LEFT JOIN documents d ON d.id = ql.document_id
            {where}
            ORDER BY ql.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}""",
        params_with_pagination,
    )

    return {
        "logs": [
            {
                "id": row["id"],
                "documentId": row["document_id"],
                "documentName": row["filename"],
                "question": row["question"],
                "answer": row["answer"],
                "retrievedDocTitles": row["retrieved_doc_titles"],
                "topScore": row["top_similarity_score"],
                "confidence": row["confidence_level"],
                "wasRefused": row["was_refused"],
                "helpful": row["user_marked_helpful"],
                "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "perPage": per_page,
    }


class FeedbackUpdate(BaseModel):
    helpful: bool


@router.patch("/query-logs/{log_id}/helpful")
async def update_query_feedback(log_id: int, req: FeedbackUpdate):
    """Admin override for query feedback."""
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE query_logs SET user_marked_helpful = $1 WHERE id = $2",
            req.helpful, log_id,
        )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Query log not found")
    return {"status": "ok"}


# ──────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────


@router.get("/stats")
async def get_stats():
    """Summary statistics for the admin dashboard."""
    pool = get_pool()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                (SELECT count(*) FROM documents) AS total_documents,
                (SELECT count(*) FROM chunks) AS total_chunks,
                (SELECT count(*) FROM query_logs) AS total_queries,
                (SELECT count(*) FROM query_logs WHERE was_refused = true) AS refused_queries,
                (SELECT count(*) FROM query_logs WHERE user_marked_helpful = false) AS unhelpful_queries,
                (SELECT avg(top_similarity_score) FROM query_logs) AS avg_similarity
        """)

    total_queries = stats["total_queries"] or 0
    return {
        "totalDocuments": stats["total_documents"],
        "totalChunks": stats["total_chunks"],
        "totalQueries": total_queries,
        "refusedQueries": stats["refused_queries"],
        "unhelpfulQueries": stats["unhelpful_queries"],
        "refusalRate": round(stats["refused_queries"] / total_queries, 3) if total_queries > 0 else 0,
        "avgSimilarity": round(float(stats["avg_similarity"]), 3) if stats["avg_similarity"] else 0,
    }


# ──────────────────────────────────────────────
# Eval
# ──────────────────────────────────────────────
# Read-only: eval/run_*.py scripts write eval_runs/eval_results directly,
# these endpoints just display the latest run. No "trigger a run" endpoint yet.


def _serialize_eval_run(row) -> dict:
    return {
        "id": row["id"],
        "status": row["status"],
        "trigger": row["trigger"],
        "totalQuestions": row["total_questions"],
        "completedQuestions": row["completed_questions"],
        "avgFaithfulness": row["avg_faithfulness"],
        "avgRelevance": row["avg_relevance"],
        "avgRetrievalPrecision": row["avg_retrieval_precision"],
        "refusalRate": row["refusal_rate"],
        "regressionDetected": row["regression_detected"],
        "startedAt": row["started_at"].isoformat() if row["started_at"] else None,
        "completedAt": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


@router.get("/eval/latest")
async def get_latest_eval():
    """Most recent eval run plus its per-question results."""
    run = await execute_query(
        "SELECT * FROM eval_runs ORDER BY id DESC LIMIT 1", fetch_one=True
    )
    if not run:
        return {"run": None, "results": []}

    results = await execute_query(
        """SELECT question_id, question, expected_doc_title, actual_answer,
                  retrieved_doc_titles, top_similarity_score, faithfulness_score,
                  relevance_score, correctness_score, retrieval_hit, was_refused,
                  judge_reasoning
           FROM eval_results WHERE eval_run_id = $1 ORDER BY id""",
        [run["id"]],
    )

    return {
        "run": _serialize_eval_run(run),
        "results": [
            {
                "questionId": r["question_id"],
                "question": r["question"],
                "expectedDocTitle": r["expected_doc_title"],
                "actualAnswer": r["actual_answer"],
                "retrievedDocTitles": r["retrieved_doc_titles"],
                "topSimilarityScore": r["top_similarity_score"],
                "faithfulnessScore": r["faithfulness_score"],
                "relevanceScore": r["relevance_score"],
                "correctnessScore": r["correctness_score"],
                "retrievalHit": r["retrieval_hit"],
                "wasRefused": r["was_refused"],
                "judgeReasoning": r["judge_reasoning"],
            }
            for r in results
        ],
    }


@router.get("/eval/history")
async def get_eval_history(limit: int = Query(20, ge=1, le=100)):
    """Last N eval runs, for a trend line."""
    runs = await execute_query(
        "SELECT * FROM eval_runs ORDER BY id DESC LIMIT $1", [limit]
    )
    return {"runs": [_serialize_eval_run(r) for r in runs]}
