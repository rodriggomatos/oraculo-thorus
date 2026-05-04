"""Permissões role-based + JSONB extras."""

from oraculo_ai.permissions.check import (
    PermissionDeniedError,
    check_permission,
    requires_permission,
)


__all__ = ["PermissionDeniedError", "check_permission", "requires_permission"]
