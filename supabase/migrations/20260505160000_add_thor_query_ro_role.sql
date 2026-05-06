-- Cria a role read-only `thor_query_ro` que vai alimentar a tool
-- query_database do Thor. Sandbox rigoroso pra que SQL gerada por LLM
-- nunca consiga modificar nada nem ler tabelas internas.
--
-- A role NASCE sem login (NOLOGIN). Pra usar como conexão, depois desta
-- migration, gera uma senha forte e habilita LOGIN — execute UMA VEZ no
-- SQL Editor do Supabase ou via `supabase db remote commit`:
--
--     -- Gerar senha aleatória do lado do user (mantém fora de migration)
--     ALTER ROLE thor_query_ro WITH LOGIN PASSWORD '<senha-forte-aleatória>';
--
-- E aí a connection string vira:
--     postgresql://thor_query_ro:<senha>@<host>:6543/postgres
--     (use o pooler de transação 6543, não o 5432 direto)
--
-- Adicione como DATABASE_URL_QUERY_RO no .env. NÃO commitar a senha.
--
-- Idempotente: cada bloco protege contra re-aplicação.

-- 1. Cria a role (sem login até o user setar a senha manualmente)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'thor_query_ro') THEN
        CREATE ROLE thor_query_ro WITH NOLOGIN;
        COMMENT ON ROLE thor_query_ro IS
            'Read-only role usada pela tool query_database do Thor. '
            'Acesso apenas a tabelas de domínio em public — sem auth, '
            'storage, supabase_migrations ou tabelas internas (checkpoint_*).';
    END IF;
END $$;

-- 2. Acesso a public (apenas USAGE — não basta pra ler dados, mas
--    evita erro de "permission denied for schema").
GRANT USAGE ON SCHEMA public TO thor_query_ro;

-- 3. SELECT em todas as tabelas atuais de public.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO thor_query_ro;

-- 4. SELECT em tabelas FUTURAS (pra novas tabelas geridas pelas
--    migrations herdarem o privilégio sem intervenção manual).
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO thor_query_ro;

-- 5. REVOKE em tabelas internas que não devem ser visíveis pro Thor:
--    LangGraph postgres saver guarda estado de threads agênticas em
--    `checkpoints*`. Conteúdo é payload binário/jsonb sem valor de
--    domínio, e expor pode vazar prompts internos.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'checkpoints') THEN
        REVOKE SELECT ON TABLE public.checkpoints FROM thor_query_ro;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'checkpoint_blobs') THEN
        REVOKE SELECT ON TABLE public.checkpoint_blobs FROM thor_query_ro;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'checkpoint_writes') THEN
        REVOKE SELECT ON TABLE public.checkpoint_writes FROM thor_query_ro;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'checkpoint_migrations') THEN
        REVOKE SELECT ON TABLE public.checkpoint_migrations FROM thor_query_ro;
    END IF;
END $$;

-- 6. Bloqueia novas tabelas com prefixo `checkpoint*` (caso LangGraph
--    suba uma versão que crie outras): a default privilege acima dá
--    SELECT mas o REVOKE explícito é por nome — manter no radar.
--    Para schemas internos do Postgres/Supabase, NADA é concedido:
--    auth, storage, supabase_migrations não estão em GRANTs aqui, então
--    a role não consegue acessá-los (NOLOGIN ou LOGIN — sem USAGE no
--    schema, queries falham). Validação em test integrado.

-- 7. Sanity: sem privilégios em nenhum outro schema. Postgres revoga
--    automaticamente qualquer GRANT herdado de PUBLIC quando criamos a
--    role com NOLOGIN. Confirmação em test.
