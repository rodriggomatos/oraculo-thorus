# Deploy na Railway — Oráculo Thórus

Guia passo a passo pra subir os 3 serviços do monorepo (`web`, `api`,
`mcp-drive`) na Railway.

> **Status**: prep concluído pelas Fases 1-5. Nenhum deploy real foi
> feito ainda — esse documento é o roteiro pra Fase 6.

## Pré-requisitos

- Conta Railway com payment method ativo (deploy não roda em free tier).
- Repo conectado ao GitHub (`rodriggomatos/oraculo-thorus`).
- Service account JSON do Google (conteúdo inline, não path no FS).
- Acesso ao Supabase project:
  - `SUPABASE_URL`
  - `SUPABASE_PUBLISHABLE_KEY` (formato novo `sb_publishable_…`)
  - `SUPABASE_SECRET_KEY` (formato novo `sb_secret_…`)
  - `SUPABASE_JWT_SECRET` ou `SUPABASE_JWKS_URL`
  - `DATABASE_URL` (use **transaction pooler** do Supabase, porta 6543)
  - Opcional: `DATABASE_URL_QUERY_RO` (role `thor_query_ro`, mesma porta 6543)
- Acesso ao Langfuse cloud:
  - `LANGFUSE_PUBLIC_KEY`
  - `LANGFUSE_SECRET_KEY`
  - `LANGFUSE_HOST` (ex: `https://cloud.langfuse.com`)
- Acesso ao Anthropic: `ANTHROPIC_API_KEY`
- Acesso ao OpenAI (embeddings): `OPENAI_API_KEY`
- Token forte aleatório pro MCP Drive:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

## Topologia

3 serviços na Railway, mesmo projeto:

| Service     | Public URL | Private URL                              | Porta |
|-------------|-----------|------------------------------------------|-------|
| `web`       | Sim       | —                                        | 3000  |
| `api`       | Sim       | `http://api.railway.internal:$PORT`      | 8000  |
| `mcp-drive` | Não       | `http://mcp-drive.railway.internal:$PORT`| 8001  |

`web` chama `api` pela URL pública (HTTPS). `api` chama `mcp-drive` pela
URL privada (`railway.internal`, plain HTTP, latência baixíssima).

## Passo 1 — Criar projeto Railway

1. Dashboard Railway → **New Project** → **Deploy from GitHub repo**.
2. Selecione `rodriggomatos/oraculo-thorus`. Branch `master`.
3. Renomeie o projeto pra `oraculo-thorus`.

Por padrão, Railway tenta detectar e provisionar tudo. Cancele essa
detecção e crie cada serviço manualmente — precisa apontar Dockerfile +
build context corretos.

## Passo 2 — Provisionar `mcp-drive`

**Settings → Source**:
- Repository: `rodriggomatos/oraculo-thorus`
- Branch: `master`
- Root Directory: `/` (raiz do monorepo)
- Build:
  - Builder: **Dockerfile**
  - Dockerfile path: `apps/mcp-drive/Dockerfile`
- Watch paths (opcional, evita rebuild a cada push em outros apps):
  - `apps/mcp-drive/**`

**Variables**:

| Variável                       | Valor                                     |
|--------------------------------|-------------------------------------------|
| `MCP_DRIVE_TRANSPORT`          | `streamable-http`                         |
| `MCP_DRIVE_HOST`               | `0.0.0.0`                                 |
| `MCP_DRIVE_AUTH_TOKEN`         | `<gerar token forte — guarde-o>`          |
| `GOOGLE_SERVICE_ACCOUNT_JSON`  | `<JSON inline>`                           |
| `THORUS_DRIVE_ROOT_ID`         | `0AGS3i6FJiluJUk9PVA`                     |
| `MCP_DRIVE_CACHE_TTL_SECONDS`  | `300`                                     |
| `MCP_DRIVE_LOG_LEVEL`          | `INFO`                                    |

**Não defina** `MCP_DRIVE_PORT` — o Dockerfile lê `$PORT` da Railway.

**Networking**:
- **Public Networking**: desligado (mcp-drive é interno).
- **Private Networking**: ligado (default na Railway).

