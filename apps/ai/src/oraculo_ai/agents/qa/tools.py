"""Tools do agente Q&A."""

from langchain_core.tools import tool

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
