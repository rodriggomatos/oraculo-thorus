# Eval Suite — Thor

Bateria de eval que roda contra o agente Thor real (Groq + MCP Drive + Postgres) pra detectar regressão antes de mexer em prompt/tools.

## Pré-requisitos

- `apps/ai` sincronizado: `cd apps/ai && uv sync`
- `apps/mcp-drive` sincronizado: `cd apps/mcp-drive && uv sync`
- `.env` raiz com `GROQ_API_KEY`, `OPENAI_API_KEY` (embeddings), `DATABASE_URL`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `THORUS_DRIVE_ROOT_ID`

## Como rodar

```bash
cd apps/ai

uv run pytest tests/eval -v                  # tudo, verbose
uv run pytest tests/eval -k "tristate"       # filtra por substring no id
uv run pytest tests/eval -m eval             # só eval (não unit)
uv run pytest tests/eval -m "not eval"       # só unit
uv run pytest tests/eval -k "embraplan"      # 1 caso específico
```

A bateria custa uma rodada de LLM por caso (Groq Llama via LiteLLM). Pra 25 casos é alguns segundos a alguns minutos dependendo do throughput do Groq.

## Como adicionar caso

Pega o YAML mais próximo do que você está testando (`datasets/*.yaml`) e adiciona:

```yaml
cases:
  - id: meu_caso_unico
    description: O que o caso valida em prosa
    input: "pergunta exata pro Thor"
    expected:
      tool_called: find_lista_definicoes
      tool_args:
        project_number: 26003
      response_contains:
        - "Embraplan"
      response_NOT_contains:
        - "https://docs.google.com/spreadsheets"
      response_regex:
        - "(?i)recomendação"
    tags:
      - my_category
```

`id` precisa ser único na suíte. Pydantic valida o schema no load — campo extra ou tipo errado quebra a coleção.

## Schema de assertions

| Campo | Tipo | Significado |
|---|---|---|
| `tool_called` | `str` | Nome da tool que DEVE ter sido chamada |
| `tool_args` | `dict` | Subset de args que a tool deve ter (partial match — outros args ignorados) |
| `tool_NOT_called` | `str` | Tool que NÃO deve ter sido chamada |
| `response_contains` | `list[str]` | Substrings obrigatórias |
| `response_NOT_contains` | `list[str]` | Substrings proibidas |
| `response_regex` | `list[str]` | Regex que precisa matchear (re.search) |

Todos opcionais — combine livremente.

## Troubleshooting

**"Failed to load drive tools"**: `apps/mcp-drive` não está sincronizado, ou `THORUS_DRIVE_ROOT_ID` ausente.

**Erro de conexão Postgres**: `DATABASE_URL` não responde — `search_definitions`/`register_definition`/`list_projects` falham. Outros casos seguem.

**"Rate limit"**: Groq tem rate limit free tier. Espalhe a bateria ou rode subset.

**Resposta vazia**: Groq pode retornar AIMessage sem conteúdo quando se enrola em tool calls. O runner trata como string vazia, e os asserts `response_contains` falham com mensagem clara.

## Tom

Sem mock — bateria roda contra o agente real. Custa $$ (Groq free tier hoje), mas garante que a regressão detectada é REAL, não artefato de mock desatualizado.

Asserts são deliberadamente simples (substring + regex). Quando o limite do substring matching aparecer (ex: refusal com substring proibida no meio), refine a regex ou parte o caso em dois.

## Flakiness

Mesmo com `temperature=0`, Groq Llama tem variação não-determinística entre runs. Tipicamente 1-2 casos ambíguos/adversariais oscilam entre passar e falhar dependendo do fraseamento que o modelo escolher. Padrão observado:

- Casos com regex de fraseamento livre (`ambiguity_*`, `adversarial_*`): margem ~5%
- Casos com `tool_called` ou números fixos: estáveis 100%

Mitigações aplicadas:
- Regex amplos com várias alternativas (`qual projeto|preciso identificar|me informar|...`)
- Sem `response_NOT_contains` em adversarial (Thor pode mencionar termo no contexto da recusa)
- Pra um caso falhar legitimamente, ele precisa quebrar em runs consecutivos. Run isolado verde = não é regressão real.

Se um caso ficar persistentemente flakey, refine o regex OU parta o caso em dois (um pra cada fraseamento aceitável).
