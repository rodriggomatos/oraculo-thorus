# Relatório — Arquitetura do agente Thor

## 1) System prompt principal

- **Path:** `apps/ai/src/oraculo_ai/agents/qa/agent.py:39-193` — constante `_SYSTEM_PROMPT`
- **Tamanho:** ~155 linhas, ~1.586 palavras / **~2.000-2.500 tokens**. Ocupa metade do `agent.py` (363 linhas).
- **Caráter:** **muito rico em domínio** — não é "você é um assistente". Codifica playbooks específicos: resolução de projeto, sintaxe `@número`, categorias LDP, registro de definição via chat, regras de herança de campo, interpretação de status do `find_lista_definicoes`, boilerplate "Recomendação de padronização" pra UNCERTAIN, e linha de auditoria final.
- **Renderização:** `_render_system_prompt` (`agent.py:204-207`) substitui `{user_name}` e `{user_email}`. ⚠️ **`{data_atual}` é referenciado (`agent.py:191`) mas nunca substituído** — o LLM alucina a data.

## 2) Tools

Tudo bound em `agent.py:242-254` via `langchain.agents.create_agent`.

**In-process** (`agents/qa/tools/`):

| Tool | Path |
|---|---|
| `search_definitions` | `tools/qa_search.py:15-49` |
| `list_projects` | `tools/qa_search.py:52-64` |
| `find_project_by_name` | `tools/qa_search.py:67-83` |
| `register_definition` (factory, bound a user_id) | `tools/qa_search.py:86-150` |
| `get_project_scope` | `tools/get_project_scope.py:14-28` |
| `get_project_scope_history` | `tools/get_project_scope.py:31-41` |
| `get_active_ldp_disciplines` | `tools/get_project_scope.py:44-57` |
| `create_project` (factory, com 3 `interrupt()` LangGraph) | `tools/create_project.py:86-221` |

**MCP Drive** (subprocess stdio, `mcp_client.py:25-78` → `apps/mcp-drive/src/mcp_drive/server.py`):
`list_project_files`, `find_lista_definicoes`, `find_atas`, `find_vof_revisoes`, `find_arquivos_externos`. Carga é best-effort: se o subprocess falhar, agente sobe sem Drive (warning).

## 3) Roteamento

- **LangGraph** via `langchain.agents.create_agent` (helper React-style do LangChain 1.x sobre LangGraph). `agent.py:6`.
- **Sem regex pré-LLM** — `@26002` é resolvido pelo LLM seguindo o prompt. Grep em `agents/` por `re.match`/`@\d+` retornou zero. `scope/parser.py` é só pra parsear orçamento, não mensagens.
- **Fluxo:** Frontend (`apps/web/src/lib/api.ts:15-45`) → `POST /query` → `apps/api/src/oraculo_api/routes/query.py:17-56` (valida JWT, monta `UserContext`, pega `AsyncPostgresSaver` de `app.state` setado em `main.py:25-36`) → `answer_question` (`agent.py:222-302`):
  1. `ChatLiteLLM(settings.llm_model_smart, temperature=0)`
  2. Carrega MCP tools lazy
  3. Rebinda `register_definition`/`create_project` com `user_id`
  4. `create_agent(model, tools, system_prompt, checkpointer)`
  5. Se frontend mandou `project_number`, prefixa `[Projeto fornecido pelo usuário: N]`
  6. `agent.ainvoke(..., config={"configurable": {"thread_id": ...}})` — checkpointer persiste por thread
- `_extract_answer` pega último `AIMessage`; `_extract_citations` (linhas 330-363) só lê `ToolMessage` de `search_definitions` — ⚠️ **outras tools não geram citação**.
- Wrap Langfuse `@observe(as_type="agent", name="qa-agent")` em `agent.py:221`.

## 4) Modelo LLM

- **Anthropic, `claude-sonnet-4-6` (smart) + `claude-haiku-4-5` (fast).** Default em `apps/ai/src/oraculo_ai/core/config.py:20-22`.
- ⚠️ **Drift de configuração:** `.env.example:10-13` e `CLAUDE.md` ainda dizem Groq Llama 3.3 70B. O memory note `feedback_groq_toolstrategy.md` indica que Groq quebra com tool-use. Em produção roda Sonnet.
- **Sem fallback/cascata.** O agente sempre usa `llm_model_smart`. O tier `model_fast` em `llm/client.py:27-30` só é consumido pelo `document_ai/extractor.py` (path antigo), não pelo Thor.
- **Tool binding:** `langchain-litellm.ChatLiteLLM` passado pro `create_agent`. Tools mistas: `@tool` in-process + `BaseTool` via `langchain-mcp-adapters`. `_resolve_api_key` (`agent.py:29-36`) escolhe env var pelo prefixo do modelo.

## 5) Thor chat livre vs create_project

**Mesmo agent loop, mesmo prompt, mesmas tools** — `create_project` é só uma tool a mais (`agent.py:249`). Não existe endpoint separado.

