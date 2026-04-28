"""Tools do agente Q&A."""

from langchain_core.tools import tool

from oraculo_ai.agents.qa.repository import ProjectRepository
from oraculo_ai.core.config import get_settings
from oraculo_ai.retrieval.schema import SearchQuery
from oraculo_ai.retrieval.search import search


@tool
async def search_definitions(
    query: str,
    project_number: int,
    top_k: int = 5,
) -> list[dict]:
    """Busca semântica nas definições técnicas do projeto. Use sempre que precisar de informação específica sobre o projeto.

    Args:
        query: Pergunta ou termo a buscar (em português).
        project_number: Número do projeto (ex.: 26002).
        top_k: Quantos resultados retornar (default 5, máx 20).
    """
    results = await search(
        SearchQuery(
            query=query,
            project_number=project_number,
            top_k=top_k,
        )
    )
    return [
        {
            "item_code": r.metadata.get("item_code", ""),
            "content": r.content,
            "score": r.score,
            "node_id": r.node_id,
            "disciplina": r.metadata.get("disciplina", ""),
            "tipo": r.metadata.get("tipo", ""),
        }
        for r in results
    ]


@tool
async def list_projects() -> list[dict]:
    """Lista os 10 projetos ativos mais recentes do sistema. Use quando o usuário não especificar projeto e você precisar mostrar opções."""
    settings = get_settings()
    async with ProjectRepository(settings.database_url) as repo:
        rows = await repo.list_active_recent(limit=10)
    return [
        {
            "project_number": int(r["project_number"]),
            "name": str(r["name"]),
            "client": str(r["client"]) if r.get("client") else "",
        }
        for r in rows
    ]


@tool
async def find_project_by_name(name_or_term: str) -> list[dict]:
    """Busca projeto por nome, cliente ou termo parcial. Use quando o usuário mencionar projeto por nome (ex: 'Stylo', 'João Batista', 'Marina'). Retorna até 5 candidatos.

    Args:
        name_or_term: Nome do projeto, cliente ou termo a buscar.
    """
    settings = get_settings()
    async with ProjectRepository(settings.database_url) as repo:
        rows = await repo.search_by_term(term=name_or_term, limit=5)
    return [
        {
            "project_number": int(r["project_number"]),
            "name": str(r["name"]),
            "client": str(r["client"]) if r.get("client") else "",
        }
        for r in rows
    ]
