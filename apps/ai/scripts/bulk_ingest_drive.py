"""Ingestor de LDP via Google Drive — processa 1 projeto por chamada.

Recebe o ID da pasta do projeto no Drive, descobre o número do projeto pelo nome
da pasta, encontra a planilha .gsheet em locais conhecidos, garante que o
projeto existe no banco e dispara a ingestão via API local.

Uso:
    cd apps/ai
    uv run python scripts/bulk_ingest_drive.py <PROJECT_FOLDER_ID>

Exemplo:
    uv run python scripts/bulk_ingest_drive.py 1sIfCVobILdNBHHMHAIIQlQPXfcsTMPBY
"""

import asyncio
import json
import sys

import httpx

from oraculo_ai.core.config import get_settings
from oraculo_ai.core.db import close_db, init_db
from oraculo_ai.document_ai.drive_scanner import (
    build_drive_service,
    find_gsheet_in_project,
    find_sheet_id_via_link_txt,
    get_folder_metadata,
    get_or_create_project,
    parse_project_folder_name,
)


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


async def _run(project_folder_id: str) -> int:
    print(f"Processando pasta: {project_folder_id}")

    settings = get_settings()
    await init_db(settings.database_url, pool_size=2)

    try:
        service = build_drive_service()

        metadata = await get_folder_metadata(service, project_folder_id)
        folder_name = str(metadata.get("name") or "")
        print(f"Nome da pasta: {folder_name}")

        try:
            project_number, client, full_name = parse_project_folder_name(folder_name)
        except ValueError as exc:
            print(f"ERRO: nome da pasta nao bate o padrao esperado: {exc}")
            return 1

        print(f"  Numero: {project_number}")
        print(f"  Cliente: {client}")
        print(f"  Nome: {full_name}")

        sheet_id = await find_gsheet_in_project(service, project_folder_id)
        if sheet_id is not None:
            print(f"  Sheet ID: {sheet_id}")
        else:
            fallback = await find_sheet_id_via_link_txt(service, project_folder_id)
            if fallback is None:
                print(
                    "SKIP: nenhuma planilha .gsheet nem .txt com link "
                    "encontrada em locais conhecidos."
                )
                return 0
            sheet_id, source_txt = fallback
            print(f"  Sheet ID: {sheet_id} (extraido de {source_txt})")

        project_info = await get_or_create_project(
            project_number=project_number,
            name=full_name,
            client=client,
            google_sheet_id=sheet_id,
        )

        if project_info["created"]:
            print(f"  Projeto criado no banco (id={project_info['id']})")
        else:
            print(f"  Projeto ja existia (id={project_info['id']})")

        print("\nDisparando ingestao via API local (pode levar 30-90s)...")
        async with httpx.AsyncClient(timeout=600.0) as http_client:
            response = await http_client.post(
                "http://localhost:8000/documents/extract-from-sheets",
                json={"project_number": project_number, "sheet_id": sheet_id},
            )
            print(f"Status: {response.status_code}")
            try:
                payload = response.json()
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            except ValueError:
                print(f"Body: {response.text}")

        return 0

    finally:
        await close_db()


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python bulk_ingest_drive.py <PROJECT_FOLDER_ID>")
        return 1
    return asyncio.run(_run(sys.argv[1]))


if __name__ == "__main__":
    sys.exit(main())
