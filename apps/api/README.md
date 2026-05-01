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

- `GET /health` — liveness
- `POST /query` — pergunta ao agente Thor
- `GET /projects` — lista projetos ativos
- `POST /documents/extract-from-sheets` — ingestão de LDP via Google Sheets
- `POST /documents/extract-ldp` — ingestão de LDP via documentos do cliente

## Observações

- A porta padrão é `8000`. Se mudar, ajuste o frontend (`NEXT_PUBLIC_AI_API_URL`).
- O CORS está aberto pra `http://localhost:3000` (Next dev server).
