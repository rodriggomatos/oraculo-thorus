-- 0001_initial_schema.sql
-- Schema inicial do Oráculo Thórus (Fase 1).
-- Espelha exatamente a seção "Schema do banco" do CLAUDE.md.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_number integer UNIQUE NOT NULL,
  name text NOT NULL,
  client text,
  google_sheet_id text,
  status text DEFAULT 'active',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE definitions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  disciplina text,
  tipo text,
  fase text,
  item_code text NOT NULL,
  pergunta text NOT NULL,
  opcao_escolhida text,
  status text,
  custo text,
  observacoes text,
  validado boolean DEFAULT false,
  informacao_auxiliar text,
  apoio_1 text,
  apoio_2 text,
  source_sheet_id text,
  source_row integer,
  raw_data jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE (project_id, item_code)
);

CREATE INDEX definitions_project_idx ON definitions(project_id);
CREATE INDEX definitions_disciplina_idx ON definitions(project_id, disciplina);
CREATE INDEX definitions_validado_idx ON definitions(project_id, validado);

CREATE TABLE chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  source_table text NOT NULL,
  source_row_id uuid NOT NULL,
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  embedding vector(1536),
  created_at timestamptz DEFAULT now()
);

CREATE INDEX chunks_project_idx ON chunks(project_id);
CREATE INDEX chunks_source_idx ON chunks(source_table, source_row_id);
CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "auth_read_projects" ON projects FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_definitions" ON definitions FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_chunks" ON chunks FOR SELECT USING (auth.role() = 'authenticated');
