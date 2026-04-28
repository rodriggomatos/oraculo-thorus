"""Cliente Google Sheets — autenticação e leitura."""

import json
from pathlib import Path
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build


_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _load_credentials(creds_input: str) -> Credentials:
    stripped = creds_input.strip()
    if stripped.startswith("{"):
        info = json.loads(stripped)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)

    path = Path(stripped)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"service account JSON not found at {path}")
    return Credentials.from_service_account_file(str(path), scopes=_SCOPES)


def build_sheets_service(creds_input: str) -> Resource:
    creds = _load_credentials(creds_input)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_sheet(
    service: Resource,
    spreadsheet_id: str,
    sheet_name: str,
) -> list[dict[str, str]]:
    result: dict[str, Any] = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueRenderOption="FORMATTED_VALUE",
        )
        .execute()
    )
    values: list[list[str]] = result.get("values", [])
    if not values:
        return []

    headers = [str(h).strip() for h in values[0]]
    width = len(headers)
    rows: list[dict[str, str]] = []
    for raw_row in values[1:]:
        padded: list[str] = list(raw_row) + [""] * (width - len(raw_row))
        row = {headers[i]: str(padded[i]).strip() for i in range(width)}
        rows.append(row)
    return rows
