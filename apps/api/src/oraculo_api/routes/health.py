"""Health check endpoint."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "oraculo-thorus-api",
        "version": "0.1.0",
    }
