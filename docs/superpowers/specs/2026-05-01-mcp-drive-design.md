# MCP Drive — Awareness do Google Drive pro Thor

**Data:** 2026-05-01
**Autor:** Rô + Claude (auto mode)
**Status:** aprovado pra implementação

## Objetivo

MCP server (Model Context Protocol da Anthropic) que dá ao agente Thor (`apps/ai`) awareness do Drive `107_PROJETOS 2026` (`0AGS3i6FJiluJUk9PVA`). Tools focadas em descoberta/pesquisa READ-ONLY de arquivos relevantes pra cada projeto Thórus.

## Casos de uso (Fase 1)

- "Onde está a lista de definições do Embraplan?" → URL do LDP
- "Tem ata de reunião do Castelo Vela?" → lista atas com URLs
- "Qual o último VOF aprovado de hidráulico do 26009?" → procura `*VOF*HID*_TEC OK*`
- "Manda os arquivos recebidos do arquiteto do 26008" → lista `04 ARQUIVOS EXTERNOS/Arquitetônico/recebido*`

## Decisões arquiteturais

| Ponto | Decisão | Motivação |
|---|---|---|
| Localização | `apps/mcp-drive/` standalone (uv project, fora do pnpm-workspace) | Apps isolados; mcp-drive é um servidor independente |
| MCP transport | stdio | Padrão; Thor spawna subprocess via `MultiServerMCPClient` |
| Scope OAuth | `drive.readonly` | Permite ler `.txt` com link (caso 26009); coerente com `drive_scanner.py` |
| Backend abstraction | `Protocol FileBackend` + `GoogleDriveBackend` única impl | Trocar = trocar bootstrap |
| project_number → folder_id | Drive search por `name contains "<num> - "`, cache LRU/TTL em memória | Sem schema DB extra |
| Classifier registry | Lista de `Classifier` dataclasses (path_matcher + name_matcher + extra_filters) | Adicionar categoria = entrada |
| Tool granularity | 5 tools específicas + 1 generic (`list_project_files`) | Como na spec |
| Drive root ID | env `THORUS_DRIVE_ROOT_ID`, default `0AGS3i6FJiluJUk9PVA` | Configurável |
| Reuse `drive_scanner.py` | Não move; reimplementa autônomo | Princípio: mcp-drive standalone |
| Cache | TTL=300s pra (project_number→folder) e (folder_id, query) → list | Drive API tem rate limit; chamadas repetidas em sessões longas |
| Project não-encontrado | Retorna `{found: false, project_number}` | Estruturado, não levanta exceção |

## Estrutura de arquivos

```
apps/mcp-drive/
├── pyproject.toml
├── README.md
├── .python-version
├── .env.example
├── src/mcp_drive/
│   ├── __init__.py
│   ├── __main__.py            # python -m mcp_drive
│   ├── config.py              # pydantic-settings
│   ├── logging.py             # stderr structured logs (stdio MCP)
│   ├── auth.py                # service account + scope validation
│   ├── cache.py               # async TTL/LRU helper
│   ├── server.py              # FastMCP setup + tool registration
│   ├── backend.py             # Protocol + FileNode + GoogleDriveBackend
│   ├── disciplines.py         # alias map (ELE → Elétrico, etc.)
│   ├── parsing.py             # extrai disciplina/revisão/data/status do nome
│   ├── classifiers.py         # registry de categorias
│   ├── schemas.py             # Pydantic responses
│   ├── project_resolver.py    # project_number → folder_id (com cache)
│   └── tools.py               # 5 tools + list_project_files
├── scripts/
│   └── test_tools.py          # validação manual contra Drive real
└── tests/
    └── __init__.py
```

## Componentes

### `backend.py` — abstração de filesystem

```python
class FileNode(BaseModel):
    id: str
    name: str
    mime_type: str
    parent_id: str | None
    web_view_link: str | None
    modified_time: datetime | None
    size: int | None

class FileBackend(Protocol):
    async def get_node(self, node_id: str) -> FileNode | None
    async def list_children(
        self, parent_id: str, *, mime_types: Sequence[str] | None = None
    ) -> list[FileNode]
    async def search(
        self, query: str, *, parent_ids: Sequence[str] | None = None
    ) -> list[FileNode]
    async def read_text(self, file_id: str) -> str | None
```

