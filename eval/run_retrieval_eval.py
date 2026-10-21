#!/usr/bin/env python3
"""Retrieval-precision eval runner.

Runs every question in eval/golden_set.json through the real /api/search
endpoint (unscoped, whole corpus) and records whether the top-1 result came
from the expected document. Writes into the eval_runs/eval_results tables
that already exist in init.sql but nothing writes to yet. This only measures
retrieval -- the generation eval (faithfulness/correctness against the gold
answer) is a separate follow-up script, not this one.

Usage (from the backend venv, so asyncpg is available):
    cd backend && source venv/bin/activate && python3 ../eval/run_retrieval_eval.py

Requires the backend running on :8000 and Postgres reachable.
"""
import asyncio
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:yourpassword@localhost:5438/ragdb"
)
GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
TOP_K = 5

# Mirrors backend/app/config.py's similarity_threshold. Duplicated here
# (rather than importing the app package) so this script has no dependency
# on being run from a particular working directory / sys.path setup.
SIMILARITY_THRESHOLD = 0.25

REGRESSION_DROP_THRESHOLD = 10.0  # percentage points, per knowledge_base_refactor.md


def search(query: str) -> list[dict]:
    body = json.dumps({"query": query, "top_k": TOP_K}).encode()
    req = urllib.request.Request(
        f"{API_URL}/api/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["results"]


def normalize_doc_title(doc_title: str) -> str:
    # vector_search() returns the literal uploaded filename ("X.pdf"), but
    # golden_set.json's expected_source_doc has no extension ("X"). Without
    # this, every comparison silently fails and precision reports 0%.
    return doc_title[:-4] if doc_title.lower().endswith(".pdf") else doc_title


async def main() -> None:
    golden_set = json.loads(GOLDEN_SET_PATH.read_text())

    rows = []
    hits = 0
    print(f"{'id':<28} {'hit':<5} {'page_hit':<9} {'score':<7} question")
    for item in golden_set:
        results = search(item["question"])
        top = results[0] if results else None

        top_doc = normalize_doc_title(top["doc_title"]) if top else None
        hit = top is not None and top_doc == item["expected_source_doc"]
        page_hit = hit and item["expected_page"] in (top.get("page_numbers") or [])
        top_score = top["score"] if top else None
        was_refused = top_score is None or top_score < SIMILARITY_THRESHOLD

        if hit:
            hits += 1

        rows.append(
            {
                "question_id": item["id"],
                "question": item["question"],
                "expected_doc_title": item["expected_source_doc"],
                "retrieved_chunk_ids": [r["id"] for r in results],
                "retrieved_doc_titles": [normalize_doc_title(r["doc_title"]) for r in results],
                "top_similarity_score": top_score,
                "retrieval_hit": hit,
                "was_refused": was_refused,
            }
        )
        print(
            f"{item['id']:<28} {'Y' if hit else 'n':<5} "
            f"{'Y' if page_hit else 'n':<9} {top_score or 0:<7.3f} {item['question'][:60]}"
        )

    total = len(golden_set)
    avg_precision = hits / total if total else 0.0
    print(f"\nretrieval precision: {hits}/{total} = {avg_precision:.1%}")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        prev = await conn.fetchval(
            "SELECT avg_retrieval_precision FROM eval_runs "
            "WHERE avg_retrieval_precision IS NOT NULL "
            "ORDER BY id DESC LIMIT 1"
        )
        regression_detected = (
            prev is not None and (prev - avg_precision) * 100 > REGRESSION_DROP_THRESHOLD
        )
        if regression_detected:
            print(f"REGRESSION: precision dropped from {prev:.1%} to {avg_precision:.1%}")

        # eval_runs.started_at/completed_at are TIMESTAMP (no tz) in init.sql;
        # asyncpg's timestamp codec rejects a tz-aware datetime against that
        # column type, so strip tzinfo after getting the UTC wall-clock time.
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with conn.transaction():
            run_id = await conn.fetchval(
                """INSERT INTO eval_runs
                       (status, trigger, total_questions, completed_questions,
                        avg_retrieval_precision, regression_detected,
                        started_at, completed_at)
                   VALUES ('completed', 'manual', $1, $1, $2, $3, $4, $4)
                   RETURNING id""",
                total,
                avg_precision,
                regression_detected,
                now,
            )
            await conn.executemany(
                """INSERT INTO eval_results
                       (eval_run_id, question_id, question, expected_doc_title,
                        retrieved_chunk_ids, retrieved_doc_titles,
                        top_similarity_score, retrieval_hit, was_refused)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                [
                    (
                        run_id,
                        r["question_id"],
                        r["question"],
                        r["expected_doc_title"],
                        r["retrieved_chunk_ids"],
                        r["retrieved_doc_titles"],
                        r["top_similarity_score"],
                        r["retrieval_hit"],
                        r["was_refused"],
                    )
                    for r in rows
                ],
            )
        print(f"wrote eval_run {run_id} with {total} eval_results rows")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
