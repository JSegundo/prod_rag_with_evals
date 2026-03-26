-- init.sql
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
    share_token VARCHAR(12) UNIQUE,
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

-- Create an index for similarity search
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Persisted chat messages
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
