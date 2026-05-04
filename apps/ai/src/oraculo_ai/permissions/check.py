"""Verificação de permissão por role + JSONB extra (user_profiles.permissions).

Roles ativos: 'admin', 'engineer', 'system' (constraint da tabela user_profiles).

- admin: tem TODAS as permissões.
- engineer/system: precisa da permissão listada em user_profiles.permissions.
"""

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Protocol, TypeVar


class _UserLike(Protocol):
    role: str
    permissions: list[str]


class PermissionDeniedError(RuntimeError):
    """Erro levantado quando usuário não tem permissão pra ação solicitada."""

    def __init__(self, user_email: str, required: str) -> None:
        super().__init__(
            f"Usuário {user_email!r} não tem permissão '{required}'"
        )
        self.user_email = user_email
        self.required = required


def check_permission(user: _UserLike, required: str) -> bool:
    """Retorna True se `user` tem a permissão `required`.

    admin sempre passa. Outros roles passam se `required` está em user.permissions.
    """
    if user.role == "admin":
        return True
    extras = user.permissions or []
    return required in extras


F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def requires_permission(required: str) -> Callable[[F], F]:
    """Decorator: levanta PermissionDeniedError se `user` (kwarg) não pode `required`.

    A função decorada precisa receber `user` como kwarg (ou via factory bound).
    """

    def decorator(fn: F) -> F:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("user")
            if user is None:
                raise PermissionDeniedError("(no user)", required)
            if not check_permission(user, required):
                raise PermissionDeniedError(getattr(user, "email", "(no email)"), required)
            return await fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
