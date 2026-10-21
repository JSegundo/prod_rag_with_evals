#!/usr/bin/env bash
# Uploads every PDF in eval/financebench/pdfs/ to the local backend, one at a
# time. Processing runs as a fire-and-forget background task (see
# backend/app/api/routes/upload.py), so this polls /api/documents after each
# upload and waits for that filename's chunk count to show up before moving
# on -- otherwise all 10 uploads would hit the OpenAI embeddings API at once.
set -euo pipefail

API="${API_URL:-http://localhost:8000}"
DIR="$(cd "$(dirname "$0")/financebench/pdfs" && pwd)"
# /api/documents is scoped to a session cookie, and a plain curl call with no
# cookie jar gets issued a brand-new empty session on every single request --
# so polling it always looked like "0 chunks" even after processing finished,
# and the "already ingested" skip check never matched, causing a duplicate
# upload. /api/admin/documents lists everything with no session filter.
DOCS_URL="$API/api/admin/documents?per_page=100"

for pdf in "$DIR"/*.pdf; do
    name="$(basename "$pdf")"

    # Skip docs a previous (interrupted) run already finished -- re-running
    # this script shouldn't re-upload and duplicate documents that already
    # have chunks.
    existing=$(curl -s "$DOCS_URL" \
        | jq --arg f "$name" '[.documents[] | select(.filename == $f) | .chunkCount] | max // 0')
    if [ "$existing" != "null" ] && [ "$existing" -gt 0 ]; then
        echo "skipping $name (already ingested, $existing chunks)"
        continue
    fi

    echo "uploading $name..."
    # pdfplumber's table extraction on a 100+ page 10-K can take minutes, and
    # it runs CPU-bound in a thread -- under the GIL that can starve this
    # single uvicorn worker's event loop long enough that a curl call made
    # while a PREVIOUS doc is still processing gets a connection/recv error.
    # Retry a few times instead of letting one flaky request kill the batch.
    for attempt in 1 2 3; do
        if curl -sf -X POST "$API/api/document/upload" \
            -F "file=@${pdf};type=application/pdf;filename=${name}" > /dev/null; then
            break
        fi
        echo "  upload attempt $attempt failed, retrying in 10s..."
        sleep 10
    done

    # Large filings take longer than a quick smoke-test timeout would allow,
    # so poll generously (up to ~10 min) rather than giving up early.
    done=0
    for _ in $(seq 1 180); do
        count=$(curl -s "$DOCS_URL" \
            | jq --arg f "$name" '[.documents[] | select(.filename == $f) | .chunkCount] | max // 0')
        if [ "$count" != "null" ] && [ "$count" -gt 0 ]; then
            echo "  done: $count chunks"
            done=1
            break
        fi
        sleep 3
    done
    if [ "$done" -eq 0 ]; then
        echo "  WARNING: $name still has 0 chunks after ~10min, check backend logs"
    fi
done
