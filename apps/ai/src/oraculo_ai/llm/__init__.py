"""Wrapper de LiteLLM.

Único ponto de acesso a LLMs e embeddings no projeto. Nenhum outro módulo
deve importar `anthropic`, `openai` ou `groq` diretamente. Modelo é
configuração (env), não código.
"""
