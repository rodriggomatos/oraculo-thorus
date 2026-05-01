"""Parser de PDF — extrai texto plano via pypdf."""

import asyncio
from pathlib import Path

from pypdf import PdfReader


def _extract_text_sync(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    return "\n\n".join(parts)


async def parse(file_path: Path) -> str:
    return await asyncio.to_thread(_extract_text_sync, file_path)
