"""Registry declarativo de categorias de arquivo Thórus.

Adicionar uma categoria nova = adicionar um `Classifier` no `CLASSIFIERS`.
Tools são genéricas o suficiente pra consumir sem mudança de código.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from mcp_drive.backend import FOLDER_MIME, SPREADSHEET_MIME, TEXT_PLAIN_MIME


CATEGORY_LISTA_DEFINICOES = "lista_definicoes"
CATEGORY_ATA_REUNIAO = "ata_reuniao"
CATEGORY_VOF_REVISAO = "vof_revisao"
CATEGORY_ENTREGA_EXECUTIVO_PDF = "entrega_executivo_pdf"
CATEGORY_ARQUIVO_EXTERNO = "arquivo_externo"


@dataclass(frozen=True)
class Classifier:
    name: str
    path_segments: tuple[tuple[str, ...], ...] = ()
    name_pattern: re.Pattern[str] | None = None
    mime_types: tuple[str, ...] | None = None
    excluded_path_segments: tuple[str, ...] = ()
    description: str = ""


_LISTA_DEFINICOES_PATHS: tuple[tuple[str, ...], ...] = (
    ("02 TRABALHO", "DEFINIÇÕES"),
    ("02 TRABALHO", "DEFINIÇÕES", "Lista de definições"),
    ("DEFINIÇÕES",),
    ("DEFINIÇÕES", "Lista de definições"),
)

_ATA_PATHS: tuple[tuple[str, ...], ...] = (
    ("02 TRABALHO", "DEFINIÇÕES", "Atas de reunião"),
    ("02 TRABALHO", "DEFINIÇÕES", "Atas de reuniao"),
    ("DEFINIÇÕES", "Atas de reunião"),
)

_EXEC_PATHS: tuple[tuple[str, ...], ...] = (
    ("01 ENTREGAS-APROVAÇÕES", "EXECUTIVO"),
)

_EXTERNOS_PATHS: tuple[tuple[str, ...], ...] = (
    ("04 ARQUIVOS EXTERNOS",),
)


CLASSIFIERS: list[Classifier] = [
    Classifier(
        name=CATEGORY_LISTA_DEFINICOES,
        path_segments=_LISTA_DEFINICOES_PATHS,
        mime_types=(SPREADSHEET_MIME, TEXT_PLAIN_MIME),
        description="Planilha de Lista de Definições do Projeto (LDP) ou .txt com link pra ela",
    ),
    Classifier(
        name=CATEGORY_ATA_REUNIAO,
        path_segments=_ATA_PATHS,
        description="Atas de reunião do projeto",
    ),
    Classifier(
        name=CATEGORY_VOF_REVISAO,
        name_pattern=re.compile(r"-VOF-", re.IGNORECASE),
        excluded_path_segments=("03 OBSOLETOS",),
        description="Revisões de VOF (Verificações de Obra/Folha) — fora da pasta OBSOLETOS",
    ),
    Classifier(
        name=CATEGORY_ENTREGA_EXECUTIVO_PDF,
        path_segments=_EXEC_PATHS,
        mime_types=("application/pdf",),
        description="PDFs entregues do projeto executivo, organizados por disciplina",
    ),
    Classifier(
        name=CATEGORY_ARQUIVO_EXTERNO,
        path_segments=_EXTERNOS_PATHS,
        description="Arquivos recebidos de terceiros (arquiteto, estrutural, cliente, etc.)",
    ),
]


CLASSIFIERS_BY_NAME: dict[str, Classifier] = {c.name: c for c in CLASSIFIERS}


_BLACKLIST_FOLDER_NAMES_LITERAL: frozenset[str] = frozenset(
    {"05 MODELOS", "LIMPANDO", "Limpo", "limpando", "limpo", "Nova pasta", "nova pasta"}
)


_BLACKLIST_FOLDER_RE: re.Pattern[str] = re.compile(r"^xx-xx-xx", re.IGNORECASE)

_BLACKLIST_EXTENSIONS: frozenset[str] = frozenset(
    {".rvt", ".bak", ".tmp", ".dwl", ".dwl2"}
)


def is_blacklisted_folder(name: str, *, depth_from_project: int = 0) -> bool:
    if name in _BLACKLIST_FOLDER_NAMES_LITERAL:
        return True
    if name == "05 MODELOS" and depth_from_project > 0:
        return True
    if _BLACKLIST_FOLDER_RE.match(name) is not None:
        return True
    return False


def is_blacklisted_file(name: str) -> bool:
    lower = name.lower()
    return any(lower.endswith(ext) for ext in _BLACKLIST_EXTENSIONS)


def get_classifier(name: str) -> Classifier:
    if name not in CLASSIFIERS_BY_NAME:
        valid = ", ".join(sorted(CLASSIFIERS_BY_NAME))
        raise ValueError(f"unknown category {name!r}; valid: {valid}")
    return CLASSIFIERS_BY_NAME[name]


def list_categories() -> list[str]:
    return [c.name for c in CLASSIFIERS]


@dataclass(frozen=True)
class CategoryMatch:
    classifier: Classifier
    matched_path: tuple[str, ...] = field(default_factory=tuple)


def category_matches_name(classifier: Classifier, name: str) -> bool:
    if classifier.name_pattern is None:
        return True
    return classifier.name_pattern.search(name) is not None


def category_matches_path(classifier: Classifier, path_from_project: Sequence[str]) -> bool:
    if not classifier.path_segments:
        return True
    for required in classifier.path_segments:
        if _path_starts_with(path_from_project, required):
            return True
    return False


def is_excluded_path(
    classifier: Classifier, path_from_project: Sequence[str]
) -> bool:
    if not classifier.excluded_path_segments:
        return False
    return any(seg in path_from_project for seg in classifier.excluded_path_segments)


def _path_starts_with(path: Sequence[str], prefix: Sequence[str]) -> bool:
    if len(path) < len(prefix):
        return False
    return all(path[i] == prefix[i] for i in range(len(prefix)))
