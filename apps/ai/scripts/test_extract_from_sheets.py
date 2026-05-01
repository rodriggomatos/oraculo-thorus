"""Teste manual do extractor de LDP via Google Sheets.

Uso:
    cd apps/ai
    uv run python scripts/test_extract_from_sheets.py 26009 1acJl65qp93jLFOcdNjskKBh4xegg0Lwynhs4oCM8PeM
"""

import asyncio
import json
import sys

import httpx


async def main(project_number: int, sheet_id: str) -> None:
    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            "http://localhost:8000/documents/extract-from-sheets",
            json={"project_number": project_number, "sheet_id": sheet_id},
        )
        print(f"Status: {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except ValueError:
            print(f"Body: {response.text}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python test_extract_from_sheets.py <project_number> <sheet_id>")
        sys.exit(1)
    asyncio.run(main(int(sys.argv[1]), sys.argv[2]))