Após o primeiro deploy, copie o token gerado e o nome interno
(`mcp-drive.railway.internal`) — vão pro service `api` no próximo passo.

## Passo 3 — Provisionar `api`

**Settings → Source**:
- Root Directory: `/`
- Builder: **Dockerfile**
- Dockerfile path: `apps/api/Dockerfile`
- Watch paths: `apps/api/**`, `apps/ai/**`

**Variables**:

```env
ENV=production
LOG_LEVEL=INFO

# CORS — SUBSTITUIR depois que o web ganhar URL Railway
ALLOWED_ORIGINS=https://<web-railway-url>

# DB
DATABASE_URL=postgresql://postgres.<ref>:<senha>@<host>:6543/postgres
DATABASE_URL_QUERY_RO=postgresql://thor_query_ro:<senha>@<host>:6543/postgres
DB_POOL_MAX_SIZE=10
DB_POOL_MIN_SIZE=2

# Supabase
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxx
SUPABASE_SECRET_KEY=sb_secret_xxx
SUPABASE_JWT_SECRET=<jwt secret HS256 ou>
SUPABASE_JWKS_URL=https://<ref>.supabase.co/auth/v1/.well-known/jwks.json
ALLOWED_EMAIL_DOMAIN=thorusengenharia.com.br

# LLM
LLM_PROVIDER=anthropic
LLM_MODEL_FAST=anthropic/claude-haiku-4-5
LLM_MODEL_SMART=anthropic/claude-sonnet-4-6
ANTHROPIC_API_KEY=<sk-ant-...>

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
OPENAI_API_KEY=<sk-...>

# Langfuse
LANGFUSE_PUBLIC_KEY=<pk-lf-...>
LANGFUSE_SECRET_KEY=<sk-lf-...>
LANGFUSE_HOST=https://cloud.langfuse.com

# MCP Drive — aponta pro service interno
MCP_DRIVE_TRANSPORT=streamable-http
MCP_DRIVE_URL=http://mcp-drive.railway.internal:8001/mcp
MCP_DRIVE_AUTH_TOKEN=<MESMO token gerado no Passo 2>

# Google (mesma SA que mcp-drive usa)
GOOGLE_SERVICE_ACCOUNT_JSON=<JSON inline>
THORUS_DRIVE_ROOT_ID=0AGS3i6FJiluJUk9PVA
THORUS_DRIVE_TEMPLATE_FOLDER_ID=1IU6InjaYd74yNtF3kREke-Ywdq4sXoXb
```

**Não defina** `PORT` — Railway injeta automaticamente. Dockerfile lê e
passa pro uvicorn.

> A `MCP_DRIVE_URL` aponta pra `mcp-drive.railway.internal:8001` mesmo
> que o serviço esteja rodando em outra porta interna (`$PORT` da Railway).
> Confirme no dashboard do mcp-drive qual porta interna ele está
> escutando e ajuste o `:8001` pra esse valor — ou padronize via
> `RAILWAY_TCP_PROXY_PORT`.

**Networking**:
- **Public Networking**: ligado. Railway gera URL `https://api-<id>.up.railway.app`.
- (Opcional) Custom domain: `api.thor.thorus.com.br`.

## Passo 4 — Provisionar `web`

**Settings → Source**:
- Root Directory: `/`
- Builder: **Dockerfile**
- Dockerfile path: `apps/web/Dockerfile`
- Watch paths: `apps/web/**`

**Variables**:

```env
NODE_ENV=production
NEXT_PUBLIC_AI_API_URL=https://<URL-pública-do-api>
NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxx
```

**Networking**:
- **Public Networking**: ligado.
- (Opcional) Custom domain: `thor.thorus.com.br`.

## Passo 5 — Configurar OAuth/Auth depois do primeiro deploy

Depois que `web` ganhar URL Railway:

1. **Google Cloud Console** → APIs & Services → Credentials → OAuth 2.0
   Client ID:
   - Authorized JavaScript origins: adicione `https://<web>.up.railway.app`
   - Authorized redirect URIs: confirma que tem
     `https://<ref>.supabase.co/auth/v1/callback`

