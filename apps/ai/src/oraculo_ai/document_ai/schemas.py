"""Pydantic schemas do Document AI."""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedDefinition(BaseModel):
    item_code: str
    pergunta_thorus: str
    opcao_escolhida: str | None = None
    observacoes: str | None = None
    informacao_auxiliar_extra: str | None = None
    status: Literal["Em análise", "Validado"] = "Em análise"
    fonte_no_documento: str | None = None
    confidence: Literal["alta", "media", "baixa"]


class ExtractedLDP(BaseModel):
    project_number: int
    items: list[ExtractedDefinition]
    items_not_covered: list[str] = Field(default_factory=list)
    notes: str | None = None


class IngestionStats(BaseModel):
    project_number: int
    files_processed: int = 0
    files_skipped_already_processed: int = 0
    total_thorus_items: int = 0
    items_filled: int = 0
    items_blank: int = 0
    items_high_confidence: int = 0
    items_medium_confidence: int = 0
    items_low_confidence: int = 0
    source_document_ids: list[str] = Field(default_factory=list)


class HeaderMappingResult(BaseModel):
    method: Literal["default_aliases", "llm_assisted"]
    mapping: dict[str, int | None]
    unmapped_headers: list[str]
    llm_cost_estimate_usd: float = 0.0


class SheetsIngestionStats(BaseModel):
    project_number: int
    sheet_id: str
    sheet_tab: str
    rows_total: int = 0
    rows_processed: int = 0
    rows_skipped_empty: int = 0
    rows_skipped_invalid: int = 0
    rows_with_error: int = 0
    errors: list[str] = Field(default_factory=list)
    header_mapping: HeaderMappingResult | None = None
    source_document_id: str | None = None
    skipped_already_processed: bool = False
