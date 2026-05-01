-- 20260429120000_add_source_documents.sql
-- Tabela de documentos-fonte do Document AI + FK opcional em definitions.
-- Idempotência via UNIQUE (project_id, content_hash) — re-rodar mesmo arquivo é no-op.

CREATE TABLE source_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  file_format TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  content_markdown TEXT,
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb,
  CONSTRAINT uniq_source_doc_per_project UNIQUE (project_id, content_hash)
);

CREATE INDEX idx_source_documents_project ON source_documents(project_id);

ALTER TABLE definitions
ADD COLUMN source_document_id UUID REFERENCES source_documents(id) ON DELETE SET NULL;

CREATE INDEX idx_definitions_source_document ON definitions(source_document_id);
