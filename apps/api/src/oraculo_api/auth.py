"""Auth: valida JWT do Supabase, carrega user_profile, expõe Depends(get_current_user)."""

import logging
import time
from typing import Any
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from psycopg.rows import dict_row

from oraculo_ai.core.config import Settings, get_settings
from oraculo_ai.core.db import get_pool


_log = logging.getLogger(__name__)

_JWKS_TTL_SECONDS = 15 * 60
_JWKS_CACHE: dict[str, tuple[dict[str, Any], float]] = {}


class UserContext(BaseModel):
    user_id: UUID
    email: str
    name: str
    role: str
    is_active: bool


def _get_cached_jwks(url: str) -> dict[str, Any] | None:
    entry = _JWKS_CACHE.get(url)
    if entry is None:
        return None
    jwks, expires_at = entry
    if time.monotonic() >= expires_at:
        return None
    return jwks


def _set_cached_jwks(url: str, jwks: dict[str, Any]) -> None:
    _JWKS_CACHE[url] = (jwks, time.monotonic() + _JWKS_TTL_SECONDS)


async def _fetch_jwks(url: str) -> dict[str, Any]:
    cached = _get_cached_jwks(url)
    if cached is not None:
        return cached
    _log.info("jwks: fetching from %s", url)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    _set_cached_jwks(url, payload)
    return payload


async def _decode_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token header: {exc}")

    algorithm = unverified_header.get("alg", "HS256")

    if algorithm == "HS256":
        if not settings.supabase_jwt_secret:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "SUPABASE_JWT_SECRET not configured for HS256 tokens",
            )
        try:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}")

    if algorithm in ("RS256", "ES256"):
        if not settings.supabase_jwks_url:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "SUPABASE_JWKS_URL not configured for asymmetric tokens",
            )
        jwks = await _fetch_jwks(settings.supabase_jwks_url)
        kid = unverified_header.get("kid")
        key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key_data is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"unknown key id: {kid}")
        kty = key_data.get("kty")
        if kty == "EC":
            public_key = jwt.algorithms.ECAlgorithm.from_jwk(key_data)
        elif kty == "RSA":
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
        else:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"unsupported key type: {kty}",
            )
        try:
            return jwt.decode(
                token,
                public_key,
                algorithms=[algorithm],
                audience="authenticated",
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}")

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED, f"unsupported algorithm: {algorithm}"
    )


async def _load_user_profile(user_id: UUID) -> dict[str, Any]:
    pool = get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT id, email, name, role, is_active FROM public.user_profiles WHERE id = %s",
                (str(user_id),),
            )
            row = await cur.fetchone()
    if row is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "user profile not found; sign in again to provision",
        )
    return row


async def get_current_user(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> UserContext:
    if not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing Authorization header")

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization must be Bearer")

    token = authorization.split(None, 1)[1].strip()
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "empty Bearer token")

    claims = await _decode_token(token, settings)

    sub = claims.get("sub")
    email = claims.get("email")
    if not sub or not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token missing sub or email")

    try:
        user_id = UUID(str(sub))
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid sub claim")

    domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
    if domain != settings.allowed_email_domain.lower():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"email domain {domain!r} not allowed",
        )

    profile = await _load_user_profile(user_id)
    if not profile["is_active"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "user is disabled")

    return UserContext(
        user_id=user_id,
        email=str(profile["email"]),
        name=str(profile["name"]),
        role=str(profile["role"]),
        is_active=bool(profile["is_active"]),
    )
