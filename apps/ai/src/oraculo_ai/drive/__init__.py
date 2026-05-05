"""Operações de escrita no Google Drive (cópia de template, manutenção de pastas)."""

from oraculo_ai.drive.folder_creator import (
    CreateFolderResult,
    DriveFolderAlreadyExistsError,
    DriveTemplateNotAccessibleError,
    copy_project_template,
    folder_url_for,
)

__all__ = [
    "CreateFolderResult",
    "DriveFolderAlreadyExistsError",
    "DriveTemplateNotAccessibleError",
    "copy_project_template",
    "folder_url_for",
]
