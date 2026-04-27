# Oráculo Thórus — Memória do Projeto

## Contexto

Sistema interno de IA pra Thórus Engenharia, escritório de engenharia/BIM.
Visão de longo prazo: plataforma agêntica que automatiza fluxos de
informação de projeto da empresa inteira (definições, e-mails, reuniões,
prazos, alertas, integrações com Asana).

Caso piloto (Fase 1): planilha de definições do projeto 26002 (Stylo - Rua João Batista Derner Neves, São José/SC).
Pergunta exemplo: "qual o material da tubulação de gás?" → resposta:
"Multicamada (interno) + aço (prumada), conforme item PL4 da lista de definições do projeto #26002".

## Stack (NÃO ALTERAR sem discussão explícita)

### Linguagens
- Python 3.11+ no backend de IA
- TypeScript em todo o resto (frontend, API routes, scripts)

### Frontend e backend de produto
- Next.js 15 (App Router) + React 18
- TypeScript estrito (sem `any`)
- shadcn/ui + Tailwind CSS
- Cliente Supabase (@supabase/ssr)
- Hosting: Railway

### Backend de IA
- FastAPI + Pydantic v2
- LlamaIndex (retrieval, ingestão, conectores)
- LangGraph (orquestração de fluxo, agentes)
- LiteLLM (abstração de provedor de LLM — NÃO acoplar a SDK específico)
- Provedor LLM atual: Groq (llama-3.3-70b-versatile) — trocável via env
- Provedor de embeddings atual: OpenAI (text-embedding-3-small, dim 1536)
- Hosting: Railway

IMPORTANTE: todo acesso a LLM passa por LiteLLM. NUNCA importar
anthropic, openai, groq SDK diretamente no código de aplicação.
A escolha de modelo é configuração, não código.

### Dados
- Supabase Cloud Pro (Postgres + pgvector + Auth + Storage)
- pgvector para embeddings (dim 1536, cosine, índice HNSW)
- Google OAuth restrito ao domínio da Thórus

### Observabilidade
- Langfuse (todas as requisições ao LLM rastreadas)

### Gerenciadores de pacote
- pnpm (workspaces TS)
- uv (Python)


## Arquitetura

### Visão de plataforma agêntica em 3 camadas

**Camada 1 — Fontes de conhecimento (Inputs)**
Conectores modulares pra cada fonte: planilhas, Drive, Gmail, Meet,
WhatsApp, contratos, histórico de obra, Construflow. Cada conector
normaliza pra chunks + metadata + entities.

**Camada 2 — Cérebro**
Vector store (pgvector) + knowledge graph (entities + relations) +
reasoning. Busca semântica com filtros, detecção de conflitos,
identificação de lacunas, relações entre entidades.

**Camada 3 — Agentes especializados (Outputs)**
Cada agente tem job específico, prompts próprios, ferramentas próprias,
guardrail de aprovação humana quando ação tem efeito externo.
Lista futura de agentes: Q&A, completude de fase, redator de e-mails,
avaliador de prazos, detector de conflitos, alerta de risco,
notificador de cliente.

### Dois backends, responsabilidades claras

**Next.js API routes (TS)** — backend de produto:
- Auth, sessões, OAuth callbacks
- CRUD de projetos
- Webhooks de sincronização
- Logs, dashboards
- Filas de aprovação humana (UI pra revisar saídas de agentes)
- Acesso ao Supabase via @supabase/ssr

**FastAPI (Python)** — backend de IA:
- POST /query → recebe pergunta + project_id, retorna resposta com citações
- POST /ingest/{project_id} → dispara ingestão de uma fonte
- POST /events → recebe eventos externos pra processar
- GET /health
- Workers de eventos (consomem tabela `events`)
- Acesso direto ao Supabase via psycopg + pgvector

Comunicação entre eles: HTTP. Frontend chama os dois conforme necessário.

### Fluxo de uma pergunta (Fase 1)

