-- init.sql — KnowledgeBase schema
CREATE EXTENSION IF NOT EXISTS vector;

-- Anonymous sessions (cookie-based)
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename TEXT,
    session_id UUID REFERENCES sessions(id),
    file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chunks table with vector support
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_text TEXT,
    embedding vector(1536),
    page_numbers INTEGER[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Persisted chat messages. document_id is legacy (kept for old rows); chat
-- is global now, so conversations are scoped by session_id instead.
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    session_id UUID REFERENCES sessions(id),
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

-- Query logging (foundation for eval dashboard)
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    session_id UUID REFERENCES sessions(id),
    question TEXT NOT NULL,
    answer TEXT,
    retrieved_chunk_ids INTEGER[],
    retrieved_doc_titles TEXT[],
    top_similarity_score FLOAT,
    confidence_level VARCHAR(10),
    was_refused BOOLEAN DEFAULT FALSE,
    user_marked_helpful BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_logs_created ON query_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_document ON query_logs(document_id);

-- Eval infrastructure
CREATE TABLE IF NOT EXISTS eval_runs (
    id SERIAL PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'pending',
    trigger VARCHAR(20),
    total_questions INTEGER,
    completed_questions INTEGER DEFAULT 0,
    avg_faithfulness FLOAT,
    avg_relevance FLOAT,
    avg_retrieval_precision FLOAT,
    refusal_rate FLOAT,
    regression_detected BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS eval_results (
    id SERIAL PRIMARY KEY,
    eval_run_id INTEGER REFERENCES eval_runs(id) ON DELETE CASCADE,
    question_id VARCHAR(50),
    question TEXT NOT NULL,
    expected_doc_title TEXT,
    actual_answer TEXT,
    retrieved_chunk_ids INTEGER[],
    retrieved_doc_titles TEXT[],
    top_similarity_score FLOAT,
    faithfulness_score FLOAT,
    relevance_score FLOAT,
    correctness_score FLOAT,
    retrieval_hit BOOLEAN,
    was_refused BOOLEAN DEFAULT FALSE,
    judge_reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_eval_results_run ON eval_results(eval_run_id);
