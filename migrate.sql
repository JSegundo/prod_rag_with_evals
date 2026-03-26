-- migrate.sql — Run on existing databases to add session + chat support
-- Safe to run multiple times

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sessions') THEN
        CREATE TABLE sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'session_id') THEN
        ALTER TABLE documents ADD COLUMN session_id UUID REFERENCES sessions(id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'share_token') THEN
        ALTER TABLE documents ADD COLUMN share_token VARCHAR(12) UNIQUE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'messages') THEN
        CREATE TABLE messages (
            id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id),
            role VARCHAR(10) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    END IF;
END $$;

-- Backfill share_tokens for existing documents
UPDATE documents SET share_token = substr(md5(random()::text), 1, 8) WHERE share_token IS NULL;
