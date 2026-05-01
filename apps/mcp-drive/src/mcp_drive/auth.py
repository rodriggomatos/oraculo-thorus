"""Autenticação via service account + validação de scope READ-ONLY."""

import json
from pathlib import Path

from google.oauth2.service_account import Credentials

from mcp_drive.logging import get_logger


_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_ALLOWED_SCOPE_SUFFIXES = (
    "drive.readonly",
    "drive.metadata.readonly",
    "spreadsheets.readonly",
)

_log = get_logger("auth")


class ScopeViolationError(RuntimeError):
    pass


def load_service_account_credentials(creds_input: str) -> Credentials:
    stripped = creds_input.strip()
    if not stripped:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")

    if stripped.startswith("{"):
        info = json.loads(stripped)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)

    path = Path(stripped)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"service account JSON not found at {path}")
    return Credentials.from_service_account_file(str(path), scopes=_SCOPES)


def validate_readonly_scopes(credentials: Credentials) -> None:
    scopes = list(credentials.scopes or [])
    if not scopes:
        raise ScopeViolationError("credentials carry no scopes")

    for scope in scopes:
        if not _is_scope_allowed(scope):
            raise ScopeViolationError(
                f"non-readonly scope detected: {scope!r}; "
                f"only readonly scopes are allowed"
            )

    _log.info("readonly scopes validated: %s", scopes)


def _is_scope_allowed(scope: str) -> bool:
    return any(scope.endswith(suffix) for suffix in _ALLOWED_SCOPE_SUFFIXES)
