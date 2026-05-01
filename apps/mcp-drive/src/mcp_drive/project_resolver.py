"""Resolve project_number → ProjectFolder pesquisando na Drive raiz, com cache."""

from mcp_drive.backend import FOLDER_MIME, FileBackend, FileNode
from mcp_drive.cache import TTLCache
from mcp_drive.logging import get_logger
from mcp_drive.schemas import ProjectFolder


_log = get_logger("project_resolver")


class ProjectResolver:
    def __init__(
        self,
        backend: FileBackend,
        drive_root_id: str,
        *,
        cache: TTLCache[int, ProjectFolder],
    ) -> None:
        self._backend = backend
        self._drive_root_id = drive_root_id
        self._cache = cache

    async def resolve(self, project_number: int) -> ProjectFolder | None:
        if project_number <= 0:
            return None

        cached = self._cache.get(project_number)
        if cached is not None:
            _log.debug("cache hit for project %s", project_number)
            return cached

        prefix = f"{project_number} - "
        candidates = await self._backend.search(
            name_contains=str(project_number),
            mime_types=[FOLDER_MIME],
        )

        match = _select_best_match(candidates, prefix)
        if match is None:
            _log.info(
                "no project folder found for %s in drive %s",
                project_number,
                self._drive_root_id,
            )
            return None

        folder = ProjectFolder(
            project_number=project_number,
            folder_id=match.id,
            folder_name=match.name,
            web_view_link=match.web_view_link,
        )
        self._cache.set(project_number, folder)
        _log.info("resolved project %s → %s", project_number, match.name)
        return folder


def _select_best_match(candidates: list[FileNode], prefix: str) -> FileNode | None:
    exact_prefix = [c for c in candidates if c.name.startswith(prefix)]
    if exact_prefix:
        if len(exact_prefix) > 1:
            _log.warning(
                "multiple folders match prefix %r; using first by modified_time desc",
                prefix,
            )
            exact_prefix.sort(
                key=lambda n: n.modified_time.timestamp() if n.modified_time else 0.0,
                reverse=True,
            )
        return exact_prefix[0]
    return None
