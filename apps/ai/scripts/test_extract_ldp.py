"""Teste manual do extractor de LDP via API HTTP.

Como rodar:
1. Coloque arquivos em C:/oraculo-thorus/incoming/<numero>/
2. Suba a API: cd apps/api && uv run uvicorn oraculo_api.main:app --port 8000
3. Em outro terminal:
       cd apps/ai
       uv run python scripts/test_extract_ldp.py 26008
"""

import asyncio
import sys

import httpx


async def main(project_number: int) -> None:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://localhost:8000/documents/extract-ldp",
            json={"project_number": project_number},
        )
        print(f"Status: {response.status_code}")
        try:
            print(f"Response: {response.json()}")
        except ValueError:
            print(f"Body: {response.text}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python test_extract_ldp.py <project_number>")
        sys.exit(1)
    asyncio.run(main(int(sys.argv[1])))
