"""Agente Q&A — recupera definições e responde com citações estruturadas."""

import json
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import ToolMessage
from langchain_litellm import ChatLiteLLM
from langfuse import get_client, observe
from pydantic import BaseModel

from oraculo_ai.agents.qa.schema import Citation, QAAnswer, QAQuery
from oraculo_ai.agents.qa.tools import search_definitions
from oraculo_ai.core.config import get_settings


_SYSTEM_PROMPT = """Você é o Thor, oráculo técnico da Thórus Engenharia.

Sua função é responder perguntas sobre definições técnicas de projetos da empresa, com base APENAS nas informações que você recupera via a tool `search_definitions`.

Regras inegociáveis:
1. SEMPRE use a tool search_definitions antes de responder. Não responda baseado em conhecimento geral.
2. Se a tool não retornar resultados relevantes (scores baixos ou conteúdo desconexo), responda honestamente: "Não encontrei essa informação na base de definições do projeto. Recomendo verificar com o engenheiro responsável ou consultar a planilha diretamente."
3. NUNCA invente informações ou complete lacunas com suposições.
4. Cite SEMPRE o item_code (ex: PL4, ELE03) ao referenciar uma definição.
5. Responda em português brasileiro, tom profissional e direto.
6. Quando houver "Opção escolhida" no chunk, destaque-a na resposta. É a decisão tomada pelo cliente.
7. Se houver "Status: Em análise" ou "Validado: não", mencione isso — é informação crítica pra engenharia."""


class _AgentOutput(BaseModel):
    answer: str
    found_relevant: bool


@observe(as_type="agent", name="qa-agent")
async def answer_question(query: QAQuery) -> QAAnswer:
    settings = get_settings()

    llm = ChatLiteLLM(
        model=settings.llm_model_smart,
        temperature=0,
        api_key=settings.groq_api_key or None,
    )

    agent = create_agent(
        model=llm,
        tools=[search_definitions],
        system_prompt=_SYSTEM_PROMPT,
        response_format=ToolStrategy(_AgentOutput),
    )

    user_message = (
        f"[Projeto {query.project_number}] {query.question}\n\n"
        f"Use top_k={query.top_k} ao buscar."
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_message}]}
    )

    structured: _AgentOutput = result["structured_response"]
    sources = _extract_citations(result["messages"])

    qa_answer = QAAnswer(
        answer=structured.answer,
        sources=sources,
        found_relevant=structured.found_relevant,
    )

    get_client().update_current_span(
        input=query.question,
        output={
            "answer_chars": str(len(qa_answer.answer)),
            "sources_count": str(len(qa_answer.sources)),
            "found_relevant": str(qa_answer.found_relevant),
        },
        metadata={
            "project_number": str(query.project_number),
            "top_k": str(query.top_k),
            "model": settings.llm_model_smart,
        },
    )

    return qa_answer


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
