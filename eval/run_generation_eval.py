#!/usr/bin/env python3
"""Generation eval runner: faithfulness, relevance, and correctness.

Runs every question in eval/golden_set.json through the real end-to-end
chat flow (global search + LLM generation, no document hint -- see
docs/architecture.md on the chat redesign) and judges the answer two
different ways:
  - faithfulness: is the answer actually grounded in the retrieved context,
    or did it come from outside knowledge?
  - correctness: does it match the known gold answer?
An answer can be faithful but wrong (misread a number out of a messy table),
or correct but unfaithful (the model already "knew" the answer and didn't
need the context) -- that's why both are judged, not just one.

This always creates a FRESH eval_runs row (retrieval + generation together),
never updates eval_run 1 (the retrieval-only run from run_retrieval_eval.py).

Usage (from the backend venv, so asyncpg is available):
    cd backend && source venv/bin/activate && python3 ../eval/run_generation_eval.py

Requires the backend running on :8000 and Postgres reachable.
"""
import asyncio
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

# The LLM-as-judge call reuses the backend's own provider abstraction rather
# than reimplementing an Anthropic/OpenAI call here. Nothing else in this
# script needs backend internals -- retrieval and generation both go through
# the real HTTP endpoints, same as run_retrieval_eval.py.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from app.services.llm.base import LLMMessage  # noqa: E402
from app.services.llm.factory import create_llm_provider  # noqa: E402

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:yourpassword@localhost:5438/ragdb"
)
GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
TOP_K = 5
REGRESSION_DROP_THRESHOLD = 10.0  # percentage points, per knowledge_base_refactor.md

JUDGE_PROMPT = """You are evaluating a RAG system's answer to a question.

Question: {question}

Retrieved context (what the system had available):
{context}

Generated answer: {answer}

Known correct answer (for reference only -- the system never saw this): {expected_answer}

Judge three things and return ONLY a JSON object, no other text:
{{
  "faithful": true/false,
  "faithfulness_score": 0.0-1.0,
  "relevant": true/false,
  "relevance_score": 0.0-1.0,
  "correct": true/false,
  "correctness_score": 0.0-1.0,
  "reasoning": "one or two sentences explaining your judgment"
}}

faithful = is the generated answer grounded in the retrieved context, not made up or pulled from outside knowledge?
relevant = does the generated answer actually address the question asked?
correct = does the generated answer match the substance of the known correct answer (not exact wording)?"""


