# oraculo-api

HTTP API do Oráculo Thórus (FastAPI + LangGraph). Roteia perguntas pro agente Q&A, dispara ingestões de documentos e expõe healthcheck.

## Rodar em dev

**Use o script `scripts/dev.ps1`** (PowerShell). Ele:

1. Mata processos que estejam escutando na porta 8000 (zumbis de runs anteriores).
2. Limpa `__pycache__/` recursivamente em `apps/api/src` e `apps/ai/src`.
3. Sobe `uvicorn` com `--reload` E **`--reload-dir`** apontando explicitamente pra `apps/api/src` E `apps/ai/src`.

```powershell
powershell -ExecutionPolicy Bypass -File apps\api\scripts\dev.ps1
```

ou, se o ExecutionPolicy permitir scripts locais:

```powershell
.\apps\api\scripts\dev.ps1
```

### Por que NÃO usar o comando direto

```powershell
uv run uvicorn oraculo_api.main:app --reload --port 8000
```

Esse comando **só** monitora `apps/api/` (o cwd). Como `apps/api` importa `oraculo-ai` (`[tool.uv.sources] oraculo-ai = { path = "../ai", editable = true }`), qualquer mudança em `apps/ai/src/oraculo_ai/...` (agente, retrieval, ingestion, etc.) **não dispara reload** — uvicorn nem fica sabendo do arquivo.

Sintoma: você muda código em `apps/ai/src/...`, recarrega o navegador, e a API ainda responde com a versão antiga. Isso já causou bug-caça falsa (filtros stale, mudanças que "não pegavam").

O `--reload-dir` adiciona ambos os pacotes ao watcher. Como `watchfiles` (>=1.x, vem com `uvicorn[standard]`) já está instalado, o reload é eventual baseado em filesystem events — não polling.

### Validação rápida

Com a API rodando via `dev.ps1`, edite qualquer função em `apps/ai/src/oraculo_ai/agents/qa/repository.py` (ex.: troque uma string de SQL e salve). O console do uvicorn deve imprimir:

```
WARNING:  WatchFiles detected changes in 'apps/ai/src/oraculo_ai/agents/qa/repository.py'. Reloading...
INFO:     Shutting down
INFO:     Started server process [...]
INFO:     Application startup complete.
```

Se isso **não** aparecer, o `--reload-dir` não pegou. Confirme que o caminho passado como `--reload-dir` no `dev.ps1` aponta pra um diretório existente (`Test-Path` deve retornar `True`).

## Endpoints principais

- `GET /health` — liveness (público)
- `GET /auth/me` — perfil do usuário logado (requer Bearer token)
- `POST /query` — pergunta ao agente Thor (requer Bearer token)
- `GET /projects` — lista projetos ativos
- `POST /documents/extract-from-sheets` — ingestão de LDP via Google Sheets
- `POST /documents/extract-ldp` — ingestão de LDP via documentos do cliente

## Observações

- A porta padrão é `8000`. Se mudar, ajuste o frontend (`NEXT_PUBLIC_AI_API_URL`).
- O CORS está aberto pra `http://localhost:3000` (Next dev server).

## Auth — Google OAuth via Supabase

A API valida JWT do Supabase e exige domínio `@thorus.com.br`. Setup:

### 1. Configurar Google OAuth no Supabase Studio

1. **Google Cloud Console** (`console.cloud.google.com`):
   - Crie projeto (ou use existente)
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Web application
   - Authorized redirect URIs: `https://YOUR-PROJECT.supabase.co/auth/v1/callback`
   - Anote: `Client ID`, `Client Secret`

2. **Supabase Studio** → Authentication → Providers → Google:
   - Enable Google
   - Client ID + Client Secret (do passo 1)
   - Save

3. **Supabase Studio** → Authentication → URL Configuration:
   - Site URL: `http://localhost:3000` (dev) ou URL de produção
   - Redirect URLs: adicionar `http://localhost:3000/auth/callback` e o de produção