1. Usuário escolhe projeto (#25074) e digita pergunta
2. Frontend → Next.js API (auth, validação) → FastAPI /query
3. FastAPI: agente Q&A (LangGraph) orquestra:
   a. LlamaIndex busca top 20 chunks no pgvector (filtro WHERE project_id)
   b. Monta prompt com chunks + pergunta + instruções
   c. Chama LLM via LiteLLM (modelo configurável)
   d. Parseia citações da resposta
4. Resposta volta com texto + lista de citações (planilha, aba, linha)
5. Frontend renderiza com links pras fontes

## Schema do banco (Supabase)

Fase 1 começa com 3 tabelas. Outras serão adicionadas conforme necessário
(conversations e messages quando o chat tiver histórico, documents quando
houver múltiplas fontes, etc).

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_number integer UNIQUE NOT NULL,
  name text NOT NULL,
  client text,
  google_sheet_id text,
  status text DEFAULT 'active',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE definitions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  disciplina text,
  tipo text,
  fase text,
  item_code text NOT NULL,
  pergunta text NOT NULL,
  opcao_escolhida text,
  status text,
  custo text,
  observacoes text,
  validado boolean DEFAULT false,
  informacao_auxiliar text,
  apoio_1 text,
  apoio_2 text,
  source_sheet_id text,
  source_row integer,
  raw_data jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE (project_id, item_code)
);

CREATE INDEX definitions_project_idx ON definitions(project_id);
CREATE INDEX definitions_disciplina_idx ON definitions(project_id, disciplina);
CREATE INDEX definitions_validado_idx ON definitions(project_id, validado);

CREATE TABLE chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  source_table text NOT NULL,
  source_row_id uuid NOT NULL,
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  embedding vector(1536),
  created_at timestamptz DEFAULT now()
);

