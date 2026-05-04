"""Unit tests pra check_permission e requires_permission."""

import pytest

from oraculo_ai.permissions import (
    PermissionDeniedError,
    check_permission,
    requires_permission,
)


class FakeUser:
    def __init__(self, role: str, permissions: list[str] | None = None) -> None:
        self.role = role
        self.email = f"{role}@thorus.com.br"
        self.permissions = permissions or []


def test_admin_has_every_permission() -> None:
    admin = FakeUser("admin")
    assert check_permission(admin, "create_project")
    assert check_permission(admin, "anything_at_all")


def test_engineer_without_extras_denied() -> None:
    engineer = FakeUser("engineer")
    assert not check_permission(engineer, "create_project")


def test_engineer_with_explicit_permission_passes() -> None:
    engineer = FakeUser("engineer", permissions=["create_project"])
    assert check_permission(engineer, "create_project")


def test_system_role_without_extras_denied() -> None:
    system = FakeUser("system")
    assert not check_permission(system, "create_project")


def test_unknown_role_denied() -> None:
    other = FakeUser("commercial")
    assert not check_permission(other, "create_project")


async def test_decorator_raises_when_missing() -> None:
    @requires_permission("create_project")
    async def fn(*, user: FakeUser) -> str:
        return "ok"

    with pytest.raises(PermissionDeniedError):
        await fn(user=FakeUser("engineer"))


async def test_decorator_passes_when_admin() -> None:
    @requires_permission("create_project")
    async def fn(*, user: FakeUser) -> str:
        return "ok"

    result = await fn(user=FakeUser("admin"))
    assert result == "ok"
