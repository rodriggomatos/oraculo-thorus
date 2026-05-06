-- Reconcilia o CHECK de `projects.estado` e adiciona o CHECK de
-- `city.estado` pra ambos aceitarem as 27 UFs brasileiras (26 estados + DF).
--
-- Drift original: a migration 20260502130000 criou `projects_estado_check`
-- restrito a 7 UFs (SC, PR, MG, SP, RS, RO, ES); em produção alguém
-- expandiu manualmente pra 27 via SQL Editor — banco aceita qualquer UF, mas
-- ambiente novo (CI / dev local) que rodasse só as migrations criaria a
-- versão restrita e quebraria seeds com projetos em outras UFs. Esta
-- migration formaliza a decisão de aceitar todas.
--
-- Para `city.estado` o CHECK só existe no banco (também aplicado direto no
-- Editor). Adicionamos aqui pra documentar a constraint que já protege a
-- tabela hoje.
--
-- Idempotente: DROP CONSTRAINT IF EXISTS antes de cada ADD; pode rodar
-- múltiplas vezes sem erro.

ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_estado_check;
ALTER TABLE projects
    ADD CONSTRAINT projects_estado_check
    CHECK (
        estado IS NULL
        OR estado = ANY (
            ARRAY[
                'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA',
                'MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN',
                'RS','RO','RR','SC','SP','SE','TO'
            ]
        )
    );

ALTER TABLE city DROP CONSTRAINT IF EXISTS city_estado_check;
ALTER TABLE city
    ADD CONSTRAINT city_estado_check
    CHECK (
        estado = ANY (
            ARRAY[
                'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA',
                'MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN',
                'RS','RO','RR','SC','SP','SE','TO'
            ]
        )
    );