**Mas o frontend bypassa o Thor.** O "+" no menu (`apps/web/src/components/chat/AttachmentMenu.tsx:73-95`) → "Agente → Criar projeto novo" → `onCreateProject` → `flow.start()` (`apps/web/src/features/create-project/hooks/useCreateProjectFlow.ts:167-185`). Isso dispara um **reducer client-side** com steps `awaiting_number_confirmation → awaiting_spreadsheet → parsing_spreadsheet → showing_validation → awaiting_validation_decision → awaiting_metadata → creating → success`, batendo direto em Next.js API routes (`/api/projects/suggest-number`, `/parse-sheet`, `/create`, `/{id}/create-drive-folder`, `/{id}/create-ldp-sheet`) que são proxies finos pra FastAPI.

⚠️ **Dois caminhos paralelos pra criar projeto** que **não compartilham código**:
1. Tool path (LLM escolhe `create_project`, usa `interrupt()` LangGraph nas confirmações)
2. UI path (reducer + Next routes, sem LLM) — provavelmente o usado em produção

## 6) Padrão pra agentes futuros

**Não existe.** `agents/__init__.py` e `agents/qa/__init__.py` são vazios. Não há base class, registry, factory, nem helper compartilhado.

`CLAUDE.md` descreve a estrutura *intencional* (`prompts/`, `tools/`, `graph.py`, `schema.py`), mas `qa/` nem segue isso: tem `agent.py` em vez de `graph.py`, sem pasta `prompts/`, sem exports.

**Adicionar agente novo hoje** = copy-paste de `answer_question`, criar tools em `agents/<name>/tools/`, FastAPI route em `apps/api/src/oraculo_api/routes/`, wire no `main.py`, client no frontend.

**Contexto enviado ao LLM por invocação:** prompt renderizado (~155 linhas) + histórico do `AsyncPostgresSaver` por `thread_id` + mensagem do user (talvez prefixada com `[Projeto fornecido...]`) + 8 schemas de tool in-process + ~5 schemas MCP.

## 7) Dados específicos da Thórus no prompt

**Sim — extensivo.** Encontrado em `agent.py`:

- Persona: "Thor, oráculo técnico da Thórus Engenharia" (linha 39)
- Exemplos de número: `@26002`, `@24021045` (45, 53)
- Exemplos de nome: "Stylo", "João Batista", "Marina" (47)
- Item codes: `PL4`, `ELE03`, `HALL01`, `COZ02`, `ACB02-piso-area-comum` (67, 98, 158)
- Categorias LDP hardcoded: "Hidráulica, Sanitário, Piscina, Elétrico/Comunicação, SPDA, Preventivo, Gás, Sprinkler, Climatização, Geral" (171-172)
- Disciplinas: "HID, ELE" (178)
- Tabelas do banco vazadas no prompt: `projects`, `project_scope`, `definitions`, `scope_to_ldp_discipline` (142, 146, 155, 174)
- Convenções de Drive: "pasta DEFINIÇÕES", `Consulte o Asana.txt`, `Lista de definição - R<XX>`, `03 OBSOLETOS` (122, 132-134)
- Campos de `definitions`: `pergunta`, `disciplina`, `tipo`, `fase`, `status`, `opcao_escolhida`, `registrado_em`, `data_informacao`, `fonte_informacao`, `fonte_descricao` (80, 82-86, 99)
- Vocabulário de status: "Validado", "Em análise" (84, 105)
- ⚠️ **R04 NÃO está no prompt** — vive em `core/config.py:57-58` (`ldp_master_sheet_id`, `ldp_master_tab`), lido pelo `create_project` (`create_project.py:165` → `read_master_r04`)

---

## Oportunidades de refatoração que valem sprint

1. **Prompt-as-data.** 155 linhas inline fazem persona + routing + regras LDP + interpretação Drive + auditoria. Quebrar em arquivos versionados em `agents/qa/prompts/` (como o CLAUDE.md prevê) ou em seções compostas. Hoje não dá pra A/B testar nem hot-swap.
2. **Bug do `{data_atual}`** — referenciado mas nunca substituído. Injetar igual `{user_name}`.
3. **Listas hardcoded** (categorias LDP, disciplinas) deveriam vir de `scope_template`/`scope_to_ldp_discipline` no startup pra evitar drift prompt↔banco.
4. **Drift de config** entre `.env.example`, `CLAUDE.md` e `core/config.py` (Groq vs Anthropic). Decidir e alinhar — o memory note diz que Groq quebra com tool-use.
5. **Sem registry de agentes.** A promessa "agentes plurais desde a Fase 1" não existe em código. Agente #2 será copy-paste.
6. **Dois fluxos divergentes pra create_project** (tool LangGraph vs reducer React). Convergir ou marcar um como deprecated.
7. **Citação só em `search_definitions`** (`agent.py:336`). Resposta usando Drive ou `get_project_scope` quebra a regra "toda resposta cita a fonte".
8. **Sem regex pré-LLM pra `@26002`.** Funciona com Sonnet, mas é carga no prompt e pesadelo de eval. 3 linhas de regex cortariam tokens e uma classe de falhas.
