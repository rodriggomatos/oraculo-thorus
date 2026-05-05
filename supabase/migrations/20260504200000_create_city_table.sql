-- Tabela `city` — lista de municípios IBGE armazenada localmente.
-- Substitui o proxy direto pra API IBGE (latência ~1-2s) por SELECT no Supabase.
-- Idempotente.
--
-- IMPORTANTE: a tabela fica VAZIA após a migration. Pra popular:
--   cd apps/ai && uv run python scripts/seed_cities.py
-- Ver apps/api/README.md → "Cities seed".

CREATE TABLE IF NOT EXISTS city (
    ibge_code TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    estado TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_city_estado ON city(estado);
CREATE INDEX IF NOT EXISTS idx_city_nome ON city(nome);

ALTER TABLE city ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth_read_city" ON city;
CREATE POLICY "auth_read_city"
    ON city FOR SELECT
    USING (auth.uid() IS NOT NULL);