2. **Supabase Dashboard** → Authentication → URL Configuration:
   - Site URL: `https://<web>.up.railway.app`
   - Additional Redirect URLs (lista):
     - `https://<web>.up.railway.app/**`
     - `https://<web>.up.railway.app/auth/callback`

3. **No service `api`** (Railway → Variables): atualize
   `ALLOWED_ORIGINS` com a URL real do web. Redeploy.

4. **Custom domain** (depois): repita 1-3 trocando os hosts. CORS no
   `api` aceita CSV — pode listar os dois durante a transição:
   `ALLOWED_ORIGINS=https://thor.thorus.com.br,https://<web>.up.railway.app`

## Passo 6 — Migrations

Migrations já estão registradas no `schema_migrations` do Supabase.
Pra aplicar mudanças futuras:

```bash
supabase db push --linked
```

A primeira vez no Railway **não precisa rodar migrations** — banco é
o mesmo Supabase Cloud já em uso. Aplicações falam direto via
`DATABASE_URL` (pooler 6543).

## Calibração do pool DB

`workers (uvicorn) × DB_POOL_MAX_SIZE = total de conexões por instância`

O `apps/api/main.py` cria **2 pools** por processo:
1. `init_db()` (oraculo_ai) — pool genérico.
2. LangGraph `AsyncPostgresSaver` — pool dedicado pro checkpointer.

Ambos usam `DB_POOL_MAX_SIZE`. Total real por worker = `2 × DB_POOL_MAX_SIZE`.

Limites Supabase Pro:
- **Direct** (porta 5432): 200 conexões totais.
- **Transaction pooler** (porta 6543): muito maior, com 1-2ms de overhead.

**Recomendação Railway** (1 instância api):
| Workers | DB_POOL_MAX_SIZE | Total conexões | Margem (vs 200) |
|---------|------------------|----------------|-----------------|
| 1       | 10               | 20             | 90% folga       |
| 2       | 10               | 40             | 80% folga       |
| 4       | 10               | 80             | 60% folga       |

Use **transaction pooler (6543)** sempre. `mcp-drive` não consome DB.
Outras conexões (Supabase Auth, Studio, scripts admin) costumam consumir
< 30 conexões.

## Troubleshooting

### "Application failed to respond"

- Confirme que o Dockerfile expõe `0.0.0.0:$PORT`. Railway só roteia
  pra binds em `0.0.0.0`, não em `127.0.0.1`.
- Cheque os logs do healthcheck. O `api` Dockerfile tem
  `HEALTHCHECK` apontando pro `/health` interno.

### CORS errors no browser

- `ALLOWED_ORIGINS` no `api` precisa incluir a URL exata do `web` (com
  `https://` e sem barra final).
- Após mudar a env var, redeploy o serviço (Railway não recarrega config
  sem restart).

### Login Google retorna `redirect_uri_mismatch`

- Confirme que cadastrou a URL Railway do `web` no Google Cloud Console.
- Confirme que `Authorized redirect URIs` inclui a URL do callback
  Supabase: `https://<ref>.supabase.co/auth/v1/callback`.

### MCP Drive não conecta

- `MCP_DRIVE_URL` no `api` deve apontar pra `*.railway.internal`, não
  pra URL pública.
- `MCP_DRIVE_AUTH_TOKEN` tem que ser **idêntico** nos dois serviços.
- `mcp-drive` falha boot se token vazio — cheque os logs do mcp-drive.
- Caminho do path: `/mcp` (default do FastMCP). URL completa:
  `http://mcp-drive.railway.internal:<porta>/mcp`.

### "DB pool exhausted"

- Aumente `DB_POOL_MAX_SIZE` ou diminua `--workers`.
- Verifique se está usando o pooler (porta 6543), não direct (5432).
- Cheque conexões idle no Supabase Dashboard → Database → Roles.

### Healthcheck falhando

- `api` Dockerfile espera `/health` retornando 200 em até 5s.
- Se DB demorar pra conectar no boot, aumente `--start-period` no
  Dockerfile (atualmente 20s).

### Deploy não rebuildou após push

- Cheque "Watch paths" no service settings. Se `apps/api/**` não bate
  com o caminho do arquivo mudado, build não dispara.
- Force rebuild: Service → Deployments → ⋯ → Redeploy.