`GoogleDriveBackend` envelopa `googleapiclient.discovery` (sync) com `asyncio.to_thread`.

### `classifiers.py` — registry declarativo

```python
@dataclass(frozen=True)
class Classifier:
    name: str                                    # "lista_definicoes", etc.
    path_segments: tuple[tuple[str, ...], ...]   # caminhos relativos à pasta de projeto
    name_pattern: re.Pattern | None              # regex no nome
    mime_types: tuple[str, ...] | None
    exclude_path_segments: tuple[str, ...] = ()  # blacklist (e.g., "03 OBSOLETOS")

CLASSIFIERS: list[Classifier] = [
    Classifier(name="lista_definicoes", path_segments=(("02 TRABALHO", "DEFINIÇÕES"), ...), ...),
    Classifier(name="ata_reuniao", path_segments=(("02 TRABALHO", "DEFINIÇÕES", "Atas de reunião"),), ...),
    Classifier(name="vof_revisao", name_pattern=re.compile(r"-VOF-", re.I), exclude_path_segments=("03 OBSOLETOS",)),
    Classifier(name="entrega_executivo_pdf", path_segments=(("01 ENTREGAS-APROVAÇÕES", "EXECUTIVO"),), mime_types=("application/pdf",)),
    Classifier(name="arquivo_externo", path_segments=(("04 ARQUIVOS EXTERNOS",),)),
]
```

### `parsing.py` — metadata do nome

Extrai:
- `disciplina`: matchea sigla (ELE, HID, PCI, CLI, COM, SDR, SAN, SPDA, FUR, PIS) com word boundaries
- `revisao`: regex `R\d{2}` ou `RV\d{2}`
- `data`: `\d{2}-\d{2}-\d{4}` ou `\d{2}-\d{2}-\d{2}`
- `status`: `_TEC OK` (técnico), `_PROJ OK` ou `_PRO OK` (projeto)

Retorna `FileMetadata` (Pydantic).

### `tools.py` — 5+1 tools

Todas async, decoradas com `@mcp.tool()`. Retornam `ToolResult` (Pydantic) com `query`, `found`, `count`, `items`. Cada item é `FileResult` (id, name, path, web_view_link, modified_time, mime_type, metadata).

Tools:
- `list_project_files(project_number, category?, discipline?, has_status?)` — generic
- `find_lista_definicoes(project_number)` — `.gsheet` em `02 TRABALHO/DEFINIÇÕES/`; fallback `.txt` com link, baixa conteúdo, extrai sheet_id, retorna URL final do spreadsheet
- `find_atas(project_number)` — arquivos em `02 TRABALHO/DEFINIÇÕES/Atas de reunião/`
- `find_vof_revisoes(project_number, discipline?, only_approved?)` — arquivos com `-VOF-`, fora de `03 OBSOLETOS`
- `find_arquivos_externos(project_number, source?)` — `04 ARQUIVOS EXTERNOS/<source>/(Baixado|recebido|recebeido) <data>/`

### `project_resolver.py`

```python
async def resolve_project(
    backend: FileBackend, drive_root_id: str, project_number: int
) -> ProjectFolder | None:
    # cache: dict[int, tuple[ProjectFolder, expires_at]]
    # cache miss: backend.search(f"name contains '{project_number} - '", parent_ids=[drive_root_id])
    # filter results to those starting with f"{project_number} - "
    # cache hit + TTL
```

### Blacklist

Aplicada em todas as travessias:
- Pasta `05 MODELOS` → não desce (apenas nível 0)
- Extensões `.rvt`, `.bak`, `.tmp`, `.dwl`, `.dwl2` → ignora
- Pastas `xx-xx-xx*`, `LIMPANDO`, `Limpo`, `Nova pasta` → ignora descida

### Auth + scope validation

