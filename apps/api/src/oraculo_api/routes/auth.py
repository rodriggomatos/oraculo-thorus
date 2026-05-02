"""Endpoints de auth: /auth/me retorna o usuário logado."""

from fastapi import APIRouter, Depends

from oraculo_api.auth import UserContext, get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserContext)
async def me(user: UserContext = Depends(get_current_user)) -> UserContext:
    return user
