"""Núcleo compartilhado: configuração, schemas globais e cliente Supabase.

Carrega `pydantic-settings` a partir do `.env`, expõe um cliente único de
Postgres (psycopg/asyncpg) e os tipos de domínio usados em todos os módulos
(Project, Definition, Chunk, Citation).
"""