def post_json(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def normalize_doc_title(doc_title: str) -> str:
    return doc_title[:-4] if doc_title.lower().endswith(".pdf") else doc_title


def build_context(search_results: list[dict]) -> str:
    parts = []
    for i, r in enumerate(search_results, 1):
        parts.append(f"[Source {i} | {r['doc_title']}]:\n{r['text']}")
    return "\n\n".join(parts) if parts else "No relevant documents found."


def parse_judge_response(text: str) -> dict:
    # Judge models sometimes wrap JSON in a markdown fence despite the
    # "return ONLY a JSON object" instruction -- strip it before parsing.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0) if match else text)


async def judge(llm, question: str, context: str, answer: str, expected_answer: str) -> dict:
    prompt = JUDGE_PROMPT.format(
        question=question, context=context, answer=answer, expected_answer=expected_answer
    )
    try:
        raw = await llm.generate([LLMMessage(role="user", content=prompt)], temperature=0.0, max_tokens=300)
        parsed = parse_judge_response(raw)
        return {
            "faithfulness_score": float(parsed.get("faithfulness_score", 0.0)),
            "relevance_score": float(parsed.get("relevance_score", 0.0)),
            "correctness_score": float(parsed.get("correctness_score", 0.0)),
            "reasoning": parsed.get("reasoning", ""),
        }
    except Exception as e:
        return {
            "faithfulness_score": None,
            "relevance_score": None,
            "correctness_score": None,
            "reasoning": f"judge call/parse failed: {e}",
        }


async def main() -> None:
    golden_set = json.loads(GOLDEN_SET_PATH.read_text())
    llm = create_llm_provider()

    rows = []
    retrieval_hits = 0
    refusals = 0
    faithfulness_scores = []
    relevance_scores = []
    correctness_scores = []

    print(f"{'id':<28} {'hit':<5} {'refused':<8} {'faith':<6} {'rel':<6} {'correct':<8} question")
    for item in golden_set:
        search_results = post_json("/api/search", {"query": item["question"], "top_k": TOP_K})["results"]
        top = search_results[0] if search_results else None
        top_doc = normalize_doc_title(top["doc_title"]) if top else None
        retrieval_hit = top is not None and top_doc == item["expected_source_doc"]
        if retrieval_hit:
            retrieval_hits += 1

        chat_response = post_json("/api/chat/chat", {"message": item["question"]})
        was_refused = chat_response.get("wasRefused", False)
        if was_refused:
            refusals += 1

        if was_refused:
            # Nothing was actually answered from context -- skip the judge
            # call rather than scoring a refusal message for faithfulness.
            j = {"faithfulness_score": None, "relevance_score": None, "correctness_score": None,
                 "reasoning": "refused, not judged"}
        else:
            context = build_context(search_results)
            j = await judge(llm, item["question"], context, chat_response["message"], item["expected_answer"])
            if j["faithfulness_score"] is not None:
                faithfulness_scores.append(j["faithfulness_score"])
                relevance_scores.append(j["relevance_score"])
                correctness_scores.append(j["correctness_score"])

        rows.append(
            {
                "question_id": item["id"],
                "question": item["question"],
                "expected_doc_title": item["expected_source_doc"],
                "actual_answer": chat_response.get("message"),
                "retrieved_chunk_ids": [r["id"] for r in search_results],
                "retrieved_doc_titles": [normalize_doc_title(r["doc_title"]) for r in search_results],
                "top_similarity_score": top["score"] if top else None,
                "faithfulness_score": j["faithfulness_score"],
                "relevance_score": j["relevance_score"],
                "correctness_score": j["correctness_score"],
                "retrieval_hit": retrieval_hit,
                "was_refused": was_refused,
                "judge_reasoning": j["reasoning"],
            }
        )

        def fmt(v):
            return f"{v:.2f}" if v is not None else "-"

        print(
            f"{item['id']:<28} {'Y' if retrieval_hit else 'n':<5} {'Y' if was_refused else 'n':<8} "
            f"{fmt(j['faithfulness_score']):<6} {fmt(j['relevance_score']):<6} {fmt(j['correctness_score']):<8} "
            f"{item['question'][:50]}"
        )

    total = len(golden_set)
    avg_retrieval_precision = retrieval_hits / total if total else 0.0
    refusal_rate = refusals / total if total else 0.0
    avg_faithfulness = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else None
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else None
    avg_correctness = sum(correctness_scores) / len(correctness_scores) if correctness_scores else None

    print(f"\nretrieval precision: {retrieval_hits}/{total} = {avg_retrieval_precision:.1%}")
    print(f"refusal rate: {refusals}/{total} = {refusal_rate:.1%}")
    print(f"avg faithfulness: {avg_faithfulness:.2f}" if avg_faithfulness is not None else "avg faithfulness: n/a")
    print(f"avg relevance: {avg_relevance:.2f}" if avg_relevance is not None else "avg relevance: n/a")
    print(f"avg correctness: {avg_correctness:.2f}" if avg_correctness is not None else "avg correctness: n/a")

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        prev = await conn.fetchval(
            "SELECT avg_retrieval_precision FROM eval_runs "
            "WHERE avg_retrieval_precision IS NOT NULL "
            "ORDER BY id DESC LIMIT 1"
        )
        regression_detected = (
            prev is not None and (prev - avg_retrieval_precision) * 100 > REGRESSION_DROP_THRESHOLD
        )
        if regression_detected:
            print(f"REGRESSION: precision dropped from {prev:.1%} to {avg_retrieval_precision:.1%}")

        now = datetime.now(timezone.utc).replace(tzinfo=None)  # eval_runs timestamps are TIMESTAMP (no tz)
        async with conn.transaction():
            run_id = await conn.fetchval(
                """INSERT INTO eval_runs
                       (status, trigger, total_questions, completed_questions,
                        avg_retrieval_precision, avg_faithfulness, avg_relevance,
                        refusal_rate, regression_detected, started_at, completed_at)
                   VALUES ('completed', 'manual', $1, $1, $2, $3, $4, $5, $6, $7, $7)
                   RETURNING id""",
                total,
                avg_retrieval_precision,
                avg_faithfulness,
                avg_relevance,
                refusal_rate,
                regression_detected,
                now,
            )
            await conn.executemany(
                """INSERT INTO eval_results
                       (eval_run_id, question_id, question, expected_doc_title, actual_answer,
                        retrieved_chunk_ids, retrieved_doc_titles, top_similarity_score,
                        faithfulness_score, relevance_score, correctness_score,
                        retrieval_hit, was_refused, judge_reasoning)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)""",
                [
                    (
                        run_id,
                        r["question_id"],
                        r["question"],
                        r["expected_doc_title"],
                        r["actual_answer"],
                        r["retrieved_chunk_ids"],
                        r["retrieved_doc_titles"],
                        r["top_similarity_score"],
                        r["faithfulness_score"],
                        r["relevance_score"],
                        r["correctness_score"],
                        r["retrieval_hit"],
                        r["was_refused"],
                        r["judge_reasoning"],
                    )
                    for r in rows
                ],
            )
        print(f"wrote eval_run {run_id} with {total} eval_results rows")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
