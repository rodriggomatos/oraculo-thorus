# mcp-drive

MCP server (Model Context Protocol) que dá ao agente Thor (`apps/ai`) awareness READ-ONLY do Google Drive Thórus `107_PROJETOS 2026` (`0AGS3i6FJiluJUk9PVA`).

## Tools expostas

| Tool | Pra que serve |
|---|---|
| `find_lista_definicoes(project_number)` | Encontra a planilha LDP de um projeto (resolve `.gsheet` direto ou `.txt` com link) |
| `find_atas(project_number)` | Lista atas de reunião do projeto |
| `find_vof_revisoes(project_number, discipline?, only_approved?)` | Lista revisões VOF (com filtro de disciplina e status `_TEC OK`) |
| `find_arquivos_externos(project_number, source?)` | Arquivos recebidos de terceiros (arquiteto, estrutural, etc.) |
| `list_project_files(project_number, category?, discipline?, has_status?)` | Tool genérica com filtros |

Todas READ-ONLY. Retornam Pydantic com `name`, `path`, `web_view_link` (URL clicável), `modified_time` e metadata extraída do nome (disciplina, revisão, data, status).

## Rodando standalone

```bash
cd apps/mcp-drive
uv sync
uv run python -m mcp_drive
```

O servidor escuta MCP via stdio. Pra teste manual sem MCP client:

```bash
uv run python scripts/test_tools.py
```

## Configuração

Variáveis (em `.env` raiz do monorepo, mais `apps/mcp-drive/.env.example`):

- `GOOGLE_SERVICE_ACCOUNT_JSON` — JSON da service account ou caminho pro arquivo (compartilhado com apps/ai)
- `THORUS_DRIVE_ROOT_ID` — default `0AGS3i6FJiluJUk9PVA`
- `MCP_DRIVE_CACHE_TTL_SECONDS` — default `300`
- `MCP_DRIVE_LOG_LEVEL` — default `INFO`

## Como o Thor consome

Em `apps/ai`, instalar `langchain-mcp-adapters` e configurar `MultiServerMCPClient` apontando pro mcp-drive (transport stdio). Tools ficam disponíveis ao agente como nativas.

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "drive": {
        "command": "uv",
        "args": ["--directory", "apps/mcp-drive", "run", "python", "-m", "mcp_drive"],
        "transport": "stdio",
    }
})
tools = await client.get_tools()
```

Veja `apps/ai/src/oraculo_ai/agents/qa/mcp_client.py` pro wiring real.

## Princípios não-negociáveis

- READ-ONLY (zero chamadas de write API). Validação de scope no boot.
- Logs estruturados no stderr (stdio MCP usa stdout pro protocolo).
- Async em tudo. Type hints. Pydantic em vez de dict crus.
- Backend abstrato (`FileBackend` Protocol) — Drive API hoje, possivelmente filesystem cache amanhã.
- Classifiers declarativos — adicionar categoria = adicionar entrada no registry.
