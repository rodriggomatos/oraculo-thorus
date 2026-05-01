"""Abstração de filesystem pro MCP server.

`FileBackend` Protocol define a interface mínima. `GoogleDriveBackend` é a
única implementação hoje, mas trocar pra um cache local ou outro provider é
trocar a linha de bootstrap.
"""

import asyncio
import unicodedata
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build
from pydantic import BaseModel, Field

from mcp_drive.logging import get_logger


_log = get_logger("backend")

FOLDER_MIME = "application/vnd.google-apps.folder"
SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
TEXT_PLAIN_MIME = "text/plain"


class FileNode(BaseModel):
    id: str
    name: str
    mime_type: str
    parent_id: str | None = None
    web_view_link: str | None = None
    modified_time: datetime | None = None
    size: int | None = None
    drive_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_folder(self) -> bool:
        return self.mime_type == FOLDER_MIME


class FileBackend(Protocol):
    async def get_node(self, node_id: str) -> FileNode | None: ...

    async def list_children(
        self,
        parent_id: str,
        *,
        mime_types: Sequence[str] | None = None,
        name_contains: str | None = None,
        only_folders: bool = False,
        only_non_folders: bool = False,
    ) -> list[FileNode]: ...

    async def search(
        self,
        *,
        name_contains: str | None = None,
        parent_id: str | None = None,
        mime_types: Sequence[str] | None = None,
    ) -> list[FileNode]: ...

    async def read_text(self, file_id: str) -> str | None: ...


_FILE_FIELDS = (
    "id,name,mimeType,parents,webViewLink,modifiedTime,size,driveId"
)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _to_node(payload: dict[str, Any]) -> FileNode:
    parents = payload.get("parents") or []
    parent_id = parents[0] if parents else None
    modified_time_raw = payload.get("modifiedTime")
    modified_time: datetime | None = None
    if isinstance(modified_time_raw, str):
        try:
            modified_time = datetime.fromisoformat(modified_time_raw.replace("Z", "+00:00"))
        except ValueError:
            modified_time = None
    size_raw = payload.get("size")
    size: int | None
    try:
        size = int(size_raw) if size_raw is not None else None
    except (TypeError, ValueError):
        size = None

    raw_name = str(payload.get("name") or "")
    return FileNode(
        id=str(payload["id"]),
        name=unicodedata.normalize("NFC", raw_name),
        mime_type=str(payload.get("mimeType") or ""),
        parent_id=parent_id,
        web_view_link=payload.get("webViewLink"),
        modified_time=modified_time,
        size=size,
        drive_id=payload.get("driveId"),
        raw=payload,
    )


class GoogleDriveBackend:
    def __init__(self, credentials: Credentials, *, drive_id: str | None = None) -> None:
        self._service: Resource = build(
            "drive", "v3", credentials=credentials, cache_discovery=False
        )
        self._drive_id = drive_id

    async def get_node(self, node_id: str) -> FileNode | None:
        def _call() -> dict[str, Any]:
            return (
                self._service.files()
                .get(fileId=node_id, fields=_FILE_FIELDS, supportsAllDrives=True)
                .execute()
            )

        try:
            payload = await asyncio.to_thread(_call)
        except Exception as exc:
            _log.warning("get_node failed for %s: %s: %s", node_id, type(exc).__name__, exc)
            return None
        return _to_node(payload)

    async def list_children(
        self,
        parent_id: str,
        *,
        mime_types: Sequence[str] | None = None,
        name_contains: str | None = None,
        only_folders: bool = False,
        only_non_folders: bool = False,
    ) -> list[FileNode]:
        clauses = [f"'{_escape(parent_id)}' in parents", "trashed=false"]
        if only_folders:
            clauses.append(f"mimeType='{FOLDER_MIME}'")
        elif only_non_folders:
            clauses.append(f"mimeType!='{FOLDER_MIME}'")
        if mime_types:
            mime_clause = " or ".join(f"mimeType='{_escape(m)}'" for m in mime_types)
            clauses.append(f"({mime_clause})")
        if name_contains:
            clauses.append(f"name contains '{_escape(name_contains)}'")
        query = " and ".join(clauses)
        return await self._list_all(query)

    async def search(
        self,
        *,
        name_contains: str | None = None,
        parent_id: str | None = None,
        mime_types: Sequence[str] | None = None,
    ) -> list[FileNode]:
        clauses: list[str] = ["trashed=false"]
        if parent_id:
            clauses.append(f"'{_escape(parent_id)}' in parents")
        if name_contains:
            clauses.append(f"name contains '{_escape(name_contains)}'")
        if mime_types:
            mime_clause = " or ".join(f"mimeType='{_escape(m)}'" for m in mime_types)
            clauses.append(f"({mime_clause})")
        query = " and ".join(clauses)
        return await self._list_all(query)

    async def read_text(self, file_id: str) -> str | None:
        def _call() -> bytes:
            return (
                self._service.files()
                .get_media(fileId=file_id, supportsAllDrives=True)
                .execute()
            )

        try:
            data = await asyncio.to_thread(_call)
        except Exception as exc:
            _log.warning("read_text failed for %s: %s: %s", file_id, type(exc).__name__, exc)
            return None

        if isinstance(data, bytes):
            return data.decode("utf-8", errors="replace")
        if isinstance(data, str):
            return data
        return None

    async def _list_all(self, query: str, page_size: int = 200) -> list[FileNode]:
        nodes: list[FileNode] = []
        page_token: str | None = None
        while True:
            payload = await self._call_list(query, page_token=page_token, page_size=page_size)
            for raw in payload.get("files", []):
                nodes.append(_to_node(raw))
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        return nodes

    async def _call_list(
        self,
        query: str,
        *,
        page_token: str | None,
        page_size: int,
    ) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            kwargs: dict[str, Any] = dict(
                q=query,
                fields=f"nextPageToken, files({_FILE_FIELDS})",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=page_size,
            )
            if self._drive_id is not None:
                kwargs["corpora"] = "drive"
                kwargs["driveId"] = self._drive_id
            if page_token:
                kwargs["pageToken"] = page_token
            return self._service.files().list(**kwargs).execute()

        return await asyncio.to_thread(_call)
