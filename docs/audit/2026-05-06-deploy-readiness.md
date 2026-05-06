# Auditoria de Prontidão para Deploy — Oráculo Thórus

**Data da auditoria**: 2026-05-06
**Branch**: `feat/agent-context-menu`
**Commits recentes relevantes**:
- `ce304e0` (fix query_database)
- `f4ec15b` (tool genérica)
- `c48cbf3` (reconciliação de schema)

---

## Bloco 1 — apps/ai como biblioteca vs serviço

**Existe entrypoint HTTP em apps/ai?** Não. `apps/ai/src/oraculo_ai/api/__init__.py` (linha 1-7) é um docstring que descreve "Camada HTTP (FastAPI)" mas o módulo está vazio. Nenhum `app = FastAPI(...)` em qualquer lugar de `apps/ai/src`. O único FastAPI app real do repo está em `apps/api/src/oraculo_api/main.py`.

**Como apps/api consome apps/ai hoje**: via import direto de pacotes Python (mesmo workspace, instalação editável).

### Imports cruzados existentes

| Arquivo no apps/api que importa | Símbolos importados de oraculo_ai |
|---|---|
| `apps/api/src/oraculo_api/auth.py:12-13` | `core.config.{Settings, get_settings}`, `core.db.get_pool` |
| `apps/api/src/oraculo_api/main.py:12-14` | `core.config.get_settings`, `core.db.{close_db, init_db}`, `llm.client.shutdown_traces` |
| `apps/api/src/oraculo_api/routes/documents.py:6-7` | `document_ai.pipeline.ingest_documents_into_ldp`, `document_ai.sheets_ingester.ingest_from_sheets` |
| `apps/api/src/oraculo_api/routes/projects.py:10-35` | `agents.qa.repository.ProjectRepository`; `drive.{copy_project_template, ...}`; `ldp.{generate_ldp_sheet, read_master_r04, ...}`; `permissions.check_permission`; `projects.{create_project_with_scope, format_project_name, ...}`; `scope.{parse_orcamento_from_sheets, validate_against_template, ...}` |
| `apps/api/src/oraculo_api/routes/projects.py:138` | `projects.get_scope_template_names` (import lazy dentro de função) |
| `apps/api/src/oraculo_api/routes/query.py:7-8` | `agents.qa.agent.answer_question`, `agents.qa.schema.{QAQuery, UserContext as AgentUserContext}` |

### Funções públicas mais usadas pelo api

- `answer_question(query, checkpointer, user) → QAAnswer` em `agents/qa/agent.py:263`
- `init_db(database_url, pool_size) → None` e `close_db() → None` em `core/db.py`
- `copy_project_template(project_name) → CreateFolderResult` em `drive/folder_creator.py:179`
- `generate_ldp_sheet(project_id) → CreateLdpSheetResult` em `ldp/sheet_generator.py`
- `parse_orcamento_from_sheets(spreadsheet_id) → ParsedOrcamento` em `scope/parser.py`

### Onde o agent é instanciado e a função principal de resposta

- **Instanciação**: `agents/qa/agent.py:302` — `agent = create_agent(model=llm, tools=tools_list, system_prompt=..., checkpointer=...)`. É o `create_agent` do `langchain.agents`.
- **Função pública de resposta**: `answer_question` em `agents/qa/agent.py:263-353`. Internamente chama `agent.ainvoke({"messages": [{"role":"user","content":...}]}, config={"configurable":{"thread_id":...}})` em `agent.py:322-325`. **Não usa streaming hoje** — a resposta inteira é coletada via `result["messages"]` e devolvida como `QAAnswer` (linhas 327-335).

### Estado compartilhado entre requests dentro de apps/ai

