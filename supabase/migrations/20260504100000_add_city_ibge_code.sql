-- Adiciona city_ibge_code em projects pra rastrear código IBGE da cidade do form.
-- Distinto da coluna `cidade` (TEXT, nome) — ibge_code é o identificador canônico.
-- Idempotente.

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS city_ibge_code TEXT;

CREATE INDEX IF NOT EXISTS idx_projects_city_ibge_code ON projects(city_ibge_code);
