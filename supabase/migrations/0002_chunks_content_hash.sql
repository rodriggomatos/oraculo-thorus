-- 0002_chunks_content_hash.sql
-- Adiciona content_hash em chunks pra detectar mudanças no conteúdo do
-- source row e evitar regenerar embeddings quando nada mudou.

ALTER TABLE chunks
  ADD COLUMN content_hash text;

CREATE INDEX chunks_content_hash_idx ON chunks(content_hash);
