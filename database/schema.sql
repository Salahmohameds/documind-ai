
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    document_id     TEXT PRIMARY KEY,
    filename        TEXT NOT NULL,
    document_type   TEXT CHECK (document_type IN ('INVOICE', 'CONTRACT', 'UNKNOWN')) DEFAULT 'UNKNOWN',
    status          TEXT CHECK (status IN ('UPLOADED', 'PROCESSING', 'INDEXED', 'FAILED')) DEFAULT 'UPLOADED',
    uploaded_at     TIMESTAMPTZ DEFAULT now(),
    indexed_at      TIMESTAMPTZ
);


CREATE TABLE IF NOT EXISTS document_chunks (
    id              SERIAL PRIMARY KEY,
    chunk_id        TEXT UNIQUE NOT NULL,
    document_id     TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL DEFAULT 0,
    page            INT,
    text            TEXT NOT NULL,
    embedding       VECTOR(384) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);


CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
    ON document_chunks (document_id);


CREATE TABLE IF NOT EXISTS extracted_fields (
    document_id     TEXT PRIMARY KEY REFERENCES documents(document_id) ON DELETE CASCADE,
    fields          JSONB NOT NULL,
    extracted_at    TIMESTAMPTZ DEFAULT now()
);


CREATE TABLE IF NOT EXISTS risk_assessments (
    document_id       TEXT PRIMARY KEY REFERENCES documents(document_id) ON DELETE CASCADE,
    risk_score         INT CHECK (risk_score BETWEEN 0 AND 100),
    financial_risk      TEXT CHECK (financial_risk IN ('Low', 'Medium', 'High')),
    legal_risk           TEXT CHECK (legal_risk IN ('Low', 'Medium', 'High')),
    operational_risk    TEXT CHECK (operational_risk IN ('Low', 'Medium', 'High')),
    risk_reasons        JSONB,
    assessed_at         TIMESTAMPTZ DEFAULT now()
);


