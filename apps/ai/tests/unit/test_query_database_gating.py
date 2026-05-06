"""Confirma que query_database só entra no toolset com permissão.

Este test exercita o contrato `check_permission(user, 'query_database')`:
- admin: True (bypass por role)
- engineer sem permissão extra: False
- engineer com 'query_database' em permissions: True

A integração no agent.py usa exatamente essa lógica pra adicionar (ou
omitir) a tool da lista passada pro create_agent.
"""

from oraculo_ai.permissions import check_permission


class _FakeUser:
    """Mínimo necessário pro check_permission ler role + permissions."""

    def __init__(self, role: str, permissions: list[str] | None = None) -> None:
        self.role = role
        self.email = f"{role}@thorus.com.br"
        self.permissions = permissions or []


def test_admin_has_query_database_access():
    assert check_permission(_FakeUser("admin"), "query_database")


def test_engineer_default_no_query_database_access():
    assert not check_permission(_FakeUser("engineer"), "query_database")


def test_engineer_with_explicit_permission_passes():
    user = _FakeUser("engineer", permissions=["query_database"])
    assert check_permission(user, "query_database")


def test_system_role_no_query_database_access():
    assert not check_permission(_FakeUser("system"), "query_database")


def test_other_permissions_do_not_grant_query_database():
    # Garante que ter create_project não vaza pra query_database.
    user = _FakeUser("engineer", permissions=["create_project"])
    assert not check_permission(user, "query_database")
