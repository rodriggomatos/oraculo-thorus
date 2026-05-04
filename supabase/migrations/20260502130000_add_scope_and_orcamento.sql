-- Scope template + LDP discipline + project_scope versioning + projects orçamento columns + user_profiles.permissions
-- Idempotente: schema já está aplicado em produção; esta migration formaliza o estado pra desenvolvedores futuros.

ALTER TABLE public.user_profiles
    ADD COLUMN IF NOT EXISTS permissions JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON public.user_profiles(role);

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS estado TEXT,
    ADD COLUMN IF NOT EXISTS area_m2 NUMERIC(10, 2),
    ADD COLUMN IF NOT EXISTS fluxo TEXT,
    ADD COLUMN IF NOT EXISTS custo_fator NUMERIC(6, 4),
    ADD COLUMN IF NOT EXISTS total_contratado NUMERIC(12, 2),
    ADD COLUMN IF NOT EXISTS margem NUMERIC(6, 4),
    ADD COLUMN IF NOT EXISTS empreendimento TEXT,
    ADD COLUMN IF NOT EXISTS cidade TEXT,
    ADD COLUMN IF NOT EXISTS drive_folder_path TEXT,
    ADD COLUMN IF NOT EXISTS orcamento_sheets_id TEXT,
    ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES public.user_profiles(id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'projects_estado_check'
          AND table_name = 'projects'
    ) THEN
        ALTER TABLE projects
            ADD CONSTRAINT projects_estado_check
            CHECK (estado IS NULL OR estado IN ('SC','PR','MG','SP','RS','RO','ES'));
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'projects'
          AND column_name = 'google_sheet_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'projects'
          AND column_name = 'ldp_sheets_id'
    ) THEN
        ALTER TABLE projects RENAME COLUMN google_sheet_id TO ldp_sheets_id;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS scope_template (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ordem INTEGER NOT NULL UNIQUE,
    nome TEXT NOT NULL UNIQUE,
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scope_template_ordem ON scope_template(ordem);

INSERT INTO scope_template (ordem, nome) VALUES
    (1,  'Hidrossanitário + Drenagem'),
    (2,  'Hidraulico legal'),
    (3,  'Sanitário legal'),
    (4,  'Drenagem legal'),
    (5,  'PIscina 01 até 30m²'),
    (6,  'PIscina 02 até 50m²'),
    (7,  'PIscina 03 acima de 50m²'),
    (8,  'Projeto de furação para obra'),
    (9,  'Elétrico + Dados'),
    (10, 'Cotas elétrico para intermediário'),
    (11, 'Pré-automação'),
    (12, 'Elétrico legal'),
    (13, 'Subestação'),
    (14, 'SPDA'),
    (15, 'Preventivo'),
    (16, 'Preventivo Legal'),
    (17, 'Rede de Gás'),
    (18, 'Escada pressurizada'),
    (19, 'EPR Legal'),
    (20, 'Sprinkler'),
    (21, 'Sprinkler Legal'),
    (22, 'Exaustão Mecânica nas Garagens'),
    (23, 'Climatização'),
    (24, 'Aspiração Central'),
    (25, 'Quantitativos Parametrizados'),
    (26, 'Canteiro de Obras ELE aprovação'),
    (27, 'Canteiro de Obras com Subestação'),
    (28, 'Canteiro de Obras HID aprovação'),
    (29, 'Canteiro de Obras ELE EXE'),
    (30, 'Canteiro de Obras HID EXE'),
    (31, 'Modelagem de Irrigação'),
    (32, 'ETE em BIM - 15mil m²'),
    (33, 'ETE em BIM - 15mil m² - 45mil m²'),
    (34, 'ETE em BIM > 45 mil m²'),
    (35, 'Cotas HIS para intermediário'),
    (36, 'Drenagem contenção'),
    (37, 'Rede de Gás executivo'),
    (38, 'Preventivo executivo (sem legal)'),
    (39, 'Rede de hidrante (sem PCI exe)'),
    (40, 'Modelagem automação'),
    (41, 'Luminotécnico para interm.'),
    (42, 'Interiores para interm. (ele)'),
    (43, 'Interiores para interm. (his)'),
    (44, 'HVAC (Pressurização, Exaustão, Renovação e climatização)')
ON CONFLICT (ordem) DO NOTHING;

CREATE TABLE IF NOT EXISTS ldp_discipline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL UNIQUE,
    sempre_ativa BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ldp_discipline_codigo ON ldp_discipline(codigo);

INSERT INTO ldp_discipline (codigo, nome, sempre_ativa) VALUES
    ('HID',   'Hidráulica',             FALSE),
    ('SAN',   'Sanitário',              FALSE),
    ('PIS',   'Piscina',                FALSE),
    ('ELE',   'Elétrico / Comunicação', FALSE),
    ('SPDA',  'SPDA',                   FALSE),
    ('PREV',  'Preventivo',             FALSE),
    ('GAS',   'Gás',                    FALSE),
    ('SPK',   'Sprinkler',              FALSE),
    ('CLI',   'Climatização',           FALSE),
    ('GERAL', 'Geral',                  TRUE)
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS scope_to_ldp_discipline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_template_id UUID NOT NULL REFERENCES scope_template(id) ON DELETE CASCADE,
    ldp_discipline_id UUID NOT NULL REFERENCES ldp_discipline(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (scope_template_id, ldp_discipline_id)
);

CREATE INDEX IF NOT EXISTS idx_scope_to_ldp_scope ON scope_to_ldp_discipline(scope_template_id);
CREATE INDEX IF NOT EXISTS idx_scope_to_ldp_ldp ON scope_to_ldp_discipline(ldp_discipline_id);

INSERT INTO scope_to_ldp_discipline (scope_template_id, ldp_discipline_id)
SELECT s.id, d.id
FROM (VALUES
    (1,  'HID'), (1,  'SAN'),
    (2,  'HID'),
    (3,  'SAN'),
    (4,  'SAN'),
    (5,  'PIS'), (6,  'PIS'), (7,  'PIS'),
    (9,  'ELE'), (10, 'ELE'), (12, 'ELE'), (13, 'ELE'),
    (14, 'SPDA'),
    (15, 'PREV'), (16, 'PREV'),
    (17, 'GAS'),
    (20, 'SPK'), (21, 'SPK'),
    (22, 'CLI'), (23, 'CLI'), (24, 'CLI'),
    (36, 'HID'),
    (37, 'GAS'),
    (38, 'PREV'), (39, 'PREV'),
    (44, 'CLI')
) AS m(ordem, codigo)
JOIN scope_template s ON s.ordem = m.ordem
JOIN ldp_discipline d ON d.codigo = m.codigo
ON CONFLICT (scope_template_id, ldp_discipline_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS project_scope (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scope_template_id UUID NOT NULL REFERENCES scope_template(id),

    version INTEGER NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,

    incluir BOOLEAN NOT NULL DEFAULT FALSE,
    unificar BOOLEAN,
    essencial BOOLEAN NOT NULL DEFAULT FALSE,
    legal TEXT NOT NULL CHECK (legal IN ('executivo', 'legal')),

    pontos NUMERIC(12, 2) NOT NULL DEFAULT 0,
    peso_disciplina NUMERIC(8, 4),
    ponto_fixo NUMERIC(12, 2),
    pontos_calculados NUMERIC(12, 2) NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES public.user_profiles(id),
    superseded_at TIMESTAMPTZ,
    superseded_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_project_scope_current ON project_scope(project_id, is_current)
    WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_project_scope_history ON project_scope(project_id, version);
CREATE INDEX IF NOT EXISTS idx_project_scope_template ON project_scope(scope_template_id);