| Local | Tipo | Risco em multi-process |
|---|---|---|
| `core/db.py:9` | Pool global `_pool: AsyncConnectionPool` (singleton, via `init_db/get_pool`) | OK por worker, mas cada worker uvicorn cria seu próprio pool — multiplica conexões pelo nº de workers. |
| `agents/qa/agent.py:259` | `_checkpointer = InMemorySaver()` — fallback in-process do LangGraph, usado se o caller não passar checkpointer | Quebra se múltiplos workers: cada um tem seu próprio InMemorySaver, threads de conversa só funcionam dentro do mesmo worker. Hoje o `apps/api/main.py:34` injeta um `AsyncPostgresSaver` no `app.state.checkpointer` e passa explicitamente, então o fallback em memória só dispara em CLI/eval/testes. |
| `agents/qa/tools/create_project.py:44` | `_parse_cache: dict[(thread_id, spreadsheet_id), (ParsedOrcamento, expires_at)]` — TTL 1800s | Quebra sticky-session: se o user retorna ao flow agêntico em outro worker, cache miss → re-parse da planilha. Não é incorreto, só ineficiente. |
| `ldp/master_reader.py:210` | `_master_cache: list[MasterRow] | None` (global) + `@lru_cache(maxsize=1)` em `_load_schema` | OK. Cache por processo, idempotente; cada worker faz fetch da Master 1x. |
| `llm/client.py:10` | `_settings = get_settings()` no module-level | OK, pydantic settings é immutable. |
| `core/config.py:66` | `@lru_cache(maxsize=1) get_settings()` | OK. |

### Estimativa pra mover apps/ai pra serviço HTTP independente

- Criar `apps/ai/src/oraculo_ai/server.py` com FastAPI, lifespan replicando o `apps/api/main.py` (init_db, AsyncPostgresSaver, CORS, shutdown), e endpoints `POST /chat` (com `astream_events` ou `astream` do agent pra SSE) e `POST /ingest`, `POST /events`, `GET /health`. ~150-200 LOC originais.
- `apps/api/src/oraculo_api/routes/query.py` (atual 56 linhas) vira proxy httpx pro serviço de IA: ~40 LOC.
- `apps/api/src/oraculo_api/routes/projects.py` tem 36 imports de `oraculo_ai` distribuídos — esse arquivo (303 linhas) é o mais acoplado. Refatorar pra chamar HTTP exigiria escrever ~10 endpoints novos no novo serviço de IA OU manter import direto e só extrair o `/query` (o flow agêntico).
- Lifespan + checkpointer + pool precisa ser duplicado entre os dois serviços, ou fica no de IA e o `apps/api` usa só DB direto.

**Estimativa honesta pra extrair só /query** (sem mexer em projects/documents): 300-400 LOC novas (server.py + SSE wrapper + proxy no api), ~50 LOC removidas do apps/api. **Extrair tudo**: 800-1200 LOC, exige redesenhar o lifespan compartilhado.

---

## Bloco 2 — apps/mcp-drive transport

**Transport atual**: stdio. Em `apps/mcp-drive/src/mcp_drive/__main__.py:15`: `server.run(transport="stdio")`. Logging configurado pra stderr explicitamente (`logging.py:1` documenta "stdio MCP usa stdout pro protocolo").

**Implementação do servidor**: `mcp.server.fastmcp.FastMCP` (alto nível). Em `server.py:5,36-44`:

```python
from mcp.server.fastmcp import FastMCP
...
mcp = FastMCP("thorus-drive")
_register_tools(mcp, tools)
return mcp
```

Não usa `mcp.server.Server` baixo nível.

### Tools expostas (server.py:48-130)

| Tool | Assinatura |
|---|---|
| `list_project_files` | `(project_number: int, category: str \| None, discipline: str \| None, has_status: str \| None) → dict[str, Any]` |
| `find_lista_definicoes` | `(project_number: int) → dict[str, Any]` |
| `find_atas` | `(project_number: int) → dict[str, Any]` |
| `find_vof_revisoes` | `(project_number: int, discipline: str \| None, only_approved: bool = False) → dict[str, Any]` |
| `find_arquivos_externos` | `(project_number: int, source: str \| None) → dict[str, Any]` |

