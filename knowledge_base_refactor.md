# KnowledgeBase — Project Spec
## Private RAG Assistant with Evaluation Layer

This document is the internal spec for Claude Code. Read it fully before writing any code or making suggestions. It defines what exists, what needs to be built, and the exact vision for the final product.

---

## What This Project Is

An internal knowledge base assistant that answers questions from a company's documents, cites every source, refuses to guess, and includes an evaluation dashboard proving it works. Built as a portfolio project to win RAG/AI engineering contracts on Upwork and similar platforms.

**The positioning:** Most RAG demos are chat windows over documents. This is different because it includes a Layer 2 — an eval dashboard with retrieval precision, faithfulness scoring, and unanswered question tracking. That eval layer is the differentiator that wins proposals.

---

## What Already Exists

Week 1 and roughly half of Week 2 are implemented at https://github.com/JSegundo/simple-RAG-pdf-chat.

**Already built:**
- PDF ingestion pipeline using Docling for parsing
- Semantic chunking with metadata preservation
- pgvector storage on PostgreSQL
- Basic retrieval (similarity search)
- Claude API integration for generation
- Basic chat endpoint

**Do not rebuild or refactor any of this unless there is a specific bug or architectural conflict with what needs to be added.** Understand the existing implementation first before touching anything.

---

## Stack

- **Ingestion:** Python + Docling (already in use)
- **Storage:** PostgreSQL + pgvector (already in use)
- **Backend:** Python FastAPI (already in use)
- **Frontend:** Next.js — chat UI + admin dashboard (to be built or extended)
- **LLM:** Claude API, model: claude-sonnet-4-6
- **Embeddings:** voyage-3 or text-embedding-3-small (use whatever is already configured)
- **Eval:** RAGAS + LLM-as-judge via Claude API
- **Infra:** AWS Lambda + RDS + S3 (target deployment)

---

## What Needs to Be Built

Everything below is net new. Do not start any of it without first reading the existing codebase.

---

### Layer 1 — Product Features

#### 1.1 Citation injection in responses

Every answer must include inline citations. The current implementation returns answers but citations may not be structured properly.

Required citation format per answer:
- Document title
- Section name (if available in chunk metadata)
- Page number (if available)
- A direct link or reference the user can act on

If the top retrieved chunk similarity score falls below a configurable threshold (start at 0.75, make it an env var), the system must return a hard refusal:

```
"I don't have information on that in the knowledge base. 
The closest document I found was: [doc title]."
```

Do not generate a speculative answer. Do not soften the refusal. Return it and stop.

#### 1.2 Confidence indicator

Each response should include a confidence level derived from the top chunk's similarity score:
- High: score >= 0.85
- Medium: score >= 0.75
- Low: below threshold → triggers refusal

Expose this in the API response and render it visibly in the chat UI.

#### 1.3 Query logging

Every query must be logged to a `query_logs` table with:
- `id`
- `question` (user query text)
- `answer` (generated response)
- `retrieved_doc_ids` (array of chunk IDs used)
- `retrieved_doc_titles` (for readability)
- `top_similarity_score`
- `confidence_level` (high / medium / low)
- `was_refused` (boolean)
- `user_marked_helpful` (boolean, nullable — set via feedback button in UI)
- `created_at`

This table is the foundation for the eval dashboard.

#### 1.4 Google Docs ingestion (optional stretch goal, build last)

If time allows: accept a Google Docs URL, fetch content via Google Docs API, parse, chunk, and store identically to PDFs. Add a re-sync button in the admin panel that re-fetches and re-indexes the document. If this stretches the timeline, skip it — the PDF ingestion is sufficient for the demo.

---

### Layer 1 — Frontend (Next.js)

Build two views: the chat UI and the admin panel.

#### Chat UI

- Clean, functional interface. Not a design showcase — a working product.
- Message thread with user messages and assistant responses
- Each assistant response renders:
  - The answer text
  - Inline citations as clickable chips or footnotes (doc title + section)
  - Confidence badge (High / Medium / Low)
- If the response is a refusal, render it clearly with the closest document name
- Thumbs up / thumbs down feedback button per response — writes to `user_marked_helpful` in query_logs
- No conversation persistence across page reloads (stateless sessions are fine for the demo)

