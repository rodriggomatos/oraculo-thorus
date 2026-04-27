"""Camada HTTP (FastAPI).

Expõe os endpoints públicos do backend de IA: `/query`, `/ingest/{project_id}`,
`/events` e `/health`. Os routers ficam aqui; lógica de negócio mora em
`agents/`, `retrieval/`, `ingestion/`.
"""
