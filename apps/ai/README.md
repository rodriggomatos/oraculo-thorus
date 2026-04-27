# oraculo-ai

Backend de IA do Oráculo Thórus.

- FastAPI expõe `/query`, `/ingest/{project_id}`, `/events`, `/health`.
- LlamaIndex faz retrieval no pgvector (Supabase).
- LangGraph orquestra os agentes (`agents/qa/` na Fase 1).
- LiteLLM abstrai o provedor de LLM (Groq inicialmente).
- Langfuse rastreia toda chamada de LLM.

Rodar local: `uv sync && uv run uvicorn oraculo_ai.api:app --reload`.
