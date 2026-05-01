"""Tools expostas via MCP — discoveries READ-ONLY no Drive Thórus."""

import re
from collections.abc import Sequence

from mcp_drive.backend import FOLDER_MIME, FileBackend, FileNode
from mcp_drive.classifiers import (
    CATEGORY_ARQUIVO_EXTERNO,
    CATEGORY_ATA_REUNIAO,
    CATEGORY_ENTREGA_EXECUTIVO_PDF,
    CATEGORY_LISTA_DEFINICOES,
    CATEGORY_VOF_REVISAO,
    CLASSIFIERS,
    Classifier,
    category_matches_name,
    get_classifier,
    is_blacklisted_file,
    is_blacklisted_folder,
    is_excluded_path,
)
from mcp_drive.disciplines import discipline_full_name, normalize_discipline
from mcp_drive.ldp_classifier import (
    LDPClassification,
    classify_ldp_files,
    has_ldp_name_marker,
    join_uncertainty_reasons,
    strip_accents,
)
from mcp_drive.logging import get_logger
from mcp_drive.parsing import FileMetadata, parse_filename
from mcp_drive.project_resolver import ProjectResolver
from mcp_drive.schemas import (
    FileResult,
    LDPResolvedVia,
    LDPResult,
    LDPStatus,
    ProjectFolder,
    ToolResult,
)


_log = get_logger("tools")


_SHEET_ID_PATTERN: re.Pattern[str] = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")


_DEFINICOES_PRIMARY_PATHS: tuple[tuple[str, ...], ...] = (
    ("02 TRABALHO", "DEFINIÇÕES"),
    ("DEFINIÇÕES",),
)

_LDP_SUBFOLDER_NAME = "Lista de definições"


