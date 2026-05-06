"""FastMCP server — registra tools e expõe via stdio."""

from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from mcp_drive.auth import load_service_account_credentials, validate_readonly_scopes
from mcp_drive.backend import GoogleDriveBackend
from mcp_drive.cache import TTLCache
from mcp_drive.classifiers import list_categories
from mcp_drive.config import Settings, get_settings
from mcp_drive.logging import configure_logging, get_logger
from mcp_drive.project_resolver import ProjectResolver
from mcp_drive.schemas import ProjectFolder
from mcp_drive.tools import DriveTools


_log = get_logger("server")


def build_server() -> FastMCP:
    settings: Settings = get_settings()
    configure_logging(settings.mcp_drive_log_level)

    credentials = load_service_account_credentials(settings.google_service_account_json)
    validate_readonly_scopes(credentials)

    backend = GoogleDriveBackend(credentials, drive_id=settings.thorus_drive_root_id)
    folder_cache: TTLCache[int, ProjectFolder] = TTLCache(
        ttl_seconds=settings.mcp_drive_cache_ttl_seconds
    )
    resolver = ProjectResolver(backend, settings.thorus_drive_root_id, cache=folder_cache)
    tools = DriveTools(backend=backend, resolver=resolver)

    mcp = FastMCP(
        "thorus-drive",
        host=settings.mcp_drive_host,
        port=settings.mcp_drive_port,
    )

    _register_tools(mcp, tools)
    _log.info(
        "server ready (drive_root=%s, categories=%s)",
        settings.thorus_drive_root_id,
        list_categories(),
    )
    return mcp


def _register_tools(mcp: FastMCP, tools: DriveTools) -> None:
    @mcp.tool()
    async def list_project_files(
        project_number: int,
        category: str | None = None,
        discipline: str | None = None,
        has_status: str | None = None,
    ) -> dict[str, Any]:
        """Lista arquivos do projeto com filtros opcionais.

        Args:
            project_number: Número do projeto Thórus (ex: 26003).
            category: Categoria específica
                ('lista_definicoes', 'ata_reuniao', 'vof_revisao',
                 'entrega_executivo_pdf', 'arquivo_externo').
                Se omitido, agrega todas.
            discipline: Sigla da disciplina (ELE, HID, PCI, CLI, COM, SDR, SAN, SPDA, FUR, PIS).
            has_status: Filtra por status no nome do arquivo ('TEC OK' ou 'PROJ OK').

        Retorna ToolResult com lista de FileResult (cada um com URL clicável e metadata).
        """
        result = await tools.list_project_files(
            project_number,
            category=category,
            discipline=discipline,
            has_status=has_status,
        )
        return _dump(result)

    @mcp.tool()
    async def find_lista_definicoes(project_number: int) -> dict[str, Any]:
        """Encontra a Lista de Definições do Projeto (LDP) e retorna sua URL.

        Procura primeiro um Google Sheet em '02 TRABALHO/DEFINIÇÕES/'.
        Se não achar, procura um .txt com 'link' no nome e extrai o sheet_id
        do conteúdo.

        Args:
            project_number: Número do projeto Thórus (ex: 26003).
        """
        result = await tools.find_lista_definicoes(project_number)
        return _dump(result)

    @mcp.tool()
    async def find_atas(project_number: int) -> dict[str, Any]:
        """Lista atas de reunião do projeto (em '02 TRABALHO/DEFINIÇÕES/Atas de reunião/').

        Args:
            project_number: Número do projeto Thórus (ex: 26003).
        """
        result = await tools.find_atas(project_number)
        return _dump(result)

    @mcp.tool()
    async def find_vof_revisoes(
        project_number: int,
        discipline: str | None = None,
        only_approved: bool = False,
    ) -> dict[str, Any]:
        """Lista revisões de VOF (arquivos com '-VOF-' no nome, fora da pasta OBSOLETOS).

        Args:
            project_number: Número do projeto Thórus.
            discipline: Sigla da disciplina (ex: 'HID' pra hidráulico).
            only_approved: Se True, só arquivos com '_TEC OK' no nome.
        """
        result = await tools.find_vof_revisoes(
            project_number, discipline=discipline, only_approved=only_approved
        )
        return _dump(result)

    @mcp.tool()
    async def find_arquivos_externos(
        project_number: int,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Lista arquivos recebidos de terceiros em '04 ARQUIVOS EXTERNOS/'.

        Args:
            project_number: Número do projeto Thórus.
            source: Filtro substring no caminho (ex: 'Arquitetônico', 'recebido', 'Estrutural').
        """
        result = await tools.find_arquivos_externos(project_number, source=source)
        return _dump(result)


def _dump(result: BaseModel) -> dict[str, Any]:
    return result.model_dump(mode="json", exclude_none=True)
