from collections.abc import Callable
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from account.domain.user import User, UserRole
from account.infra.db.user_postgres_repository import UserPostgresRepository
from shared.domain.exceptions import ForbiddenException, UnauthorizedException
from shared.infra.db.config import settings
from shared.infra.db.database import get_db_session


class AuthContext:
    def __init__(self, user_id: UUID, user: User):
        self.user_id = user_id
        self.user = user


access_token_cookie = APIKeyCookie(
    name=settings.ACCESS_TOKEN_COOKIE,
    scheme_name="sessionCookie",
    description="Sessão criada por POST /auth/login. O browser envia o cookie automaticamente.",
    auto_error=False,
)


def decode_token(token: str, expected_type: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        subject = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise UnauthorizedException("Sessão inválida ou expirada.") from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedException("Sessão inválida ou expirada.")

    return subject


async def _load_user(session: AsyncSession, token: str) -> AuthContext:
    user_id = decode_token(token, "access")
    user = await UserPostgresRepository(session).find_by_id(user_id)
    if user is None:
        raise UnauthorizedException("Sessão inválida ou expirada.")
    return AuthContext(user_id=user_id, user=user)


async def get_current_user(
    access_token: str | None = Depends(access_token_cookie),
    session: AsyncSession = Depends(get_db_session),
) -> AuthContext:
    if not access_token:
        raise UnauthorizedException("Faça login para continuar.")
    return await _load_user(session, access_token)


def require_authenticated(
    auth: AuthContext = Depends(get_current_user),
) -> AuthContext:
    return auth


def require_role(role: UserRole) -> Callable[..., AuthContext]:
    def dependency(auth: AuthContext = Depends(get_current_user)) -> AuthContext:
        if auth.user.role != role:
            raise ForbiddenException(
                "Esta ação não está disponível para o seu perfil.", code="WRONG_ROLE"
            )
        return auth

    return dependency


async def optional_user(
    access_token: str | None = Depends(access_token_cookie),
    session: AsyncSession = Depends(get_db_session),
) -> AuthContext | None:
    if not access_token:
        return None
    try:
        return await _load_user(session, access_token)
    except UnauthorizedException:
        return None
