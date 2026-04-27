"""Busca semântica com filtros (Camada 2 — Cérebro).

Wrapper sobre LlamaIndex + pgvector. Sempre filtra por `project_id` antes da
similaridade, retorna top-K (padrão 20) com metadata pra citação. Reranking
é Fase 2.
"""
