-- Drop `chunks_legacy_backup` — tabela morta desde a migration 0003.
--
-- Histórico: 0001 criou `chunks` pra embeddings; 0003 renomeou pra
-- `chunks_legacy_backup` quando movemos pra `data_chunks` gerenciado pelo
-- LlamaIndex `PGVectorStore` (schema próprio: id bigint, node_id varchar,
-- text, metadata_ jsonb, embedding vector). Backup foi mantido pra resgatar
-- conteúdo se a migração desse errado — não deu, e a tabela tem 133 linhas
-- estagnadas há sprints sem nenhum caller.
--
-- Auditoria de uso (data desta migration):
--   `grep -r chunks_legacy_backup` em apps/ai e apps/api → 0 referências.
--   Apenas as migrations 0001 (CREATE chunks), 0003 (RENAME) e o relatório
--   de drift mencionam o nome. Nenhum SELECT/INSERT/UPDATE em código
--   produtivo.
--
-- Idempotente: DROP TABLE IF EXISTS. Indexes e policy `auth_read_chunks`
-- são removidos junto pelo CASCADE implícito do DROP TABLE.

DROP TABLE IF EXISTS chunks_legacy_backup;
