-- 0003_chunks_to_legacy_backup.sql
-- Renomeia chunks → chunks_legacy_backup pra liberar espaço pra PGVectorStore
-- criar a nova tabela data_chunks no primeiro async_add(). Não cria tabela nova
-- aqui — o LlamaIndex cuida disso (schema próprio: id bigint, node_id varchar,
-- text, metadata_ jsonb, embedding vector).
-- Indexes, RLS policy e FK são preservados no rename (PostgreSQL renomeia juntos).

ALTER TABLE chunks RENAME TO chunks_legacy_backup;
