"""Tool create_project — cria projeto novo a partir da planilha de orçamento Thórus.

Fluxo (3 interrupts via LangGraph):
  1. interrupt(confirm_number) — confirma número sugerido (max+1)
  2. interrupt(validation_decision) — só quando há errors/warnings
  3. interrupt(collect_metadata) — pega cliente/empreendimento/cidade

Permissão: 'create_project' (admin sempre passa, engineers precisam permissão extra).

DECISÃO DE ARQUITETURA — cache de orçamento parseado:
LangGraph re-executa o node inteiro a cada resume — side-effects ANTES do interrupt
rodam de novo. Pra evitar chamar Sheets API 3x (e pagar latência redundante),
cacheamos o ParsedOrcamento num dict module-level keyed por (thread_id, spreadsheet_id).
Semanticamente equivalente a state-per-thread (efêmero, scoped à conversa, descartável
ao final), mas evita refatorar o state_schema compartilhado do agent.

Idempotência do INSERT: se project_number já existe, retorna o existente (não duplica).
"""

import time
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import interrupt

from oraculo_ai.agents.qa.schema import UserContext
from oraculo_ai.ldp import read_master_r04
from oraculo_ai.permissions import PermissionDeniedError, check_permission
from oraculo_ai.projects.repository import (
    create_project_with_scope,
    format_project_name,
    get_next_project_number,
    get_scope_template_names,
)
from oraculo_ai.scope.parser import parse_orcamento_from_sheets
from oraculo_ai.scope.types import ParsedOrcamento, ValidationResult
from oraculo_ai.scope.validator import validate_against_template


_PARSE_CACHE_TTL_SECONDS = 1800
_parse_cache: dict[tuple[str, str], tuple[ParsedOrcamento, float]] = {}


def _cache_get(thread_id: str, spreadsheet_id: str) -> ParsedOrcamento | None:
    key = (thread_id, spreadsheet_id)
    entry = _parse_cache.get(key)
    if entry is None:
        return None
    parsed, expires_at = entry
    if time.monotonic() >= expires_at:
        _parse_cache.pop(key, None)
        return None
    return parsed


def _cache_set(thread_id: str, spreadsheet_id: str, parsed: ParsedOrcamento) -> None:
    key = (thread_id, spreadsheet_id)
    _parse_cache[key] = (parsed, time.monotonic() + _PARSE_CACHE_TTL_SECONDS)


def _cache_clear(thread_id: str, spreadsheet_id: str) -> None:
    _parse_cache.pop((thread_id, spreadsheet_id), None)


def _extract_thread_id(config: RunnableConfig | None) -> str:
    if config is None:
        return "no-thread"
    configurable = config.get("configurable") or {}
    return str(configurable.get("thread_id") or "no-thread")


async def _parse_with_cache(
    thread_id: str, spreadsheet_id: str
) -> ParsedOrcamento:
    cached = _cache_get(thread_id, spreadsheet_id)
    if cached is not None:
        return cached
    parsed = await parse_orcamento_from_sheets(spreadsheet_id)
    _cache_set(thread_id, spreadsheet_id, parsed)
    return parsed