#### Admin Panel

Three tabs:

**Tab 1 — Document Index**
- List of all ingested documents
- Columns: title, file type, chunk count, last indexed date, status
- Upload new document button (PDF/DOCX)
- Re-index button per document
- Re-index all button

**Tab 2 — Query Log**
- Paginated table of all queries
- Columns: question (truncated), confidence, was_refused, helpful (thumbs), date
- Filter by: refused only, unhelpful only, date range
- Clicking a row shows full question + answer + retrieved docs

**Tab 3 — Eval Dashboard**
This is Layer 2. Described in full below.

---

### Layer 2 — Eval Dashboard

This is the most important part of the project from a portfolio perspective. Build it as Tab 3 of the admin panel.

The eval pipeline runs as a background job — not in the request path. Results are stored in an `eval_runs` table and displayed as time-series charts.

#### Golden test set

Create a static JSON file: `eval/golden_set.json`

Format:
```json
[
  {
    "id": "q1",
    "question": "What is the expense reimbursement policy for travel over $500?",
    "expected_source_doc": "expense-policy.pdf",
    "expected_source_section": "Travel Expenses"
  }
]
```

Build 20 questions across the sample SOP corpus (see sample documents section below). These are used for retrieval precision measurement.

#### Eval metrics

**Retrieval precision**
For each question in the golden set, run retrieval and check whether the top-1 chunk comes from the expected source document. Report as a percentage. Run this automatically after every re-index.

**Faithfulness score (LLM-as-judge)**
For each entry in `query_logs` where `was_refused = false`, run an async background job that sends the question, retrieved chunks, and generated answer to Claude with a judge prompt:

```
You are evaluating whether an AI assistant's answer is faithful to the retrieved context.

Question: {question}
Retrieved context: {chunks}
Generated answer: {answer}

Return a JSON object:
{
  "faithful": true/false,
  "reason": "one sentence explanation",
  "score": 0.0-1.0
}
```

Store the result in `eval_results` table linked to the `query_log` entry.

**Answer relevance**
Same LLM-as-judge call, add a second evaluation:
```
Does the answer actually address the question asked, regardless of faithfulness?
{
  "relevant": true/false,
  "score": 0.0-1.0
}
```

**Unanswered question log**
A dedicated section in the eval dashboard showing all queries where `was_refused = true`, grouped by rough topic (use a simple clustering or just list them). This tells a real client exactly what's missing from their knowledge base.

**Regression alerts**
After every re-index, automatically re-run the golden test set. If retrieval precision drops more than 10 percentage points compared to the previous run, log a `regression_alert` and display a banner in the admin panel.

#### Eval dashboard UI

Display as four cards + one table:

1. **Retrieval Precision** — percentage with trend line (last 5 runs)
2. **Faithfulness Score** — average score across last 7 days, color-coded (green >= 0.85, yellow >= 0.70, red below)
3. **Answer Relevance** — same format
4. **Refusal Rate** — % of queries that triggered a refusal (useful signal: too high means knowledge base gaps, too low might mean the threshold is too permissive)
5. **Unanswered Questions table** — list of refused queries, most recent first

All eval jobs run in the background. The UI shows the last computed results with a timestamp and a "Run eval now" button.

---

## Sample Documents

Generate 20-30 realistic but fictional SOP documents for the demo corpus. These should feel like real company documents. No company name — use "Acme Corp" or leave it generic.

Include:
- Employee onboarding guide (multi-section, ~8 pages)
- Expense reimbursement policy (with a table of limits by category)
- Remote work policy
- Engineering deployment checklist (with numbered steps)
- Sales playbook excerpt
- Customer refund and returns policy
- IT security policy
- Code of conduct
- PTO and leave policy
- Vendor onboarding process

**Important:** Include at least 4 documents with tables and multi-column formatting so Docling's parsing superiority over naive text extractors is visible and demonstrable in the demo. This is a key selling point of the stack.

Store sample docs in `/demo-data/` in the repo. Include a `seed.sh` script that ingests all of them in one command for easy demo setup.

---

## Database Schema (net new tables)

