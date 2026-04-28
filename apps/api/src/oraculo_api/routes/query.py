"""Endpoint do agente Q&A."""

from uuid import uuid4

from fastapi import APIRouter, Request

from oraculo_ai.agents.qa.agent import answer_question
from oraculo_ai.agents.qa.schema import QAQuery

from oraculo_api.schemas.query import CitationDTO, QueryRequest, QueryResponse


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest) -> QueryResponse:
    thread_id = body.thread_id or str(uuid4())

    qa_query = QAQuery(
        question=body.question,
        project_number=body.project_number,
        top_k=body.top_k,
        thread_id=thread_id,
    )

    checkpointer = request.app.state.checkpointer
    answer = await answer_question(qa_query, checkpointer=checkpointer)

    return QueryResponse(
        answer=answer.answer,
        sources=[
            CitationDTO(
                item_code=src.item_code,
                disciplina=src.disciplina,
                tipo=src.tipo,
                node_id=src.node_id,
                score=src.score,
            )
            for src in answer.sources
        ],
        found_relevant=answer.found_relevant,
        thread_id=thread_id,
    )
