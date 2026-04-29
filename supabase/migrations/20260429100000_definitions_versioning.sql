-- 20260429100000_definitions_versioning.sql
-- Adiciona suporte a histórico de definições: múltiplas versões por (project_id, item_code).
-- Inserts via chat (fonte_informacao != 'lista_definicoes_inicial') sempre criam nova linha.
-- Inserts via planilha LDP (fonte_informacao = 'lista_definicoes_inicial') continuam idempotentes
-- via partial unique index — UPSERT atualiza a linha inicial sem duplicar.

ALTER TABLE definitions ADD COLUMN IF NOT EXISTS data_informacao DATE;
ALTER TABLE definitions ADD COLUMN IF NOT EXISTS fonte_informacao TEXT;
ALTER TABLE definitions ADD COLUMN IF NOT EXISTS fonte_descricao TEXT;

DO $$
DECLARE
    constraint_name text;
BEGIN
    SELECT conname INTO constraint_name
    FROM pg_constraint
    WHERE conrelid = 'definitions'::regclass
      AND contype = 'u'
      AND pg_get_constraintdef(oid) ILIKE '%(project_id, item_code)%';

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE definitions DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

UPDATE definitions
SET fonte_informacao = 'lista_definicoes_inicial',
    fonte_descricao = 'Ingestão inicial da planilha LDP',
    data_informacao = created_at::date
WHERE fonte_informacao IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uniq_definitions_initial_per_item
    ON definitions (project_id, item_code)
    WHERE fonte_informacao = 'lista_definicoes_inicial';

CREATE INDEX IF NOT EXISTS idx_definitions_project_item_created
    ON definitions (project_id, item_code, created_at DESC);