Ao boot, `auth.py`:
1. Carrega service account JSON
2. Constrói `Credentials` com scope `drive.readonly`
3. Faz `files.get(fileId=DRIVE_ROOT_ID, supportsAllDrives=True)` pra validar acesso
4. Se conseguir lerr, OK; se 403 "insufficient scope" ou similar, falha startup

Detecção de scope de escrita: ao construir o `Credentials`, validar que `scopes` da config NÃO contém nada que termine em `.write`, `/drive` (escopo full), `.file`. Se houver, log CRITICAL no stderr e abort.

## Fluxo de dados

1. Thor envia chat → agent dispara tool MCP via `MultiServerMCPClient`
2. MCP server recebe request via stdio
3. `tools.py` resolve project_number → folder_id (via `project_resolver`, cache hit/miss)
4. Aplica `Classifier` apropriado pra determinar paths/filtros
5. `backend.list_children` ou `backend.search` no Drive
6. `parsing.py` extrai metadata por arquivo
7. Pydantic `ToolResult` serializado de volta via stdio

## Integração Thor

1. `apps/ai/pyproject.toml`: adiciona `langchain-mcp-adapters>=0.1.0,<1.0.0`
2. Novo módulo `apps/ai/src/oraculo_ai/agents/qa/mcp_client.py`:
   - Lazy init de `MultiServerMCPClient` apontando pro mcp-drive (stdio: `uv --directory ../mcp-drive run python -m mcp_drive`)
   - `async def get_drive_tools() -> list[BaseTool]`
   - Falha graciosa: se MCP não inicia, retorna `[]` e loga warning (não quebra Thor)
3. `agents/qa/agent.py`: importa `get_drive_tools()` e concatena à lista
4. System prompt: addendum descrevendo as 5 tools de Drive (quando usar cada)

## Erros e edge cases

- Project não existe no Drive → tool retorna `ToolResult(found=False, ...)` com mensagem amigável
- Drive API timeout → retry 1x, depois retorna erro estruturado
- `.txt` link sem URL parseável → ignora arquivo, log warning, continua
- Pasta vazia (e.g. `find_atas` sem atas) → `ToolResult(found=True, count=0, items=[])`
- Token de service account expirado → google-auth refresha automaticamente
- Race em cache (concorrência baixa em chat) → ignora; consistência eventual aceitável

## Logging

- Stderr (stdio MCP usa stdout pro protocolo)
- Format estruturado: `[mcp-drive] LEVEL component: message {key=value}`
- Níveis: DEBUG (cache hit/miss, queries), INFO (boot, tool calls), WARNING (.txt sem link, file ignorado), CRITICAL (scope inválido)
- Rastreamento básico: `tool_name`, `project_number`, `duration_ms`, `result_count`

## Testes

- Unit: `parsing.py` (regex), `classifiers.py` (matching), `cache.py` (TTL)
- Manual integration: `scripts/test_tools.py` chama as 5 tools contra Drive real com:
  - 26003 (Embraplan) — LDP `.gsheet`, 3 atas
  - 26009 (Castelo Vela) — LDP via `.txt`, sem atas, VOFs com `_TEC OK`
  - 26008 (Castelo Gard) — arquivos externos arquiteto

## Validação readonly

No boot do MCP server:
1. Loga scopes lidos da credencial
2. Aborta se algum scope for de escrita (qualquer coisa fora do whitelist `[drive.readonly, drive.metadata.readonly, spreadsheets.readonly]`)
3. Faz `files.get(DRIVE_ROOT_ID, fields="id,name")` pra validar conexão

## Out of scope (Fase 1)

- Indexação semântica do conteúdo dos arquivos (futuro: `read_text` pra ingestão)
- Watch/sync incremental
- Caching cross-process / distribuído
- Tools de write/move/delete
- Knowledge graph (entidades extraídas)

## Referências

- MCP Python SDK: `mcp` package, `mcp.server.fastmcp.FastMCP`
- langchain-mcp-adapters: `MultiServerMCPClient`
- `apps/ai/src/oraculo_ai/document_ai/drive_scanner.py` — referência de auth/scope/Drive API
- `apps/ai/src/oraculo_ai/agents/qa/agent.py` — padrão de tool registration
