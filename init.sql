CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;


CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    content_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,

    document_id BIGINT NOT NULL
        REFERENCES documents(id)
        ON DELETE CASCADE,

    chunk_index INTEGER NOT NULL,

    content TEXT NOT NULL,

    embedding vector(1536),

    page_number INTEGER,

    section_title TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE INDEX idx_document_chunks_document_id
ON document_chunks (
    document_id
);


CREATE INDEX idx_document_chunks_content_trgm
ON document_chunks
USING gin (
    content gin_trgm_ops
);


CREATE TABLE conversations (
    id UUID PRIMARY KEY,

    created_at TIMESTAMPTZ
        NOT NULL
        DEFAULT NOW(),

    updated_at TIMESTAMPTZ
        NOT NULL
        DEFAULT NOW()
);


CREATE TABLE conversation_messages (
    id BIGSERIAL PRIMARY KEY,

    conversation_id UUID NOT NULL
        REFERENCES conversations(id)
        ON DELETE CASCADE,

    role TEXT NOT NULL
        CHECK (
            role IN (
                'user',
                'assistant'
            )
        ),

    content TEXT NOT NULL,

    metadata JSONB,

    created_at TIMESTAMPTZ
        NOT NULL
        DEFAULT NOW()
);


CREATE INDEX idx_conversation_messages_conversation_id
ON conversation_messages (
    conversation_id
);


CREATE INDEX idx_conversation_messages_created_at
ON conversation_messages (
    created_at
);

