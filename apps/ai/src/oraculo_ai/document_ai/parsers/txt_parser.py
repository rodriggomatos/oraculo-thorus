"""Parser de TXT — leitura direta como texto plano."""

import asyncio
from pathlib import Path


def _read_sync(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="replace")


async def parse(file_path: Path) -> str:
    return await asyncio.to_thread(_read_sync, file_path)
