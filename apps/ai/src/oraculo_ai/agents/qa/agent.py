"""Agente Q&A — recupera definições e responde com citações estruturadas."""

import json
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_litellm import ChatLiteLLM
from langfuse import get_client, observe
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from oraculo_ai.agents.qa.schema import Citation, QAAnswer, QAQuery
from oraculo_ai.agents.qa.tools import (
    find_project_by_name,
    list_projects,
    search_definitions,
)
from oraculo_ai.core.config import get_settings


def _resolve_api_key(model: str, settings: Any) -> str | None:
    if model.startswith("anthropic/"):
        return settings.anthropic_api_key
    if model.startswith("groq/"):
        return settings.groq_api_key
    if model.startswith("openai/"):
        return settings.openai_api_key
    return None


_SYSTEM_PROMPT = """Você é o Thor, oráculo técnico da Thórus Engenharia.

Sua função é responder perguntas sobre definições técnicas de projetos da empresa.

FLUXO DE IDENTIFICAÇÃO DE PROJETO (ordem de precedência):

1. PREFIXO @ TEM PRECEDÊNCIA ABSOLUTA: se a pergunta usar '@número' (ex: '@26002', '@24021045'), extraia o número diretamente e use sem chamar tool de resolução. Mesmo se a pergunta também mencionar nome de projeto (ex: 'Stylo @26002'), priorize o '@número'. É uma referência estruturada — zero ambiguidade.

2. NOME DE PROJETO: se a pergunta mencionar projeto por nome (ex: 'Stylo', 'João Batista', 'Marina') sem '@', use find_project_by_name pra resolver o número. Se retornar múltiplos candidatos, mostre as opções e pergunte qual.

3. NÚMERO SEM @: se mencionar número sem prefixo (ex: 'no projeto 26002'), use direto.

4. CONTEXTO DA CONVERSA: se já houver projeto identificado em turno anterior do mesmo chat, reutilize sem perguntar de novo, a menos que o usuário mude explicitamente.

5. SEM PROJETO E SEM CONTEXTO: use list_projects e pergunte ao usuário qual projeto. Sugira sintaxe: "Você pode informar via @número (ex: @26002), pelo nome (ex: Stylo) ou pelo número direto."

CLAREZA DA PERGUNTA:
Se a pergunta for vaga dentro do projeto (ex: 'qual o material?' sem dizer material de quê), peça especificação antes de buscar.

BUSCA:
Use search_definitions APENAS depois de ter projeto identificado E pergunta específica.

RESPOSTA:
- Cite SEMPRE o item_code (ex: PL4, ELE03).
- Se search_definitions não retornar resultados relevantes, responda: 'Não encontrei essa informação na base de definições do projeto. Recomendo verificar com o engenheiro responsável ou consultar a planilha diretamente.'
- NUNCA invente informações.
- Português brasileiro, profissional e direto.
- Destaque 'Opção escolhida' quando houver no chunk.
- Mencione 'Status: Em análise' ou 'Validado: não' quando aplicável."""


_NEGATIVE_PHRASES: tuple[str, ...] = (
    "não encontrei",
    "não há essa informação",
    "não tenho",
    "recomendo verificar com",
)


_checkpointer = InMemorySaver()


@observe(as_type="agent", name="qa-agent")
async def answer_question(
    query: QAQuery,
    checkpointer: BaseCheckpointSaver | None = None,
) -> QAAnswer:
    settings = get_settings()

    llm = ChatLiteLLM(
        model=settings.llm_model_smart,
        temperature=0,
        api_key=_resolve_api_key(settings.llm_model_smart, settings),
    )

    agent = create_agent(
        model=llm,
        tools=[search_definitions, list_projects, find_project_by_name],
        system_prompt=_SYSTEM_PROMPT,
        checkpointer=checkpointer if checkpointer is not None else _checkpointer,
    )

    if query.project_number is not None:
        user_message = (
            f"[Projeto fornecido pelo usuário: {query.project_number}]\n"
            f"{query.question}\n\n"
            f"Use top_k={query.top_k} ao buscar definições."
        )
    else:
        user_message = (
            f"{query.question}\n\n"
            f"Use top_k={query.top_k} ao buscar definições."
        )

    config = {"configurable": {"thread_id": query.thread_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
    )

    answer_text = _extract_answer(result["messages"])
    sources = _extract_citations(result["messages"])
    found_relevant = not _looks_negative(answer_text)

    qa_answer = QAAnswer(
        answer=answer_text,
        sources=sources,
        found_relevant=found_relevant,
    )

    get_client().update_current_span(
        input=query.question,
        output={
            "answer_chars": str(len(qa_answer.answer)),
            "sources_count": str(len(qa_answer.sources)),
            "found_relevant": str(qa_answer.found_relevant),
        },
        metadata={
            "project_number": str(query.project_number) if query.project_number is not None else "none",
            "top_k": str(query.top_k),
            "model": settings.llm_model_smart,
            "thread_id": query.thread_id,
        },
    )

    return qa_answer


def _extract_answer(messages: list[Any]) -> str:
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        content = msg.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text") or block.get("content")
                    if text:
                        parts.append(str(text))
                elif isinstance(block, str):
                    parts.append(block)
            return "\n".join(parts)
    return ""


def _looks_negative(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _NEGATIVE_PHRASES)


def _extract_citations(messages: list[Any]) -> list[Citation]:
    citations: list[Citation] = []
    seen_node_ids: set[str] = set()
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        if getattr(msg, "name", None) != "search_definitions":
            continue
        content = msg.content
        if not isinstance(content, str):
            continue
        try:
            results = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(results, list):
            continue
        for r in results:
            if not isinstance(r, dict):
                continue
            node_id = r.get("node_id")
            if not node_id or node_id in seen_node_ids:
                continue
            seen_node_ids.add(node_id)
            citations.append(
                Citation(
                    item_code=str(r.get("item_code", "")),
                    disciplina=str(r.get("disciplina", "")),
                    tipo=r.get("tipo") or None,
                    node_id=str(node_id),
                    score=float(r.get("score", 0.0)),
                )
            )
    return citations
