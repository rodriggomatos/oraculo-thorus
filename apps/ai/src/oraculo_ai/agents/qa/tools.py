"""Tools do agente Q&A."""

from datetime import date

from langchain_core.tools import tool

from oraculo_ai.agents.qa.repository import ProjectRepository
from oraculo_ai.ingestion.google_sheets.pipeline import register_definition_version
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
            "data_informacao": r.metadata.get("data_informacao", ""),
            "fonte_informacao": r.metadata.get("fonte_informacao", ""),
            "fonte_descricao": r.metadata.get("fonte_descricao", ""),
            "registrado_em": r.metadata.get("registrado_em", ""),
        }
        for r in results
    ]


@tool
async def list_projects() -> list[dict]:
    """Lista os 10 projetos ativos mais recentes do sistema. Use quando o usuário não especificar projeto e você precisar mostrar opções."""
    async with ProjectRepository() as repo:
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
    async with ProjectRepository() as repo:
        rows = await repo.search_by_term(term=name_or_term, limit=5)
    return [
        {
            "project_number": int(r["project_number"]),
            "name": str(r["name"]),
            "client": str(r["client"]) if r.get("client") else "",
        }
        for r in rows
    ]


@tool
async def register_definition(
    project_number: int,
    item_code: str,
    pergunta: str,
    opcao_escolhida: str | None,
    disciplina: str | None,
    tipo: str | None,
    fase: str | None,
    status: str | None,
    fonte_informacao: str,
    fonte_descricao: str,
    data_informacao: str | None = None,
) -> str:
    """Registra uma nova versão de definição técnica para o projeto.

    Use quando o usuário informar uma alteração ou nova definição (via chat,
    reunião transcrita, email, etc).

    SEMPRE faz INSERT — nunca UPDATE. Múltiplas versões coexistem no banco;
    a busca futura retorna sempre a mais recente como vigente, mas mantém
    histórico de como evoluiu.

    Antes de chamar esta tool, USE search_definitions pra confirmar:
    - Se o item_code já existe (mudança) ou é novo
    - Se há ambiguidade (múltiplos itens parecidos) → PERGUNTE ao usuário

    Args:
        project_number: Número do projeto (ex: 26002).
        item_code: Código do item (ex: PL4, ELE03).
        pergunta: Texto da pergunta/definição.
        opcao_escolhida: Valor escolhido / decisão atual. None se ainda em aberto.
        disciplina: Disciplina (ex: Hidráulica, Elétrica, Acabamentos).
        tipo: Tipo (ex: Tubulação, Piso, Tomada).
        fase: Fase do projeto.
        status: Status (ex: validado, em análise).
        fonte_informacao: Tipo da fonte ('chat', 'reuniao', 'email', 'documento').
        fonte_descricao: Descrição livre da fonte (ex: 'User informou via chat').
        data_informacao: Data ISO 'YYYY-MM-DD' da informação. Se None, usa hoje.
    """
    parsed_date: date | None = None
    if data_informacao:
        parsed_date = date.fromisoformat(data_informacao)

    result = await register_definition_version(
        project_number=project_number,
        item_code=item_code,
        pergunta=pergunta,
        opcao_escolhida=opcao_escolhida,
        disciplina=disciplina,
        tipo=tipo,
        fase=fase,
        status=status,
        fonte_informacao=fonte_informacao,
        fonte_descricao=fonte_descricao,
        data_informacao=parsed_date,
    )

    return (
        f"Registrado: Item {result['item_code']} = {result['opcao_escolhida']}, "
        f"fonte: {result['fonte_descricao']}, data: {result['data_informacao']}"
    )
