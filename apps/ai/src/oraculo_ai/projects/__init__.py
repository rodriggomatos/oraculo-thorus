"""Repository de projetos + project_scope versionado."""

from oraculo_ai.projects.repository import (
    ProjectScopeRow,
    create_project_with_scope,
    format_project_name,
    get_active_ldp_disciplines,
    get_definitions_for_project,
    get_next_project_number,
    get_project_drive_state,
    get_project_ldp_state,
    get_project_scope_current,
    get_project_scope_history,
    get_scope_template_names,
    update_drive_folder_path,
    update_ldp_sheets_id,
)

__all__ = [
    "ProjectScopeRow",
    "create_project_with_scope",
    "format_project_name",
    "get_active_ldp_disciplines",
    "get_definitions_for_project",
    "get_next_project_number",
    "get_project_drive_state",
    "get_project_ldp_state",
    "get_project_scope_current",
    "get_project_scope_history",
    "get_scope_template_names",
    "update_drive_folder_path",
    "update_ldp_sheets_id",
]
