"""Classificação tri-state de arquivos da pasta DEFINIÇÕES — FOUND/NOT_FOUND/UNCERTAIN.

Regras de negócio Thórus:

FOUND: arquivo .gsheet/.xlsx/.txt cujo nome menciona 'Lista de definições' (com tolerância
a acento e plural) na pasta DEFINIÇÕES, sem sinais conflitantes.

UNCERTAIN: ou (a) há positivo MAS também sinal de fonte externa ('Consulte o ...'), ou
(b) sem positivo mas há .gsheet sem nome padrão / .txt com 'Consulte o ...' / outros
arquivos sem identificação clara.

NOT_FOUND: pasta DEFINIÇÕES vazia ou inexistente.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field

from mcp_drive.backend import FileNode
from mcp_drive.schemas import LDPResolvedVia, LDPStatus


_GSHEET_MIME = "application/vnd.google-apps.spreadsheet"
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_TXT_MIME = "text/plain"


_LDP_NAME_RE = re.compile(r"\blista\s+de\s+defini(?:cao|coes)\b")
_EXTERNAL_SOURCE_RE = re.compile(r"\bconsulte\s+[oa]\b")


_KIND_PRIORITY: dict[LDPResolvedVia, int] = {
    "gsheet": 0,
    "xlsx": 1,
    "link_txt": 2,
}


@dataclass(frozen=True)
class LDPClassification:
    status: LDPStatus
    primary_match: FileNode | None = None
    primary_kind: LDPResolvedVia | None = None
    positive_matches: list[FileNode] = field(default_factory=list)
    uncertainty_reasons: list[str] = field(default_factory=list)
    all_files: list[FileNode] = field(default_factory=list)


def classify_ldp_files(files: Sequence[FileNode]) -> LDPClassification:
    if not files:
        return LDPClassification(status=LDPStatus.NOT_FOUND)

    file_list = list(files)
    positives: list[tuple[FileNode, LDPResolvedVia]] = []
    external_pointers: list[FileNode] = []
    suspect_gsheets: list[FileNode] = []

    for f in file_list:
        kind = _positive_kind(f)
        if kind is not None:
            positives.append((f, kind))
            continue

        if _has_external_source_marker(f.name):
            external_pointers.append(f)
            continue

        if f.mime_type == _GSHEET_MIME:
            suspect_gsheets.append(f)

    if positives:
        primary = _select_primary(positives)
        positive_files = [p[0] for p in positives]

        if external_pointers:
            reasons = [_external_pointer_reason(f) for f in external_pointers]
            return LDPClassification(
                status=LDPStatus.UNCERTAIN,
                primary_match=primary[0],
                primary_kind=primary[1],
                positive_matches=positive_files,
                uncertainty_reasons=reasons,
                all_files=file_list,
            )

        return LDPClassification(
            status=LDPStatus.FOUND,
            primary_match=primary[0],
            primary_kind=primary[1],
            positive_matches=positive_files,
            uncertainty_reasons=[],
            all_files=file_list,
        )

    reasons: list[str] = []
    for f in suspect_gsheets:
        reasons.append(_suspect_gsheet_reason(f))
    for f in external_pointers:
        reasons.append(_external_pointer_reason(f))

    if not reasons:
        reasons = [
            "pasta DEFINIÇÕES tem arquivos mas nenhum com sinal claro de Lista de Definições",
        ]

    return LDPClassification(
        status=LDPStatus.UNCERTAIN,
        primary_match=None,
        primary_kind=None,
        positive_matches=[],
        uncertainty_reasons=reasons,
        all_files=file_list,
    )


def join_uncertainty_reasons(reasons: Sequence[str]) -> str | None:
    if not reasons:
        return None
    return "; ".join(reasons)


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if not unicodedata.combining(c)
    )


def _normalize_for_match(s: str) -> str:
    return strip_accents(s).lower()


def has_ldp_name_marker(name: str) -> bool:
    return _LDP_NAME_RE.search(_normalize_for_match(name)) is not None


def _has_external_source_marker(name: str) -> bool:
    return _EXTERNAL_SOURCE_RE.search(_normalize_for_match(name)) is not None


def _positive_kind(f: FileNode) -> LDPResolvedVia | None:
    if not has_ldp_name_marker(f.name):
        return None
    if f.mime_type == _GSHEET_MIME:
        return "gsheet"
    if f.mime_type == _XLSX_MIME or f.name.lower().endswith(".xlsx"):
        return "xlsx"
    if f.mime_type == _TXT_MIME or f.name.lower().endswith(".txt"):
        return "link_txt"
    return None


def _select_primary(
    positives: list[tuple[FileNode, LDPResolvedVia]],
) -> tuple[FileNode, LDPResolvedVia]:
    return min(positives, key=lambda p: _KIND_PRIORITY[p[1]])


def _suspect_gsheet_reason(f: FileNode) -> str:
    return f".gsheet '{f.name}' não tem 'Lista de definições' no nome"


def _external_pointer_reason(f: FileNode) -> str:
    return f"sinal de fonte externa: '{f.name}'"
