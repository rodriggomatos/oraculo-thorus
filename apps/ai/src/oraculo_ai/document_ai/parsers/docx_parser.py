"""Parser de DOCX — converte pra markdown via mammoth."""

import asyncio
from pathlib import Path

import mammoth


def _extract_markdown_sync(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        result = mammoth.convert_to_markdown(f)
    return result.value


async def parse(file_path: Path) -> str:
    return await asyncio.to_thread(_extract_markdown_sync, file_path)
