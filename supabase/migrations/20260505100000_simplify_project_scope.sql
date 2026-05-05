-- Simplifica project_scope: remove campos de domínio financeiro/comercial.
--
-- Decisão arquitetural: project_scope deve capturar APENAS o escopo do projeto
-- pra gerar a Lista de Definições. Pontos, pesos, ponto fixo e flags de
-- unificação/essencialidade pertencem ao orçamento (planilha externa) e ao
-- agregado projects.total_contratado — não a essa tabela.
--
-- Idempotente: usa DROP COLUMN IF EXISTS, seguro pra rodar em ambiente já
-- migrado (sem as colunas) ou ainda no estado anterior.
--
-- Ordem de aplicação: rodar APÓS o merge do código que removeu as referências
-- a esses campos (parser, validator, repository, agente Q&A).

ALTER TABLE project_scope DROP COLUMN IF EXISTS unificar;
ALTER TABLE project_scope DROP COLUMN IF EXISTS essencial;
ALTER TABLE project_scope DROP COLUMN IF EXISTS pontos;
ALTER TABLE project_scope DROP COLUMN IF EXISTS peso_disciplina;
ALTER TABLE project_scope DROP COLUMN IF EXISTS ponto_fixo;
ALTER TABLE project_scope DROP COLUMN IF EXISTS pontos_calculados;
