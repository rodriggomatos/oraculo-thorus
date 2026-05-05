-- Simplifica projects: remove campos que não pertencem ao escopo da feature
-- create_project. Esses dados (área, fluxo, custo, total contratado, margem)
-- ou ficam na planilha de orçamento ou são domínio comercial — não são
-- responsabilidade da tabela projects, que existe pra capturar identidade
-- do projeto (cliente, empreendimento, cidade, estado, ldp/orcamento sheets,
-- pasta no Drive). Estado continua existindo (vem do form do user).
--
-- Idempotente: usa DROP COLUMN IF EXISTS, seguro pra rodar em ambiente já
-- migrado ou no estado anterior.
--
-- Ordem de aplicação: rodar APÓS o merge do código que removeu as referências
-- (parser, validator, repository, endpoint, agente Q&A, frontend).

ALTER TABLE projects DROP COLUMN IF EXISTS area_m2;
ALTER TABLE projects DROP COLUMN IF EXISTS fluxo;
ALTER TABLE projects DROP COLUMN IF EXISTS custo_fator;
ALTER TABLE projects DROP COLUMN IF EXISTS total_contratado;
ALTER TABLE projects DROP COLUMN IF EXISTS margem;