4. **Restringir domínio Thórus** — duas camadas, defesa em profundidade:
   - **Trigger no banco** (já configurado pela migration `20260502100000_add_auth_and_audit.sql`): a função `handle_new_user` rejeita signup de e-mail fora de `@thorus.com.br`.
   - **Backend** (FastAPI `auth.py`): valida domínio em todo request, retorna 403 se não bater.
   - **Frontend** (middleware): também valida e desloga + redireciona pra `/auth/error` se domínio errado.
   - **Google OAuth `hd` param**: o login page passa `hd: 'thorus.com.br'` via `signInWithOAuth` pra que Google só ofereça contas Workspace Thórus na tela de seleção (UX — não é segurança).

### 2. Configurar variáveis de ambiente

No `.env` raiz:

```bash
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxx
SUPABASE_SECRET_KEY=sb_secret_xxx
SUPABASE_JWT_SECRET=eyJhbG...   # Settings → API → JWT secret (HS256)
# OU pra projetos novos com asymmetric JWT:
SUPABASE_JWKS_URL=https://YOUR-PROJECT.supabase.co/auth/v1/.well-known/jwks.json
ALLOWED_EMAIL_DOMAIN=thorus.com.br
```

No `apps/web/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxx
```

### 3. Aplicar migration

```bash
supabase db push
```

Ou via Supabase Studio → SQL Editor → cole o conteúdo de `supabase/migrations/20260502100000_add_auth_and_audit.sql`.

A migration é idempotente — pode rodar 2x.

### 4. Validar setup

```bash
# 1. System user existe
psql "$DATABASE_URL" -c "SELECT id, email, role FROM user_profiles WHERE role = 'system';"
# Deve retornar 00000000-0000-0000-0000-000000000001

# 2. Definitions antigas migradas
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM definitions WHERE created_by_user_id IS NULL;"
# Deve retornar 0

# 3. Frontend bloqueia sem login
# Acesse http://localhost:3000 → redireciona pra /login

# 4. Login com email não-thorus → /auth/error?reason=domain
```

### 5. Criar usuário admin manualmente

Após primeiro login Google de um colaborador, promover a admin via SQL:

```sql
UPDATE user_profiles SET role = 'admin' WHERE email = 'admin@thorus.com.br';
```

### 6. Testar fluxo de INSERT com audit trail

```bash
# Login com user X via UI
# Pergunte no chat: "registra que evaporadora é Cassete no projeto 26002"
# Verifique:
psql "$DATABASE_URL" -c "
  SELECT d.item_code, d.opcao_escolhida, u.email, u.name
  FROM definitions d
  JOIN user_profiles u ON u.id = d.created_by_user_id
  ORDER BY d.created_at DESC LIMIT 1;
"
# Deve mostrar email/nome do user X que registrou
```

A resposta do Thor menciona o autor: "Registrado por Rodrigo Matos (rodrigo@thorus.com.br) em 2026-05-02."

## Cities seed

A tabela `city` (criada pela migration `20260504200000_create_city_table.sql`) começa vazia. O combobox de cidade do form "Criar projeto novo" lê dela. Pra popular com os ~5570 municípios IBGE:

```bash
cd apps/ai
uv run python scripts/seed_cities.py
```

O script é idempotente (`ON CONFLICT (ibge_code) DO NOTHING`) — rodar de novo é seguro e só insere o que faltar. Demora ~10-30s dependendo da rede e da latência do Supabase.

Validar:

```sql
SELECT COUNT(*) FROM city;
-- ~5570 (varia conforme atualizações IBGE)

SELECT estado, COUNT(*) FROM city GROUP BY estado ORDER BY estado;
-- breakdown por UF
```

Quando rodar essa seed:

- Após aplicar a migration `20260504200000_create_city_table.sql` em ambiente novo.
- Periodicamente (semestral?), se quiser pegar municípios novos que IBGE adicionou. Não há municípios sendo removidos, então só faz INSERT — sem efeito colateral.
