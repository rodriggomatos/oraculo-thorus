"""Repository de projetos + project_scope versionado."""

from oraculo_ai.projects.repository import (
    ProjectScopeRow,
    create_project_with_scope,
    get_active_ldp_disciplines,
    get_next_project_number,
    get_project_scope_current,
    get_project_scope_history,
    get_scope_template_names,
)


__all__ = [
    "ProjectScopeRow",
    "create_project_with_scope",
    "get_active_ldp_disciplines",
    "get_next_project_number",
    "get_project_scope_current",
    "get_project_scope_history",
    "get_scope_template_names",
]
