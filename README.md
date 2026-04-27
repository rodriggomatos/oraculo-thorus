# Oráculo Thórus

Plataforma agêntica interna da Thórus Engenharia que indexa o conhecimento de projeto (planilhas, Drive, e-mails, reuniões) e responde perguntas com citações da fonte.
A Fase 1 entrega um agente de Q&A sobre a planilha de definições do projeto **#26002 (Stylo)**.
Toda chamada de LLM passa por LiteLLM e é rastreada no Langfuse; toda resposta cita a fonte.

## Estrutura

```
oraculo-thorus/
├── apps/
│   ├── web/            Frontend Next.js 15 (App Router) — placeholder
│   └── ai/             Backend de IA: FastAPI + LlamaIndex + LangGraph + LiteLLM
├── packages/
│   └── shared-types/   Tipos compartilhados entre TS e (futuramente) Python
├── infra/
│   ├── docker-compose.yml         Langfuse + Postgres pra dev local
│   └── supabase/migrations/       Schema do banco (Supabase)
├── evals/              Golden questions e métricas de avaliação do agente
├── CLAUDE.md           Memória do projeto (contexto, stack, decisões, roadmap)
└── README.md
```

## Pré-requisitos

- Node.js 20+ e **pnpm** (workspaces TS)
- Python 3.11+ e **uv** (gerenciador de pacotes Python)
- Docker + Docker Compose (Langfuse local)
- Conta Supabase Cloud Pro com `pgvector` habilitado
- Chaves: Groq (LLM), OpenAI (embeddings), Google OAuth + Service Account

## Como rodar

> Placeholder — instruções detalhadas serão preenchidas quando os apps forem inicializados.

1. Copiar `.env.example` pra `.env` e preencher.
2. Subir infra local (Langfuse): `docker compose -f infra/docker-compose.yml up -d`
3. Aplicar migrations no Supabase: `supabase/migrations/0001_initial_schema.sql`
4. Backend de IA: `cd apps/ai && uv sync && uv run uvicorn oraculo_ai.api:app --reload`
5. Frontend: `cd apps/web && pnpm install && pnpm dev`

## Roadmap resumido

| Fase | Escopo | Tempo |
|---|---|---|
| 1 | Q&A da planilha #26002 (Stylo) | 3-4 semanas |
| 2 | Multi-projeto + Drive + Meet | 4-6 semanas |
| 3+ | Detector de conflitos, redator de e-mails, completude de fase | meses |

Detalhes completos em [`CLAUDE.md`](./CLAUDE.md).
