"""Endpoint de extração de LDP a partir de documentos do cliente."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from oraculo_ai.document_ai.pipeline import ingest_documents_into_ldp
from oraculo_ai.document_ai.sheets_ingester import ingest_from_sheets


router = APIRouter()


class ExtractLDPRequest(BaseModel):
    project_number: int


class ExtractFromSheetsRequest(BaseModel):
    project_number: int
    sheet_id: str
    sheet_tab: str = "Lista de definições"


@router.post("/documents/extract-ldp")
async def extract_ldp(request: ExtractLDPRequest) -> dict:
    try:
        stats = await ingest_documents_into_ldp(request.project_number)
        return stats.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro: {type(e).__name__}: {e}",
        )


@router.post("/documents/extract-from-sheets")
async def extract_from_sheets(request: ExtractFromSheetsRequest) -> dict:
    try:
        stats = await ingest_from_sheets(
            project_number=request.project_number,
            sheet_id=request.sheet_id,
            sheet_tab=request.sheet_tab,
        )
        return stats.model_dump()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro: {type(e).__name__}: {e}",
        )
