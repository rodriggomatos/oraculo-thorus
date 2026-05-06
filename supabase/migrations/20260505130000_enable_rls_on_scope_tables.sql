-- Habilita RLS + read policy nas 5 tabelas onde o banco real já tem
-- relrowsecurity=true mas as migrations não documentavam: project_scope,
-- scope_template, ldp_discipline, scope_to_ldp_discipline,
-- source_documents.
--
-- Drift: alguém habilitou RLS direto no SQL Editor mas não criou policies.
-- Como o backend usa SUPABASE_SECRET_KEY (service_role), todas as queries
-- bypassam RLS e funcionam. Mas se um dia frontend acessar via anon/auth
-- role, todas retornam vazio silenciosamente.
--
-- Solução: declarar formalmente em migration o ENABLE RLS + adicionar uma
-- read policy pra `authenticated` (segue a convenção do 0001_initial_schema
-- pra projects/definitions/chunks). Service_role bypassa de qualquer jeito;
-- authenticated ganha leitura. Ninguém perde acesso. Comportamento atual de
-- produção fica preservado e ambiente novo passa a refletir o mesmo.
--
-- Idempotente: ENABLE RLS é seguro re-aplicar; DROP POLICY IF EXISTS antes
-- do CREATE protege.

ALTER TABLE project_scope ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_template ENABLE ROW LEVEL SECURITY;
ALTER TABLE ldp_discipline ENABLE ROW LEVEL SECURITY;
ALTER TABLE scope_to_ldp_discipline ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "auth_read_project_scope" ON project_scope;
CREATE POLICY "auth_read_project_scope"
    ON project_scope FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "auth_read_scope_template" ON scope_template;
CREATE POLICY "auth_read_scope_template"
    ON scope_template FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "auth_read_ldp_discipline" ON ldp_discipline;
CREATE POLICY "auth_read_ldp_discipline"
    ON ldp_discipline FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "auth_read_scope_to_ldp_discipline" ON scope_to_ldp_discipline;
CREATE POLICY "auth_read_scope_to_ldp_discipline"
    ON scope_to_ldp_discipline FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "auth_read_source_documents" ON source_documents;
CREATE POLICY "auth_read_source_documents"
    ON source_documents FOR SELECT
    USING (auth.role() = 'authenticated');
