"""Parser de CSV — converte pra markdown table."""

import asyncio
import csv
from pathlib import Path


def _cell_to_str(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _extract_markdown_sync(file_path: Path) -> str:
    with open(file_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return ""
    header = [_cell_to_str(c) for c in rows[0]]
    width = len(header)
    lines: list[str] = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * width) + "|")
    for row in rows[1:]:
        padded = list(row) + [""] * (width - len(row))
        cells = [_cell_to_str(c) for c in padded[:width]]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


async def parse(file_path: Path) -> str:
    return await asyncio.to_thread(_extract_markdown_sync, file_path)
