"""Agente Q&A da Fase 1.

Recebe pergunta + project_id, busca chunks relevantes via `retrieval/`,
chama o LLM via `llm/` e devolve resposta + lista de citações
(planilha, aba, linha). Sem citação válida → não responde.
"""