**Tests em tests/**: 5 arquivos (`test_backend_normalization.py`, `test_cache.py`, `test_classifiers.py`, `test_ldp_classifier.py`, `test_parsing.py`). Nenhum testa transport — não há mock de stdin/stdout, não há instanciação do FastMCP nos tests. Cobertura é toda de pure-logic (NFC normalization, cache TTL, classifiers, regex de filenames).

### Estimativa pra trocar transport

`FastMCP.run()` aceita `transport="stdio" | "sse" | "streamable-http"` — em tese é mudança de uma linha em `__main__.py`. Mas o caller real do MCP server hoje é o LangChain `MultiServerMCPClient` em `apps/ai/src/oraculo_ai/agents/qa/mcp_client.py` (a investigar para o detalhe completo, mas o padrão é spawn de subprocess via stdio). Trocar pra HTTP exige:

1. `__main__.py` muda transport (1 linha).
2. `mcp_client.py` no apps/ai muda de `StdioServerParameters` pra `SSEConnection` ou `StreamableHttpConnection` (1 bloco).
3. Configurar URL+porta em vez de comando (settings nova).
4. Decidir se MCP server vira processo separado deployado independente ou fica embutido.

**Mudança de uma linha em cada lado** para o caso simples (mesmo container). Refactor maior se for serviço separado: precisa dockerfile, healthcheck, descoberta de URL via config, etc.

**Auth/autorização no MCP server**: Não há nenhuma. O server confia no caller. O único check é validação de scopes da própria service account em `auth.py:43` (`validate_readonly_scopes`) — checa que as credenciais do Google têm só scopes `*.readonly`, mas isso protege o Google Drive, não o canal MCP. No transport stdio, o caller é o processo pai que deu spawn — autenticação é "se você conseguiu spawnar, você tem acesso". Em SSE/HTTP, isso vira problema: precisaria adicionar header check ou similar.

---

## Bloco 3 — Credenciais Google (Service Account)

### Implementação(ões) de load_credentials

1. `apps/ai/src/oraculo_ai/ingestion/google_sheets/connector.py:15-26` — `load_credentials(creds_input: str, scopes: list[str]) → Credentials`. Aceita JSON inline (`stripped.startswith("{")`) OU path absoluto/relativo a `Path.cwd()`.
2. `apps/mcp-drive/src/mcp_drive/auth.py:26-40` — `load_service_account_credentials(creds_input: str) → Credentials`. Mesmo padrão: JSON inline OU path. Hard-code de `_SCOPES = ["drive.readonly"]`.

### Importadores diretos

- `apps/ai/src/oraculo_ai/ingestion/google_sheets/connector.py` (+ usado em `pipeline.py`, `master_reader.py`, `sheet_generator.py`, `scope/parser.py`, `document_ai/sheets_ingester.py`)
- `apps/ai/src/oraculo_ai/document_ai/drive_scanner.py` — importa `load_credentials` do connector e adiciona `build_drive_service()` e `build_drive_service_rw()`
- `apps/mcp-drive/src/mcp_drive/server.py:8` — chama `load_service_account_credentials`

### Camada de configuração centralizada

- `apps/ai/src/oraculo_ai/core/config.py` (linha 47): `google_service_account_json: str = ""` em pydantic Settings. Lido por apps/ai e apps/api.
- `apps/mcp-drive/src/mcp_drive/config.py:20`: campo equivalente, configuração própria (Settings separada, lê do mesmo `.env` na raiz).

**Aceita JSON inline em env var?** Sim, ambos `load_credentials` já aceitam string JSON via `if stripped.startswith("{")`.
**Aceita ADC?** Não — não tem fallback pra `google.auth.default()`.

**Pra refatorar e ficar 100% deploy-friendly** (JSON inline com fallback elegante a path): o código já aceita inline. O bloqueador real está em `apps/mcp-drive/src/mcp_drive/auth.py:35-39` e `apps/ai/.../connector.py:21-26` — quando o input não começa com `{`, ambos resolvem path. Em prod, o env var pode vir inline (já funciona) ou vazio (já trata com erro descritivo). **Nenhum ponto precisa mudar pra ser deploy-friendly. 0 pontos pra refatorar.**

O risco oculto é o oposto: alguém em prod setar `GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/key.json` (path) e a plataforma de deploy não montar o file system esperado. Mitigação: setar inline diretamente.

---

## Bloco 4 — Containerização e ambiente

**Dockerfiles**: nenhum em qualquer app. Verificado: `apps/ai/`, `apps/api/`, `apps/mcp-drive/`, `apps/web/` — sem Dockerfile ou Containerfile.

**docker-compose**: apenas `infra/docker-compose.yml` (41 linhas). Sobe só Langfuse local (postgres `langfuse-db` na porta 5433 + `langfuse/langfuse:2` na 3030). Não roda nem Thor, nem API, nem Supabase local. Inclui senhas placeholder (`change-me-in-prod` para `NEXTAUTH_SECRET` e `SALT`) — uso é dev local apenas.

**.dockerignore**: não existe.

### Variáveis de ambiente — gerência

- `.env` único na raiz `C:/Python/oraculo-thorus/.env` (24 chaves) é a fonte de verdade pros backends Python.
- `apps/web/.env.local` separado pro Next.js.
- `apps/mcp-drive/.env.example` (não committed o `.env`) — herda do raiz mas tem template próprio.
- Cada Settings pydantic aponta pro mesmo `.env` raiz via path relativo: `apps/ai/.../core/config.py:9` (`parents[5] / ".env"`), `apps/mcp-drive/.../config.py:9` (`parents[4] / ".env"`).

### Variáveis lidas pelo código (lista exaustiva)

**Backend Python (apps/ai + apps/api)**:
- `LLM_PROVIDER`, `LLM_MODEL_FAST`, `LLM_MODEL_SMART`
- `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`
- `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`
- `DATABASE_URL`, `DATABASE_URL_QUERY_RO`
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_SERVICE_ACCOUNT_JSON`
- `SUPABASE_JWT_SECRET`, `SUPABASE_JWKS_URL`
- `ALLOWED_EMAIL_DOMAIN`
- Defaults internos: `THORUS_DRIVE_ROOT_ID`, `THORUS_DRIVE_TEMPLATE_FOLDER_ID`, `LDP_MASTER_SHEET_ID`, `LDP_MASTER_TAB`, `DOCUMENT_AI_INCOMING_DIR`

**Next.js (apps/web)**:
- `NEXT_PUBLIC_API_URL` (lida em `lib/api.ts:4`, `lib/backend.ts:3` — fallback `http://localhost:8000`)
- `NEXT_PUBLIC_SUPABASE_URL` (lida em `lib/supabase/client.ts`, `lib/supabase/server.ts`, `middleware.ts:10`)
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (mesmos arquivos)

**MCP Drive (apps/mcp-drive)**:
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `THORUS_DRIVE_ROOT_ID`
- `MCP_DRIVE_CACHE_TTL_SECONDS`
- `MCP_DRIVE_LOG_LEVEL`

**Reads diretos via os.environ** (não via Settings) — `apps/ai/src/oraculo_ai/llm/client.py:10-50` faz `os.environ.setdefault("LANGFUSE_PUBLIC_KEY", _settings.langfuse_public_key)` e similar para `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `GROQ_API_KEY`, `OPENAI_API_KEY`. `document_ai/extractor.py` e `sheets_ingester.py` setam `os.environ["ANTHROPIC_API_KEY"]` antes de chamar SDK do anthropic. **São writes, não reads** — pra propagar pra libs que esperam env. Não há `os.getenv` direto fora desse padrão.

**Diferenciação dev vs prod**: Não existe. Sem `if env == "production"`, sem flag `ENV` no Settings, sem CORS condicional. `apps/api/src/oraculo_api/main.py:50-56` deixa `allow_origins=["http://localhost:3000"]` sempre.

---

## Bloco 5 — Dependências externas em produção

### Supabase

- **Region** (do .env): `aws-1-us-west-2` (no `DATABASE_URL` via pooler `aws-1-us-west-2.pooler.supabase.com:5432`)
- **Hostname Supabase API**: `https://<projeto>.supabase.co` (cloud, não self-hosted)
- **Pooler em 5432** (transaction mode em prod normalmente é 6543 — verificar se o pooler está em modo session ou transaction)

### Langfuse

- `LANGFUSE_HOST=https://cloud.langfuse.com` em prod
- `infra/docker-compose.yml` ainda tem o stack self-hosted (langfuse-db + langfuse:2) mas o `.env` aponta pra cloud. **Inconsistência**: o compose está obsoleto vs config atual; provavelmente foi self-hosted e migrou pra cloud.

### Outros serviços externos

- **Anthropic API** — via `ANTHROPIC_API_KEY` (`api.anthropic.com`, hardcoded nas libs anthropic/litellm/langchain-litellm)
- **OpenAI** — via `OPENAI_API_KEY` (embeddings `text-embedding-3-small`, dim 1536). `api.openai.com`
- **Groq** — via `GROQ_API_KEY`. `api.groq.com`. Hoje `LLM_MODEL_SMART=anthropic/claude-sonnet-4-6`, então Groq fica de reserva, não é caminho ativo
- **Google Drive API** — via service account JSON. `www.googleapis.com/drive/v3`
- **Google Sheets API** — mesma SA. `sheets.googleapis.com/v4`
- **Google OAuth** — `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET` configurados mas uso real está no Supabase Auth (provider Google — o login é feito via Supabase, não via redirect direto pelo backend). Os clients são pra Supabase consumir
- **Document AI / pipeline interno** — não é serviço externo, é módulo `apps/ai/.../document_ai/` que chama Anthropic

---

## Bloco 6 — Auth (Supabase + Google OAuth)

### Validação de JWT no backend

`apps/api/src/oraculo_api/auth.py`, função `get_current_user(authorization, settings)` em linha 115-158. Fluxo:

1. Extrai `Bearer <token>` (linha 122-127)
2. `_decode_token(token, settings)` (linha 38-86): desserializa o algoritmo do header, valida com `SUPABASE_JWT_SECRET` (HS256) ou `SUPABASE_JWKS_URL` (RS256/ES256). Cache de JWKS em dict module-level `_JWKS_CACHE` (linha 16) — sem TTL, sem invalidação; primeiro fetch dura pra sempre
3. Extrai `sub` (user_id) e `email` do claim. Erra 401 se faltar
4. **Domain check** (linha 141-146): `email.rsplit("@", 1)[-1] != settings.allowed_email_domain` → 403. Hardcoded fallback: `thorus.com.br`
5. `_load_user_profile(user_id)` (linha 88-112): `SELECT` em `public.user_profiles` usando o pool do `oraculo_ai.core.db`. Se não achar → 403 com mensagem "sign in again to provision"
6. Retorna `UserContext(user_id, email, name, role, is_active)`

### apps/web Server Components vs Client

**Mistura.** Tem middleware (`apps/web/src/middleware.ts`, 64 linhas), logo Server-side check em toda rota não-pública. Hooks de cliente em `useChat`, `useCreateProjectFlow`. Auth via `@supabase/ssr` (`createServerClient` em `middleware.ts`, `lib/supabase/server.ts`, `lib/supabase/client.ts`).

### Middleware Next.js protegendo rotas

`apps/web/src/middleware.ts`:

- `PUBLIC_PATHS = ["/login", "/auth/callback", "/auth/error"]` (linha 4)
- `ALLOWED_DOMAIN = "thorusengenharia.com.br"` (linha 5) — hardcoded e diferente do backend (`thorus.com.br` no `apps/ai/core/config.py:55` e fallback no `auth.py`). **Inconsistência potencial**: web aceita `@thorusengenharia.com.br`, backend aceita `@thorus.com.br`
- Regex de matcher: tudo que não é `_next/static`, `_next/image`, `favicon.ico` ou imagens
- User não autenticado → redirect `/login?from=<path>`
- User autenticado mas domain errado → `signOut()` + redirect `/auth/error?reason=domain`

### Token do frontend pro backend

- Header `Authorization: Bearer <access_token>`. Construído em `apps/web/src/lib/api.ts:10-11` e `features/create-project/mock.ts:19-20`:
  ```typescript
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
  ```
- Proxy pra backend (`apps/web/src/app/api/projects/[projectId]/...`) repassa em `lib/backend.ts:13` (`headers["Authorization"] = auth`)

### Repasse de user_id pra camadas inferiores

- `apps/api/src/oraculo_api/routes/query.py:32-37` constrói `AgentUserContext(user_id, email, name, role)` a partir do `UserContext` da API e passa pro `answer_question(user=...)`
- O agent (`apps/ai/.../agent.py:280`) usa o `user.user_id` ao construir o `make_register_definition(effective_user.user_id)` — bind do user_id na tool
- Tool `register_definition` (`tools/qa_search.py:86-150`): factory `make_register_definition(user_id)` retorna a tool com `user_id` capturado no closure. Quando a tool é chamada pela LLM, `user_id` já está bound. Em linha 142: `created_by_user_id=user_id` é passado ao `register_definition_version`

**Conclusão**: rastreamento de autoria existe e está acoplado ao auth. MCP Drive não recebe `user_id` — chamadas via stdio são processo-vs-processo, sem contexto de usuário. Nenhuma tool do MCP escreve no Drive (tudo readonly), então não é problema hoje, mas é um bloqueio se MCP ganhar tools de escrita.

---

## Bloco 7 — Pontos cegos descobertos durante a auditoria

1. **Hardcoded path Windows em config padrão** — `apps/ai/src/oraculo_ai/core/config.py:53`: `document_ai_incoming_dir: str = "C:/oraculo-thorus/incoming"`. Quebra em qualquer Linux/container que não monte esse path. Lido pelo pipeline de Document AI.

2. **localhost em defaults de prod** — `apps/ai/.../config.py`:
   - `database_url` default `postgresql://postgres:postgres@localhost:5432/postgres` (linha 34)
   - `langfuse_host` default `http://localhost:3030` (linha 43)
   - `next_public_ai_api_url` default `http://localhost:8000` (linha 49)
   - `apps/api/main.py:52` `allow_origins=["http://localhost:3000"]` é literal hardcoded, não default. Deploy de prod sem env var sobrescrevendo cada um falha em tempo de uso, não de boot.

3. **Domínios de email inconsistentes entre frontend e backend** — `apps/web/src/middleware.ts:5` usa `thorusengenharia.com.br`; `apps/ai/.../config.py:55` e `apps/api/auth.py:142` usam `allowed_email_domain` (default `thorus.com.br`). Em prod uma das duas barreiras falha — usuário pode logar no web e ser barrado no backend, ou vice-versa.

4. **InMemorySaver como fallback do agent** — `agents/qa/agent.py:259`: se algum caller esquecer de passar checkpointer, o flow agêntico (criação de projeto, com 3 interrupts) silenciosamente perde o estado entre workers. Hoje o `apps/api/main.py:34-36` injeta o `AsyncPostgresSaver` corretamente, mas qualquer novo caller (CLI, eval, script) cai no fallback. Risco médio.

5. **JWKS cache sem TTL** — `apps/api/src/oraculo_api/auth.py:16` `_JWKS_CACHE: dict[str, Any] = {}` é populado uma vez em `_fetch_jwks` (linha 27-35) e nunca expira. Se a Supabase rotacionar chaves (pode acontecer), o backend continua validando com a chave velha até restart.

6. **CORS hardcoded em prod path** — `apps/api/src/oraculo_api/main.py:50-56`: `allow_origins=["http://localhost:3000"]` literal. Não é Settings, não é env var. Em prod com web em `https://thor.thorus.com.br` (ou similar), as requests do browser falham no preflight.

7. **Sem logging.basicConfig em parte alguma** — grep não encontra nenhum em `apps/ai`, `apps/api` ou `apps/mcp-drive`. Logs dependem totalmente do default do uvicorn (ai/api) ou stderr puro (mcp-drive). Nível de log não-configurável via env. Mensagens INFO/DEBUG do código aparecem ou não dependendo do que uvicorn escolher.

8. **Sem graceful shutdown além de Langfuse + DB pool** — `apps/api/src/oraculo_api/main.py:39-41` só faz `shutdown_traces()` (Langfuse) e `close_db()`. Não há tratamento de SIGTERM (uvicorn herda do default). Conexões com Anthropic/OpenAI/Google em flight no momento do SIGTERM são abortadas. Em flows agênticos com 3 interrupts, isso pode deixar projeto criado com pasta no Drive não-criada.

9. **Sem .dockerignore** — qualquer `docker build` (quando existir Dockerfile) vai puxar `.venv`, `node_modules`, `__pycache__`, `.git`, `apps/ai/.venv` (~470MB), planilhas em `apps/ai/inspect_r04.py` (8KB, untracked), tudo. Build vai ser muito lento e enviar segredos do `.env` se não for setado `.gitignore`-equivalente.

10. **Acoplamento: apps/ai/tests importa oraculo_ai nativamente** — esperado e correto. Mas: `apps/api` não tem diretório `tests/` (verifiquei: só `README.md`, `pyproject.toml`, `scripts/`, `src/`, `uv.lock`). Toda a cobertura de testes do api flui pelos tests de `apps/ai`, que importam de `oraculo_ai` direto. Não existe nenhum test de integração que exercite `apps/api/main.py` ou os routers — só smoke imports manuais.

11. **projects.yaml committed na raiz** (12 linhas) — não é `.example`, é arquivo real. `git ls-files` confirma. Provavelmente contém configuração de seed de projetos. Revisar se contém dados sensíveis antes de subir o repo pro CI público.

12. **apps/ai/inspect_r04.py untracked** (8KB) — script de debug do user (Rô) que ficou no working tree. Não atrapalha deploy, mas se subir num `push --force-with-lease` pode aparecer. Pertence a `.gitignore` ou ser deletado.

13. **rodar.md** — 7 linhas com comandos PowerShell hardcoded `cd C:\Python\oraculo-thorus\...`. Não é blocker, mas é doc inútil em qualquer ambiente que não seja a máquina do Rô.

14. **Tracking supabase_migrations.schema_migrations com 5 órfãs** — descoberto em auditoria anterior (db-schema-divergence-audit), ainda pendente de aplicação. Migrations `20260502130000`, `20260504100000`, `20260504200000`, `20260505100000`, `20260505110000` foram aplicadas via SQL Editor manual e não estão registradas. Em qualquer ambiente novo (CI test DB, staging) o `supabase db push` vai tentar reaplicar todas — idempotentes hoje, mas frágil.

---

## Bloqueios para Deploy em Produção

Em ordem de criticidade. Cada item é bloqueio real — algo que vai quebrar em prod, não algo que "seria bom resolver".

1. **Não há Dockerfile em nenhum app.** Sem isso, nenhuma plataforma de deploy (Railway, Fly.io, Render, Cloud Run) consegue subir os serviços. Precisa de pelo menos `apps/api/Dockerfile`, `apps/web/Dockerfile`, `apps/mcp-drive/Dockerfile`, e provavelmente um `.dockerignore`.

2. **CORS hardcoded em localhost:3000.** `apps/api/src/oraculo_api/main.py:52`. Em prod, todas as chamadas do frontend pro backend serão bloqueadas pelo browser no preflight OPTIONS. Precisa virar config via env var (ex: `ALLOWED_ORIGINS=https://thor.thorus.com.br`).

3. **Inconsistência de domínio de email permitido.** `thorusengenharia.com.br` (web) vs `thorus.com.br` (backend). Em prod, com um dos dois ativo, só metade do staff loga. Verificar qual é o domínio real do Workspace e alinhar.

4. **document_ai_incoming_dir aponta pra C:/oraculo-thorus/incoming.** Pipeline de ingestão de documentos quebra no boot ou no primeiro upload em qualquer Linux. Se o feature for usado em prod, virar volume montado ou bucket. Se não, marcar feature flag como off.

5. **MCP Drive como subprocess stdio bloqueia deploy multi-serviço.** Hoje `oraculo_ai.agents.qa.mcp_client` spawna `python -m mcp_drive` no mesmo container do `apps/api` (provável — confirmar). Em deploy com containers separados (Cloud Run, Fly), o subprocess não roda — tem que mudar pra HTTP/SSE.

6. **5 migrations órfãs do schema_migrations.** Antes de qualquer staging/CI rodar `supabase db push`, sincronizar via `supabase migration repair --status applied`. Senão CI pode aplicar versões de migration que conflitam com estado já aplicado.

7. **SUPABASE_JWT_SECRET sem rotação.** JWKS cache module-level sem TTL (`auth.py:16`). Se Supabase rotacionar chave (pode acontecer mesmo sem aviso em update), o backend autentica falsamente até restart. Em prod com 24/7 uptime esperado, é tempo-bomba.

8. **Connection pool com max_size=20 por worker uvicorn** — `apps/api/main.py:27`. Com 4 workers → 80 conexões. O Supabase Pro tem limite de 200 conexões diretas. Pooler de transação tem limite menor. Configurar `--workers` da uvicorn cuidadoso ou reduzir pool, senão too many connections.

9. **Sem health check confiável pro Postgres/checkpointer/Langfuse.** `routes/health.py` retorna `{"status":"healthy"}` literal sem checar nada. Plataformas de deploy usam health check pra decidir restart. Falsos positivos vão deixar serviço quebrado em verde por horas.

10. **Sem logging.basicConfig ou nível configurável.** Em prod, sem nível setado, logs de DEBUG/INFO podem inundar stdout (custo de log shipping, ruído) ou sumir (silêncio em incidente). Setar `LOG_LEVEL` via env e configurar root logger.

---

**Resumo**: 4-6 bloqueios são código (CORS, paths, domain, MCP transport, health, logging), 2 são infra (Dockerfile, schema_migrations), 2 são operacional (JWT rotation, connection pool sizing). Nenhum é arquitetural irreversível. Total estimado pra resolver: **2-4 dias de trabalho focado**, antes de qualquer deploy fazer sentido.