class DriveTools:
    def __init__(self, *, backend: FileBackend, resolver: ProjectResolver) -> None:
        self._backend = backend
        self._resolver = resolver

    async def list_project_files(
        self,
        project_number: int,
        *,
        category: str | None = None,
        discipline: str | None = None,
        has_status: str | None = None,
    ) -> ToolResult:
        project = await self._resolver.resolve(project_number)
        if project is None:
            return _not_found(project_number)

        classifiers = self._select_classifiers(category)
        normalized_discipline = normalize_discipline(discipline)
        ldp_strict = category == CATEGORY_LISTA_DEFINICOES
        items: list[FileResult] = []
        for classifier in classifiers:
            files = await self._collect_for_classifier(project, classifier)
            for f in files:
                if normalized_discipline and f.metadata.discipline != normalized_discipline:
                    continue
                if has_status and (f.metadata.status or "").upper() != has_status.upper():
                    continue
                if ldp_strict and not has_ldp_name_marker(f.name):
                    continue
                items.append(f)

        return ToolResult(
            found=True,
            project_number=project_number,
            project_folder_name=project.folder_name,
            project_folder_link=project.web_view_link,
            category=category,
            discipline=discipline_full_name(normalized_discipline) if normalized_discipline else None,
            count=len(items),
            items=items,
        )

    async def find_lista_definicoes(self, project_number: int) -> LDPResult:
        project = await self._resolver.resolve(project_number)
        if project is None:
            return LDPResult(
                status=LDPStatus.NOT_FOUND,
                project_number=project_number,
                note=f"projeto {project_number} não encontrado no Drive raiz",
            )

        candidates, base_path = await self._collect_definicoes_candidates(project)

        if base_path is None:
            return LDPResult(
                status=LDPStatus.NOT_FOUND,
                project_number=project_number,
                project_folder_name=project.folder_name,
                project_folder_link=project.web_view_link,
                note="pasta DEFINIÇÕES não encontrada na estrutura do projeto",
            )

        classification = classify_ldp_files(candidates)

        if classification.status == LDPStatus.NOT_FOUND:
            return LDPResult(
                status=LDPStatus.NOT_FOUND,
                project_number=project_number,
                project_folder_name=project.folder_name,
                project_folder_link=project.web_view_link,
                note="pasta DEFINIÇÕES está vazia",
            )

        if classification.status == LDPStatus.FOUND:
            return await self._build_found_result(
                project, classification, base_path
            )

        return self._build_uncertain_result(project, classification, base_path)

    async def _build_found_result(
        self,
        project: ProjectFolder,
        classification: LDPClassification,
        base_path: list[str],
    ) -> LDPResult:
        primary = classification.primary_match
        kind = classification.primary_kind
        assert primary is not None
        assert kind is not None

        primary_path = self._derive_path(primary, base_path)
        primary_result = _to_file_result(primary, primary_path)

        sheet_id, sheet_url, note = await self._resolve_sheet(primary, kind)

        if sheet_id is None and kind == "link_txt":
            return LDPResult(
                status=LDPStatus.UNCERTAIN,
                project_number=project.project_number,
                project_folder_name=project.folder_name,
                project_folder_link=project.web_view_link,
                items=[primary_result],
                found_files=[
                    _to_file_result(f, self._derive_path(f, base_path))
                    for f in classification.all_files
                ],
                uncertainty_reason=(
                    f"arquivo '{primary.name}' não contém URL de planilha legível"
                ),
            )

        return LDPResult(
            status=LDPStatus.FOUND,
            project_number=project.project_number,
            project_folder_name=project.folder_name,
            project_folder_link=project.web_view_link,
            items=[primary_result],
            sheet_id=sheet_id,
            sheet_url=sheet_url,
            resolved_via=kind,
            note=note,
        )

    def _build_uncertain_result(
        self,
        project: ProjectFolder,
        classification: LDPClassification,
        base_path: list[str],
    ) -> LDPResult:
        positives = [
            _to_file_result(f, self._derive_path(f, base_path))
            for f in classification.positive_matches
        ]
        all_files = [
            _to_file_result(f, self._derive_path(f, base_path))
            for f in classification.all_files
        ]
        return LDPResult(
            status=LDPStatus.UNCERTAIN,
            project_number=project.project_number,
            project_folder_name=project.folder_name,
            project_folder_link=project.web_view_link,
            items=positives,
            found_files=all_files,
            uncertainty_reason=join_uncertainty_reasons(
                classification.uncertainty_reasons
            ),
        )

    async def _resolve_sheet(
        self, primary: FileNode, kind: LDPResolvedVia
    ) -> tuple[str | None, str | None, str | None]:
        if kind == "gsheet" or kind == "xlsx":
            return primary.id, primary.web_view_link, None
        content = await self._backend.read_text(primary.id)
        if not content:
            return None, None, None
        match = _SHEET_ID_PATTERN.search(content)
        if match is None:
            _log.warning("link file %r has no spreadsheet URL", primary.name)
            return None, None, None
        sheet_id = match.group(1)
        return (
            sheet_id,
            f"https://docs.google.com/spreadsheets/d/{sheet_id}",
            f"resolvido via {primary.name}",
        )

    async def _collect_definicoes_candidates(
        self, project: ProjectFolder
    ) -> tuple[list[FileNode], list[str] | None]:
        for path in _DEFINICOES_PRIMARY_PATHS:
            target = await self._descend(project.folder_id, path)
            if target is None:
                continue
            files = await self._list_direct_files(target)

            sub_id = await self._descend_tolerant(target, [_LDP_SUBFOLDER_NAME])
            if sub_id is not None:
                sub_files = await self._list_direct_files(sub_id)
                files.extend(sub_files)

            return _dedupe_nodes(files), list(path)

        return [], None

    async def _list_direct_files(self, folder_id: str) -> list[FileNode]:
        return await self._backend.list_children(folder_id, only_non_folders=True)

    async def _descend_tolerant(
        self, parent_id: str, segments: Sequence[str]
    ) -> str | None:
        current = parent_id
        for segment in segments:
            children = await self._backend.list_children(current, only_folders=True)
            target_norm = strip_accents(segment).lower()
            match = next(
                (c for c in children if strip_accents(c.name).lower() == target_norm),
                None,
            )
            if match is None:
                return None
            current = match.id
        return current

    def _derive_path(self, node: FileNode, base_path: list[str]) -> list[str]:
        return list(base_path)

    async def find_atas(self, project_number: int) -> ToolResult:
        return await self.list_project_files(
            project_number, category=CATEGORY_ATA_REUNIAO
        )

    async def find_vof_revisoes(
        self,
        project_number: int,
        *,
        discipline: str | None = None,
        only_approved: bool = False,
    ) -> ToolResult:
        result = await self.list_project_files(
            project_number,
            category=CATEGORY_VOF_REVISAO,
            discipline=discipline,
            has_status="TEC OK" if only_approved else None,
        )
        return result

    async def find_arquivos_externos(
        self,
        project_number: int,
        *,
        source: str | None = None,
    ) -> ToolResult:
        project = await self._resolver.resolve(project_number)
        if project is None:
            return _not_found(project_number, category=CATEGORY_ARQUIVO_EXTERNO)

        classifier = get_classifier(CATEGORY_ARQUIVO_EXTERNO)
        files = await self._collect_for_classifier(project, classifier)

        if source:
            source_lower = source.lower()
            files = [
                f for f in files
                if any(source_lower in seg.lower() for seg in f.path)
            ]

        return ToolResult(
            found=True,
            project_number=project_number,
            project_folder_name=project.folder_name,
            project_folder_link=project.web_view_link,
            category=CATEGORY_ARQUIVO_EXTERNO,
            count=len(files),
            items=files,
            note=f"source={source!r}" if source else None,
        )

    def _select_classifiers(self, category: str | None) -> list[Classifier]:
        if category is None:
            return list(CLASSIFIERS)
        return [get_classifier(category)]

    async def _collect_for_classifier(
        self, project: ProjectFolder, classifier: Classifier
    ) -> list[FileResult]:
        if classifier.path_segments:
            return await self._collect_by_paths(project, classifier)
        return await self._collect_by_walk(project, classifier)

    async def _collect_by_paths(
        self, project: ProjectFolder, classifier: Classifier
    ) -> list[FileResult]:
        results: list[FileResult] = []
        for path_segments in classifier.path_segments:
            target = await self._descend(project.folder_id, path_segments)
            if target is None:
                continue
            walked = await self._walk(
                target,
                base_path=list(path_segments),
                classifier=classifier,
            )
            results.extend(walked)
        return _dedupe_by_id(results)

    async def _collect_by_walk(
        self, project: ProjectFolder, classifier: Classifier
    ) -> list[FileResult]:
        return await self._walk(project.folder_id, base_path=[], classifier=classifier)

    async def _descend(
        self, parent_id: str, segments: Sequence[str]
    ) -> str | None:
        current = parent_id
        for segment in segments:
            children = await self._backend.list_children(
                current, only_folders=True, name_contains=segment
            )
            match = next((c for c in children if c.name == segment), None)
            if match is None:
                return None
            current = match.id
        return current

    async def _walk(
        self,
        folder_id: str,
        *,
        base_path: list[str],
        classifier: Classifier,
        max_depth: int = 6,
    ) -> list[FileResult]:
        results: list[FileResult] = []

        async def _recurse(node_id: str, path: list[str], depth: int) -> None:
            if depth > max_depth:
                return
            children = await self._backend.list_children(node_id)
            for child in children:
                if child.is_folder:
                    if is_blacklisted_folder(child.name, depth_from_project=len(path)):
                        continue
                    new_path = path + [child.name]
                    if is_excluded_path(classifier, new_path):
                        continue
                    await _recurse(child.id, new_path, depth + 1)
                else:
                    if is_blacklisted_file(child.name):
                        continue
                    if not category_matches_name(classifier, child.name):
                        continue
                    if classifier.mime_types and child.mime_type not in classifier.mime_types:
                        continue
                    results.append(_to_file_result(child, path))

        await _recurse(folder_id, list(base_path), depth=0)
        return results


def _dedupe_by_id(items: list[FileResult]) -> list[FileResult]:
    seen: set[str] = set()
    out: list[FileResult] = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        out.append(item)
    return out


def _dedupe_nodes(nodes: list[FileNode]) -> list[FileNode]:
    seen: set[str] = set()
    out: list[FileNode] = []
    for node in nodes:
        if node.id in seen:
            continue
        seen.add(node.id)
        out.append(node)
    return out


def _to_file_result(node: FileNode, path: list[str]) -> FileResult:
    metadata: FileMetadata = parse_filename(node.name)
    return FileResult(
        id=node.id,
        name=node.name,
        path=list(path),
        web_view_link=node.web_view_link,
        modified_time=node.modified_time,
        mime_type=node.mime_type,
        size=node.size,
        metadata=metadata,
    )


def _not_found(project_number: int, *, category: str | None = None) -> ToolResult:
    return ToolResult(
        found=False,
        project_number=project_number,
        category=category,
        note=f"projeto {project_number} não encontrado no Drive raiz",
    )
