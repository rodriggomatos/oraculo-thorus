"""Extração de metadata estruturada do nome do arquivo."""

import re
from datetime import date

from pydantic import BaseModel

from mcp_drive.disciplines import all_discipline_codes


class FileMetadata(BaseModel):
    discipline: str | None = None
    revision: str | None = None
    file_date: date | None = None
    status: str | None = None


_REVISION_RE = re.compile(
    r"(?<![A-Za-z0-9])(R|RV)(\d{2,3})(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_DATE_DDMMYYYY_RE = re.compile(r"\b(\d{2})-(\d{2})-(\d{4})\b")
_DATE_DDMMYY_RE = re.compile(r"\b(\d{2})-(\d{2})-(\d{2})\b")
_STATUS_TEC_RE = re.compile(r"_TEC\s*OK\b", re.IGNORECASE)
_STATUS_PROJ_RE = re.compile(r"_(PROJ|PRO)\s*OK\b", re.IGNORECASE)


def _build_discipline_re() -> re.Pattern[str]:
    codes = sorted(all_discipline_codes(), key=len, reverse=True)
    pattern = r"(?<![A-Z0-9])(" + "|".join(re.escape(c) for c in codes) + r")(?![A-Z0-9])"
    return re.compile(pattern, re.IGNORECASE)


_DISCIPLINE_RE = _build_discipline_re()


def parse_filename(name: str) -> FileMetadata:
    return FileMetadata(
        discipline=_extract_discipline(name),
        revision=_extract_revision(name),
        file_date=_extract_date(name),
        status=_extract_status(name),
    )


def _extract_discipline(name: str) -> str | None:
    match = _DISCIPLINE_RE.search(name)
    if match is None:
        return None
    return match.group(1).upper()


def _extract_revision(name: str) -> str | None:
    match = _REVISION_RE.search(name)
    if match is None:
        return None
    prefix = match.group(1).upper()
    digits = match.group(2)
    return f"{prefix}{digits}"


def _extract_date(name: str) -> date | None:
    full = _DATE_DDMMYYYY_RE.search(name)
    if full is not None:
        try:
            return date(int(full.group(3)), int(full.group(2)), int(full.group(1)))
        except ValueError:
            pass
    short = _DATE_DDMMYY_RE.search(name)
    if short is not None:
        year_short = int(short.group(3))
        year = 2000 + year_short if year_short < 70 else 1900 + year_short
        try:
            return date(year, int(short.group(2)), int(short.group(1)))
        except ValueError:
            return None
    return None


def _extract_status(name: str) -> str | None:
    if _STATUS_TEC_RE.search(name):
        return "TEC OK"
    if _STATUS_PROJ_RE.search(name):
        return "PROJ OK"
    return None
