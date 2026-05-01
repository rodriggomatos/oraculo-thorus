"""Pydantic schemas compartilhados entre conectores de ingestão."""

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class Definition(BaseModel):
    id: UUID | None = None
    project_id: UUID
    disciplina: str | None = None
    tipo: str | None = None
    fase: str | None = None
    item_code: str
    pergunta: str
    opcao_escolhida: str | None = None
    status: str | None = None
    custo: str | None = None
    observacoes: str | None = None
    validado: bool | None = None
    informacao_auxiliar: str | None = None
    apoio_1: str | None = None
    apoio_2: str | None = None
    source_sheet_id: str | None = None
    source_row: int | None = None
    raw_data: dict[str, Any] | None = None
    data_informacao: date | None = None
    fonte_informacao: str | None = None
    fonte_descricao: str | None = None
    source_document_id: UUID | None = None


class IngestionStats(BaseModel):
    total_rows: int = 0
    definitions_created: int = 0
    definitions_updated: int = 0
    chunks_created: int = 0
    chunks_updated: int = 0
    chunks_unchanged: int = 0
    embedding_calls: int = 0
