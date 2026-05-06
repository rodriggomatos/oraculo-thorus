-- Recria a policy `auth_read_city` em `city` que ficou faltando no banco
-- real.
--
-- Achado da investigação: a migration 20260504200000_create_city_table.sql
-- contém quatro statements em sequência (CREATE TABLE, CREATE INDEX,
-- ENABLE RLS, DROP+CREATE POLICY). Em produção, os três primeiros foram
-- aplicados via SQL Editor manual mas o bloco de CREATE POLICY ficou de
-- fora — provavelmente o trecho colado parou antes. A tabela existe com
-- RLS=true e a policy ausente.
--
-- Sintoma: como o backend usa service_role (bypassa RLS), nada quebra
-- hoje. Qualquer cliente Supabase autenticado (anon/auth) que tente ler
-- city retorna vazio silenciosamente.
--
-- Esta migration recria a policy seguindo a definição original (SELECT,
-- usando auth.uid() IS NOT NULL — qualquer authenticated lê).
--
-- Nota correlata: as migrations 20260502130000, 20260504100000,
-- 20260504200000, 20260505100000 e 20260505110000 não estão registradas
-- em `supabase_migrations.schema_migrations` (foram aplicadas via Editor
-- ao invés de `supabase migration up`). Reconciliar o tracking é tarefa
-- separada — todas elas são idempotentes (CREATE TABLE IF NOT EXISTS,
-- ADD COLUMN IF NOT EXISTS, DROP COLUMN IF EXISTS), então re-aplicar via
-- CLI seria seguro.
--
-- Idempotente: DROP POLICY IF EXISTS protege re-aplicação.

DROP POLICY IF EXISTS "auth_read_city" ON city;
CREATE POLICY "auth_read_city"
    ON city FOR SELECT
    USING (auth.uid() IS NOT NULL);