```sql
-- Query logging
CREATE TABLE query_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question TEXT NOT NULL,
  answer TEXT,
  retrieved_doc_ids TEXT[],
  retrieved_doc_titles TEXT[],
  top_similarity_score FLOAT,
  confidence_level VARCHAR(10), -- 'high', 'medium', 'low'
  was_refused BOOLEAN DEFAULT FALSE,
  user_marked_helpful BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Eval results per query
CREATE TABLE eval_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_log_id UUID REFERENCES query_logs(id),
  faithful BOOLEAN,
  faithfulness_score FLOAT,
  relevant BOOLEAN,
  relevance_score FLOAT,
  judge_reason TEXT,
  evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Eval runs (golden set + regression tracking)
CREATE TABLE eval_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  triggered_by VARCHAR(50), -- 'reindex', 'manual', 'scheduled'
  retrieval_precision FLOAT,
  avg_faithfulness FLOAT,
  avg_relevance FLOAT,
  refusal_rate FLOAT,
  regression_detected BOOLEAN DEFAULT FALSE,
  run_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Environment Variables

```
ANTHROPIC_API_KEY=
DATABASE_URL=
SIMILARITY_THRESHOLD=0.75
EVAL_JUDGE_MODEL=claude-sonnet-4-6
```

---

## API Endpoints (net new or to be confirmed existing)

```
POST   /api/chat                    # query the KB, returns answer + citations + confidence
POST   /api/documents/upload        # upload and ingest a new document
POST   /api/documents/{id}/reindex  # reindex a specific document
POST   /api/documents/reindex-all   # reindex full corpus
GET    /api/documents               # list all documents with metadata
GET    /api/query-logs              # paginated query log
PATCH  /api/query-logs/{id}/helpful # mark a query as helpful/not helpful
GET    /api/eval/latest             # latest eval run results
POST   /api/eval/run                # trigger a manual eval run
GET    /api/eval/history            # last N eval runs for trend charts
```

---

## How to Demo It Publicly

**Live URL:** `kb.segu.work` (subdomain of existing portfolio)

**What visitors see:**
- The chat UI pre-loaded with the Acme Corp SOP corpus
- A banner: "Built with FastAPI · pgvector · Claude API · Docling · Next.js · AWS serverless"
- A "View Eval Dashboard" button that opens the admin panel in read-only mode (no upload/reindex for public visitors)
- The eval dashboard shows live RAGAS-equivalent scores and the unanswered question log

**The demo flow to walk through in proposals:**
1. Ask a question that's clearly in the corpus — show citation with doc title + section
2. Ask a question with low confidence — show the graceful refusal with closest doc
3. Open the eval dashboard — show retrieval precision %, faithfulness score, refusal rate
4. Show the unanswered question log — explain what this tells a real client

**The README tells the story in this order:**
1. The problem: RAG systems hallucinate and nobody knows until it's in production
2. The solution architecture (diagram)
3. Layer 1 — the product features
4. Layer 2 — the eval layer and why it matters
5. How to run locally with seed data
6. Live demo link

---

## Build Order

Do not jump ahead. Complete each phase before starting the next.

**Phase 1 — Backend completion (chat endpoint hardening)**
- Read existing codebase fully
- Confirm citation metadata is captured in chunks
- Add confidence scoring and refusal logic to chat endpoint
- Add query logging to all chat responses

**Phase 2 — Admin panel backend**
- Document index endpoints
- Query log endpoints
- Feedback (helpful) endpoint

**Phase 3 — Frontend**
- Chat UI with citations, confidence badge, feedback buttons
- Admin panel with Document Index and Query Log tabs

**Phase 4 — Eval layer**
- Golden test set JSON
- LLM-as-judge background job
- Retrieval precision runner
- Regression detection on re-index
- Eval dashboard tab in admin panel

**Phase 5 — Demo polish**
- Sample SOP corpus + seed script
- Public read-only eval dashboard view
- Deploy to AWS
- README

---

## What Not to Do

- Do not use LangChain unless it's already in the existing codebase
- Do not swap out pgvector for Pinecone or any managed vector service
- Do not add features outside this spec without asking
- Do not refactor existing working code unless there is a clear conflict
- Do not use Streamlit or any notebook-based UI
- Do not skip the eval layer — it is the most important part of this project