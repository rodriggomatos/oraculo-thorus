"""Dispatcher de parsers por extensão de arquivo."""

from pathlib import Path

from oraculo_ai.document_ai.parsers import (
    csv_parser,
    docx_parser,
    pdf_parser,
    txt_parser,
    xlsx_parser,
)


_PARSERS = {
    ".pdf": (pdf_parser.parse, "pdf"),
    ".docx": (docx_parser.parse, "docx"),
    ".xlsx": (xlsx_parser.parse, "xlsx"),
    ".csv": (csv_parser.parse, "csv"),
    ".txt": (txt_parser.parse, "txt"),
}


SUPPORTED_EXTENSIONS: tuple[str, ...] = tuple(_PARSERS.keys())


async def parse_file(file_path: Path) -> tuple[str, str]:
    suffix = file_path.suffix.lower()
    entry = _PARSERS.get(suffix)
    if entry is None:
        raise ValueError(
            f"Formato não suportado: {suffix}. "
            f"Suportados: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    parser_fn, file_format = entry
    content = await parser_fn(file_path)
    return content, file_format
