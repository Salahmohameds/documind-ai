-- Migration 002: Drop the IVFFlat index on document_chunks.embedding

DROP INDEX IF EXISTS idx_document_chunks_embedding;
