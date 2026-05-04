"""Tools auxiliares pra leitura do escopo contratado, histórico e LDP ativa."""

from typing import Any

from langchain_core.tools import tool

from oraculo_ai.projects import (
    get_active_ldp_disciplines as _get_active_ldp_disciplines_db,
    get_project_scope_current,
    get_project_scope_history as _get_project_scope_history_db,
)


@tool
async def get_project_scope(project_number: int) -> list[dict[str, Any]]:
    """Retorna ESCOPO CONTRATADO atual do projeto: disciplinas, valores, pesos.

    Use quando user pergunta sobre PREÇO, VALOR, ORÇAMENTO, MARGEM, PONTOS,
    DISCIPLINAS CONTRATADAS, "o que foi vendido". NÃO confunde com
    search_definitions (decisões TÉCNICAS de execução).

    Args:
        project_number: Número do projeto (ex: 26002).
    """
    rows = await get_project_scope_current(project_number)
    return [r.to_dict() for r in rows]


@tool
async def get_project_scope_history(project_number: int) -> list[dict[str, Any]]:
    """Retorna histórico de versões do escopo contratado.

    Use quando user pergunta sobre MUDANÇAS, VERSÕES anteriores, "quando alteramos",
    "quem mudou o escopo".

    Args:
        project_number: Número do projeto.
    """
    return await _get_project_scope_history_db(project_number)


@tool
async def get_active_ldp_disciplines(project_number: int) -> list[dict[str, str]]:
    """Retorna as categorias da LDP ativas pro projeto.

    Geral é sempre ativa. Outras categorias só ficam ativas se alguma disciplina
    contratada (project_scope.incluir=TRUE) mapeia pra elas via scope_to_ldp_discipline.

    Use ANTES de filtrar definitions por categoria (HID, ELE, etc.) — assim o agente
    NÃO mostra categorias que não foram contratadas.

    Args:
        project_number: Número do projeto.
    """
    return await _get_active_ldp_disciplines_db(project_number)