def make_create_project(user: UserContext) -> Callable[..., Awaitable[Any]]:
    """Cria a tool bound ao user_context atual.

    A factory bind garante que o user_id/role usados na verificação de permissão
    e no INSERT sejam exatamente os do request — não confiando em arg do LLM.
    """

    @tool
    async def create_project(
        spreadsheet_id: str,
        config: RunnableConfig | None = None,
    ) -> dict[str, Any]:
        """Cria projeto novo a partir de planilha de orçamento Google Sheets.

        REQUER PERMISSÃO: 'create_project' (admin ou engineer com permissão extra).

        Args:
            spreadsheet_id: ID do Google Sheets do orçamento (não a URL inteira).

        Fluxo: sugere número → confirma com user → parseia planilha → valida →
        decide sobre warnings → coleta metadados → cria projeto + escopo (atomic).

        Returns dict com status, project_id, project_number, scope_inserted.
        """
        if not check_permission(user, "create_project"):
            return {
                "status": "permission_denied",
                "message": (
                    f"Usuário {user.email} (role={user.role}) não tem permissão "
                    f"pra criar projetos. Peça pra um admin liberar."
                ),
            }

        thread_id = _extract_thread_id(config)

        suggested = await get_next_project_number()
        confirmed_value = interrupt(
            {
                "type": "confirm_number",
                "suggested": suggested,
                "spreadsheet_id": spreadsheet_id,
            }
        )
        confirmed_number = _coerce_number(confirmed_value, suggested)

        try:
            parsed = await _parse_with_cache(thread_id, spreadsheet_id)
        except PermissionError as exc:
            return {
                "status": "spreadsheet_inaccessible",
                "message": str(exc),
            }

        template_names = await get_scope_template_names()
        validation = validate_against_template(parsed, template_names)

        if not validation.ok or validation.warnings:
            decision = interrupt(
                {
                    "type": "validation_decision",
                    "validation": validation.model_dump(mode="json"),
                }
            )
            if not _is_continue(decision):
                _cache_clear(thread_id, spreadsheet_id)
                return {
                    "status": "cancelled_by_user",
                    "validation": validation.model_dump(mode="json"),
                }

        metadata_value = interrupt(
            {
                "type": "collect_metadata",
                "fields": ["cliente", "empreendimento", "cidade"],
            }
        )
        metadata = _coerce_metadata(metadata_value)

        try:
            master_rows = await read_master_r04()
        except PermissionError as exc:
            _cache_clear(thread_id, spreadsheet_id)
            return {
                "status": "spreadsheet_inaccessible",
                "message": str(exc),
            }

        try:
            result = await create_project_with_scope(
                project_number=confirmed_number,
                name=format_project_name(
                    project_number=confirmed_number,
                    client=metadata["cliente"],
                    empreendimento=metadata["empreendimento"],
                    cidade=metadata["cidade"],
                    estado=None,
                ),
                client=metadata["cliente"],
                empreendimento=metadata["empreendimento"],
                cidade=metadata["cidade"],
                estado=None,
                orcamento_sheets_id=spreadsheet_id,
                disciplinas=parsed.disciplinas,
                created_by=user.user_id,
                master_rows=master_rows,
            )
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Falha ao persistir projeto: {type(exc).__name__}: {exc}",
            }
        finally:
            _cache_clear(thread_id, spreadsheet_id)

        if not result.get("created", True):
            return {
                "status": "already_exists",
                "project_id": result["project_id"],
                "project_number": result["project_number"],
                "message": (
                    f"Projeto {result['project_number']} já existia no banco; retornei o ID existente."
                ),
            }

        return {
            "status": "success",
            "project_id": result["project_id"],
            "project_number": result["project_number"],
            "drive_folder_pending": True,
            "scope_inserted": result.get("scope_inserted", 0),
            "scope_skipped": result.get("scope_skipped", []),
            "definitions_count": result.get("definitions_count", 0),
            "definitions_by_discipline": result.get("definitions_by_discipline", {}),
        }

    return create_project


def _coerce_number(value: Any, fallback: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            return int(digits)
    if isinstance(value, dict) and "confirmed_number" in value:
        return _coerce_number(value["confirmed_number"], fallback)
    return fallback


def _is_continue(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"continue", "continuar", "continuar mesmo assim", "ok", "yes", "true"}
    if isinstance(value, dict):
        return _is_continue(value.get("decision") or value.get("action") or "")
    return False


def _coerce_metadata(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {
            "cliente": str(value.get("cliente") or "").strip(),
            "empreendimento": str(value.get("empreendimento") or "").strip(),
            "cidade": str(value.get("cidade") or "").strip(),
        }
    if isinstance(value, str):
        return {"cliente": value.strip(), "empreendimento": "", "cidade": ""}
    return {"cliente": "", "empreendimento": "", "cidade": ""}