CREATE INDEX chunks_project_idx ON chunks(project_id);
CREATE INDEX chunks_source_idx ON chunks(source_table, source_row_id);
CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "auth_read_projects" ON projects FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_definitions" ON definitions FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "auth_read_chunks" ON chunks FOR SELECT USING (auth.role() = 'authenticated');
```

## Estrutura de pastas

```
oraculo-thorus/
├── apps/
│   ├── web/                          (vazia, Next.js criado depois)
│   └── ai/
│       ├── pyproject.toml
│       ├── .python-version
│       ├── src/oraculo_ai/
│       │   ├── __init__.py
│       │   ├── api/
│       │   │   └── __init__.py
│       │   ├── core/                 config, schemas globais, supabase client
│       │   │   └── __init__.py
│       │   ├── llm/                  wrapper LiteLLM
│       │   │   └── __init__.py
│       │   ├── ingestion/            conectores modulares
│       │   │   ├── __init__.py
│       │   │   ├── base.py           interface Connector
│       │   │   └── google_sheets/
│       │   │       └── __init__.py
│       │   ├── retrieval/            busca semântica + filtros
│       │   │   └── __init__.py
│       │   ├── agents/               um por agente
│       │   │   ├── __init__.py
│       │   │   └── qa/               agente Q&A da Fase 1
│       │   │       ├── __init__.py
│       │   │       ├── prompts/
│       │   │       ├── tools/
│       │   │       ├── graph.py
│       │   │       └── schema.py
│       │   ├── events/               sistema de eventos
│       │   │   └── __init__.py
│       │   └── knowledge/            knowledge graph
│       │       └── __init__.py
│       └── tests/
│           └── __init__.py
├── packages/
│   └── shared-types/
├── infra/
│   └── docker-compose.yml
├── supabase/
│   ├── .gitignore
│   ├── config.toml
│   └── migrations/
│       └── 0001_initial_schema.sql
├── evals/
│   └── README.md
├── CLAUDE.md
├── README.md
├── .env.example
├── pnpm-workspace.yaml
└── .gitignore
```

## Convenções de código

### Geral
- Sem `any` em TypeScript
- Sem comentários em código (preferência do dev)
- Nomes em inglês no código, mensagens de UI em português brasileiro
- Strings de log em inglês

### Python
- Type hints obrigatórios
- Pydantic v2 pra todos os schemas de I/O
- Async por padrão (FastAPI + httpx + asyncpg)
- Estrutura: src layout, separar I/O de lógica de negócio
- Configuração via pydantic-settings (.env)

### TypeScript
- TS estrito habilitado
- Server Components por padrão no Next.js, Client só quando precisar
- Schemas com Zod
- Tipos do Supabase auto-gerados via CLI

### Convenções de retrieval
- Embedding via LiteLLM (modelo configurável, padrão: text-embedding-3-small)
- Dim 1536 (OpenAI). Se trocar de provedor de embeddings, REINDEXAR tudo
- Top K inicial = 20 (sem rerank na fase 1; rerank vem depois)
- Filtro WHERE project_id sempre antes da similaridade
- Metadata jsonb com: aba, linha, disciplina, ambiente, projeto_nome, projeto_numero

## Princípios de produto

1. Toda resposta cita a fonte (planilha, aba, linha). Sem citação = não responder
2. Se não tem confiança, dizer "não sei" em vez de inventar
3. Toda interação rastreada no Langfuse (não negociável)
4. UX define o projeto antes da pergunta (seletor explícito ou prefixo #25074)
5. Toda ação com efeito externo passa por aprovação humana

## Princípios arquiteturais pra plataforma agêntica

Mesmo na Fase 1, a estrutura DEVE permitir crescer pras fases seguintes
sem reescrita. Por isso:

### 1. Agentes plurais desde o início
Pasta agents/ contém um subdiretório por agente. Cada agente tem:
- prompts/ — templates de prompt versionados
- tools/ — funções que o agente pode invocar
- graph.py — definição LangGraph do fluxo
- schema.py — Pydantic schemas de input/output

Fase 1 implementa só agents/qa/ (Q&A sobre planilhas).
Fases seguintes adicionam novos diretórios sem mexer nos existentes.

### 2. Tipo de saída como cidadão de primeira classe
Tabela agent_outputs:
- type pode ser: 'answer', 'email_draft', 'risk_alert',
  'phase_completion_check', 'conflict_warning', 'definition_suggestion'
- requires_approval boolean
- approval_status: 'pending' | 'approved' | 'rejected' | 'auto'

### 3. Human approval como camada
Tabela approvals registra toda decisão humana sobre saídas de agentes.
Toda ação com efeito externo passa por aqui.

### 4. Knowledge graph leve desde o dia 1
Tabelas entities e relations existem desde a Fase 1, mesmo populadas só
com projetos. A estrutura está pronta pra crescer.

### 5. Conectores modulares
Cada fonte = um diretório em ingestion/ implementando interface Connector.
Adicionar fonte = adicionar pasta. Não tocar em código existente.

### 6. Eventos > pedidos diretos
Sistema agêntico reage a eventos. Tabela events + worker que consome
e dispara agentes. Na Fase 1 quase não usamos, mas a infraestrutura existe.

## Realidade do projeto (calibração honesta)

- 1 dev (Rô) em tempo integral
- Visão completa: ~12-15 meses pra cobrir o diagrama todo
- Primeira entrega de valor (Fase 1): 3-4 semanas
- Disciplina de escopo é crítica: não cair em scope creep
- Toda fase tem definition of done explícito antes de seguir pra próxima

## Roadmap (alto nível)

| Fase | Escopo | Tempo |
|---|---|---|
| 1 | Oráculo Q&A da planilha 25074 | 3-4 semanas |
| 2 | Multi-projeto + Drive + transcrições Meet | 4-6 semanas |
| 3 | Detector de conflitos e lacunas (passivo) | 4-6 semanas |
| 4 | Agente redator de e-mail (com aprovação) | 6-8 semanas |
| 5 | Agente de completude de fase + Asana | 8-12 semanas |
| 6+ | Prazos, alertas, e-mails ao cliente | meses |

## Decisões já tomadas (não revisitar sem justificativa forte)

- LiteLLM como camada de abstração de LLM (não usar SDKs direto)
- Groq + Llama 3.3 70B como provedor inicial (gratuito, rápido)
- OpenAI text-embedding-3-small como provedor de embeddings inicial
- Supabase Cloud foi escolhido sobre self-hosted por simplicidade operacional
- Railway foi escolhido sobre Fly.io por DX
- LangChain "clássico" foi rejeitado em favor de LangGraph + LlamaIndex
- Não duplicar planilha em tabela estruturada — só indexar no pgvector
- Todos os engenheiros veem todos os projetos (RLS aberto entre autenticados)
- Conversas e mensagens são privadas por usuário
- Reranking adiado pra fase 2 (sem Cohere Rerank no piloto)
- Estrutura agêntica desde Fase 1 (agents/, agent_outputs, approvals, events)
- Supabase keys usam o formato novo (sb_publishable_xxx e sb_secret_xxx) — variáveis de ambiente são SUPABASE_PUBLISHABLE_KEY e SUPABASE_SECRET_KEY (não anon/service_role).